#!/bin/bash
# Run the ground-first baseline from the paper reproduction.
#
# The experiment generator emits LiftedTCORE, LCC, and ground_tcore results
# together so all methods share identical tasks and plans. This script keeps a
# standalone baseline entry point while using the same artifact contract.
#
# Usage:
#   bash scripts/baseline.sh <name>

set -e

cd /home/user

python method/run_experiments.py --output outputs/method_results.json "$@"
bash scripts/evaluate.sh outputs/method_results.json
