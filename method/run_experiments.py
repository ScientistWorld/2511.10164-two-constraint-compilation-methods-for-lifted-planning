from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

from benchmarks import make_at_most_once_problem, make_constraint_suite, make_transfer_problem
from planning import (
    compile_ground_tcore,
    compile_lcc,
    compile_lifted_tcore,
    plan_valid,
    size_stats,
)


def timed_compile(fn, problem):
    started = time.perf_counter()
    compiled = fn(problem)
    return compiled, time.perf_counter() - started


def ground_name(name: str, args: tuple[str, ...]) -> str:
    return f"{name}_{'_'.join(args)}"


def compile_size_experiment(n_objects: int, quantified: bool) -> Dict[str, Any]:
    problem, plan = make_transfer_problem(n_objects=n_objects, quantified=quantified)
    lifted, lifted_t = timed_compile(compile_lifted_tcore, problem)
    lcc, lcc_t = timed_compile(compile_lcc, problem)
    ground, ground_t = timed_compile(compile_ground_tcore, problem)
    lifted_plan_ok = plan_valid(lifted, plan)
    lcc_plan_ok = plan_valid(lcc, plan + [("fin", ())])
    ground_plan = [(ground_name(name, args), ()) for name, args in plan]
    ground_plan_ok = plan_valid(ground, ground_plan)
    return {
        "n_objects": n_objects,
        "quantified": quantified,
        "original_plan_valid": plan_valid(problem, plan),
        "lifted_tcore": {
            **size_stats(lifted),
            "compile_seconds": lifted_t,
            "plan_valid": lifted_plan_ok,
        },
        "lcc": {
            **size_stats(lcc),
            "compile_seconds": lcc_t,
            "plan_valid": lcc_plan_ok,
        },
        "ground_tcore": {
            **size_stats(ground),
            "compile_seconds": ground_t,
            "plan_valid": ground_plan_ok,
        },
    }


def at_most_once_experiment(n_objects: int) -> Dict[str, Any]:
    problem, valid_plan, invalid_plan = make_at_most_once_problem(n_objects=n_objects)
    lifted, lifted_t = timed_compile(compile_lifted_tcore, problem)
    lcc, lcc_t = timed_compile(compile_lcc, problem)
    ground, ground_t = timed_compile(compile_ground_tcore, problem)
    return {
        "n_objects": n_objects,
        "original_valid_plan": plan_valid(problem, valid_plan),
        "original_rejects_invalid": not plan_valid(problem, invalid_plan),
        "lifted_tcore": {
            **size_stats(lifted),
            "compile_seconds": lifted_t,
            "valid_plan_accepted": plan_valid(lifted, valid_plan),
            "invalid_plan_rejected": not plan_valid(lifted, invalid_plan),
        },
        "lcc": {
            **size_stats(lcc),
            "compile_seconds": lcc_t,
            "valid_plan_accepted": plan_valid(lcc, valid_plan + [("fin", ())]),
            "invalid_plan_rejected": not plan_valid(lcc, invalid_plan + [("fin", ())]),
        },
        "ground_tcore": {
            **size_stats(ground),
            "compile_seconds": ground_t,
            "valid_plan_accepted": plan_valid(ground, [(ground_name(n, a), ()) for n, a in valid_plan]),
            "invalid_plan_rejected": not plan_valid(ground, [(ground_name(n, a), ()) for n, a in invalid_plan]),
        },
    }


def constraint_suite_experiment() -> Dict[str, Any]:
    cases = make_constraint_suite()
    totals: Dict[str, Dict[str, Any]] = {
        method: {
            "valid_accepted": 0,
            "invalid_rejected": 0,
            "actions": 0,
            "effects": 0,
            "compile_seconds": 0.0,
            "cases": {},
        }
        for method in ("lifted_tcore", "lcc", "ground_tcore")
    }
    for name, problem, valid_plan, invalid_plan in cases:
        compiled = {}
        compiled["lifted_tcore"], lifted_t = timed_compile(compile_lifted_tcore, problem)
        compiled["lcc"], lcc_t = timed_compile(compile_lcc, problem)
        compiled["ground_tcore"], ground_t = timed_compile(compile_ground_tcore, problem)
        compile_times = {"lifted_tcore": lifted_t, "lcc": lcc_t, "ground_tcore": ground_t}
        for method, compiled_problem in compiled.items():
            if method == "lcc":
                valid = valid_plan + [("fin", ())]
                invalid = invalid_plan + [("fin", ())]
            elif method == "ground_tcore":
                valid = [(ground_name(n, a), ()) for n, a in valid_plan]
                invalid = [(ground_name(n, a), ()) for n, a in invalid_plan]
            else:
                valid = valid_plan
                invalid = invalid_plan
            valid_ok = plan_valid(compiled_problem, valid)
            invalid_rejected = not plan_valid(compiled_problem, invalid)
            totals[method]["valid_accepted"] += int(valid_ok)
            totals[method]["invalid_rejected"] += int(invalid_rejected)
            stats = size_stats(compiled_problem)
            totals[method]["actions"] += stats["actions"]
            totals[method]["effects"] += stats["effects"]
            totals[method]["compile_seconds"] += compile_times[method]
            totals[method]["cases"][name] = {
                "valid_plan_accepted": valid_ok,
                "invalid_plan_rejected": invalid_rejected,
                **stats,
            }
    for method in totals:
        totals[method]["valid_accept_rate"] = totals[method]["valid_accepted"] / len(cases)
        totals[method]["invalid_reject_rate"] = totals[method]["invalid_rejected"] / len(cases)
    return {"constraint_types": [case[0] for case in cases], **totals}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/method_results.json")
    parser.add_argument("--n-small", type=int, default=7)
    parser.add_argument("--n-large", type=int, default=16)
    args = parser.parse_args()

    results = {
        "ground_constraints_size": compile_size_experiment(args.n_large, quantified=False),
        "nonground_constraints_size": compile_size_experiment(args.n_small, quantified=True),
        "constraint_semantics": at_most_once_experiment(args.n_small),
        "constraint_type_suite": constraint_suite_experiment(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
