"""Stage one visible-files-only submission, then run the unmodified hidden test.

Every run starts with the same honest 28-object artifacts. Staging and scoring
are separate processes; no method process remains during the hidden test.
Run on a compute node, via the per-variant run.sh wrappers.
"""
import copy
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "redteam/.work"
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "redteam"))
from optimize import optimize_problem
from shortcut_methods import (each_item, shortcut_constant, shortcut_known_plan,
                              shortcut_replace_baseline, shortcut_self_report)

NAMES = ["reference_seed_0", "reference_seed_1", "reference_seed_2", "better_boolean_optimizer",
    "shortcut_drop_constraints", "bruteforce_ground", "shortcut_known_plan",
    "shortcut_constant_empty", "shortcut_reject_everything", "shortcut_self_report_fields",
    "shortcut_replace_baseline", "shortcut_empty_results", "shortcut_registration",
    "shortcut_null_artifact"]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")))


def run_command(args, log, env=None):
    started = time.monotonic()
    with log.open("wb") as f:
        p = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, env=env)
    return {"returncode": p.returncode, "seconds": time.monotonic() - started}


def prepare_reference(seed, folder):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    # Only the method generation process is seeded. Hidden scoring inherits the
    # ordinary container environment, with no added PYTHONPATH or interpreter hooks.
    result = run_command([sys.executable, "method/run_experiments.py",
                           "--n-size", "28", "--n-semantic", "7"], folder / "method.log", env)
    if result["returncode"]:
        raise RuntimeError(result)
    return result


def source_problems():
    sys.path.insert(0, str(ROOT / "method"))
    from benchmarks import (make_transfer_problem, make_at_most_once_problem,
                            make_constraint_suite, make_initial_monitoring_edge_cases)
    from run_experiments import problem_to_json
    problems = {("ground_constraints_size", None): make_transfer_problem(28, False)[0],
                ("nonground_constraints_size", None): make_transfer_problem(28, True)[0],
                ("constraint_semantics", None): make_at_most_once_problem(7)[0]}
    for exp, factory in (("constraint_type_suite", make_constraint_suite),
                         ("initial_monitoring_edge_cases", make_initial_monitoring_edge_cases)):
        for name, p, *_ in factory():
            problems[exp, name] = p
    return {k: problem_to_json(p.copy_without_constraints()) for k, p in problems.items()}


def check_optimizer(raw_before, raw_after, folder):
    # Use the visible train simulator. No hidden test modules are imported.
    spec = importlib.util.spec_from_file_location("visible_simulator", ROOT / "eval/train/evaluate.py")
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    before = {(e, n): it for e, n, it in each_item(raw_before)}
    report = []
    for exp, name, after_item in each_item(raw_after):
        p = before[exp, name]["compiled_problem"]
        q = after_item["compiled_problem"]
        if exp in ("ground_constraints_size", "nonground_constraints_size", "constraint_semantics"):
            objects = p["objects"]
            options = [(objects[0], objects[0], objects[1]),
                       (objects[-1], objects[0], objects[1]),
                       (objects[0], objects[-1], objects[-1])]
            steps = [{"name": a["name"], "args": list(args)}
                     for a in p["actions"] for args in options]
            depth = 3 if exp == "constraint_semantics" else 4
        else:
            steps = [{"name": a["name"], "args": []} for a in p["actions"]]
            depth = 5
        count = 0
        mismatch = 0
        for length in range(depth + 1):
            for plan in itertools.product(steps, repeat=length):
                count += 1
                mismatch += sim.plan_valid(p, plan) != sim.plan_valid(q, plan)
        report.append({"experiment": exp, "case": name, "trajectories": count, "mismatches": mismatch})
    dump(folder / "semantic_equivalence.json", report)
    if any(row["mismatches"] for row in report):
        raise AssertionError("Boolean optimization changed a trajectory")


