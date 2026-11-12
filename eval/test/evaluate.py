"""Held-out test evaluation.

Runs every compiler registered in ``outputs/compilers/*.json`` on held-out
instances that are generated here, in memory, at test time, and writes
``scoring/scores_test.json``.  Every number is recomputed from the compiled
tasks; counterexamples are not reported so the held-out instances stay hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_lib  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=str(test_lib.ROOT / "outputs" / "compilers"))
    parser.add_argument("--output", default=str(test_lib.ROOT / "scoring" / "scores_test.json"))
    args = parser.parse_args()
    started = time.time()
    scores = test_lib.score_all(Path(args.registry), verbose=False, log=lambda m: print(m, flush=True))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(f"wrote {out} in {time.time() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
