#!/bin/bash
# End-to-end reproduction of the reference (CPU only, ~5 minutes on 1 core):
#   unit tests of the lifted compilers, registration of LiftedTCORE, LCC and the
#   ground-first TCORE baseline, train-slice and held-out test-slice scoring,
#   and workspace validation.
# The hardening audit (variants and shortcuts) is run separately by
# redteam/hardening/run_hardening.sh followed by redteam/hardening/summarize.py.
set -euo pipefail
cd /home/user

# JOB-ONLY (hardening): private-search audit on the hidden test
mkdir -p outputs/compilers && bash scripts/method.sh >/dev/null && bash redteam/hardening/run_private_search.sh

echo "planning regression tests"
PYTHONPATH=method python3 method/test_planning.py

echo "register compilers"
rm -rf outputs/compilers
bash scripts/method.sh
bash scripts/baseline.sh

echo "train slice"
bash scripts/evaluate_train.sh
echo "held-out test slice"
bash scripts/evaluate_test.sh
cp scoring/scores_train.json scoring/scores.json

python3 validate.py
