"""Private-search shortcut: prune monitoring that the method's own sampled trajectories never need.

Usage: python redteam/hardening/prune_attack.py IN.json OUT.json

The compiler has the constrained task and a copy of the public simulator
(eval/train/train_lib.py).  It compiles with LiftedTCORE and then greedily
deletes added monitoring preconditions/effects whenever its own random
trajectories (random walks from the initial state, same sampler as the public
generator) cannot tell the difference: every prefix must stay executable
exactly when the constrained task is not yet violated, and the monitoring part
of the goal must agree with the constraint monitors.  Small tasks (< 10
objects, checked exhaustively by the evaluator) are returned unpruned, so the
attack only bets against the probe-based checks of the large tasks.
"""
from __future__ import annotations

import copy
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "method"))
sys.path.insert(0, str(ROOT / "eval" / "train"))
sys.setrecursionlimit(20000)

import train_lib as T  # noqa: E402  (public simulator)
from planning import compile_lifted_tcore  # noqa: E402
from pjson import problem_from_json, problem_to_json  # noqa: E402

BUDGET_S = 20.0


def conjuncts(js):
    return js["children"] if js.get("op") == "and" else [js]


def main():
    started = time.time()
    task_js = json.loads(Path(sys.argv[1]).read_text())
    compiled = problem_to_json(compile_lifted_tcore(problem_from_json(task_js)))
    if len(task_js["objects"]) < 10:
        Path(sys.argv[2]).write_text(json.dumps(compiled))
        return
    orig = T.Task(task_js)
    meta = []
    for name in orig.order:
        pre = orig.actions[name][2]
        conj = pre[1] if pre[0] == "and" else (pre,)
        meta.append([(c[1], c[2]) for c in conj if c[0] == "atom" and not c[3]])
    sampler = T.Sampler(orig, meta)
    rng = random.Random(0)
    trajs = []
    while len(trajs) < 150 and time.time() - started < 6:
        plan, _ = sampler.walk(rng, orig.init, rng.randint(4, 14), allow_noop=False)
        if plan:
            trajs.append(plan)
    cons = orig.constraints
    objs = orig.objects

    def orig_status(plan):
        out, st = [], orig.init
        m = T.mon_step(cons, tuple(0 for _ in cons), st, objs)
        out.append((m is not None, T.mon_accept(cons, m)))
        for name, args in plan:
            st = T.apply(orig.actions[name], st, args, objs) if m is not None else None
            m = T.mon_step(cons, m, st, objs) if st is not None else None
            out.append((m is not None, T.mon_accept(cons, m)))
        return out

    ref = [orig_status(p) for p in trajs]
    orig_goal = {json.dumps(c, sort_keys=True) for c in conjuncts(task_js["goal"])}

    def comp_status(js, plan):
        comp = T.Compiled(js, orig)
        mon_goal = [T.parse_formula(c, frozenset()) for c in conjuncts(js["goal"])
                    if json.dumps(c, sort_keys=True) not in orig_goal]
        def acc(S):
            return any(all(T.ev(g, s, {}, objs) for g in mon_goal) for s in S)
        S = comp.closure([comp.task.init])
        out = [(bool(S), acc(S))]
        for name, args in plan:
            S = comp.step(S, name, tuple(args)) if S else frozenset()
            out.append((bool(S), acc(S) if S else False))
        return out

    def agrees(js):
        for plan, r in zip(trajs, ref):
            c = comp_status(js, plan)
            if any(ra != ca or (ra and racc != cacc) for (ra, racc), (ca, cacc) in zip(r, c)):
                return False
        return True

    orig_by_name = {a["name"]: a for a in task_js["actions"]}
    items = []
    for ai, a in enumerate(compiled["actions"]):
        base_pre = {json.dumps(c, sort_keys=True) for c in conjuncts(orig_by_name[a["name"]]["precondition"])}
        for ci, c in enumerate(conjuncts(a["precondition"])):
            if json.dumps(c, sort_keys=True) not in base_pre:
                items.append(("pre", ai, json.dumps(c, sort_keys=True)))
        for ei in range(len(orig_by_name[a["name"]]["effects"]), len(a["effects"])):
            items.append(("eff", ai, json.dumps(a["effects"][ei], sort_keys=True)))
    rng.shuffle(items)
    current = compiled
    if agrees(current):
        for kind, ai, key in items:
            if time.time() - started > BUDGET_S:
                break
            trial = copy.deepcopy(current)
            act = trial["actions"][ai]
            if kind == "pre":
                kept = [c for c in conjuncts(act["precondition"]) if json.dumps(c, sort_keys=True) != key]
                act["precondition"] = {"op": "and", "children": kept} if len(kept) > 1 else (kept[0] if kept else {"op": "bool", "value": True})
            else:
                act["effects"] = [e for e in act["effects"] if json.dumps(e, sort_keys=True) != key]
            if agrees(trial):
                current = trial
    Path(sys.argv[2]).write_text(json.dumps(current))


if __name__ == "__main__":
    main()
