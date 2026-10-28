"""Run a Chipyard benchmark, retaining raw diagnostics beside validated CSV."""
import argparse
from pathlib import Path
import subprocess
from run_benchmarks import FIELDS, summarize


def extract_csv(stdout):
    header = ",".join(FIELDS)
    lines = stdout.splitlines()
    if lines.count(header) != 1:
        raise ValueError("Simulator output must contain exactly one benchmark header")
    # Verilator, UART and the HTIF program can all write to stdout. Preserve
    # everything in the raw log; accept only the benchmark's defined CSV rows.
    return "\n".join([header] + [line for line in lines
                    if line.startswith(("int8_matmul,", "floyd_warshall,"))]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator",type=Path,required=True)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--csv",type=Path,required=True)
    parser.add_argument("--trials",type=int,default=3)
    parser.add_argument("--max-cycles",type=int,default=200000000)
    args = parser.parse_args()
    args.csv.parent.mkdir(parents=True,exist_ok=True)
    command = [str(args.simulator.resolve()), "+permissive",
               f"+loadmem={args.binary.resolve()}",
               f"+max-cycles={args.max_cycles}", "+permissive-off",str(args.binary.resolve())]
    raw_path = args.csv.with_suffix(".stdout.log")
    with args.csv.with_suffix(".stderr").open("w") as stderr, raw_path.open("w",encoding="utf-8") as raw:
        with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=stderr,text=True) as process:
            for line in process.stdout:
                raw.write(line)
                raw.flush()
                if line.startswith(("int8_matmul,", "floyd_warshall,")):
                    print(line.rstrip(),flush=True)
            returncode = process.wait()
    if returncode:
        raise SystemExit(f"Simulator failed ({returncode}); see raw stdout/stderr logs")
    try:
        text = extract_csv(raw_path.read_text(encoding="utf-8"))
        count, report = summarize(text,args.trials)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    args.csv.write_text(text,encoding="utf-8")
    target = args.csv.with_name(args.csv.stem+"_report.md")
    target.write_text(report,encoding="utf-8")
    print(f"Verified {count} Rocket measurements; CSV: {args.csv}; report: {target}")


if __name__ == "__main__":
    main()
