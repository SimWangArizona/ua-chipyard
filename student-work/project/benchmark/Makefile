CC = cc
CFLAGS = -O2 -std=c11 -Wall -Wextra -Werror -fno-tree-vectorize
CPPFLAGS =
LDFLAGS =
LDLIBS =
SOURCES = benchmark.c dot_bench.c dp_bench.c
EXTRA_SOURCES =
.PHONY: all run clean
all: build/dot_bench build/dp_bench build/integrated_bench
build:
	mkdir -p build
build/dot_bench: $(SOURCES) $(EXTRA_SOURCES) bench.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DDOT_ONLY $(SOURCES) $(EXTRA_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@
build/dp_bench: $(SOURCES) $(EXTRA_SOURCES) bench.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DDP_ONLY $(SOURCES) $(EXTRA_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@
build/integrated_bench: $(SOURCES) $(EXTRA_SOURCES) bench.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SOURCES) $(EXTRA_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@
run: all
	python3 run_benchmarks.py
clean:
	rm -f build/dot_bench build/dp_bench build/integrated_bench
