from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Term = str
Substitution = Dict[str, str]
Unification = Tuple[Substitution, Tuple[Tuple[Term, Term], ...]]


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

    def atom(self) -> Tuple[str, Tuple[str, ...]]:
        return (self.pred, self.args)


class Formula:
    def substitute(self, subst: Substitution) -> "Formula":
        raise NotImplementedError

    def atoms(self) -> List[Literal]:
        raise NotImplementedError

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class Bool(Formula):
    value: bool

    def substitute(self, subst: Substitution) -> "Formula":
        return self

    def atoms(self) -> List[Literal]:
        return []

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
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

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        present = self.lit.positive().atom() in state
        return not present if self.lit.negated else present


@dataclass(frozen=True)
class Not(Formula):
    child: Formula

    def substitute(self, subst: Substitution) -> Formula:
        return Not(self.child.substitute(subst))

    def atoms(self) -> List[Literal]:
        return self.child.atoms()

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        return not self.child.eval(state, objects)


@dataclass(frozen=True)
class And(Formula):
    children: Tuple[Formula, ...]

    def substitute(self, subst: Substitution) -> Formula:
        return make_and(*(c.substitute(subst) for c in self.children))

    def atoms(self) -> List[Literal]:
        out: List[Literal] = []
        for child in self.children:
            out.extend(child.atoms())
        return out

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        return all(c.eval(state, objects) for c in self.children)


@dataclass(frozen=True)
class Or(Formula):
    children: Tuple[Formula, ...]

    def substitute(self, subst: Substitution) -> Formula:
        return make_or(*(c.substitute(subst) for c in self.children))

    def atoms(self) -> List[Literal]:
        out: List[Literal] = []
        for child in self.children:
            out.extend(child.atoms())
        return out

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        return any(c.eval(state, objects) for c in self.children)


@dataclass(frozen=True)
class Imply(Formula):
    left: Formula
    right: Formula

    def substitute(self, subst: Substitution) -> Formula:
        return Imply(self.left.substitute(subst), self.right.substitute(subst))

    def atoms(self) -> List[Literal]:
        return self.left.atoms() + self.right.atoms()

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        return (not self.left.eval(state, objects)) or self.right.eval(state, objects)


@dataclass(frozen=True)
class Eq(Formula):
    left: Term
    right: Term

    def substitute(self, subst: Substitution) -> Formula:
        return Eq(subst.get(self.left, self.left), subst.get(self.right, self.right))

    def atoms(self) -> List[Literal]:
        return []

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
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

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        for values in product(objects, repeat=len(self.vars)):
            if self.child.substitute(dict(zip(self.vars, values))).eval(state, objects):
                return True
        return False


@dataclass(frozen=True)
class ForAll(Formula):
    vars: Tuple[str, ...]
    child: Formula

    def substitute(self, subst: Substitution) -> Formula:
        scoped = {k: v for k, v in subst.items() if k not in self.vars}
        return ForAll(self.vars, self.child.substitute(scoped))

    def atoms(self) -> List[Literal]:
        return self.child.atoms()

    def eval(self, state: Set[Tuple[str, Tuple[str, ...]]], objects: Sequence[str]) -> bool:
        for values in product(objects, repeat=len(self.vars)):
            if not self.child.substitute(dict(zip(self.vars, values))).eval(state, objects):
                return False
        return True


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
    init: Set[Tuple[str, Tuple[str, ...]]]
    goal: Formula
    constraints: Tuple[Constraint, ...] = ()
    predicates: Set[str] = field(default_factory=set)

    def copy_without_constraints(self) -> "Problem":
        return Problem(self.objects, self.actions, set(self.init), self.goal, (), set(self.predicates))


def unify_literals(query: Literal, effect: Literal) -> Optional[Unification]:
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


def lifted_gamma(lit: Literal, action: Action) -> Formula:
    pieces: List[Formula] = []
    for eff in action.effects:
        unification = unify_literals(lit, eff.literal)
        if unification is None:
            continue
        subst, equality_terms = unification
        z_subst = {k: v for k, v in subst.items() if k in eff.forall}
        equalities = [Eq(v, k) for k, v in subst.items() if k not in eff.forall]
        equalities.extend(Eq(left, right) for left, right in equality_terms)
        free_z = tuple(z for z in eff.forall if z not in z_subst and _var_occurs(z, eff.condition))
        cond = eff.condition.substitute(z_subst)
        if free_z:
            cond = Exists(free_z, cond)
        pieces.append(make_and(cond, *equalities))
    return make_or(*pieces)


def _var_occurs(var: str, formula: Formula) -> bool:
    return any(var in atom.args for atom in formula.atoms())


