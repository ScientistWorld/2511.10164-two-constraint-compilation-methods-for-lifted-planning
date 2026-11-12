"""Read actual hidden-test outputs and apply the stated rank formula.

Future-attempt variances are unknown: report an explicitly defined audit
population AND the exact two-attempt comparison, not an invented global rank.
"""
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "reference/metric_config.json").read_text())["experiments"]
REFERENCE = json.loads((ROOT / "reference/scores_original.json").read_text())["experiments"]


def read_candidate(name):
    p = ROOT / name / "scores_test.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return {e: exp["results"].get("lifted_tcore", {}) for e, exp in data["experiments"].items()}


def main():
    from run_trial import NAMES
    values = {n: read_candidate(n) for n in NAMES}
    values = {n: v for n, v in values.items() if v is not None}
    sigmas = {}
    for exp, conf in CONFIG.items():
        for metric, mc in conf["metrics"].items():
            if not abs(mc["coefficient"]):
                continue
            xs = [v[exp][metric] for v in values.values() if metric in v.get(exp, {})]
            sigmas[exp, metric] = statistics.pstdev(xs) if xs else 0.0
    report = {"normalization": "Population standard deviation across successful audit attempts, excluding missing values; zero-variance terms contribute zero.",
              "population": list(values), "reference": "original scoring/scores_test.json, lifted_tcore",
              "attempts": {}, "sigmas": {f"{e}/{m}": s for (e, m), s in sigmas.items()},
              "reference_seed_spread": {}, "reference_at_bound": []}
    for name, results in values.items():
        total = 0.0
        pairwise = 0.0
        improvements = worsens = equal = missing = 0
        terms = []
        for exp, conf in CONFIG.items():
            for metric, mc in conf["metrics"].items():
                coefficient = abs(mc["coefficient"])
                if not coefficient:
                    continue
                value = results.get(exp, {}).get(metric)
                if value is None:
                    missing += 1
                    continue
                ref = REFERENCE[exp]["results"]["lifted_tcore"][metric]
                delta = (value - ref) * (1 if mc["higher_is_better"] else -1)
                improvements += delta > 0
                worsens += delta < 0
                equal += delta == 0
                pairwise += conf["weight"] * coefficient * (2 if delta > 0 else -2 if delta < 0 else 0)
                sigma = sigmas[exp, metric]
                term = conf["weight"] * coefficient * delta / sigma if sigma else 0.0
                total += term
                terms.append({"experiment": exp, "metric": metric, "value": value,
                              "reference": ref, "directional_delta": delta, "audit_rank_contribution": term})
        report["attempts"][name] = {"audit_population_rank_gain": total, "two_attempt_rank_gain": pairwise,
            "better_metrics": improvements, "worse_metrics": worsens, "equal_metrics": equal,
            "missing_scored_metrics": missing, "terms": terms}
    for exp, conf in CONFIG.items():
        for metric, mc in conf["metrics"].items():
            if not abs(mc["coefficient"]):
                continue
            xs = [values[f"reference_seed_{s}"][exp][metric] for s in range(3)]
            report["reference_seed_spread"][f"{exp}/{metric}"] = {
                "min": min(xs), "max": max(xs), "range": max(xs) - min(xs)}
            ref = REFERENCE[exp]["results"]["lifted_tcore"][metric]
            if mc["higher_is_better"] and ref == 1 and ("rate" in metric or "accepted" in metric or "rejected" in metric):
                report["reference_at_bound"].append(f"{exp}/{metric}=1")
            if exp.endswith("_size") and metric in ("actions", "action_ratio_vs_ground"):
                report["reference_at_bound"].append(f"{exp}/{metric}={ref}: minimum for a nonempty compiled task and fixed baseline")
    for n in NAMES:
        if n not in values:
            report["attempts"][n] = {"failed": True, "rank": None}
    (ROOT / "rank_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = ["name\taudit_population_gain\ttwo_attempt_gain\tbetter/worse/equal/missing"]
    for n, r in report["attempts"].items():
        if r.get("failed"):
            lines.append(f"{n}\tFAILED\tFAILED\tno worst-value record")
        else:
            lines.append(f'{n}\t{r["audit_population_rank_gain"]:.6f}\t{r["two_attempt_rank_gain"]:.6f}\t'
                         f'{r["better_metrics"]}/{r["worse_metrics"]}/{r["equal_metrics"]}/{r["missing_scored_metrics"]}')
    (ROOT / "rank_summary.tsv").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
