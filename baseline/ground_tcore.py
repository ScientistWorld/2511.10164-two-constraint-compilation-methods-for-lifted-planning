"""Ground-first TCORE baseline (Bonassi et al. 2021): ground, then compile by regression.

Usage: python baseline/ground_tcore.py [--max-ground-actions N] IN.json OUT.json

Every action schema is instantiated for every tuple of objects, quantifiers in
the constraint formulae are expanded over the objects, and constraints are
compiled away with the (ground) regression operator of Rintanen (2008):
R(f, a) = Gamma_f(a) or (f and not Gamma_-f(a)).  Monitoring follows TCORE:
always -> precondition R(phi,a); sometime -> R(phi,a) |> hold; at-most-once ->
R(phi,a) |> seen plus precondition not(seen and not phi and R(phi,a));
sometime-before -> R(psi,a) |> seen_psi and precondition R(phi,a) -> seen_psi;
sometime-after -> R(psi,a) |> hold and R(phi and not psi,a) |> not hold.
Updates whose regression leaves the formula unchanged are skipped, so only the
ground actions that can affect a constraint are touched.

Ground actions are named ``schema(arg1,...,argk)`` with no parameters.  The
baseline refuses (exit code 3) when grounding would exceed
``--max-ground-actions`` (default 200000); ``0`` disables the limit.

Self-contained: does not import the paper's method.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

sys.setrecursionlimit(20000)
TRUE = {"op": "bool", "value": True}
FALSE = {"op": "bool", "value": False}


def subst_term(t, env):
    return env.get(t, t)


def ground(f, env, objects):
    """Substitute variables and expand quantifiers over the objects."""
    op = f["op"]
    if op == "bool":
        return f
    if op == "atom":
        lit = f["literal"]
        return {"op": "atom", "literal": {"pred": lit["pred"], "args": [subst_term(a, env) for a in lit.get("args", [])],
                                          "negated": lit.get("negated", False)}}
    if op == "eq":
        return TRUE if subst_term(f["left"], env) == subst_term(f["right"], env) else FALSE
    if op == "not":
        return mk_not(ground(f["child"], env, objects))
    if op in ("and", "or"):
        return mk(op, [ground(c, env, objects) for c in f["children"]])
    if op == "imply":
        return mk("or", [mk_not(ground(f["left"], env, objects)), ground(f["right"], env, objects)])
    vs = f["vars"]
    parts = []
    for vals in itertools.product(objects, repeat=len(vs)):
        e2 = dict(env)
        e2.update(zip(vs, vals))
        parts.append(ground(f["child"], e2, objects))
    return mk("or" if op == "exists" else "and", parts)


def mk_not(f):
    if f["op"] == "bool":
        return FALSE if f["value"] else TRUE
    if f["op"] == "not":
        return f["child"]
    if f["op"] == "atom":
        lit = dict(f["literal"])
        lit["negated"] = not lit.get("negated", False)
        return {"op": "atom", "literal": lit}
    return {"op": "not", "child": f}


def mk(op, children):
    unit, zero = (TRUE, FALSE) if op == "and" else (FALSE, TRUE)
    flat, seen = [], set()
    for c in children:
        if c == zero:
            return zero
        if c == unit:
            continue
        for d in (c["children"] if c["op"] == op else [c]):
            k = json.dumps(d, sort_keys=True)
            if k not in seen:
                seen.add(k)
                flat.append(d)
    if not flat:
        return unit
    return flat[0] if len(flat) == 1 else {"op": op, "children": flat}


def key_of(lit):
    return lit["pred"], tuple(lit.get("args", []))


def atoms_of(f, out):
    op = f["op"]
    if op == "atom":
        out.add(key_of(f["literal"]))
    elif op == "not":
        atoms_of(f["child"], out)
    elif op in ("and", "or"):
        for c in f["children"]:
            atoms_of(c, out)
    return out


def regress(f, add, dele):
    op = f["op"]
    if op == "bool":
        return f
    if op == "atom":
        k = key_of(f["literal"])
        if k not in add and k not in dele:
            return f
        pos = {"op": "atom", "literal": {"pred": k[0], "args": list(k[1]), "negated": False}}
        r = mk("or", [add.get(k, FALSE), mk("and", [pos, mk_not(dele.get(k, FALSE))])])
        return mk_not(r) if f["literal"].get("negated", False) else r
    if op == "not":
        return mk_not(regress(f["child"], add, dele))
    return mk(op, [regress(c, add, dele) for c in f["children"]])


def evaluate(f, state):
    op = f["op"]
    if op == "bool":
        return f["value"]
    if op == "atom":
        return (key_of(f["literal"]) in state) != f["literal"].get("negated", False)
    if op == "not":
        return not evaluate(f["child"], state)
    if op == "and":
        return all(evaluate(c, state) for c in f["children"])
    return any(evaluate(c, state) for c in f["children"])


def compile_task(task, max_ground):
    objects = task["objects"]
    n = len(objects)
    total = sum(n ** len(a.get("params", [])) for a in task["actions"])
    if max_ground and total > max_ground:
        raise SystemExit(3)
    init = {key_of(a) for a in task.get("init", [])}
    cons = []
    for c in task.get("constraints", []):
        phi = ground(c["phi"], {}, objects)
        psi = ground(c["psi"], {}, objects) if c.get("psi") is not None else None
        cons.append((c["kind"], phi, psi))
    taken = {p for p, _ in init} | {a["name"] for a in task["actions"]}
    prefix = "tmon_"
    while any(p.startswith(prefix) for p in taken):
        prefix = "_" + prefix
    hold = lambda i: {"pred": f"{prefix}hold{i}", "args": [], "negated": False}
    seen = lambda i: {"pred": f"{prefix}seen{i}", "args": [], "negated": False}
    atom = lambda lit: {"op": "atom", "literal": lit}
    new_init = set(init)
    goal = [ground(task["goal"], {}, objects)]
    for i, (kind, phi, psi) in enumerate(cons):
        if kind == "always" and not evaluate(phi, init) or kind == "sometime_before" and evaluate(phi, init):
            goal = [FALSE]
        if kind in ("sometime", "sometime_after"):
            goal.append(atom(hold(i)))
        if kind == "sometime" and evaluate(phi, init):
            new_init.add(key_of(hold(i)))
        if kind == "sometime_after" and (evaluate(psi, init) or not evaluate(phi, init)):
            new_init.add(key_of(hold(i)))
        if kind == "at_most_once" and evaluate(phi, init):
            new_init.add(key_of(seen(i)))
        if kind == "sometime_before" and evaluate(psi, init):
            new_init.add(key_of(seen(i)))
    actions = []
    for a in task["actions"]:
        params = a.get("params", [])
        for vals in itertools.product(objects, repeat=len(params)):
            env = dict(zip(params, vals))
            pre = ground(a["precondition"], env, objects)
            effects, add, dele = [], {}, {}
            for e in a.get("effects", []):
                fv = e.get("forall", [])
                for fvals in itertools.product(objects, repeat=len(fv)):
                    e2 = dict(env)
                    e2.update(zip(fv, fvals))
                    cond = ground(e.get("condition", TRUE), e2, objects)
                    if cond == FALSE:
                        continue
                    lit = e["literal"]
                    glit = {"pred": lit["pred"], "args": [subst_term(x, e2) for x in lit.get("args", [])],
                            "negated": lit.get("negated", False)}
                    effects.append({"forall": [], "condition": cond, "literal": glit})
                    target = dele if glit["negated"] else add
                    k = key_of(glit)
                    target[k] = mk("or", [target.get(k, FALSE), cond])
            P = []
            touched = set(add) | set(dele)
            for i, (kind, phi, psi) in enumerate(cons):
                def r(f):
                    return None if not (atoms_of(f, set()) & touched) else regress(f, add, dele)
                if kind == "always":
                    x = r(phi)
                    if x is not None:
                        P.append(x)
                elif kind == "sometime":
                    x = r(phi)
                    if x is not None:
                        effects.append({"forall": [], "condition": x, "literal": hold(i)})
                elif kind == "at_most_once":
                    x = r(phi)
                    if x is not None:
                        effects.append({"forall": [], "condition": x, "literal": seen(i)})
                        P.append(mk_not(mk("and", [atom(seen(i)), mk_not(phi), x])))
                elif kind == "sometime_before":
                    x = r(psi)
                    if x is not None:
                        effects.append({"forall": [], "condition": x, "literal": seen(i)})
                    y = r(phi)
                    if y is not None:
                        P.append(mk("or", [mk_not(y), atom(seen(i))]))
                else:
                    x = r(psi)
                    if x is not None:
                        effects.append({"forall": [], "condition": x, "literal": hold(i)})
                    y = r(mk("and", [phi, mk_not(psi)]))
                    if y is not None:
                        effects.append({"forall": [], "condition": y,
                                        "literal": {**hold(i), "negated": True}})
            actions.append({"name": f"{a['name']}({','.join(vals)})", "params": [],
                            "precondition": mk("and", [pre] + P), "effects": effects})
    return {"objects": objects, "actions": actions,
            "init": [{"pred": p, "args": list(x)} for p, x in sorted(new_init)], "goal": mk("and", goal)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ground-actions", type=int, default=200000)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    task = json.loads(Path(args.input).read_text())
    try:
        compiled = compile_task(task, args.max_ground_actions)
    except SystemExit as exc:
        if exc.code == 3:
            print("ground-first compilation exceeds the ground-action budget", file=sys.stderr)
        raise
    Path(args.output).write_text(json.dumps(compiled, separators=(",", ":")))


if __name__ == "__main__":
    main()
