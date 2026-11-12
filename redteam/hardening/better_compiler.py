"""A genuinely better LiftedTCORE variant used to test the gym's headroom.

Invariant-aware regression: LiftedTCORE's monitoring preconditions are only
ever evaluated in reachable states of the compiled task, where facts implied
by the monitoring are known:

* Always(phi): phi holds in the current state (initial check + R(phi,a) precondition);
* SometimeBefore(phi, psi): if seen_psi is false then phi is false (otherwise the
  constraint was already violated), so inside ``R(phi,a) -> seen_psi`` we may
  assume not phi;
* AtMostOnce(phi): inside ``not(seen and not phi and R(phi,a))`` not phi is asserted.

Literals fixed by such knowledge (conjunctive literals, universally quantified
literals) let the persistence part ``f and not Gamma_{not f}`` of R^L(f, a)
fold to a constant.  The compiled task has the same valid plans.  The generic
Boolean simplifier of the earlier audit is applied afterwards.

Usage: python redteam/hardening/better_compiler.py IN.json OUT.json
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "method"))
sys.path.insert(0, str(ROOT / "redteam"))
sys.setrecursionlimit(10000)

from optimize import optimize_problem  # noqa: E402
from planning import (FALSE, And, Atom, Effect, Exists, ForAll, Imply, Not, Or, Problem,  # noqa: E402
                      _dedupe, _Monitors, _prepared_constraints, _unsolvable, affected, lifted_gamma,
                      make_and, make_not, make_or, regress)
from pjson import problem_from_json, problem_to_json  # noqa: E402


def knowledge(phi, positive=True, kt=None, kf=None):
    """Literals fixed whenever ``phi`` (or not phi if positive=False) holds."""
    kt = set() if kt is None else kt
    kf = set() if kf is None else kf
    if isinstance(phi, Atom):
        lit = phi.lit
        is_true = (not lit.negated) == positive
        (kt if is_true else kf).add(lit.positive())
    elif isinstance(phi, Not):
        knowledge(phi.child, not positive, kt, kf)
    elif isinstance(phi, And) and positive or isinstance(phi, Or) and not positive:
        for c in phi.children:
            knowledge(c, positive, kt, kf)
    elif isinstance(phi, ForAll) and positive or isinstance(phi, Exists) and not positive:
        knowledge(phi.child, positive, kt, kf)  # bound variables are unique after renaming apart
    elif isinstance(phi, Imply) and not positive:  # not(A -> B) == A and not B
        knowledge(phi.left, True, kt, kf)
        knowledge(phi.right, False, kt, kf)
    return kt, kf


def regress_k(formula, action, kt, kf):
    if not affected(formula, action):
        return formula
    if isinstance(formula, Atom):
        lit = formula.lit
        if lit.negated:
            return make_not(regress_k(Atom(lit.positive()), action, kt, kf))
        add = lifted_gamma(lit, action)
        if lit in kf:
            return add
        if lit in kt:
            return make_or(add, make_not(lifted_gamma(lit.negate(), action)))
        return make_or(add, make_and(Atom(lit), make_not(lifted_gamma(lit.negate(), action))))
    if isinstance(formula, Not):
        return make_not(regress_k(formula.child, action, kt, kf))
    if isinstance(formula, And):
        return make_and(*(regress_k(c, action, kt, kf) for c in formula.children))
    if isinstance(formula, Or):
        return make_or(*(regress_k(c, action, kt, kf) for c in formula.children))
    if isinstance(formula, Imply):
        return Imply(regress_k(formula.left, action, kt, kf), regress_k(formula.right, action, kt, kf))
    if isinstance(formula, Exists):
        return Exists(formula.vars, regress_k(formula.child, action, kt, kf))
    if isinstance(formula, ForAll):
        return ForAll(formula.vars, regress_k(formula.child, action, kt, kf))
    return formula


def compile_invariant_tcore(problem: Problem) -> Problem:
    constraints = _prepared_constraints(problem)
    objects, init = problem.objects, problem.init
    for c in constraints:
        if c.kind == "always" and not c.phi.eval(init, objects) or c.kind == "sometime_before" and c.phi.eval(init, objects):
            return _unsolvable(problem)
    mon = _Monitors(problem)
    new_init, hold_goals = set(init), []
    for i, c in enumerate(constraints):
        if c.kind == "sometime":
            if c.phi.eval(init, objects):
                new_init.add(mon.hold(i).atom())
            hold_goals.append(Atom(mon.hold(i)))
        elif c.kind == "sometime_after":
            if c.psi.eval(init, objects) or not c.phi.eval(init, objects):
                new_init.add(mon.hold(i).atom())
            hold_goals.append(Atom(mon.hold(i)))
        elif c.kind == "at_most_once" and c.phi.eval(init, objects):
            new_init.add(mon.seen(c.phi).atom())
        elif c.kind == "sometime_before" and c.psi.eval(init, objects):
            new_init.add(mon.seen(c.psi).atom())
    know_pos = [knowledge(c.phi, True) for c in constraints]
    know_neg = [knowledge(c.phi, False) for c in constraints]
    actions = []
    for a in problem.actions:
        P, E = [], []
        for i, c in enumerate(constraints):
            changed = lambda f: regress(f, a) != f
            if c.kind == "always":
                if changed(c.phi):
                    P.append(regress_k(c.phi, a, *know_pos[i]))
            elif c.kind == "sometime":
                if changed(c.phi):
                    E.append(Effect(regress(c.phi, a), mon.hold(i)))
            elif c.kind == "at_most_once":
                if changed(c.phi):
                    seen = mon.seen(c.phi)
                    E.append(Effect(regress(c.phi, a), seen))
                    P.append(make_not(make_and(Atom(seen), make_not(c.phi), regress_k(c.phi, a, *know_neg[i]))))
            elif c.kind == "sometime_before":
                seen = mon.seen(c.psi)
                if changed(c.psi):
                    E.append(Effect(regress(c.psi, a), seen))
                if changed(c.phi):
                    P.append(Imply(regress_k(c.phi, a, *know_neg[i]), Atom(seen)))
            elif c.kind == "sometime_after":
                hold = mon.hold(i)
                if changed(c.psi):
                    E.append(Effect(regress(c.psi, a), hold))
                bad = make_and(c.phi, make_not(c.psi))
                if changed(bad):
                    E.append(Effect(regress(bad, a), hold.negate()))
        actions.append(replace(a, precondition=make_and(a.precondition, *_dedupe(P)),
                               effects=tuple(_dedupe(list(a.effects) + E))))
    return Problem(objects, tuple(actions), new_init, make_and(problem.goal, *hold_goals), (), set(problem.predicates))


def main():
    task = problem_from_json(json.loads(Path(sys.argv[1]).read_text()))
    out = optimize_problem(problem_to_json(compile_invariant_tcore(task)))
    Path(sys.argv[2]).write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
