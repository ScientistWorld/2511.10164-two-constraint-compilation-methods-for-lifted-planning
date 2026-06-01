from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def ratio(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def score_compile_size(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        out[method] = {
            "actions": item["actions"],
            "effects": item["effects"],
            "formula_atoms": item["formula_atoms"],
            "compile_seconds": item["compile_seconds"],
            "plan_valid_rate": 1.0 if item["plan_valid"] else 0.0,
        }
    out["lifted_tcore"]["action_ratio_vs_ground"] = ratio(out["lifted_tcore"]["actions"], out["ground_tcore"]["actions"])
    out["lcc"]["action_ratio_vs_ground"] = ratio(out["lcc"]["actions"], out["ground_tcore"]["actions"])
    out["ground_tcore"]["action_ratio_vs_ground"] = 1.0
    return out


def score_semantics(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        out[method] = {
            "valid_plan_accepted": 1.0 if item["valid_plan_accepted"] else 0.0,
            "invalid_plan_rejected": 1.0 if item["invalid_plan_rejected"] else 0.0,
            "actions": item["actions"],
            "effects": item["effects"],
            "compile_seconds": item["compile_seconds"],
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="?", default="outputs/method_results.json")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    raw = json.loads(Path(args.results).read_text())
    scores = {
        "experiments": {
            "ground_constraints_size": {"results": score_compile_size(raw["ground_constraints_size"])},
            "nonground_constraints_size": {"results": score_compile_size(raw["nonground_constraints_size"])},
            "constraint_semantics": {"results": score_semantics(raw["constraint_semantics"])},
        }
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(json.dumps(scores, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
