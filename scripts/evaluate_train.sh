#!/bin/bash
# Train-slice evaluation: every compiler registered in outputs/compilers/ is
# run on the public train instances; writes scoring/scores_train.json.
set -e
cd /home/user
mkdir -p scoring
python3 eval/train/evaluate.py --output scoring/scores_train.json
