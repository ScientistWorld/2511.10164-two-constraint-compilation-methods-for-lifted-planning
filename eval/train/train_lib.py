"""Evaluator library (train slice).

Everything that is compared lives here and is owned by the evaluator:

* the constrained planning instances (random lifted domains with high-arity
  actions, conditional and universally quantified effects, and task-aware
  trajectory constraints), generated in memory from fixed seeds;
* the original-task semantics (plan replay and trajectory-constraint
  monitors) and the trajectories used to check compiled tasks;
* the ground-first comparator sizes (computed analytically from the task);
* the size metrics, the semantic gate and the worst values of a failed run.

A method only supplies a compiler command (``outputs/compilers/<name>.json``)
that maps one constrained task (JSON) to one constraint-free task (JSON).
"""
from __future__ import annotations

import itertools
import json
import math
import os
import random
import resource
import signal
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.setrecursionlimit(20000)

ROOT = Path(__file__).resolve().parents[2]
SLICE = "train"
SEED_BASE = 1_000_003

KINDS = ("always", "sometime", "at_most_once", "sometime_before", "sometime_after")
BINARY = ("sometime_before", "sometime_after")
TRUE = ("bool", True)
FALSE = ("bool", False)

COMPILE_TIMEOUT_S = 30
COMPILE_MEMORY_BYTES = 4 * 1024 ** 3
MAX_OUTPUT_BYTES = 32 * 1024 ** 2
AUX_DEPTH = 3
AUX_MAX_STATES = 64

EXPERIMENTS: Dict[str, Dict[str, Any]] = {
    "ground_constraints_size": dict(
        n=16, mode="probes", objects=(24, 32), fluents=(5, 8), schemas=(4, 6), arity=(2, 5), plan_len=(6, 10),
        n_constraints=(2, 6), quantified=0.0, alternatives=110, probes_max=40, initial_true=False),
    "nonground_constraints_size": dict(
        n=16, mode="probes", objects=(24, 32), fluents=(5, 8), schemas=(4, 6), arity=(2, 5), plan_len=(6, 10),
        n_constraints=(2, 6), quantified=1.0, alternatives=110, probes_max=40, initial_true=False),
    "many_constraints_size": dict(
        n=8, mode="probes", objects=(20, 28), fluents=(6, 8), schemas=(4, 6), arity=(2, 5), plan_len=(8, 12),
        n_constraints=(30, 45), quantified=0.5, alternatives=160, probes_max=90, initial_true=False),
    "constraint_type_suite": dict(
        n=24, mode="exhaustive", objects=(3, 4), fluents=(3, 4), schemas=(3, 4), arity=(1, 2), plan_len=(3, 5),
        n_constraints=(1, 3), quantified=0.5, alternatives=60, budget=20000, max_states=2500, initial_true=False),
    "initial_monitoring_edge_cases": dict(
        n=16, mode="exhaustive", objects=(3, 4), fluents=(3, 4), schemas=(3, 4), arity=(1, 2), plan_len=(3, 5),
        n_constraints=(1, 2), quantified=0.4, alternatives=60, budget=20000, max_states=2500, initial_true=True),
}
EXPERIMENT_ORDER = tuple(EXPERIMENTS)

METRICS = ("semantic_agreement", "effects_vs_ground_log10", "actions_vs_ground_log10",
           "formula_nodes_log10", "max_formula_nodes_log10")
WORST = {"semantic_agreement": 0.0, "effects_vs_ground_log10": 1.0, "actions_vs_ground_log10": 1.0,
         "formula_nodes_log10": 7.0, "max_formula_nodes_log10": 7.0}


class FormatError(Exception):
    pass


# ---------------------------------------------------------------------------
# Formulas: JSON <-> tuples, validation, evaluation, size
# ---------------------------------------------------------------------------

def _term(t: Any, bound: frozenset) -> str:
    if not isinstance(t, str) or not t:
        raise FormatError("terms must be non-empty strings")
    if t[0] == "?" and t not in bound:
        raise FormatError(f"unbound variable {t}")
    return t


def parse_literal(js: Any, bound: frozenset) -> Tuple[str, Tuple[str, ...], bool]:
    if not isinstance(js, dict) or not isinstance(js.get("pred"), str) or not js["pred"]:
        raise FormatError("literal needs a predicate name")
    args = js.get("args", [])
    if not isinstance(args, list):
        raise FormatError("literal args must be a list")
    neg = js.get("negated", False)
    if not isinstance(neg, bool):
        raise FormatError("literal 'negated' must be a bool")
    return js["pred"], tuple(_term(a, bound) for a in args), neg


def parse_formula(js: Any, bound: frozenset) -> tuple:
    if not isinstance(js, dict):
        raise FormatError("formula must be an object")
    op = js.get("op")
    if op == "bool":
        if not isinstance(js.get("value"), bool):
            raise FormatError("bool needs a boolean value")
        return TRUE if js["value"] else FALSE
    if op == "atom":
        pred, args, neg = parse_literal(js.get("literal"), bound)
        return ("atom", pred, args, neg)
    if op == "not":
        return ("not", parse_formula(js.get("child"), bound))
    if op in ("and", "or"):
        children = js.get("children")
        if not isinstance(children, list):
            raise FormatError(f"{op} needs a children list")
        return (op, tuple(parse_formula(c, bound) for c in children))
    if op == "imply":
        return ("imply", parse_formula(js.get("left"), bound), parse_formula(js.get("right"), bound))
    if op == "eq":
        return ("eq", _term(js.get("left"), bound), _term(js.get("right"), bound))
    if op in ("exists", "forall"):
        vs = js.get("vars")
        if not isinstance(vs, list) or not vs or not all(isinstance(v, str) and v.startswith("?") for v in vs):
            raise FormatError(f"{op} needs a non-empty list of ?variables")
        vs = tuple(dict.fromkeys(vs))
        child = parse_formula(js.get("child"), bound | frozenset(vs))
        return (op, vs, child, binders(child, frozenset(vs), op == "exists"))
    raise FormatError(f"unknown formula op {op!r}")


# --- exact quantifier evaluation by binding candidates ------------------------
# ``binders(f, vs, want)`` returns alternatives that together cover every
# assignment of ``vs`` under which ``f`` evaluates to ``want`` (or ``None`` when
# no restriction is known).  Each alternative is ("atom", pred, args) -- the
# assignment matches an atom of the current state -- or ("eq", var, term).
# Quantifiers then only enumerate covered assignments and still evaluate the
# full body for each, so the result is identical to enumerating every object.

