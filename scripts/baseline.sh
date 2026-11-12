#!/bin/bash
# Register the ground-first TCORE baseline (baseline/ground_tcore.py) with the evaluator.
# It grounds every action schema before compiling the constraints away and
# refuses tasks whose grounding exceeds its ground-action budget.
#
# Usage: bash scripts/baseline.sh

set -e
cd /home/user
mkdir -p outputs/compilers
cat > outputs/compilers/ground_tcore.json <<'JSON'
{"command": ["python3", "baseline/ground_tcore.py"]}
JSON
echo "registered: ground_tcore"
