"""Summarise the hardening run: ranks, paired per-instance comparisons, determinism.

Usage: python redteam/hardening/summarize.py [results_dir]
Writes <results_dir>/summary.json and prints a markdown table.

Rank (as specified for this gym): for each experiment e and scored metric k,
weight_e * |coef_k| * (improvement of the method over the reference in k's
better direction) / spread_k, summed.  spread_k is the population standard
deviation of k across the attempts being ranked; zero-spread terms add 0.
Population A = every attempt in the hidden-test file; population P = the
reference and the one attempt only.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = "lifted_tcore"


def load(p):
    return json.loads(Path(p).read_text())


def terms(scores, reference):
    out = []
    for exp, spec in reference["experiments"].items():
        res = scores["experiments"].get(exp, {}).get("results", {})
        for k, m in spec["metrics"].items():
            if m.get("coefficient", 0) == 0:
                continue
            out.append((exp, k, spec["weight"] * abs(m["coefficient"]), 1 if m["higher_is_better"] else -1, res))
    return out


def rank(scores, reference, method, population):
    total = 0.0
    for exp, k, w, sign, res in terms(scores, reference):
        if method not in res or REF not in res or k not in res[method]:
            continue
        vals = [res[m][k] for m in population if m in res and k in res[m]]
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        if sd == 0:
            continue
        total += w * sign * (res[method][k] - res[REF][k]) / sd
    return total


def paired(scores, method):
    meta = scores["_metadata"]["methods"]
    if meta.get(method, {}).get("status") != "ok" or meta.get(REF, {}).get("status") != "ok":
        return None
    names = ["effects_vs_ground_log10", "actions_vs_ground_log10", "formula_nodes_log10", "max_formula_nodes_log10"]
    out = {}
    for exp, d in meta[REF]["diagnostics"].items():
        a = d["per_instance"]
        b = meta[method]["diagnostics"][exp]["per_instance"]
        for j, name in enumerate(names):
            diffs = [y[j] - x[j] for x, y in zip(a, b)]  # method - reference (lower is better for all four)
            n = len(diffs)
            mean = sum(diffs) / n
            se = statistics.stdev(diffs) / math.sqrt(n) if n > 1 else 0.0
            out[f"{exp}/{name}"] = {"n": n, "mean_diff": mean, "se": se,
                                    "t": (mean / se) if se > 0 else (0.0 if mean == 0 else math.copysign(math.inf, mean)),
                                    "better": sum(1 for x in diffs if x < -1e-12), "worse": sum(1 for x in diffs if x > 1e-12)}
    return out


def main():
    res_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "redteam/hardening/results"
    reference = load(ROOT / "scoring/reference.json")
    summary = {}
    for split in ("test", "train"):
        path = res_dir / f"scores_{split}_all.json"
        if not path.exists():
            continue
        scores = load(path)
        methods = sorted(scores["_metadata"]["methods"])
        rows = {}
        for m in methods:
            rows[m] = {
                "status": scores["_metadata"]["methods"][m]["status"],
                "reason": scores["_metadata"]["methods"][m].get("reason"),
                "rank_population_A": rank(scores, reference, m, methods),
                "rank_pair_P": rank(scores, reference, m, [REF, m]),
            }
        summary[split] = {"ranks": rows,
                          "paired_vs_reference": {m: paired(scores, m) for m in methods if m != REF},
                          "metrics": {exp: v["results"] for exp, v in scores["experiments"].items()}}
        print(f"\n### {split}\n\n| attempt | status | rank A | rank P |\n|---|---|---:|---:|")
        for m, r in sorted(rows.items(), key=lambda kv: -kv[1]["rank_population_A"]):
            print(f"| {m} | {r['status']} | {r['rank_population_A']:+.4f} | {r['rank_pair_P']:+.4f} |")
    empty = res_dir / "scores_test_empty.json"
    if empty.exists():
        summary["empty_registry"] = load(empty)["experiments"]
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
