# Run inside the course container after sourcing /workspace/chipyard/env.sh.
PYTHON ?= python3
STAGES := env reference wrappers baseline dp dp-pipeline dot dot-pipeline pipeline all-hw
.PHONY: $(STAGES) software s7 s7-isa s7-traps s7-build s8 benchmark
$(STAGES):
	$(PYTHON) scripts/verify.py $@ $(if $(SIMULATOR),--simulator $(SIMULATOR),)
software: env reference wrappers
s7:
	$(PYTHON) scripts/verify_s7.py $(if $(FRESH_SIMULATOR),--fresh-simulator $(FRESH_SIMULATOR),)
s7-isa:
	$(PYTHON) scripts/verify_s7.py --part isa
s7-traps:
	$(PYTHON) scripts/verify_s7.py --part traps
s7-build:
	$(PYTHON) scripts/build_s7.py
s8 benchmark:
	$(PYTHON) scripts/benchmark_s8.py $(if $(RESUME),--resume $(RESUME),)
