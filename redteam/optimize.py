"""A genuine, task-independent Boolean optimization of compiled formulas."""
import copy
import json


def key(f):
    return json.dumps(f, sort_keys=True)


def boolean(v):
    return {"op": "bool", "value": bool(v)}


def simplify(f):
    op = f["op"]
    if op in ("bool", "atom"):
        return copy.deepcopy(f)
    if op == "eq":
        if f["left"] == f["right"]:
            return boolean(True)
        if not f["left"].startswith("?") and not f["right"].startswith("?"):
            return boolean(False)
        return copy.deepcopy(f)
    if op == "not":
        c = simplify(f["child"])
        if c["op"] == "bool":
            return boolean(not c["value"])
        if c["op"] == "not":
            return c["child"]
        return {"op": "not", "child": c}
    if op == "imply":
        a, b = simplify(f["left"]), simplify(f["right"])
        if a == b or a == boolean(False) or b == boolean(True):
            return boolean(True)
        if a == boolean(True):
            return b
        if b == boolean(False):
            return simplify({"op": "not", "child": a})
        return {"op": op, "left": a, "right": b}
    if op in ("exists", "forall"):
        c = simplify(f["child"])
        # Removing an empty binder is valid even with an empty object universe.
        if not f.get("vars", []):
            return c
        return {**f, "child": c}
    if op in ("and", "or"):
        identity = op == "and"
        children = []
        for child in f.get("children", []):
            child = simplify(child)
            children.extend(child.get("children", []) if child["op"] == op else [child])
        kept = {}
        for c in children:
            if c == boolean(not identity):
                return boolean(not identity)
            if c != boolean(identity):
                kept[key(c)] = c
        for c in list(kept.values()):
            if key(simplify({"op": "not", "child": c})) in kept:
                return boolean(not identity)
        # Absorption: a AND (a OR b) == a; its dual is also valid.
        opposite = "or" if op == "and" else "and"
        children = [c for c in kept.values() if not (
            c["op"] == opposite and any(key(d) in kept for d in c["children"]))]
        if not children:
            return boolean(identity)
        if len(children) == 1:
            return children[0]
        return {"op": op, "children": children}
    raise ValueError(op)


def optimize_problem(p):
    p = copy.deepcopy(p)
    p["goal"] = simplify(p["goal"])
    for action in p["actions"]:
        action["precondition"] = simplify(action["precondition"])
        effects = []
        seen = set()
        for effect in action.get("effects", []):
            effect["condition"] = simplify(effect["condition"])
            if effect["condition"] == boolean(False):
                continue
            k = key(effect)
            if k not in seen:
                seen.add(k)
                effects.append(effect)
        action["effects"] = effects
    return p