def _cost(alts, vs) -> int:
    total = 0
    for b in alts:
        bound = {b[1]} if b[0] == "eq" else {a for a in b[2] if a in vs}
        total += (1 if b[0] == "eq" else 4) + 1000 * len(vs - bound)
    return total


def _best(options, vs):
    options = [o for o in options if o is not None]
    if not options:
        return None
    return min(options, key=lambda o: _cost(o, vs))


def _union(options):
    if any(o is None for o in options):
        return None
    return tuple(b for o in options for b in o)


def binders(f: tuple, vs: frozenset, want: bool):
    op = f[0]
    if op == "atom":
        if f[3] == want or not any(a in vs for a in f[2]):  # want true of a negated literal / want false of a positive one
            return None
        return (("atom", f[1], f[2]),)
    if op == "eq":
        if not want:
            return None
        l_in, r_in = f[1] in vs, f[2] in vs
        if l_in and not r_in:
            return (("eq", f[1], f[2]),)
        if r_in and not l_in:
            return (("eq", f[2], f[1]),)
        return None
    if op == "bool":
        return () if f[1] != want else None
    if op == "not":
        return binders(f[1], vs, not want)
    if op == "and":
        parts = [binders(c, vs, want) for c in f[1]]
        return _best(parts, vs) if want else _union(parts)
    if op == "or":
        parts = [binders(c, vs, want) for c in f[1]]
        return _union(parts) if want else _best(parts, vs)
    if op == "imply":
        if want:
            return _union([binders(f[1], vs, False), binders(f[2], vs, True)])
        return _best([binders(f[1], vs, True), binders(f[2], vs, False)], vs)
    return None


_IDX: Dict[frozenset, Dict[Any, Any]] = {}
_OBJSET: Dict[tuple, frozenset] = {}


def _index(st) -> Dict[Any, Any]:
    """Per-state index: pred -> [args], and lazily (pred, position) -> {value: [args]}."""
    idx = _IDX.get(st)
    if idx is None:
        if len(_IDX) > 4096:
            _IDX.clear()
        idx = {}
        for pred, args in st:
            lst = idx.get(pred)
            if lst is None:
                idx[pred] = [args]
            else:
                lst.append(args)
        _IDX[st] = idx
    return idx


def _by_position(idx, pred: str, pos: int) -> Dict[str, list]:
    key = (pred, pos)
    sub = idx.get(key)
    if sub is None:
        sub = {}
        for t in idx.get(pred, ()):
            if len(t) > pos:
                sub.setdefault(t[pos], []).append(t)
        idx[key] = sub
    return sub


def assignments(vs: tuple, alts, st, env: Dict[str, str], objs: Sequence[str]):
    """Yield dicts assigning ``vs`` that cover all assignments relevant for ``alts``."""
    if alts is None:
        for vals in itertools.product(objs, repeat=len(vs)):
            yield dict(zip(vs, vals))
        return
    objs = tuple(objs)
    objset = _OBJSET.get(objs)
    if objset is None:
        objset = _OBJSET[objs] = frozenset(objs)
    for b in alts:
        if b[0] == "eq":
            val = env.get(b[2], b[2])
            if val not in objset:
                continue
            fixed = {b[1]: val}
        else:
            fixed = None
        if fixed is not None:
            cands = (fixed,)
        else:
            args = b[2]
            n = len(args)
            cands = []
            idx = _index(st)
            pool = None
            for i, a in enumerate(args):
                if a not in vs:
                    pool = _by_position(idx, b[1], i).get(env.get(a, a), ())
                    break
            if pool is None:
                pool = idx.get(b[1], ())
            for t in pool:
                if len(t) != n:
                    continue
                d = {}
                for a, o in zip(args, t):
                    if a in vs:
                        if d.setdefault(a, o) != o or o not in objset:
                            d = None
                            break
                    elif env.get(a, a) != o:
                        d = None
                        break
                if d is not None:
                    cands.append(d)
        for d in cands:
            rest = [v for v in vs if v not in d]
            if not rest:
                yield d
            else:
                for vals in itertools.product(objs, repeat=len(rest)):
                    out = dict(d)
                    out.update(zip(rest, vals))
                    yield out


def annotate(f: tuple) -> tuple:
    """Re-parse a generator-built formula so that quantifier nodes carry binders."""
    return parse_formula(formula_js(f), frozenset())


def formula_js(f: tuple) -> Dict[str, Any]:
    op = f[0]
    if op == "bool":
        return {"op": "bool", "value": f[1]}
    if op == "atom":
        return {"op": "atom", "literal": {"pred": f[1], "args": list(f[2]), "negated": f[3]}}
    if op == "not":
        return {"op": "not", "child": formula_js(f[1])}
    if op in ("and", "or"):
        return {"op": op, "children": [formula_js(c) for c in f[1]]}
    if op == "imply":
        return {"op": "imply", "left": formula_js(f[1]), "right": formula_js(f[2])}
    if op == "eq":
        return {"op": "eq", "left": f[1], "right": f[2]}
    return {"op": op, "vars": list(f[1]), "child": formula_js(f[2])}


def ev(f: tuple, st, env: Dict[str, str], objs: Sequence[str]) -> bool:
    op = f[0]
    if op == "atom":
        args = f[2]
        key = (f[1], tuple([env.get(a, a) for a in args]) if args else ())
        return (key in st) != f[3]
    if op == "and":
        for c in f[1]:
            if not ev(c, st, env, objs):
                return False
        return True
    if op == "or":
        for c in f[1]:
            if ev(c, st, env, objs):
                return True
        return False
    if op == "not":
        return not ev(f[1], st, env, objs)
    if op == "imply":
        return (not ev(f[1], st, env, objs)) or ev(f[2], st, env, objs)
    if op == "eq":
        return env.get(f[1], f[1]) == env.get(f[2], f[2])
    if op == "bool":
        return f[1]
    want = op == "exists"
    e2 = dict(env)
    for d in assignments(f[1], f[3] if len(f) > 3 else None, st, env, objs):
        e2.update(d)
        if ev(f[2], st, e2, objs) == want:
            return want
    return not want


