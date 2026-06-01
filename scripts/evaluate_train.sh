#!/bin/bash
# Train-slice evaluation entry point. Mirrors scripts/evaluate.sh by reading
# a method-produced result artifact and writing a scoring JSON file.

set -e

cd /home/user

mkdir -p scoring

RESULTS="${1:-outputs/method_results.json}"
python eval/train/evaluate.py "$RESULTS" --output scoring/scores_train.json
