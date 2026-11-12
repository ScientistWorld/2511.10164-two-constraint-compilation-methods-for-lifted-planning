"""Compiler entry point registered with the evaluator.

Usage: python method/compile.py --variant {lifted_tcore,lcc,lifted_tcore_no_omission} IN.json OUT.json

Reads a constrained planning task (JSON, see briefing/evaluation.md) and writes
the constraint-free compiled task.  ``lifted_tcore`` is the paper's Algorithm 1
(with the Section 3.2 omission of R^L(phi,a)=phi updates), ``lcc`` is
Algorithm 2, and ``lifted_tcore_no_omission`` is the ablation that keeps every
regression update (the reproduction's earlier, weaker variant).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.setrecursionlimit(10000)

from planning import compile_lcc, compile_lifted_tcore  # noqa: E402
from pjson import problem_from_json, problem_to_json  # noqa: E402

VARIANTS = {
    "lifted_tcore": lambda p: compile_lifted_tcore(p, omit_unchanged=True),
    "lifted_tcore_no_omission": lambda p: compile_lifted_tcore(p, omit_unchanged=False),
    "lcc": compile_lcc,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    problem = problem_from_json(json.loads(Path(args.input).read_text()))
    compiled = VARIANTS[args.variant](problem)
    Path(args.output).write_text(json.dumps(problem_to_json(compiled), separators=(",", ":")))


if __name__ == "__main__":
    main()