def nodes(f: tuple) -> int:
    op = f[0]
    if op in ("bool", "atom", "eq"):
        return 1
    if op == "not":
        return 1 + nodes(f[1])
    if op in ("and", "or"):
        return 1 + sum(nodes(c) for c in f[1])
    if op == "imply":
        return 1 + nodes(f[1]) + nodes(f[2])
    return 1 + nodes(f[2])


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class Task:
    """A parsed planning task. ``actions``: name -> (name, params, pre, effects).

    Each effect is ``(forall_vars, condition, pred, args, negated, binders)``.
    """

    def __init__(self, js: Dict[str, Any], objects: Optional[Sequence[str]] = None, allow_constraints: bool = True):
        if not isinstance(js, dict):
            raise FormatError("task must be a JSON object")
        if objects is None:
            objects = js.get("objects")
            if not isinstance(objects, list) or not objects or not all(isinstance(o, str) and o and o[0] != "?" for o in objects):
                raise FormatError("objects must be a non-empty list of constants")
        self.objects = tuple(objects)
        acts = js.get("actions")
        if not isinstance(acts, list):
            raise FormatError("actions must be a list")
        self.actions: Dict[str, tuple] = {}
        self.order: List[str] = []
        for a in acts:
            if not isinstance(a, dict) or not isinstance(a.get("name"), str) or not a["name"]:
                raise FormatError("action needs a name")
            name = a["name"]
            if name in self.actions:
                raise FormatError(f"duplicate action name {name}")
            params = a.get("params", [])
            if (not isinstance(params, list) or not all(isinstance(p, str) and p.startswith("?") for p in params)
                    or len(set(params)) != len(params)):
                raise FormatError(f"action {name}: params must be distinct ?variables")
            bound = frozenset(params)
            pre = parse_formula(a.get("precondition", {"op": "bool", "value": True}), bound)
            effs = []
            raw_effs = a.get("effects", [])
            if not isinstance(raw_effs, list):
                raise FormatError(f"action {name}: effects must be a list")
            for e in raw_effs:
                if not isinstance(e, dict):
                    raise FormatError("effect must be an object")
                fv = e.get("forall", [])
                if not isinstance(fv, list) or not all(isinstance(v, str) and v.startswith("?") for v in fv):
                    raise FormatError("effect forall must be a list of ?variables")
                b2 = bound | frozenset(fv)
                cond = parse_formula(e.get("condition", {"op": "bool", "value": True}), b2)
                pred, largs, neg = parse_literal(e.get("literal"), b2)
                fv = tuple(dict.fromkeys(fv))
                effs.append((fv, cond, pred, largs, neg, binders(cond, frozenset(fv), True) if fv else None))
            self.actions[name] = (name, tuple(params), pre, tuple(effs))
            self.order.append(name)
        init = js.get("init", [])
        if not isinstance(init, list):
            raise FormatError("init must be a list")
        atoms = set()
        for at in init:
            if not isinstance(at, dict) or not isinstance(at.get("pred"), str):
                raise FormatError("init atoms need a predicate")
            args = at.get("args", [])
            if not isinstance(args, list) or not all(isinstance(x, str) and x and x[0] != "?" for x in args):
                raise FormatError("init atom args must be constants")
            atoms.add((at["pred"], tuple(args)))
        self.init = frozenset(atoms)
        self.goal = parse_formula(js.get("goal"), frozenset())
        cons = js.get("constraints", [])
        if cons and not allow_constraints:
            raise FormatError("compiled task still contains trajectory constraints")
        self.constraints: List[Tuple[str, tuple, Optional[tuple]]] = []
        if allow_constraints:
            for c in cons:
                kind = c["kind"]
                phi = parse_formula(c["phi"], frozenset())
                psi = parse_formula(c["psi"], frozenset()) if kind in BINARY else None
                self.constraints.append((kind, phi, psi))


def apply(act: tuple, st: frozenset, args: Sequence[str], objs: Sequence[str]) -> Optional[frozenset]:
    _, params, pre, effs = act
    env = dict(zip(params, args)) if params else {}
    if not ev(pre, st, env, objs):
        return None
    adds: List[tuple] = []
    dels: List[tuple] = []
    for fv, cond, pred, largs, neg, alts in effs:
        if fv:
            e2 = dict(env)
            for d in assignments(fv, alts, st, env, objs):
                e2.update(d)
                if ev(cond, st, e2, objs):
                    (dels if neg else adds).append((pred, tuple([e2.get(x, x) for x in largs])))
        elif ev(cond, st, env, objs):
            (dels if neg else adds).append((pred, tuple([env.get(x, x) for x in largs])))
    if not adds and not dels:
        return st
    s = set(st)
    s.difference_update(dels)
    s.update(adds)
    return frozenset(s)


# --- original-task trajectory-constraint monitors -----------------------------

def mon_step(cons, m: Optional[tuple], s, objs) -> Optional[tuple]:
    """Advance the constraint monitors into state ``s``; ``None`` = irrevocably violated."""
    if m is None:
        return None
    out = []
    for (kind, phi, psi), v in zip(cons, m):
        if kind == "always":
            if not ev(phi, s, {}, objs):
                return None
            out.append(0)
        elif kind == "sometime":
            out.append(1 if v or ev(phi, s, {}, objs) else 0)
        elif kind == "at_most_once":
            if ev(phi, s, {}, objs):
                if v == 2:
                    return None
                out.append(1)
            else:
                out.append(2 if v == 1 else v)
        elif kind == "sometime_before":
            if not v and ev(phi, s, {}, objs):
                return None
            out.append(1 if v or ev(psi, s, {}, objs) else 0)
        else:  # sometime_after
            if ev(psi, s, {}, objs):
                out.append(0)
            elif ev(phi, s, {}, objs):
                out.append(1)
            else:
                out.append(v)
    return tuple(out)


def mon_accept(cons, m: Optional[tuple]) -> bool:
    if m is None:
        return False
    for (kind, _, _), v in zip(cons, m):
        if (kind == "sometime" and not v) or (kind == "sometime_after" and v):
            return False
    return True


def replay(task: Task, plan) -> Optional[List[frozenset]]:
    st = task.init
    trace = [st]
    for name, args in plan:
        act = task.actions.get(name)
        if act is None or len(act[1]) != len(args):
            return None
        st = apply(act, st, args, task.objects)
        if st is None:
            return None
        trace.append(st)
    return trace


def original_verdict(task: Task, plan) -> bool:
    trace = replay(task, plan)
    if trace is None or not ev(task.goal, trace[-1], {}, task.objects):
        return False
    m: Optional[tuple] = tuple(0 for _ in task.constraints)
    for s in trace:
        m = mon_step(task.constraints, m, s, task.objects)
    return mon_accept(task.constraints, m)


