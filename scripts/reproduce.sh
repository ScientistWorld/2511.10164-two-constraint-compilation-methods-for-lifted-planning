#!/bin/bash
# Reproduce the paper's comparison end-to-end: register LiftedTCORE, LCC and
# the ground-first TCORE baseline, then score them (scoring/scores.json).
set -e
cd /home/user
bash scripts/method.sh
bash scripts/baseline.sh
bash scripts/evaluate.sh
