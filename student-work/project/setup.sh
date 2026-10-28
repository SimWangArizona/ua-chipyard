#!/usr/bin/env bash
set -euo pipefail
CHIPYARD=${CHIPYARD:-/workspace/chipyard}
PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
bash /workspace/course-scripts/install-course-configs.sh
# Remove only the obsolete link installed by an earlier project setup.
if [[ -L "$CHIPYARD/ece562-tests.sbt" && $(readlink "$CHIPYARD/ece562-tests.sbt") == "$PROJECT/dot/ece562-tests.sbt" ]]; then
    rm "$CHIPYARD/ece562-tests.sbt"
fi
echo "DotRoCCConfig installed. Use make test-hardware for test-only sbt settings."