def holds_on_trace(kind: str, phi: tuple, psi: Optional[tuple], trace, objs) -> bool:
    """Direct (non-incremental) definition of each constraint family, Section 2.1."""
    pv = [ev(phi, s, {}, objs) for s in trace]
    if kind == "always":
        return all(pv)
    if kind == "sometime":
        return any(pv)
    if kind == "at_most_once":
        blocks = sum(1 for i, v in enumerate(pv) if v and (i == 0 or not pv[i - 1]))
        return blocks <= 1
    qv = [ev(psi, s, {}, objs) for s in trace]
    if kind == "sometime_before":
        return all(not p or any(qv[:i]) for i, p in enumerate(pv))
    return all(not p or any(qv[i:]) for i, p in enumerate(pv))


# ---------------------------------------------------------------------------
# Instance generator
# ---------------------------------------------------------------------------

def _atom(pred, args):
    return ("atom", pred, tuple(args), False)


def _lit(pred, args, neg):
    return ("atom", pred, tuple(args), neg)


def _and(*cs):
    return cs[0] if len(cs) == 1 else ("and", tuple(cs))


def gen_domain(rng: random.Random, cfg: Dict[str, Any]):
    n = rng.randint(*cfg["objects"])
    objs = tuple(f"o{i}" for i in range(n))
    nf = rng.randint(*cfg["fluents"])
    fluents = []
    for j in range(nf):
        ar = rng.choice((0, 1, 1, 2, 2, 2, 3))
        fluents.append((f"f{j}", ar))
    if not any(a == 1 for _, a in fluents):
        fluents.append((f"f{len(fluents)}", 1))
    if not any(a == 2 for _, a in fluents):
        fluents.append((f"f{len(fluents)}", 2))
    init = set()
    s0 = [o for o in objs if rng.random() < 0.6] or objs[:2]
    init.update(("s0", (o,)) for o in s0)
    for o in objs:
        for t in rng.sample(objs, min(3, n)):
            if t != o:
                init.add(("s1", (o, t)))
    for f, ar in fluents:
        if ar == 0:
            if rng.random() < 0.5:
                init.add((f, ()))
        elif ar == 1:
            init.update((f, (o,)) for o in objs if rng.random() < 0.35)
        else:
            for _ in range(2 * n):
                init.add((f, tuple(rng.choice(objs) for _ in range(ar))))
    ns = rng.randint(*cfg["schemas"])
    lo, hi = cfg["arity"]
    arities = [rng.randint(lo, hi) for _ in range(ns)]
    arities[rng.randrange(ns)] = hi  # at least one schema of maximal arity
    actions, meta = [], []
    for i, k in enumerate(arities):
        js, binds = gen_schema(rng, f"act{i}", k, fluents, n)
        actions.append(js)
        meta.append(binds)
    preds = {f: a for f, a in fluents}
    preds.update({"s0": 1, "s1": 2})
    return objs, fluents, init, actions, meta, preds


def gen_schema(rng: random.Random, name: str, k: int, fluents, n: int):
    P = [f"?x{j}" for j in range(k)]
    fits = [f for f in fluents if f[1] <= k]
    pos = [f for f in fits if f[1] >= 1]
    used = set()
    pre, binds, effs = [], [], []
    F, ar = rng.choice(pos)
    a1 = tuple(rng.sample(P, ar))
    pre.append(_atom(F, a1))
    binds.append((F, a1))
    used.update(a1)
    if k >= 2 and rng.random() < 0.55:
        i, j = rng.sample(P, 2)
        pre.append(_atom("s1", (i, j)))
        binds.append(("s1", (i, j)))
        used.update((i, j))
    if rng.random() < 0.3:
        G, gar = rng.choice(fits)
        ga = tuple(rng.sample(P, gar))
        if (G, ga) != (F, a1):
            pre.append(_lit(G, ga, True))
            used.update(ga)
    if rng.random() < 0.7:
        effs.append(((), TRUE, F, a1, True))
    for _ in range(rng.randint(1, 2)):
        G, gar = rng.choice(fits)
        ga = tuple(rng.sample(P, gar))
        effs.append(((), TRUE, G, ga, False))
        used.update(ga)
    if rng.random() < 0.45:
        C, car = rng.choice(fits)
        ca = tuple(rng.sample(P, car))
        E, ear = rng.choice(fits)
        ea = tuple(rng.sample(P, ear))
        effs.append(((), _lit(C, ca, rng.random() < 0.4), E, ea, rng.random() < 0.4))
        used.update(ca + ea)
    binaries = [f for f, a in fluents if a == 2]
    if rng.random() < 0.35 and binaries:
        H = rng.choice(binaries)
        p = rng.choice(P)
        z = "?z0"
        unary = [f for f, a in fluents if a == 1]
        if unary and rng.random() < 0.6:
            effs.append(((z,), _atom(H, (z, p)), rng.choice(unary), (z,), rng.random() < 0.5))
        else:
            effs.append(((z,), _atom(H, (z, p)), H, (z, p), True))
        used.add(p)
    for p in P:
        if p not in used:
            pre.append(_atom("s0", (p,)))
            binds.append(("s0", (p,)))
    js = {
        "name": name,
        "params": P,
        "precondition": formula_js(_and(*pre)),
        "effects": [{"forall": list(fv), "condition": formula_js(c), "literal": {"pred": pr, "args": list(a), "negated": ng}}
                    for fv, c, pr, a, ng in effs],
    }
    return js, binds


class Sampler:
    """Draws random applicable ground actions by joining positive preconditions with the state."""

    def __init__(self, task: Task, meta) -> None:
        self.task = task
        self.meta = meta
        self.cache: Dict[frozenset, Dict[str, list]] = {}

    def index(self, st: frozenset) -> Dict[str, list]:
        idx = self.cache.get(st)
        if idx is None:
            idx = {}
            for pred, args in sorted(st):
                idx.setdefault(pred, []).append(args)
            if len(self.cache) > 4000:
                self.cache.clear()
            self.cache[st] = idx
        return idx

    def step(self, rng: random.Random, st: frozenset, tries: int = 50, allow_noop: bool = True):
        idx = self.index(st)
        objs = self.task.objects
        fallback = None
        for _ in range(tries):
            ai = rng.randrange(len(self.task.order))
            act = self.task.actions[self.task.order[ai]]
            binding: Dict[str, str] = {}
            ok = True
            for pred, largs in self.meta[ai]:
                cands = [t for t in idx.get(pred, ()) if all(binding.get(v, o) == o for v, o in zip(largs, t))]
                if not cands:
                    ok = False
                    break
                for v, o in zip(largs, rng.choice(cands)):
                    binding[v] = o
            if not ok:
                continue
            args = tuple(binding[p] if p in binding else rng.choice(objs) for p in act[1])
            nxt = apply(act, st, args, objs)
            if nxt is None:
                continue
            if nxt == st and not allow_noop:
                fallback = fallback or ((act[0], args), nxt)
                continue
            return (act[0], args), nxt
        return fallback if fallback else (None, None)

    def walk(self, rng, st, length, allow_noop=True):
        plan = []
        for _ in range(length):
            step, nxt = self.step(rng, st, allow_noop=allow_noop)
            if step is None:
                break
            plan.append(step)
            st = nxt
        return plan, st


