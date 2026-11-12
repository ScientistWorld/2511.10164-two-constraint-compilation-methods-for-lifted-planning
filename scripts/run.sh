#!/bin/bash
# Example job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -euo pipefail

cd /home/user

echo "Running planning compiler regression tests"
PYTHONPATH=method python method/test_planning.py

echo "Regenerating full reproduction artifacts"
bash scripts/reproduce.sh

echo "Checking paper-scale high-arity grounding benchmark"
python - <<'PY'
import json
from pathlib import Path

scores = json.loads(Path("scoring/scores.json").read_text())
ground_actions = scores["experiments"]["ground_constraints_size"]["results"]["ground_tcore"]["actions"]
nonground_actions = scores["experiments"]["nonground_constraints_size"]["results"]["ground_tcore"]["actions"]
if ground_actions < 20_000 or nonground_actions < 20_000:
    raise SystemExit(
        "Expected 28-object size benchmarks to generate at least 20K "
        f"ground actions; got ground={ground_actions}, nonground={nonground_actions}."
    )
print(f"ground_tcore action counts: ground={ground_actions}, nonground={nonground_actions}")
PY

echo "Running train/test scoring slices"
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh

echo "Validating scoring structure and paper comparison"
python validate.py --compare
