#!/bin/bash
# Held-out test-slice evaluation entry point. It reads the same method output
# artifact as evaluate_train.sh and, when present, matches the method keys
# already scored in scoring/scores_train.json.

set -e

cd /home/user

mkdir -p scoring

RESULTS="${1:-outputs/method_results.json}"
python eval/test/evaluate.py "$RESULTS" --output scoring/scores_test.json --train-scores scoring/scores_train.json