def _mutate(rng: random.Random, sampler: Sampler, task: Task, W, wtrace):
    r = rng.random()
    L = len(W)
    if r < 0.5:  # detours
        cuts = sorted(rng.randrange(L + 1) for _ in range(rng.randint(1, 3)))
        plan, st, alive, ci = [], task.init, True, 0
        for i in range(L + 1):
            while ci < len(cuts) and cuts[ci] == i:
                ci += 1
                if alive:
                    step, nxt = sampler.step(rng, st, allow_noop=False)
                    if step is not None:
                        plan.append(step)
                        st = nxt
            if i < L:
                plan.append(W[i])
                if alive:
                    nxt = apply(task.actions[W[i][0]], st, W[i][1], task.objects)
                    alive = nxt is not None
                    st = nxt if alive else st
        return plan
    if r < 0.6 and L >= 2:  # drop a step
        j = rng.randrange(L)
        return W[:j] + W[j + 1:]
    if r < 0.7 and L >= 2:  # swap neighbours
        j = rng.randrange(L - 1)
        return W[:j] + [W[j + 1], W[j]] + W[j + 2:]
    if r < 0.85:  # prefix + random continuation
        j = rng.randint(0, L)
        tail, _ = sampler.walk(rng, wtrace[j], rng.randint(1, L + 2), allow_noop=False)
        return W[:j] + tail
    if r < 0.93:  # witness + extra steps after reaching the goal
        tail, _ = sampler.walk(rng, wtrace[-1], rng.randint(1, 3), allow_noop=False)
        return W + tail
    plan, _ = sampler.walk(rng, task.init, max(1, L + rng.randint(-2, 3)), allow_noop=False)
    return plan


def _changing_atoms(traces) -> List[tuple]:
    count: Dict[tuple, int] = {}
    total = 0
    for tr in traces:
        for s in tr:
            total += 1
            for a in s:
                count[a] = count.get(a, 0) + 1
    return sorted(a for a, c in count.items() if c < total and a[0] not in ("s0", "s1"))


def _rand_lit(rng, atoms):
    pred, args = rng.choice(atoms)
    return _lit(pred, args, rng.random() < 0.35)


def _ground_formula(rng, atoms):
    r = rng.random()
    if r < 0.5 or len(atoms) < 2:
        return _rand_lit(rng, atoms)
    a, b = _rand_lit(rng, atoms), _rand_lit(rng, atoms)
    if a[1:3] == b[1:3]:
        return a
    return ("and", (a, b)) if r < 0.75 else ("or", (a, b))


VAR_POOLS = (("?q0", "?q1"), ("?q0", "?q1"), ("?q0", "?q1"), ("?x0", "?z0"))  # occasional clash with domain names


def _quant_formula(rng, atoms):
    cands = [a for a in atoms if len(a[1]) >= 1]
    if not cands:
        return _ground_formula(rng, atoms)
    pred, args = rng.choice(cands)
    names = rng.choice(VAR_POOLS)
    npos = 2 if len(args) >= 2 and rng.random() < 0.3 else 1
    pos = rng.sample(range(len(args)), npos)
    vs = tuple(names[:npos])
    body_args = list(args)
    for p, v in zip(pos, vs):
        body_args[p] = v
    body = _atom(pred, body_args)
    other = [a for a in cands if a[0] != pred] or cands
    p2, a2 = rng.choice(other)
    a2 = list(a2)
    a2[rng.randrange(len(a2))] = vs[0]
    body2 = _lit(p2, a2, rng.random() < 0.3)
    r = rng.random()
    if r < 0.35:
        f = ("exists", vs, body)
    elif r < 0.6:
        f = ("forall", vs, ("not", body))
    elif r < 0.8:
        f = ("exists", vs, ("and", (body, body2)))
    else:
        f = ("forall", vs, ("imply", body, body2))
    return ("not", f) if rng.random() < 0.15 else f


def _formula(rng, atoms, quantified: bool):
    return _quant_formula(rng, atoms) if quantified else _ground_formula(rng, atoms)


def _edge_ok(kind, phi, psi, s0, objs) -> bool:
    if kind in ("at_most_once", "sometime"):
        return ev(phi, s0, {}, objs)
    if kind == "sometime_before":
        return ev(psi, s0, {}, objs) and not ev(phi, s0, {}, objs)
    if kind == "sometime_after":
        return ev(phi, s0, {}, objs) or ev(psi, s0, {}, objs)
    return True


def build_instance(seed: int, cfg: Dict[str, Any], index: int) -> Dict[str, Any]:
    for k in range(8):  # deterministic fallback seeds
        rng = random.Random(seed + 15_485_863 * k)
        for _attempt in range(60):
            try:
                inst = _try_build(rng, cfg, index)
            except (ValueError, IndexError, AssertionError):
                inst = None
            if inst is not None:
                return inst
    raise RuntimeError(f"could not generate instance for seed {seed}")


