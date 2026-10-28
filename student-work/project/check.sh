#!/usr/bin/env bash
# Execute inside the course container; all results stay on the host bind mount.
set -eo pipefail
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --software-only ) ]]; then
    echo "Usage: bash check.sh [--software-only]" >&2
    exit 2
fi
source /workspace/chipyard/env.sh
cd /workspace/student-work/project
make verify-host riscv
for lanes in 4 8; do
    for accumulate in 0 1; do
        make verify-host ROCC_LANES="$lanes" ROCC_ACCUMULATE="$accumulate"
        gcc -O1 -g -std=c11 -Wall -Wextra -Werror -fno-pie -no-pie -fsanitize=address,undefined \
            -DECE562_DOT_ROCC -DECE562_ROCC_MODEL -DROCC_LANES="$lanes" \
            -DROCC_ACCUMULATE="$accumulate" dot/tests/adapter_test.c \
            dot/dot_rocc.c benchmark/dot_bench.c -o benchmark/build/adapter_test
        benchmark/build/adapter_test
    done
done
gcc -O2 -std=c11 -Wall -Wextra -Werror dot/dot_ref.c -o benchmark/build/dot_ref
benchmark/build/dot_ref
gcc -O2 -std=c11 -Wall -Wextra -Werror -DECE562_ROCC_MODEL dot/tests/dot_smoke.c -o benchmark/build/smoke_model
benchmark/build/smoke_model
python3 -m unittest discover -s benchmark -p 'test_*.py'
if [[ "${1:-}" != --software-only ]]; then
    make test-hardware
fi
