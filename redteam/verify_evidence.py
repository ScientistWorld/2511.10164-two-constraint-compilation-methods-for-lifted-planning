"""Lightweight consistency checks over saved evidence; never reruns a method."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def main():
    report = read("rank_report.json")
    reference = read("reference/scores_original.json")["experiments"]
    config = read("reference/metric_config.json")["experiments"]
    checked = 0
    for name, row in report["attempts"].items():
        status = read(f"{name}/status.json")
        if name == "shortcut_null_artifact":
            assert status["test"]["returncode"] == 1
            assert not status["test_wrote_scores"]
            assert not (ROOT / name / "scores_test.json").exists()
            assert row["failed"]
            continue
        assert status["train"]["returncode"] == status["test"]["returncode"] == 0
        assert status["test_wrote_scores"]
        scored = read(f"{name}/scores_test.json")["experiments"]
        assert set(scored) == set(reference)
        checked += 1
        if name.startswith("reference_seed_"):
            for experiment, conf in config.items():
                for metric, mc in conf["metrics"].items():
                    if mc["coefficient"]:
                        assert scored[experiment]["results"]["lifted_tcore"][metric] == (
                            reference[experiment]["results"]["lifted_tcore"][metric])
    assert checked == 13
    assert all(v["range"] == 0 for v in report["reference_seed_spread"].values())
    for name, improvements in (("better_boolean_optimizer", 9),
                               ("shortcut_known_plan", 15),
                               ("shortcut_constant_empty", 19),
                               ("shortcut_replace_baseline", 2)):
        row = report["attempts"][name]
        assert row["better_metrics"] == improvements and row["worse_metrics"] == 0
        assert row["audit_population_rank_gain"] > 0
    empty = read("shortcut_empty_results/scores_test.json")["experiments"]
    assert all(not ex["results"] for ex in empty.values())
    assert report["attempts"]["shortcut_empty_results"]["missing_scored_metrics"] == 27
    assert report["attempts"]["shortcut_registration"]["missing_scored_metrics"] == 15
    assert report["attempts"]["shortcut_reject_everything"]["two_attempt_rank_gain"] > 0
    assert report["attempts"]["shortcut_drop_constraints"]["two_attempt_rank_gain"] > 0
    trajectories = read("better_boolean_optimizer/semantic_equivalence.json")
    assert sum(v["trajectories"] for v in trajectories) == 8257
    assert not any(v["mismatches"] for v in trajectories)
    result = {"audit_status": "complete", "successful_evaluations": checked,
              "expected_failed_evaluations": 1, "scored_metric_seed_spread": 0,
              "optimizer_trajectory_checks": 8257, "checks": "passed",
              "reproduction_milestone": "core_claim",
              "milestone_change": "none; audit only"}
    (ROOT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
