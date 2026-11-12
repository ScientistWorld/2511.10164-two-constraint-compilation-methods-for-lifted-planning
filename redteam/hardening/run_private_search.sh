#!/bin/bash
# Private-search shortcut (prune_attack.py) through the unmodified no-argument
# hidden test, next to the reference; the reference registry is restored after.
set -uo pipefail
cd /home/user
H=redteam/hardening
mkdir -p $H/results
rm -rf outputs/compilers.reference && cp -r outputs/compilers outputs/compilers.reference
rm -rf outputs/compilers && mkdir -p outputs/compilers
cp $H/registry/shortcut_probe_pruning.json $H/registry/lifted_tcore.json outputs/compilers/
bash scripts/evaluate_test.sh > $H/results/test_private_search.log 2>&1; echo "test_private_search rc=$?" | tee -a $H/results/rc.txt
cp scoring/scores_test.json $H/results/scores_test_private_search.json
rm -rf outputs/compilers && mv outputs/compilers.reference outputs/compilers