def regress(formula: Formula, action: Action) -> Formula:
    if isinstance(formula, Bool):
        return formula
    if isinstance(formula, Atom):
        lit = formula.lit
        if lit.negated:
            return Not(regress(Atom(lit.negate()), action))
        add = lifted_gamma(lit, action)
        delete = lifted_gamma(lit.negate(), action)
        return make_or(add, make_and(Atom(lit), Not(delete)))
    if isinstance(formula, Not):
        return Not(regress(formula.child, action))
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
    if isinstance(formula, Eq):
        return formula
    raise TypeError(formula)


def compile_lifted_tcore(problem: Problem) -> Problem:
    new_init = set(problem.init)
    new_goal = problem.goal
    new_actions: List[Action] = []
    hold_goals: List[Formula] = []
    for constraint in problem.constraints:
        if constraint.kind == "always" and not constraint.phi.eval(problem.init, problem.objects):
            raise ValueError("Always constraint violated in initial state")
        if constraint.kind == "sometime_before" and constraint.phi.eval(problem.init, problem.objects):
            raise ValueError("SometimeBefore constraint violated in initial state")
        mon = _hold(constraint)
        if constraint.kind == "sometime" and constraint.phi.eval(problem.init, problem.objects):
            new_init.add(mon.atom())
        if constraint.kind == "sometime_after":
            assert constraint.psi is not None
            if constraint.psi.eval(problem.init, problem.objects) or not constraint.phi.eval(problem.init, problem.objects):
                new_init.add(mon.atom())
        if constraint.kind in {"sometime", "sometime_after"}:
            hold_goals.append(Atom(mon))
    for action in problem.actions:
        preconditions = [action.precondition]
        effects = list(action.effects)
        for constraint in problem.constraints:
            phi_r = regress(constraint.phi, action)
            if constraint.kind == "always":
                preconditions.append(phi_r)
            elif constraint.kind == "sometime":
                effects.append(Effect(phi_r, _hold(constraint)))
            elif constraint.kind == "at_most_once":
                seen = _seen(constraint.phi)
                effects.append(Effect(phi_r, seen))
                preconditions.append(Not(make_and(Atom(seen), Not(constraint.phi), phi_r)))
            elif constraint.kind == "sometime_before":
                assert constraint.psi is not None
                seen = _seen(constraint.psi)
                effects.append(Effect(regress(constraint.psi, action), seen))
                preconditions.append(Imply(phi_r, Atom(seen)))
            elif constraint.kind == "sometime_after":
                assert constraint.psi is not None
                hold = _hold(constraint)
                effects.append(Effect(regress(constraint.psi, action), hold))
                effects.append(Effect(regress(make_and(constraint.phi, Not(constraint.psi)), action), hold.negate()))
        new_actions.append(replace(action, precondition=make_and(*preconditions), effects=tuple(effects)))
    if hold_goals:
        new_goal = make_and(new_goal, *hold_goals)
    return Problem(problem.objects, tuple(new_actions), new_init, new_goal, (), set(problem.predicates))


def compile_lcc(problem: Problem) -> Problem:
    preconditions: List[Formula] = [Not(Atom(Literal("end")))]
    effects: List[Effect] = []
    goal_bits = [problem.goal, Atom(Literal("end"))]
    init = set(problem.init)
    for constraint in problem.constraints:
        if constraint.kind == "always":
            preconditions.append(constraint.phi)
        elif constraint.kind == "sometime":
            hold = _hold(constraint)
            effects.append(Effect(constraint.phi, hold))
            goal_bits.append(Atom(hold))
        elif constraint.kind == "at_most_once":
            seen = _seen(constraint.phi)
            prevent = _prevent(constraint.phi)
            effects.append(Effect(constraint.phi, seen))
            effects.append(Effect(make_and(Not(constraint.phi), Atom(seen)), prevent))
            preconditions.append(Not(make_and(constraint.phi, Atom(prevent))))
        elif constraint.kind == "sometime_before":
            assert constraint.psi is not None
            seen = _seen(constraint.psi)
            effects.append(Effect(constraint.psi, seen))
            preconditions.append(Imply(constraint.phi, Atom(seen)))
        elif constraint.kind == "sometime_after":
            assert constraint.psi is not None
            hold = _hold(constraint)
            init.add(hold.atom())
            goal_bits.append(Atom(hold))
            effects.append(Effect(constraint.psi, hold))
            effects.append(Effect(make_and(constraint.phi, Not(constraint.psi)), hold.negate()))
    new_actions = []
    for action in problem.actions:
        new_actions.append(replace(action, precondition=make_and(action.precondition, *preconditions), effects=action.effects + tuple(effects)))
    fin = Action("fin", (), make_and(*preconditions), tuple(effects + [Effect(TRUE, Literal("end"))]))
    new_actions.append(fin)
    return Problem(problem.objects, tuple(new_actions), init, make_and(*goal_bits), (), set(problem.predicates))