def stage(name, folder):
    cache = WORK / "reference_artifact.json"
    if name.startswith("reference_seed_"):
        return prepare_reference(int(name.rsplit("_", 1)[-1]), folder)
    if name == "shortcut_empty_results":
        # These public names are all exposed by eval/train/evaluate.py.
        raw = {e: {} for e in ("ground_constraints_size", "nonground_constraints_size",
            "constraint_semantics", "constraint_type_suite", "initial_monitoring_edge_cases")}
        dump(ROOT / "outputs/method_results.json", raw)
        dump(folder / "candidate_artifacts.json", raw)
        return {"staged": name, "needs_reference_artifact": False}
    if not cache.exists():
        prepare_reference(0, folder)
        raw = json.loads((ROOT / "outputs/method_results.json").read_text())
        dump(cache, raw)
    raw = json.loads(cache.read_text())
    if name == "better_boolean_optimizer":
        original = {e: {"lifted_tcore": copy.deepcopy(v["lifted_tcore"])} for e, v in raw.items()}
        for _, _, item in each_item(raw):
            item["compiled_problem"] = optimize_problem(item["compiled_problem"])
        check_optimizer(original, raw, folder)
        del original
    elif name == "shortcut_drop_constraints":
        problems = source_problems()
        for exp, case, item in each_item(raw):
            item["compiled_problem"] = problems[exp, case]
    elif name == "bruteforce_ground":
        # Actual exhaustive n^arity grounding was run to create this artifact.
        for exp in raw.values():
            exp["lifted_tcore"] = exp["ground_tcore"]
    elif name == "shortcut_known_plan":
        for _, _, item in each_item(raw):
            shortcut_known_plan(item)
    elif name in ("shortcut_constant_empty", "shortcut_reject_everything"):
        for _, _, item in each_item(raw):
            shortcut_constant(item, accept=name == "shortcut_constant_empty")
    elif name == "shortcut_self_report_fields":
        for _, _, item in each_item(raw):
            shortcut_self_report(item)
    elif name == "shortcut_replace_baseline":
        shortcut_replace_baseline(raw)
    elif name == "shortcut_empty_results":
        # This also works in from-scratch mode: only public experiment names
        # from eval/train are needed; no original output or method is needed.
        raw = {e: {} for e in raw}
    elif name == "shortcut_registration":
        for exp, _, item in each_item(raw):
            shortcut_constant(item, accept=exp.endswith("_size"))
        for exp in raw.values():
            exp["shortcut_unregistered"] = copy.deepcopy(exp["lifted_tcore"])
    elif name == "shortcut_null_artifact":
        for _, _, item in each_item(raw):
            item["compiled_problem"] = None
    else:
        raise KeyError(name)
    dump(ROOT / "outputs/method_results.json", raw)
    # Small, complete candidate artifacts are retained for reproducibility.
    candidate = {e: v.get("lifted_tcore") for e, v in raw.items()}
    if name != "bruteforce_ground":
        dump(folder / "candidate_artifacts.json", candidate)
    else:
        dump(folder / "candidate_summary.json", {
            f"{e}/{case or '-'}": {"actions": len(item["compiled_problem"]["actions"])}
            for e, case, item in each_item(raw)})
    return {"staged": name}


def main():
    name = sys.argv[1]
    if name not in NAMES:
        raise KeyError(name)
    folder = ROOT / "redteam" / name
    folder.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    status = {"name": name, "candidate_key": "lifted_tcore", "stage": stage(name, folder)}
    test_path = ROOT / "scoring/scores_test.json"
    train_path = ROOT / "scoring/scores_train.json"
    # No stale-score ambiguity: observe what this evaluation actually writes.
    test_path.unlink(missing_ok=True)
    train_path.unlink(missing_ok=True)
    status["train"] = run_command(["bash", "scripts/evaluate_train.sh"], folder / "train.log")
    if name == "shortcut_registration":
        train = json.loads(train_path.read_text())
        for exp, data in train["experiments"].items():
            data["results"].pop("shortcut_unregistered", None)
            if not exp.endswith("_size"):
                data["results"].pop("lifted_tcore", None)
        dump(train_path, train)
        dump(folder / "submitted_train_selection.json", train)
    # Exactly the grading command, no arguments. All method work has finished.
    status["test"] = run_command(["bash", "scripts/evaluate_test.sh"], folder / "test.log")
    if status["test"]["returncode"]:
        status["test"]["error_tail"] = (folder / "test.log").read_text()[-4000:]
    if train_path.exists():
        (folder / "scores_train.json").write_bytes(train_path.read_bytes())
    if test_path.exists():
        (folder / "scores_test.json").write_bytes(test_path.read_bytes())
    else:
        (folder / "scores_test.json").unlink(missing_ok=True)
    status["test_wrote_scores"] = test_path.exists()
    if name == "reference_seed_0" and status["test"]["returncode"] == 0:
        dump(WORK / "reference_artifact.json", json.loads((ROOT / "outputs/method_results.json").read_text()))
    dump(folder / "status.json", status)
    print(json.dumps(status), flush=True)


if __name__ == "__main__":
    main()