def _try_build(rng: random.Random, cfg: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
    objs, fluents, init, actions, meta, preds = gen_domain(rng, cfg)
    base = {"objects": list(objs), "predicates": preds, "actions": actions,
            "init": [{"pred": p, "args": list(a)} for p, a in sorted(init)], "goal": {"op": "bool", "value": True}}
    task = Task(base)
    sampler = Sampler(task, meta)
    L = rng.randint(*cfg["plan_len"])
    W, _ = sampler.walk(rng, task.init, L, allow_noop=False)
    if len(W) < L:
        return None
    wtrace = replay(task, W)
    fluent_names = {f for f, _ in fluents}
    goal_cands = sorted(a for a in wtrace[-1] - wtrace[0] if a[0] in fluent_names)
    if not goal_cands:
        return None
    goal_atoms = rng.sample(goal_cands, rng.randint(1, min(3, len(goal_cands))))
    goal = _and(*[_atom(p, a) for p, a in sorted(goal_atoms)])
    task.goal = goal
    plans = [_mutate(rng, sampler, task, W, wtrace) for _ in range(cfg["alternatives"])]
    reach, other_goal_free, inapplicable = [], [], []
    seen_plans = {tuple(W)}
    for p in plans:
        key = tuple(p)
        if key in seen_plans or not p:
            continue
        seen_plans.add(key)
        tr = replay(task, p)
        if tr is None:
            inapplicable.append(p)
        elif ev(goal, tr[-1], {}, objs):
            reach.append((p, tr))
        else:
            other_goal_free.append(p)
    if len(reach) < 6:
        return None
    atoms = _changing_atoms([wtrace] + [tr for _, tr in reach])
    if len(atoms) < 3:
        return None
    s0 = task.init
    want = rng.randint(*cfg["n_constraints"])
    kinds_cycle = list(KINDS) if not cfg["initial_true"] else ["at_most_once", "sometime_before", "sometime", "sometime_after"]
    offset = index % len(kinds_cycle)
    constraints, violators, keys = [], [], set()
    edge_atoms = sorted(a for a in s0 if a[0] in fluent_names and a in set(atoms)) or sorted(
        a for a in s0 if a[0] in fluent_names)
    attempts = 0
    while len(constraints) < want and attempts < want * 60:
        kind = kinds_cycle[(offset + len(constraints) + attempts // 25) % len(kinds_cycle)] if (
            cfg["initial_true"] and not constraints) else KINDS[(offset + len(constraints) + attempts // 25) % 5]
        attempts += 1
        quant = rng.random() < cfg["quantified"]
        edge = cfg["initial_true"] and not constraints
        pool = edge_atoms if edge and kind in ("at_most_once", "sometime", "sometime_after") and edge_atoms else atoms
        phi = _formula(rng, pool, quant)
        psi = None
        if kind in BINARY:
            pool_psi = edge_atoms if edge and kind == "sometime_before" and edge_atoms else atoms
            psi = _formula(rng, pool_psi, rng.random() < cfg["quantified"])
        phi = annotate(phi)
        psi = annotate(psi) if psi is not None else None
        key = (kind, phi, psi)
        if key in keys:
            continue
        if edge and not _edge_ok(kind, phi, psi, s0, objs):
            continue
        if not holds_on_trace(kind, phi, psi, wtrace, objs):
            continue
        viol = []
        order = list(range(len(reach)))
        rng.shuffle(order)
        for i in order:
            if not holds_on_trace(kind, phi, psi, reach[i][1], objs):
                viol.append(i)
                if len(viol) >= 3:
                    break
        if not viol and not (edge and attempts > 40):
            continue
        keys.add(key)
        constraints.append(key)
        violators.append(viol)
    if len(constraints) < max(1, int(0.6 * want)):
        return None
    problem = dict(base)
    problem["goal"] = formula_js(goal)
    problem["constraints"] = [{"name": f"c{i}", "kind": k, "phi": formula_js(f),
                               **({"psi": formula_js(g)} if g is not None else {})}
                              for i, (k, f, g) in enumerate(constraints)]
    task = Task(problem)
    assert original_verdict(task, W), "witness plan must be valid"
    if cfg["mode"] == "exhaustive":
        size = reachable_states(task, cfg["max_states"] + 1)
        if size > cfg["max_states"] or size < 12:
            return None  # keep the exhaustive check complete (and non-trivial)
    inst: Dict[str, Any] = {"problem": problem, "n_constraints": len(constraints),
                            "kinds": [k for k, _, _ in constraints]}
    if cfg["mode"] == "probes":
        probes = [W]
        chosen = {tuple(W)}
        for rnd in range(2):
            for viol in violators:
                if rnd < len(viol):
                    p = reach[viol[rnd]][0]
                    if tuple(p) not in chosen:
                        chosen.add(tuple(p))
                        probes.append(p)
        valid = [p for p, _ in reach if tuple(p) not in chosen and original_verdict(task, p)]
        rng.shuffle(valid)
        extra = valid[:10] + other_goal_free[:4] + inapplicable[:3]
        for p in extra:
            if tuple(p) not in chosen:
                chosen.add(tuple(p))
                probes.append(p)
        probes = probes[:cfg["probes_max"]]
        inst["probes"] = [(p, original_verdict(task, p)) for p in probes]
    return inst


def reachable_states(task: Task, cap: int) -> int:
    """Number of reachable (state, constraint-monitor) pairs of the original task, up to ``cap``."""
    objs = task.objects
    steps = [(n, a) for n in task.order for a in itertools.product(objs, repeat=len(task.actions[n][1]))]
    m0 = mon_step(task.constraints, tuple(0 for _ in task.constraints), task.init, objs)
    if m0 is None:
        return 0
    seen = {(task.init, m0)}
    queue = deque(seen)
    while queue and len(seen) < cap:
        o, m = queue.popleft()
        for name, args in steps:
            o2 = apply(task.actions[name], o, args, objs)
            if o2 is None:
                continue
            m2 = mon_step(task.constraints, m, o2, objs)
            if m2 is not None and (o2, m2) not in seen:
                seen.add((o2, m2))
                queue.append((o2, m2))
    return len(seen)


def ground_comparator(task: Task) -> Tuple[int, int]:
    """Size of the fully grounded (unconstrained) task: actions and conditional effects."""
    n = len(task.objects)
    g_actions = g_effects = 0
    for _, params, _, effs in task.actions.values():
        cnt = n ** len(params)
        g_actions += cnt
        g_effects += cnt * sum(n ** len(fv) for fv, *_ in effs)
    return g_actions, g_effects


def generate_all(experiments: Optional[Sequence[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    out = {}
    for ei, exp in enumerate(EXPERIMENT_ORDER):
        if experiments and exp not in experiments:
            continue
        cfg = EXPERIMENTS[exp]
        insts = []
        for i in range(cfg["n"]):
            inst = build_instance(SEED_BASE + 7919 * ei + 104_729 * i, cfg, i)
            inst["task"] = Task(inst["problem"])
            inst["ground"] = ground_comparator(inst["task"])
            inst["memo"] = {}
            insts.append(inst)
        out[exp] = insts
    return out


# ---------------------------------------------------------------------------
# Compiled tasks and the semantic gate
# ---------------------------------------------------------------------------

class Compiled:
    def __init__(self, js: Any, orig: Task):
        self.task = Task(js, objects=orig.objects, allow_constraints=False)
        self.orig = orig
        self.lifted: Dict[str, tuple] = {}
        self.ground: Dict[str, tuple] = {}
        self.aux: List[tuple] = []
        for name in self.task.order:
            act = self.task.actions[name]
            if name in orig.actions:
                if len(act[1]) != len(orig.actions[name][1]):
                    raise FormatError(f"action {name} changed its arity")
                self.lifted[name] = act
            elif "(" in name and name.split("(", 1)[0] in orig.actions:
                if act[1]:
                    raise FormatError(f"ground action {name} must not have parameters")
                self.ground[name] = act
            else:
                if act[1]:
                    raise FormatError(f"auxiliary action {name} must not have parameters")
                self.aux.append(act)

    def lookup(self, name: str, args: Tuple[str, ...]):
        act = self.lifted.get(name)
        if act is not None:
            return act, args
        act = self.ground.get(f"{name}({','.join(args)})")
        if act is not None:
            return act, ()
        return None, None

    def closure(self, states) -> frozenset:
        states = frozenset(states)
        if not self.aux or not states:
            return states
        seen = set(states)
        frontier = list(states)
        objs = self.task.objects
        for _ in range(AUX_DEPTH):
            nxt = []
            for s in frontier:
                for a in self.aux:
                    r = apply(a, s, (), objs)
                    if r is not None and r not in seen and len(seen) < AUX_MAX_STATES:
                        seen.add(r)
                        nxt.append(r)
            frontier = nxt
            if not frontier:
                break
        return frozenset(seen)

    def step(self, states: frozenset, name: str, args: Tuple[str, ...]) -> frozenset:
        act, a = self.lookup(name, args)
        if act is None or not states:
            return frozenset()
        objs = self.task.objects
        out = set()
        for s in states:
            r = apply(act, s, a, objs)
            if r is not None:
                out.add(r)
        return self.closure(out)

    def accepts(self, states: frozenset) -> bool:
        objs = self.task.objects
        return any(ev(self.task.goal, s, {}, objs) for s in states)

    def verdict(self, plan) -> bool:
        S = self.closure([self.task.init])
        for name, args in plan:
            S = self.step(S, name, tuple(args))
            if not S:
                return False
        return self.accepts(S)


def check_probes(comp: Compiled, inst: Dict[str, Any]):
    agree = 0
    for plan, expected in inst["probes"]:
        if comp.verdict(plan) == expected:
            agree += 1
        else:
            return agree, len(inst["probes"]), {"plan": plan, "expected": expected}
    return agree, len(inst["probes"]), None


def check_exhaustive(comp: Compiled, inst: Dict[str, Any], budget: int):
    """Breadth-first exploration of the product of the original task (with its
    constraint monitors) and the compiled task over every ground action sequence;
    acceptance must agree in every reached product state (bounded by ``budget``)."""
    task = inst["task"]
    objs = task.objects
    cons = task.constraints
    memo = inst["memo"]
    steps = inst.get("steps")
    if steps is None:
        steps = [(name, args) for name in task.order
                 for args in itertools.product(objs, repeat=len(task.actions[name][1]))]
        inst["steps"] = steps
    m0 = mon_step(cons, tuple(0 for _ in cons), task.init, objs)
    o0 = task.init if m0 is not None else None
    S0 = comp.closure([comp.task.init])
    start = (o0, m0, S0)

    def orig_accept(o, m):
        return o is not None and mon_accept(cons, m) and ev(task.goal, o, {}, objs)

    checks = 1
    if orig_accept(o0, m0) != comp.accepts(S0):
        return 0, 1, {"plan": [], "expected": orig_accept(o0, m0)}
    seen = {start}
    queue = deque([(start, ())])
    while queue:
        (o, m, S), path = queue.popleft()
        for step in steps:
            if o is not None:
                key = (o, m, step)
                res = memo.get(key)
                if res is None:
                    o2 = apply(task.actions[step[0]], o, step[1], objs)
                    m2 = mon_step(cons, m, o2, objs) if o2 is not None else None
                    res = (o2, m2) if m2 is not None else (None, None)
                    memo[key] = res
                o2, m2 = res
            else:
                o2, m2 = None, None
            S2 = comp.step(S, step[0], step[1]) if S else frozenset()
            if o2 is None and not S2:
                continue
            node = (o2, m2, S2)
            if node in seen:
                continue
            checks += 1
            exp = orig_accept(o2, m2)
            if exp != comp.accepts(S2):
                return checks - 1, checks, {"plan": list(path) + [step], "expected": exp}
            if len(seen) < budget:
                seen.add(node)
                queue.append((node, path + (step,)))
            else:
                inst["truncated"] = inst.get("truncated", 0) + 1
    return checks, checks, None


# ---------------------------------------------------------------------------
# Size metrics
# ---------------------------------------------------------------------------

def size_metrics(comp: Compiled, inst: Dict[str, Any]) -> Dict[str, float]:
    t = comp.task
    acts = [t.actions[n] for n in t.order]
    formulas = [a[2] for a in acts] + [e[1] for a in acts for e in a[3]] + [t.goal]
    sizes = [nodes(f) for f in formulas]
    total = sum(sizes) + len(t.init ^ inst["task"].init)
    n_eff = sum(len(a[3]) for a in acts)
    g_act, g_eff = inst["ground"]
    return {
        "effects_vs_ground_log10": min(WORST["effects_vs_ground_log10"], math.log10(max(n_eff, 1) / g_eff)),
        "actions_vs_ground_log10": min(WORST["actions_vs_ground_log10"], math.log10(max(len(acts), 1) / g_act)),
        "formula_nodes_log10": min(WORST["formula_nodes_log10"], math.log10(max(total, 1))),
        "max_formula_nodes_log10": min(WORST["max_formula_nodes_log10"], math.log10(max(max(sizes), 1))),
        "_effects": n_eff, "_actions": len(acts), "_formula_nodes": total, "_max_formula_nodes": max(sizes),
    }


# ---------------------------------------------------------------------------
# Running registered compilers
# ---------------------------------------------------------------------------

def _limit_resources() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (COMPILE_MEMORY_BYTES, COMPILE_MEMORY_BYTES))
    except (ValueError, OSError):
        pass


def run_compiler(cmd: List[str], problem: Dict[str, Any]):
    with tempfile.TemporaryDirectory(prefix="compile_") as d:
        inp, out = Path(d) / "problem.json", Path(d) / "compiled.json"
        inp.write_text(json.dumps(problem))
        try:
            proc = subprocess.Popen(cmd + [str(inp), str(out)], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    start_new_session=True, preexec_fn=_limit_resources)
        except OSError as exc:
            return None, f"cannot start compiler: {exc}"
        try:
            _, err = proc.communicate(timeout=COMPILE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.communicate()
            return None, f"timeout after {COMPILE_TIMEOUT_S}s"
        if proc.returncode != 0:
            tail = (err or b"").decode(errors="replace").strip().splitlines()[-1:] or [""]
            return None, f"compiler exited with code {proc.returncode}: {tail[0][:200]}"
        if not out.is_file():
            return None, "compiler wrote no output"
        if out.stat().st_size > MAX_OUTPUT_BYTES:
            return None, f"compiled task larger than {MAX_OUTPUT_BYTES} bytes"
        try:
            return json.loads(out.read_text()), None
        except (ValueError, UnicodeDecodeError):
            return None, "compiled task is not valid JSON"


def registered(registry: Path) -> List[Tuple[str, Optional[List[str]], Optional[str]]]:
    out = []
    for p in sorted(registry.glob("*.json")) if registry.is_dir() else []:
        name = p.stem if not p.stem.startswith("_") else "unnamed" + p.stem
        try:
            cmd = json.loads(p.read_text())["command"]
            if not isinstance(cmd, list) or not cmd or not all(isinstance(c, str) for c in cmd):
                raise ValueError
            out.append((name, cmd, None))
        except (ValueError, KeyError, TypeError, OSError):
            out.append((name, None, "invalid registration (need {\"command\": [..]})"))
    return out


def evaluate_method(cmd: List[str], instances: Dict[str, List[Dict[str, Any]]], verbose: bool, log=print):
    """Returns (per-experiment metrics, failure dict or None, diagnostics)."""
    per_exp: Dict[str, Dict[str, float]] = {}
    diag: Dict[str, Any] = {}
    for exp in EXPERIMENT_ORDER:
        if exp not in instances:
            continue
        cfg = EXPERIMENTS[exp]
        agree = checks = 0
        rows = []
        for i, inst in enumerate(instances[exp]):
            js, err = run_compiler(cmd, inst["problem"])
            if err is None:
                try:
                    comp = Compiled(js, inst["task"])
                except FormatError as exc:
                    err = f"malformed compiled task: {exc}"
                except (RecursionError, KeyError, TypeError, ValueError) as exc:
                    err = f"malformed compiled task: {type(exc).__name__}"
            if err is not None:
                return None, {"experiment": exp, "instance": i, "reason": err}, diag
            try:
                if cfg["mode"] == "probes":
                    a, c, cex = check_probes(comp, inst)
                else:
                    a, c, cex = check_exhaustive(comp, inst, cfg["budget"])
            except (RecursionError, KeyError, TypeError, ValueError) as exc:
                return None, {"experiment": exp, "instance": i, "reason": f"compiled task not executable: {type(exc).__name__}"}, diag
            agree += a
            checks += c
            if cex is not None:
                fail = {"experiment": exp, "instance": i, "reason": "compiled task does not preserve the constrained task's valid plans"}
                if verbose:
                    fail["counterexample"] = cex
                return None, fail, diag
            rows.append(size_metrics(comp, inst))
        res = {"semantic_agreement": agree / checks if checks else 0.0}
        for m in METRICS[1:]:
            res[m] = sum(r[m] for r in rows) / len(rows)
        per_exp[exp] = res
        diag[exp] = {"checks": checks,
                     "truncated_explorations": sum(1 for inst in instances[exp] if inst.get("truncated")),
                     **{k: sum(r[k] for r in rows) / len(rows)
                        for k in ("_effects", "_actions", "_formula_nodes", "_max_formula_nodes")},
                     "per_instance": [[round(r[m], 6) for m in METRICS[1:]] for r in rows]}
        log(f"  {exp}: " + ", ".join(f"{k}={v:.4f}" for k, v in res.items()))
    return per_exp, None, diag


def describe(instances) -> Dict[str, Any]:
    out = {}
    for exp, insts in instances.items():
        kinds = {k: 0 for k in KINDS}
        for inst in insts:
            for k in inst["kinds"]:
                kinds[k] += 1
        out[exp] = {
            "instances": len(insts),
            "mode": EXPERIMENTS[exp]["mode"],
            "mean_objects": sum(len(i["task"].objects) for i in insts) / len(insts),
            "mean_constraints": sum(i["n_constraints"] for i in insts) / len(insts),
            "mean_ground_actions": sum(i["ground"][0] for i in insts) / len(insts),
            "constraint_kinds": kinds,
            "quantified_constraints": sum(1 for i in insts for c in i["problem"]["constraints"]
                                          if "exists" in json.dumps(c) or "forall" in json.dumps(c)),
        }
        if EXPERIMENTS[exp]["mode"] == "probes":
            out[exp]["mean_probes"] = sum(len(i["probes"]) for i in insts) / len(insts)
            out[exp]["mean_invalid_probes"] = sum(sum(1 for _, v in i["probes"] if not v) for i in insts) / len(insts)
    return out


def score_all(registry: Path, verbose: bool, experiments: Optional[Sequence[str]] = None, log=print) -> Dict[str, Any]:
    instances = generate_all(experiments)
    log(f"[{SLICE}] generated " + ", ".join(f"{e}={len(v)}" for e, v in instances.items()))
    methods = registered(registry)
    results: Dict[str, Dict[str, Dict[str, float]]] = {exp: {} for exp in instances}
    meta_methods: Dict[str, Any] = {}
    if not methods:
        methods = [("missing_submission", None, "no compiler registered in " + str(registry.relative_to(ROOT) if registry.is_relative_to(ROOT) else registry))]
    for name, cmd, reg_err in methods:
        log(f"[{SLICE}] method {name}")
        if cmd is None:
            per_exp, fail, diag = None, {"reason": reg_err}, {}
        else:
            per_exp, fail, diag = evaluate_method(cmd, instances, verbose, log)
        if fail is not None:
            log(f"  FAILED: {fail}")
            for exp in instances:
                results[exp][name] = dict(WORST)
            meta_methods[name] = {"status": "failed", **fail}
        else:
            for exp in instances:
                results[exp][name] = per_exp[exp]
            meta_methods[name] = {"status": "ok", "diagnostics": diag}
    return {
        "_metadata": {
            "slice": SLICE,
            "registry": str(registry),
            "worst_values": WORST,
            "experiments": describe(instances),
            "methods": meta_methods,
        },
        "experiments": {exp: {"results": results[exp]} for exp in instances},
    }
