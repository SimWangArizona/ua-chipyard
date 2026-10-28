"""Check that a truncated or corrupt capture cannot produce a passing report."""
import csv
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from run_benchmarks import FIELDS, summarize
from run_sim import extract_csv


def capture(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output,fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(zip(FIELDS,["int8_matmul",str(n),impl,str(t),"host","PASS","","","","100","42"]))
                     for n in (1,4,7,8,16,32) for impl in ("baseline","rocc_model") for t in (1,2,3)]

    def test_complete_host(self):
        self.assertEqual(summarize(capture(self.rows))[0],36)

    def test_simulator_diagnostics(self):
        raw = "[UART] UART0 is here\n" + capture(self.rows) + "- TestDriver.v:158: Verilog $finish\n"
        self.assertEqual(summarize(extract_csv(raw))[0],36)
        with self.assertRaises(ValueError): extract_csv(raw+capture(self.rows))

    @unittest.skipUnless(os.name == "posix", "The Chipyard runner executes Linux simulators")
    def test_runner_retains_logs_and_rejects_failed_process(self):
        rows = [dict(r,platform="rocket_rv64",cycles="200",instructions="100",cpi="2.000000",host_elapsed_ns="",
                     implementation="rocc" if r["implementation"] == "rocc_model" else "baseline") for r in self.rows]
        raw = "[UART] startup\n"+capture(rows)+"- TestDriver.v:158: Verilog $finish\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            simulator = root/"simulator"
            binary = root/"test.riscv"
            binary.touch()
            for code in (0,3):
                simulator.write_text("#!/usr/bin/env python3\nimport sys\nsys.stdout.write("+repr(raw)+")\nsys.exit("+str(code)+")\n",encoding="utf-8")
                simulator.chmod(0o755)
                target = root/f"capture-{code}.csv"
                result = subprocess.run([sys.executable,str(Path(__file__).with_name("run_sim.py")),
                                         "--simulator",str(simulator),"--binary",str(binary),"--csv",str(target)],
                                        capture_output=True,text=True)
                self.assertTrue(target.with_suffix(".stdout.log").exists())
                self.assertTrue(target.with_suffix(".stderr").exists())
                self.assertEqual(target.exists(),code == 0)
                self.assertEqual(result.returncode == 0,code == 0)
                if code == 0: self.assertEqual(summarize(target.read_text())[0],36)

    def test_complete_hardware(self):
        for row in self.rows:
            row.update(platform="rocket_rv64",implementation="rocc" if row["implementation"] == "rocc_model" else "baseline",
                       cycles="200",instructions="100",cpi="2.000000",host_elapsed_ns="")
        self.assertEqual(summarize(capture(self.rows))[0],36)

    def test_corruption(self):
        cases = []
        cases.append(self.rows[:-1])
        cases.append(self.rows+self.rows[:1])
        cases.append([r for r in self.rows if r["size"] != "32"])
        cases.append([r for r in self.rows if r["implementation"] != "baseline"])
        for field,value in (("status","FAIL"),("checksum","43"),("cycles","10")):
            rows = [dict(r) for r in self.rows]
            rows[-1][field] = value
            cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows[-1]):
                with self.assertRaises(ValueError): summarize(capture(rows))


if __name__ == "__main__":
    unittest.main()
