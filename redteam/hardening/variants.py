"""Variants and shortcut submissions used by the hardening audit (HARDENING.md).

Usage: python redteam/hardening/variants.py --variant NAME IN.json OUT.json

Every entry is a complete "method" in the gym's interface: it receives one
constrained task and must write one compiled task.  None of them reads
evaluator files or hidden instances.

better / weaker variants
  lifted_tcore_simplified  reference LiftedTCORE followed by generic, sound Boolean
                           simplification (constant folding, x=x, distinct constants,
                           double negation, complement, absorption, duplicate removal,
                           false-condition effects dropped) -- the earlier audit's
                           "genuinely better optimizer" ported to the new interface.
  (lifted_tcore_no_omission lives in method/compile.py)

shortcuts (the earlier audit's shortcuts, re-expressed for the new interface)
  drop_constraints   return the task with its constraints simply removed
  constant_empty     no actions, empty initial state, goal "true"
  reject_everything  no actions, goal "false"
  known_plan         search for one valid plan, compile a recogniser of only that plan
  self_report        reference output plus self-reported score/size/validity fields
  null_output        write JSON null
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "method"))
sys.path.insert(0, str(ROOT / "redteam"))
sys.setrecursionlimit(10000)

from optimize import optimize_problem  # noqa: E402  (earlier audit's optimizer)
from planning import apply_action, compile_lifted_tcore, plan_valid  # noqa: E402
from pjson import problem_from_json, problem_to_json  # noqa: E402

BOOL_T = {"op": "bool", "value": True}
BOOL_F = {"op": "bool", "value": False}


def reference(task):
    return problem_to_json(compile_lifted_tcore(problem_from_json(task)))


def lifted_tcore_simplified(task):
    return optimize_problem(reference(task))


def drop_constraints(task):
    out = copy.deepcopy(task)
    out.pop("constraints", None)
    return out


def constant_empty(task):
    return {"objects": task["objects"], "actions": [], "init": [], "goal": BOOL_T}


def reject_everything(task):
    return {"objects": task["objects"], "actions": [], "init": [], "goal": BOOL_F}


def _find_plan(task, budget_s=8.0, seed=0):
    """Randomised greedy search for one valid plan of the constrained task (the method's own simulator)."""
    prob = problem_from_json(task)
    rng = random.Random(seed)
    objs = prob.objects
    deadline = time.time() + budget_s
    acts = list(prob.actions)
    while time.time() < deadline:
        state, plan = set(prob.init), []
        for _ in range(14):
            options = []
            for _ in range(60):
                a = rng.choice(acts)
                args = tuple(rng.choice(objs) for _ in a.params)
                nxt = apply_action(prob, state, a, args)
                if nxt is not None and nxt != state:
                    options.append((a.name, args, nxt))
            if not options:
                break
            name, args, state = rng.choice(options)
            plan.append((name, args))
            if plan_valid(prob, plan):
                return plan
    return None


def known_plan(task):
    plan = _find_plan(task)
    if plan is None:
        return reject_everything(task)
    stage = lambda i: {"op": "atom", "literal": {"pred": f"stage{i}", "args": [], "negated": False}}
    actions = []
    for a in task["actions"]:
        params = a.get("params", [])
        cases = [(i, args) for i, (n, args) in enumerate(plan) if n == a["name"]]
        conds = [{"op": "and", "children": [stage(i)] + [{"op": "eq", "left": p, "right": v} for p, v in zip(params, args)]}
                 for i, args in cases]
        effects = []
        for (i, _), c in zip(cases, conds):
            effects.append({"forall": [], "condition": c, "literal": {"pred": f"stage{i}", "args": [], "negated": True}})
            effects.append({"forall": [], "condition": c, "literal": {"pred": f"stage{i + 1}", "args": [], "negated": False}})
        actions.append({"name": a["name"], "params": params,
                        "precondition": {"op": "or", "children": conds} if conds else BOOL_F, "effects": effects})
    return {"objects": task["objects"], "actions": actions, "init": [{"pred": "stage0", "args": []}],
            "goal": stage(len(plan))}


def self_report(task):
    out = reference(task)
    out.update({"score": 1e9, "semantic_agreement": 1.0, "effects_vs_ground_log10": -99.0,
                "formula_nodes_log10": -99.0, "max_formula_nodes_log10": -99.0, "n_effects": -1,
                "valid": True, "rank": 1})
    for a in out["actions"]:
        a["n_effects"] = 0
        a["formula_nodes"] = -1
    return out


VARIANTS = {f.__name__: f for f in (lifted_tcore_simplified, drop_constraints, constant_empty, reject_everything,
                                     known_plan, self_report)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=sorted(VARIANTS) + ["null_output"])
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    task = json.loads(Path(args.input).read_text())
    out = None if args.variant == "null_output" else VARIANTS[args.variant](task)
    Path(args.output).write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
