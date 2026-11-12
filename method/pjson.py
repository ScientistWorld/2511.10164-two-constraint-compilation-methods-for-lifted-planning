"""JSON (de)serialisation of planning tasks for the method's compilers."""
from __future__ import annotations

from typing import Any, Dict

from planning import (Action, And, Atom, Bool, Constraint, Effect, Eq, Exists, ForAll, Formula, Imply,
                      Literal, Not, Or, Problem)


def literal_from_json(js: Dict[str, Any]) -> Literal:
    return Literal(js["pred"], tuple(js.get("args", [])), bool(js.get("negated", False)))


def literal_to_json(lit: Literal) -> Dict[str, Any]:
    return {"pred": lit.pred, "args": list(lit.args), "negated": lit.negated}


def formula_from_json(js: Dict[str, Any]) -> Formula:
    op = js["op"]
    if op == "bool":
        return Bool(bool(js["value"]))
    if op == "atom":
        return Atom(literal_from_json(js["literal"]))
    if op == "not":
        return Not(formula_from_json(js["child"]))
    if op == "and":
        return And(tuple(formula_from_json(c) for c in js["children"]))
    if op == "or":
        return Or(tuple(formula_from_json(c) for c in js["children"]))
    if op == "imply":
        return Imply(formula_from_json(js["left"]), formula_from_json(js["right"]))
    if op == "eq":
        return Eq(js["left"], js["right"])
    if op == "exists":
        return Exists(tuple(js["vars"]), formula_from_json(js["child"]))
    if op == "forall":
        return ForAll(tuple(js["vars"]), formula_from_json(js["child"]))
    raise ValueError(f"unknown formula op {op!r}")


def formula_to_json(f: Formula) -> Dict[str, Any]:
    if isinstance(f, Bool):
        return {"op": "bool", "value": f.value}
    if isinstance(f, Atom):
        return {"op": "atom", "literal": literal_to_json(f.lit)}
    if isinstance(f, Not):
        return {"op": "not", "child": formula_to_json(f.child)}
    if isinstance(f, And):
        return {"op": "and", "children": [formula_to_json(c) for c in f.children]}
    if isinstance(f, Or):
        return {"op": "or", "children": [formula_to_json(c) for c in f.children]}
    if isinstance(f, Imply):
        return {"op": "imply", "left": formula_to_json(f.left), "right": formula_to_json(f.right)}
    if isinstance(f, Eq):
        return {"op": "eq", "left": f.left, "right": f.right}
    if isinstance(f, Exists):
        return {"op": "exists", "vars": list(f.vars), "child": formula_to_json(f.child)}
    if isinstance(f, ForAll):
        return {"op": "forall", "vars": list(f.vars), "child": formula_to_json(f.child)}
    raise TypeError(f)


def problem_from_json(js: Dict[str, Any]) -> Problem:
    actions = []
    for a in js["actions"]:
        effects = tuple(Effect(formula_from_json(e.get("condition", {"op": "bool", "value": True})),
                               literal_from_json(e["literal"]), tuple(e.get("forall", [])))
                        for e in a.get("effects", []))
        actions.append(Action(a["name"], tuple(a.get("params", [])), formula_from_json(a["precondition"]), effects))
    constraints = []
    for i, c in enumerate(js.get("constraints", [])):
        psi = c.get("psi")
        constraints.append(Constraint(c["kind"], formula_from_json(c["phi"]),
                                      None if psi is None else formula_from_json(psi), c.get("name", f"c{i}")))
    init = {(atom["pred"], tuple(atom.get("args", []))) for atom in js.get("init", [])}
    return Problem(tuple(js["objects"]), tuple(actions), init, formula_from_json(js["goal"]), tuple(constraints),
                   set(js.get("predicates", {})))


def problem_to_json(p: Problem) -> Dict[str, Any]:
    return {
        "objects": list(p.objects),
        "actions": [{
            "name": a.name,
            "params": list(a.params),
            "precondition": formula_to_json(a.precondition),
            "effects": [{"forall": list(e.forall), "condition": formula_to_json(e.condition),
                         "literal": literal_to_json(e.literal)} for e in a.effects],
        } for a in p.actions],
        "init": [{"pred": pred, "args": list(args)} for pred, args in sorted(p.init)],
        "goal": formula_to_json(p.goal),
    }
