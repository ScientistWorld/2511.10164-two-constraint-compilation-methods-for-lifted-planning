#!/bin/bash
# Hardening audit: run every variant and shortcut through the unmodified,
# no-argument evaluation entry points, then restore the reference registry.
#   1. all registrations in redteam/hardening/registry/ -> outputs/compilers/
#      a misleading scoring/scores_train.json is planted first: the test must
#      ignore it (earlier train-registration shortcut)
#   2. empty registry (earlier empty-results shortcut)
set -uo pipefail
cd /home/user
H=redteam/hardening
mkdir -p $H/results
rm -rf outputs/compilers.reference && cp -r outputs/compilers outputs/compilers.reference

rm -rf outputs/compilers && mkdir -p outputs/compilers && cp $H/registry/*.json outputs/compilers/
echo '{"experiments": {"ground_constraints_size": {"results": {"lifted_tcore": {}}}}}' > scoring/scores_train.json
bash scripts/evaluate_test.sh > $H/results/test_all.log 2>&1; echo "test_all rc=$?" | tee -a $H/results/rc.txt
cp scoring/scores_test.json $H/results/scores_test_all.json
bash scripts/evaluate_train.sh > $H/results/train_all.log 2>&1; echo "train_all rc=$?" | tee -a $H/results/rc.txt
cp scoring/scores_train.json $H/results/scores_train_all.json

rm -rf outputs/compilers && mkdir -p outputs/compilers
rm -f scoring/scores_test.json
bash scripts/evaluate_test.sh > $H/results/test_empty.log 2>&1; echo "test_empty rc=$?" | tee -a $H/results/rc.txt
cp scoring/scores_test.json $H/results/scores_test_empty.json

rm -rf outputs/compilers && mv outputs/compilers.reference outputs/compilers
