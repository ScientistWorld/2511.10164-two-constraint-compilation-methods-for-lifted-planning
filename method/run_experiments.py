from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

from benchmarks import (
    make_at_most_once_problem,
    make_constraint_suite,
    make_initial_monitoring_edge_cases,
    make_transfer_problem,
)
from planning import (
    Action,
    And,
    Atom,
    Bool,
    Effect,
    Eq,
    Exists,
    ForAll,
    Formula,
    Imply,
    Literal,
    Not,
    Or,
    Problem,
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


def literal_to_json(lit: Literal) -> Dict[str, Any]:
    return {"pred": lit.pred, "args": list(lit.args), "negated": lit.negated}


def formula_to_json(formula: Formula) -> Dict[str, Any]:
    if isinstance(formula, Bool):
        return {"op": "bool", "value": formula.value}
    if isinstance(formula, Atom):
        return {"op": "atom", "literal": literal_to_json(formula.lit)}
    if isinstance(formula, Not):
        return {"op": "not", "child": formula_to_json(formula.child)}
    if isinstance(formula, And):
        return {"op": "and", "children": [formula_to_json(c) for c in formula.children]}
    if isinstance(formula, Or):
        return {"op": "or", "children": [formula_to_json(c) for c in formula.children]}
    if isinstance(formula, Imply):
        return {"op": "imply", "left": formula_to_json(formula.left), "right": formula_to_json(formula.right)}
    if isinstance(formula, Eq):
        return {"op": "eq", "left": formula.left, "right": formula.right}
    if isinstance(formula, Exists):
        return {"op": "exists", "vars": list(formula.vars), "child": formula_to_json(formula.child)}
    if isinstance(formula, ForAll):
        return {"op": "forall", "vars": list(formula.vars), "child": formula_to_json(formula.child)}
    raise TypeError(formula)


def effect_to_json(effect: Effect) -> Dict[str, Any]:
    return {
        "condition": formula_to_json(effect.condition),
        "literal": literal_to_json(effect.literal),
        "forall": list(effect.forall),
    }


def action_to_json(action: Action) -> Dict[str, Any]:
    return {
        "name": action.name,
        "params": list(action.params),
        "precondition": formula_to_json(action.precondition),
        "effects": [effect_to_json(e) for e in action.effects],
    }


def problem_to_json(problem: Problem) -> Dict[str, Any]:
    return {
        "objects": list(problem.objects),
        "actions": [action_to_json(a) for a in problem.actions],
        "init": [{"pred": pred, "args": list(args)} for pred, args in sorted(problem.init)],
        "goal": formula_to_json(problem.goal),
    }


def plan_to_json(plan: list[tuple[str, tuple[str, ...]]]) -> list[Dict[str, Any]]:
    return [{"name": name, "args": list(args)} for name, args in plan]


def compiled_artifact(
    compiled: Problem,
    compile_seconds: float,
    valid_plan: list[tuple[str, tuple[str, ...]]],
    invalid_plan: list[tuple[str, tuple[str, ...]]] | None = None,
) -> Dict[str, Any]:
    artifact = {
        "compiled_problem": problem_to_json(compiled),
        "compile_seconds": compile_seconds,
        "valid_plan": plan_to_json(valid_plan),
    }
    if invalid_plan is not None:
        artifact["invalid_plan"] = plan_to_json(invalid_plan)
    return artifact


def compile_size_experiment(n_objects: int, quantified: bool) -> Dict[str, Any]:
    problem, plan = make_transfer_problem(n_objects=n_objects, quantified=quantified)
    lifted, lifted_t = timed_compile(compile_lifted_tcore, problem)
    lcc, lcc_t = timed_compile(compile_lcc, problem)
    ground, ground_t = timed_compile(compile_ground_tcore, problem)
    lifted_plan_ok = plan_valid(lifted, plan)
    lcc_plan_ok = plan_valid(lcc, plan + [("fin", ())])
    ground_plan = [(ground_name(name, args), ()) for name, args in plan]
    return {
        "n_objects": n_objects,
        "quantified": quantified,
        "original_plan_valid": plan_valid(problem, plan),
        "lifted_tcore": {**compiled_artifact(lifted, lifted_t, plan), "plan_valid": lifted_plan_ok, **size_stats(lifted)},
        "lcc": {**compiled_artifact(lcc, lcc_t, plan + [("fin", ())]), "plan_valid": lcc_plan_ok, **size_stats(lcc)},
        "ground_tcore": {**compiled_artifact(ground, ground_t, ground_plan), "plan_valid": plan_valid(ground, ground_plan), **size_stats(ground)},
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
            **compiled_artifact(lifted, lifted_t, valid_plan, invalid_plan),
            "valid_plan_accepted": plan_valid(lifted, valid_plan),
            "invalid_plan_rejected": not plan_valid(lifted, invalid_plan),
            **size_stats(lifted),
        },
        "lcc": {
            **compiled_artifact(lcc, lcc_t, valid_plan + [("fin", ())], invalid_plan + [("fin", ())]),
            "valid_plan_accepted": plan_valid(lcc, valid_plan + [("fin", ())]),
            "invalid_plan_rejected": not plan_valid(lcc, invalid_plan + [("fin", ())]),
            **size_stats(lcc),
        },
        "ground_tcore": {
            **compiled_artifact(ground, ground_t, [(ground_name(n, a), ()) for n, a in valid_plan], [(ground_name(n, a), ()) for n, a in invalid_plan]),
            "valid_plan_accepted": plan_valid(ground, [(ground_name(n, a), ()) for n, a in valid_plan]),
            "invalid_plan_rejected": not plan_valid(ground, [(ground_name(n, a), ()) for n, a in invalid_plan]),
            **size_stats(ground),
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
                **compiled_artifact(compiled_problem, compile_times[method], valid, invalid),
                "valid_plan_accepted": valid_ok,
                "invalid_plan_rejected": invalid_rejected,
                **stats,
            }
    for method in totals:
        totals[method]["valid_accept_rate"] = totals[method]["valid_accepted"] / len(cases)
        totals[method]["invalid_reject_rate"] = totals[method]["invalid_rejected"] / len(cases)
    return {"constraint_types": [case[0] for case in cases], **totals}


def initial_monitoring_edge_case_experiment() -> Dict[str, Any]:
    cases = make_initial_monitoring_edge_cases()
    totals: Dict[str, Dict[str, Any]] = {
        method: {
            "valid_accepted": 0,
            "valid_cases": 0,
            "invalid_rejected": 0,
            "invalid_cases": 0,
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
                invalid = None if invalid_plan is None else invalid_plan + [("fin", ())]
            elif method == "ground_tcore":
                valid = [(ground_name(n, a), ()) for n, a in valid_plan]
                invalid = None if invalid_plan is None else [(ground_name(n, a), ()) for n, a in invalid_plan]
            else:
                valid = valid_plan
                invalid = invalid_plan
            valid_ok = plan_valid(compiled_problem, valid)
            invalid_rejected = None if invalid is None else not plan_valid(compiled_problem, invalid)
            totals[method]["valid_cases"] += 1
            totals[method]["valid_accepted"] += int(valid_ok)
            if invalid_rejected is not None:
                totals[method]["invalid_cases"] += 1
                totals[method]["invalid_rejected"] += int(invalid_rejected)
            stats = size_stats(compiled_problem)
            totals[method]["actions"] += stats["actions"]
            totals[method]["effects"] += stats["effects"]
            totals[method]["compile_seconds"] += compile_times[method]
            artifact = compiled_artifact(compiled_problem, compile_times[method], valid)
            if invalid is not None:
                artifact["invalid_plan"] = plan_to_json(invalid)
            totals[method]["cases"][name] = {
                **artifact,
                "valid_plan_accepted": valid_ok,
                "invalid_plan_rejected": invalid_rejected,
                **stats,
            }
    for method in totals:
        totals[method]["valid_accept_rate"] = totals[method]["valid_accepted"] / totals[method]["valid_cases"]
        totals[method]["invalid_reject_rate"] = totals[method]["invalid_rejected"] / totals[method]["invalid_cases"]
    return {"edge_cases": [case[0] for case in cases], **totals}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/method_results.json")
    parser.add_argument(
        "--n-size",
        type=int,
        default=28,
        help="Object count for high-arity size experiments; 28^3 ~= 21K grounded actions, matching the paper's Table 3 scale.",
    )
    parser.add_argument(
        "--n-semantic",
        type=int,
        default=7,
        help="Object count for semantic accept/reject checks, kept small because these tests do not rely on grounding blow-up.",
    )
    args = parser.parse_args()

    results = {
        "ground_constraints_size": compile_size_experiment(args.n_size, quantified=False),
        "nonground_constraints_size": compile_size_experiment(args.n_size, quantified=True),
        "constraint_semantics": at_most_once_experiment(args.n_semantic),
        "constraint_type_suite": constraint_suite_experiment(),
        "initial_monitoring_edge_cases": initial_monitoring_edge_case_experiment(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "output": str(output),
                "experiments": sorted(results),
                "note": "Full compiled-task artifacts were written to the output JSON.",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
