#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

python method/run_experiments.py --output outputs/method_results.json "$@"
bash scripts/evaluate.sh outputs/method_results.json
