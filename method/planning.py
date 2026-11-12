"""Symbolic planning core and the paper's two lifted constraint compilers.

* ``compile_lifted_tcore`` -- Algorithm 1 (LiftedTCORE): lifted gamma operator
  (Definitions 2-5) via most-general unification against (possibly universally
  quantified) conditional effects, lifted regression (Definition 6), and
  action-specific monitoring preconditions/effects.  As in Section 3.2 of the
  paper, regression formulae with ``R^L(phi, a) = phi`` are omitted.
* ``compile_lcc`` -- Algorithm 2 (LCC): action-independent monitoring
  preconditions/effects shared by every action plus the final ``fin`` action.

Two details of the displayed pseudo-code are completed so that the
correctness propositions hold when a monitored formula is already true in the
initial state: LiftedTCORE also initialises ``seen_phi`` for AtMostOnce(phi)
and ``seen_psi`` for SometimeBefore(phi, psi) when they hold in ``I``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Term = str
Substitution = Dict[str, str]
Unification = Tuple[Substitution, Tuple[Tuple[Term, Term], ...]]
GroundAtom = Tuple[str, Tuple[str, ...]]


def is_var(term: str) -> bool:
    return term.startswith("?")


@dataclass(frozen=True)
class Literal:
    pred: str
    args: Tuple[Term, ...] = ()
    negated: bool = False

    def substitute(self, subst: Substitution) -> "Literal":
        return Literal(self.pred, tuple(subst.get(a, a) for a in self.args), self.negated)

    def positive(self) -> "Literal":
        return Literal(self.pred, self.args, False)

    def negate(self) -> "Literal":
        return Literal(self.pred, self.args, not self.negated)

    def atom(self) -> GroundAtom:
        return (self.pred, self.args)


class Formula:
    def substitute(self, subst: Substitution) -> "Formula":
        raise NotImplementedError

    def atoms(self) -> List[Literal]:
        raise NotImplementedError

    def eval(self, state: Set[GroundAtom], objects: Sequence[str]) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class Bool(Formula):
    value: bool

    def substitute(self, subst: Substitution) -> Formula:
        return self

    def atoms(self) -> List[Literal]:
        return []

    def eval(self, state, objects) -> bool:
        return self.value


TRUE = Bool(True)
FALSE = Bool(False)


@dataclass(frozen=True)
class Atom(Formula):
    lit: Literal

    def substitute(self, subst: Substitution) -> Formula:
        return Atom(self.lit.substitute(subst))

    def atoms(self) -> List[Literal]:
        return [self.lit]

    def eval(self, state, objects) -> bool:
        present = self.lit.positive().atom() in state
        return not present if self.lit.negated else present


@dataclass(frozen=True)
class Not(Formula):
    child: Formula

    def substitute(self, subst: Substitution) -> Formula:
        return Not(self.child.substitute(subst))

    def atoms(self) -> List[Literal]:
        return self.child.atoms()

    def eval(self, state, objects) -> bool:
        return not self.child.eval(state, objects)


@dataclass(frozen=True)
class And(Formula):
    children: Tuple[Formula, ...]

    def substitute(self, subst: Substitution) -> Formula:
        return make_and(*(c.substitute(subst) for c in self.children))

    def atoms(self) -> List[Literal]:
        return [a for c in self.children for a in c.atoms()]

    def eval(self, state, objects) -> bool:
        return all(c.eval(state, objects) for c in self.children)


@dataclass(frozen=True)
class Or(Formula):
    children: Tuple[Formula, ...]

    def substitute(self, subst: Substitution) -> Formula:
        return make_or(*(c.substitute(subst) for c in self.children))

    def atoms(self) -> List[Literal]:
        return [a for c in self.children for a in c.atoms()]

    def eval(self, state, objects) -> bool:
        return any(c.eval(state, objects) for c in self.children)


@dataclass(frozen=True)
class Imply(Formula):
    left: Formula
    right: Formula

    def substitute(self, subst: Substitution) -> Formula:
        return Imply(self.left.substitute(subst), self.right.substitute(subst))

    def atoms(self) -> List[Literal]:
        return self.left.atoms() + self.right.atoms()

    def eval(self, state, objects) -> bool:
        return (not self.left.eval(state, objects)) or self.right.eval(state, objects)


@dataclass(frozen=True)
class Eq(Formula):
    left: Term
    right: Term

    def substitute(self, subst: Substitution) -> Formula:
        return Eq(subst.get(self.left, self.left), subst.get(self.right, self.right))

    def atoms(self) -> List[Literal]:
        return []

    def eval(self, state, objects) -> bool:
        return self.left == self.right


@dataclass(frozen=True)
class Exists(Formula):
    vars: Tuple[str, ...]
    child: Formula

    def substitute(self, subst: Substitution) -> Formula:
        scoped = {k: v for k, v in subst.items() if k not in self.vars}
        return Exists(self.vars, self.child.substitute(scoped))

    def atoms(self) -> List[Literal]:
        return self.child.atoms()

    def eval(self, state, objects) -> bool:
        return any(self.child.substitute(dict(zip(self.vars, vals))).eval(state, objects)
                   for vals in product(objects, repeat=len(self.vars)))


@dataclass(frozen=True)
class ForAll(Formula):
    vars: Tuple[str, ...]
    child: Formula

    def substitute(self, subst: Substitution) -> Formula:
        scoped = {k: v for k, v in subst.items() if k not in self.vars}
        return ForAll(self.vars, self.child.substitute(scoped))

    def atoms(self) -> List[Literal]:
        return self.child.atoms()

    def eval(self, state, objects) -> bool:
        return all(self.child.substitute(dict(zip(self.vars, vals))).eval(state, objects)
                   for vals in product(objects, repeat=len(self.vars)))


def make_and(*children: Formula) -> Formula:
    flat: List[Formula] = []
    for child in children:
        if child == FALSE:
            return FALSE
        if child == TRUE:
            continue
        if isinstance(child, And):
            flat.extend(child.children)
        else:
            flat.append(child)
    if not flat:
        return TRUE
    if len(flat) == 1:
        return flat[0]
    return And(tuple(flat))


def make_or(*children: Formula) -> Formula:
    flat: List[Formula] = []
    for child in children:
        if child == TRUE:
            return TRUE
        if child == FALSE:
            continue
        if isinstance(child, Or):
            flat.extend(child.children)
        else:
            flat.append(child)
    if not flat:
        return FALSE
    if len(flat) == 1:
        return flat[0]
    return Or(tuple(flat))


def make_not(child: Formula) -> Formula:
    if isinstance(child, Bool):
        return FALSE if child.value else TRUE
    return Not(child)


@dataclass(frozen=True)
class Effect:
    condition: Formula
    literal: Literal
    forall: Tuple[str, ...] = ()

    def ground(self, objects: Sequence[str], subst: Substitution) -> Iterable[Tuple[Formula, Literal]]:
        if not self.forall:
            yield self.condition.substitute(subst), self.literal.substitute(subst)
            return
        for values in product(objects, repeat=len(self.forall)):
            full = dict(subst)
            full.update(zip(self.forall, values))
            yield self.condition.substitute(full), self.literal.substitute(full)


@dataclass(frozen=True)
class Action:
    name: str
    params: Tuple[str, ...]
    precondition: Formula
    effects: Tuple[Effect, ...]


@dataclass(frozen=True)
class Constraint:
    kind: str
    phi: Formula
    psi: Optional[Formula] = None
    name: str = ""


@dataclass
class Problem:
    objects: Tuple[str, ...]
    actions: Tuple[Action, ...]
    init: Set[GroundAtom]
    goal: Formula
    constraints: Tuple[Constraint, ...] = ()
    predicates: Set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Lifted unification, gamma and regression (Definitions 2-6)
# ---------------------------------------------------------------------------

def unify_literals(query: Literal, effect: Literal) -> Optional[Unification]:
    """Most general unifier of a query literal and an effect literal.

    Returns ``(subst, equalities)``: ``subst`` binds effect variables (action
    parameters or forall variables) to query terms, or query variables to effect
    constants; ``equalities`` are residual term equalities created by repeated
    variables.  Query and effect variables must be named apart.
    """
    if query.pred != effect.pred or query.negated != effect.negated or len(query.args) != len(effect.args):
        return None
    subst: Substitution = {}
    equalities: List[Tuple[Term, Term]] = []
    for q, e in zip(query.args, effect.args):
        if q == e:
            continue
        if is_var(e):
            current = subst.get(e)
            if current is not None:
                if current == q:
                    continue
                if not is_var(current) and not is_var(q):
                    return None
                equalities.append((current, q))
                continue
            subst[e] = q
        elif is_var(q):
            current = subst.get(q)
            if current is not None:
                if current == e:
                    continue
                if not is_var(current) and not is_var(e):
                    return None
                equalities.append((current, e))
                continue
            subst[q] = e
        else:
            return None
    return subst, tuple(equalities)


class _Fresh:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return f"{self.prefix}{self.n}"


_FRESH = _Fresh("?__g")


def _var_occurs(var: str, formula: Formula) -> bool:
    return any(var in atom.args for atom in formula.atoms()) or _eq_mentions(var, formula)


def _eq_mentions(var: str, formula: Formula) -> bool:
    if isinstance(formula, Eq):
        return var in (formula.left, formula.right)
    if isinstance(formula, (Not,)):
        return _eq_mentions(var, formula.child)
    if isinstance(formula, (And, Or)):
        return any(_eq_mentions(var, c) for c in formula.children)
    if isinstance(formula, Imply):
        return _eq_mentions(var, formula.left) or _eq_mentions(var, formula.right)
    if isinstance(formula, (Exists, ForAll)):
        return var not in formula.vars and _eq_mentions(var, formula.child)
    return False


def weakest_condition(lit: Literal, eff: Effect) -> Formula:
    """w_l(forall z: c |> e) of Definition 4 (Definition 2 when z is empty)."""
    unification = unify_literals(lit, eff.literal)
    if unification is None:
        return FALSE
    subst, equality_terms = unification
    z_subst = {k: v for k, v in subst.items() if k in eff.forall}
    equalities = [Eq(v, k) for k, v in subst.items() if k not in eff.forall]
    equalities.extend(Eq(left, right) for left, right in equality_terms)
    free_z = [z for z in eff.forall if z not in z_subst and _var_occurs(z, eff.condition)]
    rename = {z: _FRESH() for z in free_z}  # keep the existential binder capture-free
    cond = eff.condition.substitute({**z_subst, **rename})
    if free_z:
        cond = Exists(tuple(rename[z] for z in free_z), cond)
    return make_and(cond, *equalities)


def lifted_gamma(lit: Literal, action: Action) -> Formula:
    """Gamma^L_l(a) of Definition 5."""
    return make_or(*(weakest_condition(lit, eff) for eff in action.effects))


def _may_change(lit: Literal, action: Action) -> bool:
    pos = lit.positive()
    for eff in action.effects:
        if eff.literal.pred != pos.pred or len(eff.literal.args) != len(pos.args):
            continue
        if unify_literals(pos, eff.literal.positive()) is not None:
            return True
    return False


def affected(formula: Formula, action: Action) -> bool:
    return any(_may_change(lit, action) for lit in formula.atoms())


def regress(formula: Formula, action: Action) -> Formula:
    """R^L(phi, a) of Definition 6; returns ``formula`` itself when ``a`` cannot change it."""
    if not affected(formula, action):
        return formula
    if isinstance(formula, Atom):
        lit = formula.lit
        if lit.negated:
            return make_not(regress(Atom(lit.positive()), action))
        add = lifted_gamma(lit, action)
        delete = lifted_gamma(lit.negate(), action)
        return make_or(add, make_and(Atom(lit), make_not(delete)))
    if isinstance(formula, Not):
        return make_not(regress(formula.child, action))
    if isinstance(formula, And):
        return make_and(*(regress(c, action) for c in formula.children))
    if isinstance(formula, Or):
        return make_or(*(regress(c, action) for c in formula.children))
    if isinstance(formula, Imply):
        return Imply(regress(formula.left, action), regress(formula.right, action))
    if isinstance(formula, Exists):
        return Exists(formula.vars, regress(formula.child, action))
    if isinstance(formula, ForAll):
        return ForAll(formula.vars, regress(formula.child, action))
    return formula


# ---------------------------------------------------------------------------
# Helpers shared by the compilers
# ---------------------------------------------------------------------------

def rename_bound(formula: Formula, prefix: str, counter: List[int]) -> Formula:
    """Rename every quantified variable apart (``?__c<k>``) to avoid capture."""
    if isinstance(formula, (Exists, ForAll)):
        mapping = {}
        for v in formula.vars:
            counter[0] += 1
            mapping[v] = f"{prefix}{counter[0]}"
        child = rename_bound(formula.child.substitute(mapping), prefix, counter)
        return type(formula)(tuple(mapping[v] for v in formula.vars), child)
    if isinstance(formula, Not):
        return Not(rename_bound(formula.child, prefix, counter))
    if isinstance(formula, And):
        return And(tuple(rename_bound(c, prefix, counter) for c in formula.children))
    if isinstance(formula, Or):
        return Or(tuple(rename_bound(c, prefix, counter) for c in formula.children))
    if isinstance(formula, Imply):
        return Imply(rename_bound(formula.left, prefix, counter), rename_bound(formula.right, prefix, counter))
    return formula


def _all_predicates(problem: Problem) -> Set[str]:
    preds = set(problem.predicates) | {p for p, _ in problem.init}
    for a in problem.actions:
        preds |= {l.pred for l in a.precondition.atoms()}
        for e in a.effects:
            preds.add(e.literal.pred)
            preds |= {l.pred for l in e.condition.atoms()}
    preds |= {l.pred for l in problem.goal.atoms()}
    for c in problem.constraints:
        preds |= {l.pred for l in c.phi.atoms()}
        if c.psi is not None:
            preds |= {l.pred for l in c.psi.atoms()}
    return preds


class _Monitors:
    """Deterministic, clash-free monitoring atoms (seen atoms are shared per formula)."""

    def __init__(self, problem: Problem) -> None:
        taken = _all_predicates(problem)
        prefix = "mon_"
        while any(p.startswith(prefix) for p in taken):
            prefix = "_" + prefix
        self.prefix = prefix
        self._seen: Dict[Formula, Literal] = {}

    def hold(self, index: int) -> Literal:
        return Literal(f"{self.prefix}hold{index}")

    def seen(self, formula: Formula) -> Literal:
        if formula not in self._seen:
            self._seen[formula] = Literal(f"{self.prefix}seen{len(self._seen)}")
        return self._seen[formula]

    def prevent(self, index: int) -> Literal:
        return Literal(f"{self.prefix}prevent{index}")

    def end(self) -> Literal:
        return Literal(f"{self.prefix}end")


def _prepared_constraints(problem: Problem) -> List[Constraint]:
    counter = [0]
    out = []
    for c in problem.constraints:
        phi = rename_bound(c.phi, "?__c", counter)
        psi = None if c.psi is None else rename_bound(c.psi, "?__c", counter)
        out.append(Constraint(c.kind, phi, psi, c.name))
    return out


def _dedupe(items: Iterable) -> List:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _unsolvable(problem: Problem) -> Problem:
    return Problem(problem.objects, problem.actions, set(problem.init), FALSE, (), set(problem.predicates))


# ---------------------------------------------------------------------------
# Algorithm 1: LiftedTCORE
# ---------------------------------------------------------------------------

def compile_lifted_tcore(problem: Problem, omit_unchanged: bool = True) -> Problem:
    """LiftedTCORE.  ``omit_unchanged=False`` keeps updates with R^L(phi,a)=phi (ablation)."""
    constraints = _prepared_constraints(problem)
    objects, init = problem.objects, problem.init
    for c in constraints:  # line 1-2: irrevocable violation in the initial state
        if c.kind == "always" and not c.phi.eval(init, objects):
            return _unsolvable(problem)
        if c.kind == "sometime_before" and c.phi.eval(init, objects):
            return _unsolvable(problem)
    mon = _Monitors(problem)
    new_init = set(init)
    hold_goals: List[Formula] = []
    for i, c in enumerate(constraints):  # lines 3-4
        if c.kind == "sometime":
            if c.phi.eval(init, objects):
                new_init.add(mon.hold(i).atom())
            hold_goals.append(Atom(mon.hold(i)))
        elif c.kind == "sometime_after":
            if c.psi.eval(init, objects) or not c.phi.eval(init, objects):
                new_init.add(mon.hold(i).atom())
            hold_goals.append(Atom(mon.hold(i)))
        elif c.kind == "at_most_once":
            if c.phi.eval(init, objects):
                new_init.add(mon.seen(c.phi).atom())
        elif c.kind == "sometime_before":
            if c.psi.eval(init, objects):
                new_init.add(mon.seen(c.psi).atom())

    def reg(formula: Formula, action: Action) -> Optional[Formula]:
        r = regress(formula, action)
        if omit_unchanged and r == formula:
            return None
        return r

    new_actions: List[Action] = []
    for action in problem.actions:  # lines 5-8, COMPILECREGRESS
        P: List[Formula] = []
        E: List[Effect] = []
        for i, c in enumerate(constraints):
            if c.kind == "always":
                r = reg(c.phi, action)
                if r is not None:
                    P.append(r)
            elif c.kind == "sometime":
                r = reg(c.phi, action)
                if r is not None:
                    E.append(Effect(r, mon.hold(i)))
            elif c.kind == "at_most_once":
                r = reg(c.phi, action)
                if r is not None:
                    seen = mon.seen(c.phi)
                    E.append(Effect(r, seen))
                    P.append(make_not(make_and(Atom(seen), make_not(c.phi), r)))
            elif c.kind == "sometime_before":
                seen = mon.seen(c.psi)
                r_psi = reg(c.psi, action)
                if r_psi is not None:
                    E.append(Effect(r_psi, seen))
                r_phi = reg(c.phi, action)
                if r_phi is not None:
                    P.append(Imply(r_phi, Atom(seen)))
            elif c.kind == "sometime_after":
                hold = mon.hold(i)
                r_psi = reg(c.psi, action)
                if r_psi is not None:
                    E.append(Effect(r_psi, hold))
                r_bad = reg(make_and(c.phi, make_not(c.psi)), action)
                if r_bad is not None:
                    E.append(Effect(r_bad, hold.negate()))
            else:
                raise ValueError(f"unsupported constraint kind {c.kind}")
        pre = make_and(action.precondition, *_dedupe(P))
        effects = _dedupe(list(action.effects) + E)
        new_actions.append(replace(action, precondition=pre, effects=tuple(effects)))
    goal = make_and(problem.goal, *hold_goals)  # line 9
    return Problem(objects, tuple(new_actions), new_init, goal, (), set(problem.predicates))


# ---------------------------------------------------------------------------
# Algorithm 2: LCC
# ---------------------------------------------------------------------------

def compile_lcc(problem: Problem, fin_name: str = "fin") -> Problem:
    constraints = _prepared_constraints(problem)
    mon = _Monitors(problem)
    end = mon.end()
    names = {a.name for a in problem.actions}
    while fin_name in names:
        fin_name = "_" + fin_name
    P: List[Formula] = []
    E: List[Effect] = []
    goal_bits: List[Formula] = [problem.goal]
    init = set(problem.init)
    for i, c in enumerate(constraints):
        if c.kind == "always":
            P.append(c.phi)
        elif c.kind == "sometime":
            E.append(Effect(c.phi, mon.hold(i)))
            goal_bits.append(Atom(mon.hold(i)))
        elif c.kind == "at_most_once":
            seen, prevent = mon.seen(c.phi), mon.prevent(i)
            E.append(Effect(c.phi, seen))
            E.append(Effect(make_and(make_not(c.phi), Atom(seen)), prevent))
            P.append(make_not(make_and(c.phi, Atom(prevent))))
        elif c.kind == "sometime_before":
            seen = mon.seen(c.psi)
            E.append(Effect(c.psi, seen))
            P.append(Imply(c.phi, Atom(seen)))
        elif c.kind == "sometime_after":
            hold = mon.hold(i)
            init.add(hold.atom())
            goal_bits.append(Atom(hold))
            E.append(Effect(c.psi, hold))
            E.append(Effect(make_and(c.phi, make_not(c.psi)), hold.negate()))
        else:
            raise ValueError(f"unsupported constraint kind {c.kind}")
    P = _dedupe(P)
    E = _dedupe(E)
    not_end = make_not(Atom(end))
    new_actions = [replace(a, precondition=make_and(a.precondition, *P, not_end), effects=tuple(a.effects) + tuple(E))
                   for a in problem.actions]
    new_actions.append(Action(fin_name, (), make_and(*P, not_end), tuple(E) + (Effect(TRUE, end),)))
    goal_bits.append(Atom(end))
    return Problem(problem.objects, tuple(new_actions), init, make_and(*goal_bits), (), set(problem.predicates))


# ---------------------------------------------------------------------------
# Plan semantics (used by the method's own unit tests)
# ---------------------------------------------------------------------------

def apply_action(problem: Problem, state: Set[GroundAtom], action: Action, args: Tuple[str, ...] = ()):
    subst = dict(zip(action.params, args))
    if not action.precondition.substitute(subst).eval(state, problem.objects):
        return None
    grounded: List[Tuple[Formula, Literal]] = []
    for eff in action.effects:
        grounded.extend(eff.ground(problem.objects, subst))
    deletes = {lit.positive().atom() for cond, lit in grounded if lit.negated and cond.eval(state, problem.objects)}
    adds = {lit.atom() for cond, lit in grounded if not lit.negated and cond.eval(state, problem.objects)}
    return (state - deletes) | adds


def plan_trace(problem: Problem, plan: Sequence[Tuple[str, Tuple[str, ...]]]):
    by_name = {a.name: a for a in problem.actions}
    state = set(problem.init)
    trace = [set(state)]
    for name, args in plan:
        if name not in by_name:
            return None
        nxt = apply_action(problem, state, by_name[name], tuple(args))
        if nxt is None:
            return None
        state = nxt
        trace.append(set(state))
    return trace


def constraint_holds(constraint: Constraint, trace, objects) -> bool:
    phi = [constraint.phi.eval(s, objects) for s in trace]
    if constraint.kind == "always":
        return all(phi)
    if constraint.kind == "sometime":
        return any(phi)
    if constraint.kind == "at_most_once":
        seen_true = left = False
        for val in phi:
            if val and left:
                return False
            if val:
                seen_true = True
            elif seen_true:
                left = True
        return True
    psi = [constraint.psi.eval(s, objects) for s in trace]
    if constraint.kind == "sometime_before":
        return all(not p or any(psi[:i]) for i, p in enumerate(phi))
    if constraint.kind == "sometime_after":
        return all(not p or any(psi[i:]) for i, p in enumerate(phi))
    raise ValueError(constraint.kind)


def plan_valid(problem: Problem, plan) -> bool:
    trace = plan_trace(problem, plan)
    if trace is None or not problem.goal.eval(trace[-1], problem.objects):
        return False
    return all(constraint_holds(c, trace, problem.objects) for c in problem.constraints)


def formula_size(formula: Formula) -> int:
    if isinstance(formula, (Bool, Eq, Atom)):
        return 1
    if isinstance(formula, Not):
        return 1 + formula_size(formula.child)
    if isinstance(formula, (And, Or)):
        return 1 + sum(formula_size(c) for c in formula.children)
    if isinstance(formula, Imply):
        return 1 + formula_size(formula.left) + formula_size(formula.right)
    if isinstance(formula, (Exists, ForAll)):
        return 1 + formula_size(formula.child)
    raise TypeError(formula)
