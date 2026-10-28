SHELL := /bin/bash
CC := cc
RISCV_PREFIX ?= riscv64-unknown-elf-
CHIPYARD ?= /workspace/chipyard
JOBS ?= 2
JAVA_HEAP_SIZE ?= 3G
TRIALS ?= 3
ROCC_LANES ?= 8
ROCC_ACCUMULATE ?= 1
BUILD := benchmark/build
RESULTS := benchmark/results
BENCH := benchmark/benchmark.c benchmark/dot_bench.c benchmark/dp_bench.c
DOT := dot/dot_rocc.c
HEADERS := benchmark/bench.h dot/dot_rocc.h
WARN := -O2 -std=c11 -Wall -Wextra -Werror -fno-tree-vectorize
DEFINES := -DTRIALS=$(TRIALS) -DROCC_LANES=$(ROCC_LANES) -DROCC_ACCUMULATE=$(ROCC_ACCUMULATE)
# The image ships lp64d runtime libraries only. Kernel/counter code remains
# integer-only so it can execute on the no-FPU BaselineConfig.
RVFLAGS := -march=rv64imafd -mabi=lp64d -mcmodel=medany -specs=htif_nano.specs
RVLINK := -static -T htif.ld
MODE := lanes$(ROCC_LANES)-acc$(ROCC_ACCUMULATE)-trials$(TRIALS)

.PHONY: host verify-host setup test-hardware riscv sim run-rocc run-baseline clean
host: $(BUILD)/host-baseline $(BUILD)/host-model-$(MODE)
$(BUILD) $(RESULTS):
	mkdir -p $@
$(BUILD)/host-baseline: $(BENCH) $(HEADERS) Makefile | $(BUILD)
	$(CC) $(WARN) $(BENCH) -o $@
$(BUILD)/host-model-$(MODE): $(BENCH) $(DOT) $(HEADERS) Makefile | $(BUILD)
	$(CC) $(WARN) $(DEFINES) -DECE562_DOT_ROCC -DECE562_ROCC_MODEL $(BENCH) $(DOT) -o $@
verify-host: host | $(RESULTS)
	$(BUILD)/host-baseline > $(RESULTS)/host_baseline.csv
	python3 benchmark/run_benchmarks.py --csv $(RESULTS)/host_baseline.csv
	$(BUILD)/host-model-$(MODE) > $(RESULTS)/host_model-$(MODE).csv
	python3 benchmark/run_benchmarks.py --trials $(TRIALS) --csv $(RESULTS)/host_model-$(MODE).csv
setup:
	bash setup.sh
test-hardware: setup
	cd $(CHIPYARD) && sbt -J-Xmx$(JAVA_HEAP_SIZE) \
	  'set chipyard / libraryDependencies ++= Seq("edu.berkeley.cs" %% "chiseltest" % "6.0.0" % Test, "org.scalatest" %% "scalatest" % "3.2.19" % Test)' \
	  'set chipyard / Test / unmanagedSourceDirectories += file("/workspace/student-work/project/dot/tests")' \
	  'chipyard/testOnly chipyard.Dot4UnitSpec chipyard.DotRoCCDatapathSpec'
riscv: $(BUILD)/baseline.riscv $(BUILD)/dot-rocc-$(MODE).riscv $(BUILD)/dot-smoke.riscv
$(BUILD)/baseline.riscv: $(BENCH) $(HEADERS) Makefile | $(BUILD)
	$(RISCV_PREFIX)gcc $(WARN) $(RVFLAGS) -DECE562_RISCV_COUNTERS $(BENCH) $(RVLINK) -o $@
$(BUILD)/dot-rocc-$(MODE).riscv: $(BENCH) $(DOT) $(HEADERS) Makefile | $(BUILD)
	$(RISCV_PREFIX)gcc $(WARN) $(RVFLAGS) $(DEFINES) -DECE562_RISCV_COUNTERS -DECE562_DOT_ROCC $(BENCH) $(DOT) $(RVLINK) -o $@
$(BUILD)/dot-smoke.riscv: dot/tests/dot_smoke.c dot/dot_rocc.h Makefile | $(BUILD)
	$(RISCV_PREFIX)gcc $(WARN) $(RVFLAGS) $< $(RVLINK) -o $@
sim: setup
	$(MAKE) -C $(CHIPYARD)/sims/verilator CONFIG=DotRoCCConfig JAVA_HEAP_SIZE=$(JAVA_HEAP_SIZE) -j$(JOBS)
run-rocc: riscv sim | $(RESULTS)
	set -o pipefail; $(CHIPYARD)/sims/verilator/simulator-chipyard.harness-DotRoCCConfig +permissive +loadmem=$(abspath $(BUILD)/dot-smoke.riscv) +max-cycles=1000000 +permissive-off $(abspath $(BUILD)/dot-smoke.riscv) 2>$(RESULTS)/smoke.stderr | tee $(RESULTS)/smoke.log
	python3 benchmark/run_sim.py --simulator $(CHIPYARD)/sims/verilator/simulator-chipyard.harness-DotRoCCConfig --binary $(BUILD)/dot-rocc-$(MODE).riscv --csv $(RESULTS)/rocket-$(MODE).csv --trials $(TRIALS)
run-baseline: $(BUILD)/baseline.riscv | $(RESULTS)
	$(MAKE) -C $(CHIPYARD)/sims/verilator CONFIG=BaselineConfig JAVA_HEAP_SIZE=$(JAVA_HEAP_SIZE) -j$(JOBS)
	python3 benchmark/run_sim.py --simulator $(CHIPYARD)/sims/verilator/simulator-chipyard.harness-BaselineConfig --binary $(BUILD)/baseline.riscv --csv $(RESULTS)/baseline.csv
clean:
	rm -f $(BUILD)/host-baseline $(BUILD)/host-model-* $(BUILD)/baseline.riscv $(BUILD)/dot-rocc-*.riscv $(BUILD)/dot-smoke.riscv
