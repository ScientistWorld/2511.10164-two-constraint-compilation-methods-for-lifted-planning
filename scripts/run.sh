#!/bin/bash
# Full job: unit tests, hardening audit (all variants/shortcuts through the
# unmodified evaluation entry points), then the reference-only train/test
# scores that ship with the gym, and validation.
set -uo pipefail
cd /home/user
stamp() { echo "[$(date +%H:%M:%S)] $*"; }

stamp "planning regression tests"
PYTHONPATH=method python3 method/test_planning.py || exit 1

stamp "register reference compilers"
rm -rf outputs/compilers
bash scripts/method.sh && bash scripts/baseline.sh || exit 1

stamp "hardening audit"
rm -f redteam/hardening/results/rc.txt
bash redteam/hardening/run_hardening.sh
stamp "hardening audit done"

stamp "reference train slice"
bash scripts/evaluate_train.sh; echo "reference train rc=$?"
stamp "reference test slice"
bash scripts/evaluate_test.sh; echo "reference test rc=$?"
cp scoring/scores_train.json scoring/scores.json

stamp "summaries"
python3 redteam/hardening/summarize.py redteam/hardening/results
python3 validate.py
stamp "done"
