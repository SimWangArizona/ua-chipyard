#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-BaselineConfig}"

SIM="/workspace/chipyard/sims/verilator/simulator-chipyard.harness-${CONFIG}"
BENCH="/workspace/output/isp_bench.riscv"

if [[ ! -x "$SIM" ]]; then
    echo "Error: simulator not found for config: $CONFIG"
    exit 1
fi

if [[ ! -f "$BENCH" ]]; then
    echo "Error: benchmark binary not found: $BENCH"
    exit 1
fi

echo "Running ISP benchmark on ${CONFIG}..."
exec "$SIM" "$BENCH"
