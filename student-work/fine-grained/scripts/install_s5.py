#!/usr/bin/env python3
"""Upgrade verified S4 sources to S5; persist a cumulative clean-base patch."""
from pathlib import Path
import subprocess
import install_s4

ROOT = Path(__file__).resolve().parents[1]


def main():
    install_s4.main()  # Apply the current saved patch, check revision and dirty state.
    folder = install_s4.ROCKET/'src/main/scala/rocket'
    files = {name:(folder/name).read_text() for name in
             ['ALU.scala','CustomInstructions.scala','IDecode.scala','RocketCore.scala']}
    if 'useFineGrainedDot: Boolean = false' in files['RocketCore.scala']:
        print('S5 cumulative patch already installed')
        return
    edit = install_s4.replace_once
    files['ALU.scala'] = edit(files['ALU.scala'],
        '  def FN_FG_ADD_MAX = 22.U\n',
        '  def FN_FG_DOT4_ACC = 21.U\n  def FN_FG_ADD_MAX = 22.U\n')
    files['ALU.scala'] = edit(files['ALU.scala'],
        '  val out = MuxLookup(io.fn, shift_logic_cond)(Seq(\n',
        '''  // Four signed INT8 lanes; accumulation wraps only at the final 32 bits.
  val useFineGrainedDot = coreParams match {
    case r: RocketCoreParams => r.useFineGrainedDot
    case _ => false
  }
  val fineGrainedDotResults = if (useFineGrainedDot) {
    require(xLen == 64, "Native packed dot requires RV64")
    val products = (0 until 4).map { i =>
      val a = io.in1(8*i+7, 8*i).asSInt
      val b = io.in2(8*i+7, 8*i).asSInt
      a * b // 16-bit signed product
    }
    val pair01 = products(0) +& products(1) // 17 bits
    val pair23 = products(2) +& products(3) // 17 bits
    val dot18 = pair01 +& pair23 // 18 bits, includes +65536
    val accumulated = io.in1(63,32).asSInt +& dot18 // 33 bits
    val result32 = accumulated.asUInt(31,0)
    Seq(FN_FG_DOT4_ACC -> Cat(Fill(32, result32(31)), result32))
  } else Nil

  val out = MuxLookup(io.fn, shift_logic_cond)(Seq(
''')
    files['ALU.scala'] = edit(files['ALU.scala'],
        '  ) else Nil) ++ fineGrainedDPResults)\n',
        '  ) else Nil) ++ fineGrainedDPResults ++ fineGrainedDotResults)\n')
    files['CustomInstructions.scala'] = edit(files['CustomInstructions.scala'],
        'object CustomInstructions {\n',
        'object CustomInstructions {\n  def FG_DOT4_ACC = BitPat("b0000001??????????000?????0001011")\n')
    files['IDecode.scala'] = edit(files['IDecode.scala'],
        'class FineGrainedDPDecode(implicit val p: Parameters) extends DecodeConstants\n',
        '''class FineGrainedDotDecode(implicit val p: Parameters) extends DecodeConstants
{
  val table: Array[(BitPat, List[BitPat])] = Array(
    FG_DOT4_ACC-> List(Y,N,N,N,N,N,Y,Y,A2_RS2,A1_RS1,IMM_X,DW_XPR,FN_FG_DOT4_ACC,N,M_X,N,N,N,N,N,N,Y,CSR.N,N,N,N,N))
}

class FineGrainedDPDecode(implicit val p: Parameters) extends DecodeConstants
''')
    files['RocketCore.scala'] = edit(files['RocketCore.scala'],
        '  useFineGrainedDP: Boolean = false,\n',
        '  useFineGrainedDP: Boolean = false,\n  useFineGrainedDot: Boolean = false,\n')
    files['RocketCore.scala'] = edit(files['RocketCore.scala'],
        '    (rocketParams.useFineGrainedDP.option(new FineGrainedDPDecode)) ++:\n',
        '    (rocketParams.useFineGrainedDP.option(new FineGrainedDPDecode)) ++:\n' +
        '    (rocketParams.useFineGrainedDot.option(new FineGrainedDotDecode)) ++:\n')
    files['RocketCore.scala'] = edit(files['RocketCore.scala'],
        '  require(!(usingRoCC && rocketParams.useFineGrainedDP), "Native DP overlaps RoCC custom decode")\n',
        '''  require(!(usingRoCC && rocketParams.useFineGrainedDP), "Native DP overlaps RoCC custom decode")
  require(!rocketParams.useFineGrainedDot || xLen == 64, "Native packed dot requires RV64")
  require(!(usingRoCC && rocketParams.useFineGrainedDot), "Native dot overlaps RoCC custom decode")
''')
    patch = ROOT/'rocket-chip.patch'
    backup = ROOT/'patches/s4.patch'
    backup.parent.mkdir(exist_ok=True)
    if backup.exists() and backup.read_bytes() != patch.read_bytes():
        raise SystemExit('Existing S4 backup differs; refusing overwrite')
    backup.write_bytes(patch.read_bytes())
    # All anchors checked before changing the container source.
    for name,content in files.items():
        (folder/name).write_text(content)
    subprocess.run(['git','diff','--check'],cwd=install_s4.ROCKET,check=True)
    patch.write_bytes(install_s4.git('diff','HEAD'))
    install_s4.main()  # Verify cumulative patch applies to clean base and matches sources.
    print('S5 dot source and cumulative S4+S5 patch installed')


if __name__=='__main__':
    main()
