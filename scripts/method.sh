#!/bin/bash
# Register the paper's two compilers (LiftedTCORE, LCC) with the evaluator.
#
# A "method" in this gym is a compiler command: the evaluator appends
# <input.json> <output.json> and runs it once per constrained task.  Each
# registration is outputs/compilers/<method_name>.json = {"command": [...]}.
#
# Usage: bash scripts/method.sh

set -e
cd /home/user
mkdir -p outputs/compilers
cat > outputs/compilers/lifted_tcore.json <<'JSON'
{"command": ["python3", "method/compile.py", "--variant", "lifted_tcore"]}
JSON
cat > outputs/compilers/lcc.json <<'JSON'
{"command": ["python3", "method/compile.py", "--variant", "lcc"]}
JSON
echo "registered: lifted_tcore lcc"
