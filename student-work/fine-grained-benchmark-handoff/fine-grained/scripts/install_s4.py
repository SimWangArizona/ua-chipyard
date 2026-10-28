#!/usr/bin/env python3
"""Install the reproducible S4 patch/config. Refuse unrelated Rocket changes."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ROCKET = Path('/workspace/chipyard/generators/rocket-chip')
REV = '55bcad0f59436de98ea510334121de8546b9e9d7'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROCKET)


def replace_once(content, old, new):
    if content.count(old) != 1:
        raise RuntimeError('Source anchor must match once: ' + old[:80])
    return content.replace(old, new, 1)


def main():
    if git('rev-parse', 'HEAD').decode().strip() != REV:
        raise SystemExit('Unsupported Rocket revision; no sources changed')
    patch = ROOT / 'rocket-chip.patch'
    if patch.exists():
        applied = subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=ROCKET,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0
        if applied:
            if git('diff','HEAD') != patch.read_bytes():
                raise SystemExit('Patch present with additional changes; inspect manually')
            print('S4 patch already installed')
        else:
            if git('status','--porcelain').strip():
                raise SystemExit('Rocket is dirty; no patch applied')
            subprocess.run(['git','apply','--check',str(patch)],cwd=ROCKET,check=True)
            subprocess.run(['git','apply',str(patch)],cwd=ROCKET,check=True)
            print('Applied saved S4 patch')
    else:
        if git('status','--porcelain').strip():
            raise SystemExit('Rocket is dirty; no sources changed')
        folder = ROCKET / 'src/main/scala/rocket'
        originals = {name:(folder/name).read_text() for name in
                     ['ALU.scala','CustomInstructions.scala','IDecode.scala','RocketCore.scala']}
        changes = dict(originals)
        changes['ALU.scala'] = replace_once(changes['ALU.scala'],
            '  def FN_BEXT = 19.U\n',
            '  def FN_BEXT = 19.U\n  def FN_FG_ADD_MAX = 22.U\n  def FN_FG_ADD_MIN = 23.U\n')
        changes['ALU.scala'] = replace_once(changes['ALU.scala'],
            '  val out = MuxLookup(io.fn, shift_logic_cond)(Seq(\n',
            '''  // Packed native DP: in1 = {c32, a32}, in2.low32 = b32.
  // Use a dedicated 32-bit sum: packed c must not participate in arithmetic.
  val useFineGrainedDP = coreParams match {
    case r: RocketCoreParams => r.useFineGrainedDP
    case _ => false
  }
  val fineGrainedDPResults = if (useFineGrainedDP) {
    require(xLen == 64, "Native packed DP requires RV64")
    val sum32 = Wire(UInt(32.W))
    sum32 := io.in1(31,0) + io.in2(31,0)
    val c32 = io.in1(63,32)
    val sumLess = sum32.asSInt < c32.asSInt
    val max32 = Mux(sumLess, c32, sum32)
    val min32 = Mux(sumLess, sum32, c32)
    Seq(
      FN_FG_ADD_MAX -> Cat(Fill(32, max32(31)), max32),
      FN_FG_ADD_MIN -> Cat(Fill(32, min32(31)), min32)
    )
  } else Nil

  val out = MuxLookup(io.fn, shift_logic_cond)(Seq(
''')
        changes['ALU.scala'] = replace_once(changes['ALU.scala'],
            '  ) else Nil))\n', '  ) else Nil) ++ fineGrainedDPResults)\n')
        patterns = '\n'.join('  def FG_ADD_' + name + ' = BitPat("b' + format(fn,'07b') +
                             '??????????000?????0001011")' for name,fn in [('MAX',2),('MIN',3)])
        changes['CustomInstructions.scala'] = replace_once(changes['CustomInstructions.scala'],
            'object CustomInstructions {\n',
            'object CustomInstructions {\n  // Fine-grained native DP, custom-0, two integer sources.\n' + patterns + '\n')
        changes['IDecode.scala'] = replace_once(changes['IDecode.scala'],
            'class ConditionalZeroDecode(implicit val p: Parameters) extends DecodeConstants\n',
            '''class FineGrainedDPDecode(implicit val p: Parameters) extends DecodeConstants
{
  val table: Array[(BitPat, List[BitPat])] = Array(
    FG_ADD_MAX-> List(Y,N,N,N,N,N,Y,Y,A2_RS2,A1_RS1,IMM_X,DW_XPR,FN_FG_ADD_MAX,N,M_X,N,N,N,N,N,N,Y,CSR.N,N,N,N,N),
    FG_ADD_MIN-> List(Y,N,N,N,N,N,Y,Y,A2_RS2,A1_RS1,IMM_X,DW_XPR,FN_FG_ADD_MIN,N,M_X,N,N,N,N,N,N,Y,CSR.N,N,N,N,N))
}

class ConditionalZeroDecode(implicit val p: Parameters) extends DecodeConstants
''')
        changes['RocketCore.scala'] = replace_once(changes['RocketCore.scala'],
            '  useConditionalZero: Boolean = false,\n',
            '  useConditionalZero: Boolean = false,\n  useFineGrainedDP: Boolean = false,\n')
        changes['RocketCore.scala'] = replace_once(changes['RocketCore.scala'],
            '    (usingConditionalZero.option(new ConditionalZeroDecode)) ++:\n',
            '    (usingConditionalZero.option(new ConditionalZeroDecode)) ++:\n' +
            '    (rocketParams.useFineGrainedDP.option(new FineGrainedDPDecode)) ++:\n')
        changes['RocketCore.scala'] = replace_once(changes['RocketCore.scala'],
            '  require(decodeWidth == 1 /* TODO */ && retireWidth == decodeWidth)\n',
            '''  require(decodeWidth == 1 /* TODO */ && retireWidth == decodeWidth)
  require(!rocketParams.useFineGrainedDP || xLen == 64, "Native packed DP requires RV64")
  require(!(usingRoCC && rocketParams.useFineGrainedDP), "Native DP overlaps RoCC custom decode")
''')
        # Compute every edit before touching any source file.
        for name,content in changes.items():
            (folder/name).write_text(content)
        subprocess.run(['git','diff','--check'],cwd=ROCKET,check=True)
        patch.write_bytes(git('diff','HEAD'))
        print('Created and saved S4 patch:',patch)
    # Check the saved patch on clean base files without resetting this tree.
    names = ['ALU.scala','CustomInstructions.scala','IDecode.scala','RocketCore.scala']
    with tempfile.TemporaryDirectory(prefix='fg-s4-patch-check-') as check_dir:
        clean = Path(check_dir)
        for name in names:
            relative = 'src/main/scala/rocket/' + name
            target = clean/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(git('show',REV+':'+relative))
        subprocess.run(['git','apply','--check',str(patch)],cwd=clean,check=True)
        subprocess.run(['git','apply',str(patch)],cwd=clean,check=True)
        for name in names:
            relative = 'src/main/scala/rocket/' + name
            if (clean/relative).read_bytes() != (ROCKET/relative).read_bytes():
                raise SystemExit('Saved patch differs from installed source: ' + name)
    print('Saved patch clean-base application and source equality: PASS')
    destination = Path('/workspace/chipyard/generators/chipyard/src/main/scala/config/FineGrainedConfig.scala')
    source = ROOT/'FineGrainedConfig.scala'
    if destination.is_symlink() and destination.resolve() == source.resolve():
        print('Student configuration already linked')
    elif destination.exists() or destination.is_symlink():
        raise SystemExit('Configuration destination occupied; not overwritten')
    else:
        destination.symlink_to(source)
        print('Linked student configuration:',destination)
    print(git('diff','--stat').decode())


if __name__ == '__main__':
    main()
