#!/usr/bin/env python3
"""Independent gates; missing hardware is BLOCKED (exit 2), never PASS."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CHIP = Path(os.environ.get("CHIPYARD_ROOT", "/workspace/chipyard"))
ROCKET = CHIP / "generators/rocket-chip"
BASE_REV = "55bcad0f59436de98ea510334121de8546b9e9d7"


class Blocked(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["env", "reference", "wrappers", "baseline", "dp", "dp-pipeline", "dot", "dot-pipeline", "pipeline", "all-hw"])
    parser.add_argument("--simulator", type=Path, help="Explicit matching Verilator simulator")
    parser.add_argument("--timeout", type=int, help="Seconds per command; default 600 for all-hw, 300 otherwise")
    parser.add_argument("--full", action="store_true", help="Use the original large all-hw suite instead of focused integration")
    parser.add_argument("--random-cases", type=int, help="Override randomized case count (recorded in build flags)")
    args = parser.parse_args()
    if args.timeout is None:
        args.timeout = 600 if args.stage == 'all-hw' else 300
    if args.full and args.stage != 'all-hw':
        parser.error('--full is supported only for all-hw')
    if args.random_cases is not None and args.random_cases < 0:
        parser.error("random-cases must be nonnegative")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = ROOT / "results" / (stamp + "-" + args.stage)
    run_dir.mkdir(parents=True)
    log = (run_dir / "run.log").open("w")
    report = {"stage": args.stage, "utc": stamp, "commands": [], "status": "FAIL"}
    source_files = [p for p in ROOT.rglob("*") if p.is_file()
                    and p.relative_to(ROOT).parts[0] not in ("results", "build", "__pycache__")]
    report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in source_files}

    def note(message):
        print(message, flush=True)
        log.write(message + "\n")
        log.flush()

    def run(command, cwd=ROOT):
        command = [str(x) for x in command]
        report["commands"].append(command)
        note("$ " + " ".join(command))
        # File-backed output avoids pipe stalls and exposes live simulator output.
        capture = run_dir / ("command-%03d.log" % len(report["commands"]))
        start = time.monotonic()
        with capture.open("wb") as output, capture.open("r", errors="replace") as reader:
            proc = subprocess.Popen(command,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,
                                    start_new_session=True)
            chunks = []
            try:
                while True:
                    chunk = reader.read()
                    if chunk:
                        chunks.append(chunk)
                        print(chunk,end="",flush=True)
                        log.write(chunk); log.flush()
                    if proc.poll() is not None:
                        chunk = reader.read()
                        if chunk:
                            chunks.append(chunk)
                            print(chunk,end="",flush=True)
                            log.write(chunk); log.flush()
                        break
                    if time.monotonic()-start > args.timeout:
                        raise RuntimeError("command timed out; this is not a passing trap test")
                    time.sleep(0.2)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL)
                        proc.wait()
            if proc.returncode:
                raise RuntimeError("command exited with status " + str(proc.returncode))
            return "".join(chunks)

    def tool(name):
        if not shutil.which(name):
            raise Blocked("missing tool: " + name + "; source /workspace/chipyard/env.sh first")

    def cross(source, output, defines=(), object_only=False, cpp=False, optimization="-O2"):
        compiler = "riscv64-unknown-elf-g++" if cpp else "riscv64-unknown-elf-gcc"
        tool(compiler)
        command = [compiler, "-std=gnu++11" if cpp else "-std=gnu99", optimization,
                   "-Wall", "-Wextra", "-Werror", "-march=rv64imafd", "-mabi=lp64d",
                   "-mcmodel=medany", "-I", ROOT / "include"]
        command += list(defines)
        if cpp:
            command += ["-x", "c++"]
        if object_only:
            command += ["-c"]
        else:
            command += ["-specs=htif_nano.specs", "-static", "-T", "htif.ld"]
        sources = [source] if isinstance(source,str) else source
        run(command + [ROOT / "tests" / name for name in sources] + ["-o", output])

    def check_encodings(obj):
        dump = run(["riscv64-unknown-elf-objdump", "-d", obj])
        obj.with_suffix(".dump").write_text(dump)
        # Read constants from the one authoritative header, not a duplicated opcode table.
        header = (ROOT / "include/fg_encoding.h").read_text()
        constants = {name: int(value, 0) for name, value in
                     re.findall(r"^#define (FG_\w+) (0x[0-9a-fA-F]+|[0-9]+)$", header, re.M)}
        blocks = re.split(r"^[0-9a-f]+ <([^>]+)>:\s*$", dump, flags=re.M)
        functions = dict(zip(blocks[1::2], blocks[2::2]))
        for name, fn in (("probe_dot", "FG_DOT_FUNCT7"), ("probe_max", "FG_MAX_FUNCT7"),
                         ("probe_min", "FG_MIN_FUNCT7")):
            words = [int(x,16) for x in re.findall(r"^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s", functions.get(name,""), re.M)]
            custom = [w for w in words if w & 127 == constants["FG_OPCODE"]]
            if len(custom) != 1:
                raise RuntimeError(name + ": expected exactly one custom instruction")
            word = custom[0]
            if (word >> 25 != constants[fn] or (word >> 12) & 7 != constants["FG_FUNCT3"]
                    or not ((word >> 7) & 31) or not ((word >> 15) & 31) or not ((word >> 20) & 31)):
                raise RuntimeError(name + ": incorrect fields or zero source/destination register")
        note("Encoding fields verified for all three wrapper probes")

    try:
        if ROCKET.is_dir():
            report["rocket_revision"] = run(["git", "rev-parse", "HEAD"], ROCKET).strip()
            report["rocket_status"] = run(["git", "status", "--short"], ROCKET).strip()
            diff = run(["git", "diff", "--stat"], ROCKET)
            report["rocket_diff_stat"] = diff
            # Preserve tracked changes as evidence; status also identifies untracked files.
            patch = subprocess.check_output(["git", "diff", "HEAD"], cwd=ROCKET)
            (run_dir / "rocket-working.patch").write_bytes(patch)
        if args.stage == "env":
            if not ROCKET.is_dir():
                raise Blocked("Rocket source directory missing")
            for name in ("gcc", "g++", "make", "riscv64-unknown-elf-gcc",
                         "riscv64-unknown-elf-g++", "riscv64-unknown-elf-objdump", "verilator", "java"):
                tool(name)
                run([name, "-version" if name == "java" else "--version"])
            if report["rocket_revision"] != BASE_REV:
                raise Blocked("Rocket revision differs from inspected baseline; review compatibility")
            for name in ("ALU.scala","IDecode.scala","RocketCore.scala","CustomInstructions.scala"):
                if not (ROCKET / "src/main/scala/rocket" / name).is_file():
                    raise Blocked("missing Rocket file " + name)
            alu = (ROCKET / "src/main/scala/rocket/ALU.scala").read_text()
            report["alu_function_definitions"] = re.findall(r"def FN_\w+\s*=\s*\d+\.U", alu)
            note("Environment inspection passed; simulator execution is a separate gate")
        elif args.stage == "reference":
            for cpp in (False, True):
                for opt in ("-O0", "-O2"):
                    compiler = "g++" if cpp else "gcc"
                    tool(compiler)
                    exe = run_dir / (compiler.replace("+","p") + opt)
                    run([compiler, "-x", "c++" if cpp else "c", "-std=c++11" if cpp else "-std=c99",
                         opt, "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                         "-fno-sanitize-recover=all", "-I", ROOT / "include",
                         ROOT / "tests/test_arithmetic.c", "-o", exe])
                    if "FG PASS reference" not in run([exe]):
                        raise RuntimeError("reference PASS marker missing")
        elif args.stage == "wrappers":
            tool("riscv64-unknown-elf-objdump")
            for cpp in (False, True):
                for opt in ("-O0", "-O2"):
                    obj = run_dir / (("cpp" if cpp else "c") + opt + ".o")
                    cross("encoding_probe.c",obj,object_only=True,cpp=cpp,optimization=opt)
                    # At O0 the inline wrapper is out-of-line; inspect the O2 probe itself.
                    if opt == "-O2":
                        check_encodings(obj)
            for kind, defs in (("baseline",[]),("dp",["-DFG_HARDWARE","-DFG_TEST_DOT=0"]),
                               ("dot",["-DFG_HARDWARE","-DFG_TEST_DP=0"]),
                               ("all",["-DFG_HARDWARE"])):
                cross("test_arithmetic.c",run_dir/(kind+".riscv"),defs)
            cross("test_pipeline.c",run_dir/"pipeline.riscv")
            cross("test_dp.c",run_dir/"dp-focused.riscv")
            cross("test_dot.c",run_dir/"dot-focused.riscv")
            cross("test_pipeline.c",run_dir/"dot-pipeline.riscv",["-DFG_TEST_DP=0"])
            note("Cross-build and encoding checks only; no custom instruction executed")
        else:
            configs = {"baseline":"BaselineConfig", "dp":"FineGrainedDPConfig",
                       "dp-pipeline":"FineGrainedDPConfig",
                       "dot-pipeline":"FineGrainedDotConfig",
                       "dot":"FineGrainedDotConfig", "pipeline":"FineGrainedConfig", "all-hw":"FineGrainedConfig"}
            sim = (args.simulator or CHIP / "sims/verilator" /
                   ("simulator-chipyard.harness-"+configs[args.stage])).resolve()
            if not sim.is_file():
                raise Blocked("simulator missing: " + str(sim) + "; implement/build the matching configuration first")
            report["simulator"] = str(sim)
            report["simulator_sha256"] = hashlib.sha256(sim.read_bytes()).hexdigest()
            binary = run_dir / (args.stage+".riscv")
            defs = [] if args.stage == "baseline" else ["-DFG_HARDWARE"]
            if args.stage == "dp": defs += ["-DFG_TEST_DOT=0"]
            if args.stage == "dp-pipeline": defs += ["-DFG_TEST_DOT=0"]
            if args.stage == "dot": defs += ["-DFG_TEST_DP=0"]
            if args.stage == "dot-pipeline": defs += ["-DFG_TEST_DP=0"]
            source = "test_pipeline.c" if args.stage in ("pipeline","dp-pipeline","dot-pipeline") else "test_arithmetic.c"
            if args.stage == "dp": source = "test_dp.c"
            if args.stage == "dot": source = "test_dot.c"
            if args.stage == 'all-hw' and not args.full:
                source = ['test_all.c','test_dot.c','test_dp.c']
                defs += ['-DFG_COMBINED']
                note('S6 focused integration: both real-instruction suites in one combined-core process')
            if args.random_cases is not None: defs += ["-DFG_RANDOM_CASES=" + str(args.random_cases)]
            cross(source,binary,defs)
            marker = {"baseline":"reference","dp":"hardware-dp","dot":"hardware-dot",
                      "dp-pipeline":"dp-pipeline",
                      "dot-pipeline":"dot-pipeline",
                      "all-hw":"hardware-all","pipeline":"pipeline"}[args.stage]
            if "FG PASS " + marker not in run([sim,binary]):
                raise RuntimeError("expected simulator PASS marker missing")
        report["status"] = "PASS"
        code = 0
    except KeyboardInterrupt:
        report.update(status="INTERRUPTED",reason="Stopped by user; no PASS claimed")
        code = 130
    except Blocked as exc:
        report.update(status="BLOCKED", reason=str(exc))
        code = 2
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        report.update(status="FAIL", reason=str(exc))
        code = 1
    note(report["status"] + ": " + args.stage + " " + report.get("reason", ""))
    (run_dir / "result.json").write_text(json.dumps(report,indent=2)+"\n")
    note("Evidence: " + str(run_dir))
    log.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
