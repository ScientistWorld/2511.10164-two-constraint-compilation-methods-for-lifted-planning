from __future__ import annotations

import argparse
import json
from pathlib import Path
from itertools import product
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

State = Set[Tuple[str, Tuple[str, ...]]]


def ratio(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def subst_term(term: str, subst: Dict[str, str]) -> str:
    return subst.get(term, term)


def subst_literal(lit: Dict[str, Any], subst: Dict[str, str]) -> Dict[str, Any]:
    return {
        "pred": lit["pred"],
        "args": [subst_term(a, subst) for a in lit.get("args", [])],
        "negated": lit.get("negated", False),
    }


def subst_formula(formula: Dict[str, Any], subst: Dict[str, str]) -> Dict[str, Any]:
    op = formula["op"]
    if op in {"bool", "eq"}:
        if op == "eq":
            return {"op": "eq", "left": subst_term(formula["left"], subst), "right": subst_term(formula["right"], subst)}
        return formula
    if op == "atom":
        return {"op": "atom", "literal": subst_literal(formula["literal"], subst)}
    if op == "not":
        return {"op": "not", "child": subst_formula(formula["child"], subst)}
    if op in {"and", "or"}:
        return {"op": op, "children": [subst_formula(c, subst) for c in formula.get("children", [])]}
    if op == "imply":
        return {"op": "imply", "left": subst_formula(formula["left"], subst), "right": subst_formula(formula["right"], subst)}
    if op in {"exists", "forall"}:
        scoped = {k: v for k, v in subst.items() if k not in formula.get("vars", [])}
        return {"op": op, "vars": formula.get("vars", []), "child": subst_formula(formula["child"], scoped)}
    raise ValueError(op)


def eval_formula(formula: Dict[str, Any], state: State, objects: Sequence[str]) -> bool:
    op = formula["op"]
    if op == "bool":
        return bool(formula["value"])
    if op == "atom":
        lit = formula["literal"]
        present = (lit["pred"], tuple(lit.get("args", []))) in state
        return not present if lit.get("negated", False) else present
    if op == "not":
        return not eval_formula(formula["child"], state, objects)
    if op == "and":
        return all(eval_formula(c, state, objects) for c in formula.get("children", []))
    if op == "or":
        return any(eval_formula(c, state, objects) for c in formula.get("children", []))
    if op == "imply":
        return (not eval_formula(formula["left"], state, objects)) or eval_formula(formula["right"], state, objects)
    if op == "eq":
        return formula["left"] == formula["right"]
    if op in {"exists", "forall"}:
        vars_ = formula.get("vars", [])
        values_iter = product(objects, repeat=len(vars_))
        if op == "exists":
            return any(eval_formula(subst_formula(formula["child"], dict(zip(vars_, values))), state, objects) for values in values_iter)
        return all(eval_formula(subst_formula(formula["child"], dict(zip(vars_, values))), state, objects) for values in values_iter)
    raise ValueError(op)


def ground_effect(effect: Dict[str, Any], objects: Sequence[str], subst: Dict[str, str]) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    forall = effect.get("forall", [])
    if not forall:
        yield subst_formula(effect["condition"], subst), subst_literal(effect["literal"], subst)
        return
    for values in product(objects, repeat=len(forall)):
        full = dict(subst)
        full.update(zip(forall, values))
        yield subst_formula(effect["condition"], full), subst_literal(effect["literal"], full)


def apply_action(problem: Dict[str, Any], state: State, action: Dict[str, Any], args: Sequence[str]) -> State | None:
    subst = dict(zip(action.get("params", []), args))
    objects = problem["objects"]
    if not eval_formula(subst_formula(action["precondition"], subst), state, objects):
        return None
    grounded: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for effect in action.get("effects", []):
        grounded.extend(ground_effect(effect, objects, subst))
    deletes = {
        (lit["pred"], tuple(lit.get("args", [])))
        for cond, lit in grounded
        if lit.get("negated", False) and eval_formula(cond, state, objects)
    }
    adds = {
        (lit["pred"], tuple(lit.get("args", [])))
        for cond, lit in grounded
        if not lit.get("negated", False) and eval_formula(cond, state, objects)
    }
    return (state - deletes) | adds


def plan_valid(problem: Dict[str, Any], plan: Sequence[Dict[str, Any]]) -> bool:
    by_name = {a["name"]: a for a in problem["actions"]}
    state: State = {(atom["pred"], tuple(atom.get("args", []))) for atom in problem["init"]}
    for step in plan:
        action = by_name.get(step["name"])
        if action is None:
            return False
        nxt = apply_action(problem, state, action, step.get("args", []))
        if nxt is None:
            return False
        state = nxt
    return eval_formula(problem["goal"], state, problem["objects"])


def formula_size(formula: Dict[str, Any]) -> int:
    op = formula["op"]
    if op in {"bool", "atom", "eq"}:
        return 1
    if op == "not":
        return 1 + formula_size(formula["child"])
    if op in {"and", "or"}:
        return 1 + sum(formula_size(c) for c in formula.get("children", []))
    if op == "imply":
        return 1 + formula_size(formula["left"]) + formula_size(formula["right"])
    if op in {"exists", "forall"}:
        return 1 + formula_size(formula["child"])
    raise ValueError(op)


def size_stats(problem: Dict[str, Any]) -> Dict[str, float]:
    return {
        "actions": len(problem["actions"]),
        "effects": sum(len(a.get("effects", [])) for a in problem["actions"]),
        "formula_atoms": sum(
            formula_size(a["precondition"]) + sum(formula_size(e["condition"]) for e in a.get("effects", []))
            for a in problem["actions"]
        ),
    }


def item_stats(item: Dict[str, Any]) -> Dict[str, float]:
    stats = size_stats(item["compiled_problem"])
    stats["compile_seconds"] = item["compile_seconds"]
    return stats


def score_compile_size(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        stats = item_stats(item)
        out[method] = {
            **stats,
            "plan_valid_rate": 1.0 if plan_valid(item["compiled_problem"], item["valid_plan"]) else 0.0,
        }
    out["lifted_tcore"]["action_ratio_vs_ground"] = ratio(out["lifted_tcore"]["actions"], out["ground_tcore"]["actions"])
    out["lcc"]["action_ratio_vs_ground"] = ratio(out["lcc"]["actions"], out["ground_tcore"]["actions"])
    out["ground_tcore"]["action_ratio_vs_ground"] = 1.0
    return out


def score_semantics(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        stats = item_stats(item)
        out[method] = {
            "valid_plan_accepted": 1.0 if plan_valid(item["compiled_problem"], item["valid_plan"]) else 0.0,
            "invalid_plan_rejected": 1.0 if not plan_valid(item["compiled_problem"], item["invalid_plan"]) else 0.0,
            "actions": stats["actions"],
            "effects": stats["effects"],
            "compile_seconds": stats["compile_seconds"],
        }
    return out


def score_constraint_suite(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    n_cases = len(exp["constraint_types"])
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        valid = 0
        invalid = 0
        actions = 0
        effects = 0
        compile_seconds = 0.0
        for case in item["cases"].values():
            valid += int(plan_valid(case["compiled_problem"], case["valid_plan"]))
            invalid += int(not plan_valid(case["compiled_problem"], case["invalid_plan"]))
            stats = item_stats(case)
            actions += stats["actions"]
            effects += stats["effects"]
            compile_seconds += stats["compile_seconds"]
        out[method] = {
            "constraint_types_tested": n_cases,
            "valid_accept_rate": valid / n_cases,
            "invalid_reject_rate": invalid / n_cases,
            "actions": actions,
            "effects": effects,
            "compile_seconds": compile_seconds,
        }
    return out


def score_initial_monitoring_edges(exp: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    n_cases = len(exp["edge_cases"])
    for method in ("lifted_tcore", "lcc", "ground_tcore"):
        item = exp[method]
        valid = 0
        invalid = 0
        invalid_cases = 0
        actions = 0
        effects = 0
        compile_seconds = 0.0
        for case in item["cases"].values():
            valid += int(plan_valid(case["compiled_problem"], case["valid_plan"]))
            if "invalid_plan" in case:
                invalid_cases += 1
                invalid += int(not plan_valid(case["compiled_problem"], case["invalid_plan"]))
            stats = item_stats(case)
            actions += stats["actions"]
            effects += stats["effects"]
            compile_seconds += stats["compile_seconds"]
        out[method] = {
            "edge_cases_tested": n_cases,
            "valid_accept_rate": valid / n_cases,
            "invalid_reject_rate": invalid / invalid_cases,
            "actions": actions,
            "effects": effects,
            "compile_seconds": compile_seconds,
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
            "constraint_type_suite": {"results": score_constraint_suite(raw["constraint_type_suite"])},
            "initial_monitoring_edge_cases": {"results": score_initial_monitoring_edges(raw["initial_monitoring_edge_cases"])},
        }
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(json.dumps(scores, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
