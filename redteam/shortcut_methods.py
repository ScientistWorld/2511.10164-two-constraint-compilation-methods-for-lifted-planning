"""File-only shortcut submissions. No hidden evaluator imports or process hooks."""
import copy

from optimize import boolean, simplify


def atom(name):
    return {"op": "atom", "literal": {"pred": name, "args": [], "negated": False}}


def combine(op, children):
    return simplify({"op": op, "children": children})


def shortcut_constant(item, accept=True, replace_probes=True):
    """Shortcut: erase the planning problem and optionally supply an empty witness."""
    p = item["compiled_problem"]
    item["compiled_problem"] = {"objects": p["objects"], "actions": [], "init": [], "goal": boolean(accept)}
    if replace_probes:
        item["valid_plan"] = []
        if "invalid_plan" in item:
            item["invalid_plan"] = [{"name": "shortcut_nonexistent", "args": []}]


def shortcut_known_plan(item):
    """Shortcut: recognize only the supplied positive probe, rather than compile constraints.

    Preserve BOTH plan probes. No constraint, original transition, or original goal
    is represented. Shared argument equalities are factored for compactness.
    """
    old = item["compiled_problem"]
    plan = item["valid_plan"]
    by_name = {a["name"]: a for a in old["actions"]}
    names = list(dict.fromkeys(s["name"] for s in plan))
    actions = []
    for name in names:
        occurrences = [(i, s) for i, s in enumerate(plan) if s["name"] == name]
        params = by_name[name].get("params", [])
        common = {j: occurrences[0][1]["args"][j] for j in range(len(params))
                  if len({s["args"][j] for _, s in occurrences}) == 1}
        equalities = [{"op": "eq", "left": params[j], "right": v} for j, v in common.items()]
        conditions = []
        effects = []
        for i, step in occurrences:
            cond = combine("and", [atom(f"shortcut_stage_{i}")] + [
                {"op": "eq", "left": params[j], "right": v}
                for j, v in enumerate(step.get("args", [])) if j not in common])
            conditions.append(cond)
            for stage, negated in ((i, True), (i + 1, False)):
                effects.append({"condition": cond, "forall": [], "literal": {
                    "pred": f"shortcut_stage_{stage}", "args": [], "negated": negated}})
        actions.append({"name": name, "params": params,
                        "precondition": combine("and", equalities + [combine("or", conditions)]),
                        "effects": effects})
    item["compiled_problem"] = {"objects": old["objects"], "actions": actions,
        "init": [{"pred": "shortcut_stage_0", "args": []}], "goal": atom(f"shortcut_stage_{len(plan)}")}


def each_item(raw, method="lifted_tcore"):
    for experiment, exp in raw.items():
        if method not in exp:
            continue
        value = exp[method]
        if "cases" in value:
            for name, item in value["cases"].items():
                yield experiment, name, item
        elif "compiled_problem" in value:
            yield experiment, None, value


def shortcut_self_report(item):
    # These fields are deliberately false/impossible. The compiled task stays intact.
    for k in ("actions", "effects", "formula_atoms", "slice_structural_units", "compile_seconds"):
        item[k] = -1e100
    for k in ("plan_valid", "plan_valid_rate", "valid_plan_accepted", "invalid_plan_rejected"):
        item[k] = 1e100
    item["success"] = True
    item["score"] = None


def shortcut_replace_baseline(raw):
    for exp_name in ("ground_constraints_size", "nonground_constraints_size"):
        item = raw[exp_name]["ground_tcore"]
        # Small dictionaries keep this comparison-side replacement inexpensive.
        action = {"name": "shortcut_padding", "params": [], "precondition": boolean(False), "effects": []}
        item["compiled_problem"] = {"objects": item["compiled_problem"]["objects"],
            "actions": [action] * 100000, "init": [], "goal": boolean(True)}
        item["valid_plan"] = []