def ground_problem(problem: Problem) -> Problem:
    actions: List[Action] = []
    for action in problem.actions:
        for values in product(problem.objects, repeat=len(action.params)):
            subst = dict(zip(action.params, values))
            effects: List[Effect] = []
            for eff in action.effects:
                for cond, lit in eff.ground(problem.objects, subst):
                    effects.append(Effect(cond, lit))
            actions.append(Action(f"{action.name}_{'_'.join(values)}", (), action.precondition.substitute(subst), tuple(effects)))
    return Problem(problem.objects, tuple(actions), set(problem.init), problem.goal, problem.constraints, set(problem.predicates))


def compile_ground_tcore(problem: Problem) -> Problem:
    return compile_lifted_tcore(ground_problem(problem))


def apply_action(problem: Problem, state: Set[Tuple[str, Tuple[str, ...]]], action: Action, args: Tuple[str, ...] = ()) -> Optional[Set[Tuple[str, Tuple[str, ...]]]]:
    subst = dict(zip(action.params, args))
    if not action.precondition.substitute(subst).eval(state, problem.objects):
        return None
    grounded: List[Tuple[Formula, Literal]] = []
    for eff in action.effects:
        grounded.extend(eff.ground(problem.objects, subst))
    deletes = {lit.positive().atom() for cond, lit in grounded if lit.negated and cond.eval(state, problem.objects)}
    adds = {lit.atom() for cond, lit in grounded if not lit.negated and cond.eval(state, problem.objects)}
    return (state - deletes) | adds


def plan_trace(problem: Problem, plan: Sequence[Tuple[str, Tuple[str, ...]]]) -> Optional[List[Set[Tuple[str, Tuple[str, ...]]]]]:
    by_name = {a.name: a for a in problem.actions}
    state = set(problem.init)
    trace = [set(state)]
    for name, args in plan:
        nxt = apply_action(problem, state, by_name[name], args)
        if nxt is None:
            return None
        state = nxt
        trace.append(set(state))
    return trace


def plan_valid(problem: Problem, plan: Sequence[Tuple[str, Tuple[str, ...]]]) -> bool:
    trace = plan_trace(problem, plan)
    if trace is None or not problem.goal.eval(trace[-1], problem.objects):
        return False
    return all(constraint_holds(c, trace, problem.objects) for c in problem.constraints)


def constraint_holds(constraint: Constraint, trace: Sequence[Set[Tuple[str, Tuple[str, ...]]]], objects: Sequence[str]) -> bool:
    phi = [constraint.phi.eval(s, objects) for s in trace]
    if constraint.kind == "always":
        return all(phi)
    if constraint.kind == "sometime":
        return any(phi)
    if constraint.kind == "at_most_once":
        seen_false_after = False
        seen_true = False
        for val in phi:
            if val and seen_false_after:
                return False
            if val:
                seen_true = True
            elif seen_true:
                seen_false_after = True
        return True
    assert constraint.psi is not None
    psi = [constraint.psi.eval(s, objects) for s in trace]
    if constraint.kind == "sometime_before":
        return all(not p or any(psi[:i]) for i, p in enumerate(phi))
    if constraint.kind == "sometime_after":
        return all(not p or any(psi[i:]) for i, p in enumerate(phi))
    raise ValueError(constraint.kind)


def size_stats(problem: Problem) -> Dict[str, int]:
    return {
        "actions": len(problem.actions),
        "effects": sum(len(a.effects) for a in problem.actions),
        "formula_atoms": sum(_formula_size(a.precondition) + sum(_formula_size(e.condition) for e in a.effects) for a in problem.actions),
    }


def _formula_size(formula: Formula) -> int:
    if isinstance(formula, (Bool, Eq)):
        return 1
    if isinstance(formula, Atom):
        return 1
    if isinstance(formula, Not):
        return 1 + _formula_size(formula.child)
    if isinstance(formula, (And, Or)):
        return 1 + sum(_formula_size(c) for c in formula.children)
    if isinstance(formula, Imply):
        return 1 + _formula_size(formula.left) + _formula_size(formula.right)
    if isinstance(formula, (Exists, ForAll)):
        return 1 + _formula_size(formula.child)
    raise TypeError(formula)


def _key(formula: Formula) -> str:
    return str(abs(hash(formula)) % 10_000_000)


def _hold(constraint: Constraint) -> Literal:
    return Literal(f"hold_{constraint.name or constraint.kind}_{_key(constraint.phi)}")


def _seen(formula: Formula) -> Literal:
    return Literal(f"seen_{_key(formula)}")


def _prevent(formula: Formula) -> Literal:
    return Literal(f"prevent_{_key(formula)}")
