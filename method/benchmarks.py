from __future__ import annotations

from planning import (
    Action,
    And,
    Atom,
    Constraint,
    Effect,
    Eq,
    Exists,
    ForAll,
    Literal,
    Not,
    Problem,
    TRUE,
    make_and,
)


def atom(pred: str, *args: str) -> Atom:
    return Atom(Literal(pred, tuple(args)))


def neg_atom(pred: str, *args: str) -> Atom:
    return Atom(Literal(pred, tuple(args), True))


def make_transfer_problem(n_objects: int = 8, quantified: bool = False) -> tuple[Problem, list[tuple[str, tuple[str, ...]]]]:
    """High-arity toy planning task used to expose grounding blow-up.

    The action has three object parameters although only one is semantically
    moved. Grounding therefore creates n^3 actions, while the lifted compilers
    keep one lifted schema and add monitoring logic to it.
    """

    objects = tuple(f"o{i}" for i in range(n_objects))
    move = Action(
        "move",
        ("?x", "?aux1", "?aux2"),
        atom("at_a", "?x"),
        (
            Effect(TRUE, Literal("at_a", ("?x",), True)),
            Effect(TRUE, Literal("at_b", ("?x",))),
            Effect(TRUE, Literal("touched", ("?aux1", "?aux2"))),
        ),
    )
    init = {("at_a", (o,)) for o in objects}
    goal = atom("at_b", objects[-1])
    if quantified:
        constraints = (
            Constraint("always", ForAll(("?z",), Not(atom("bad", "?z"))), name="all_safe"),
            Constraint("sometime", Exists(("?z",), atom("at_b", "?z")), name="some_arrived"),
            Constraint("sometime_before", atom("at_b", objects[-1]), atom("touched", objects[0], objects[1]), name="before_goal"),
        )
        plan = [("move", (objects[0], objects[0], objects[1])), ("move", (objects[-1], objects[0], objects[1]))]
    else:
        constraints = (
            Constraint("always", Not(atom("bad", objects[-1])), name="safe_goal"),
            Constraint("sometime", atom("at_b", objects[-1]), name="goal_seen"),
            Constraint("sometime_before", atom("at_b", objects[-1]), atom("touched", objects[0], objects[1]), name="before_goal"),
            Constraint("sometime_after", atom("touched", objects[0], objects[1]), atom("at_b", objects[-1]), name="after_touch"),
        )
        plan = [("move", (objects[0], objects[0], objects[1])), ("move", (objects[-1], objects[0], objects[1]))]
    return Problem(objects, (move,), init, goal, constraints, {"at_a", "at_b", "touched", "bad"}), plan


def make_at_most_once_problem(n_objects: int = 7) -> tuple[Problem, list[tuple[str, tuple[str, ...]]], list[tuple[str, tuple[str, ...]]]]:
    objects = tuple(f"o{i}" for i in range(n_objects))
    toggle_on = Action(
        "toggle_on",
        ("?x", "?y", "?z"),
        TRUE,
        (Effect(TRUE, Literal("flag", ("?x",))), Effect(TRUE, Literal("noise", ("?y", "?z")))),
    )
    toggle_off = Action(
        "toggle_off",
        ("?x", "?y", "?z"),
        atom("flag", "?x"),
        (Effect(TRUE, Literal("flag", ("?x",), True)), Effect(TRUE, Literal("noise", ("?y", "?z")))),
    )
    done = Action("done", ("?x", "?y", "?z"), TRUE, (Effect(TRUE, Literal("finished", ("?x",))),))
    target = objects[0]
    init: set[tuple[str, tuple[str, ...]]] = set()
    goal = atom("finished", target)
    constraints = (Constraint("at_most_once", atom("flag", target), name="flag_once"),)
    valid = [("toggle_on", (target, objects[1], objects[2])), ("done", (target, objects[1], objects[2]))]
    invalid = [
        ("toggle_on", (target, objects[1], objects[2])),
        ("toggle_off", (target, objects[1], objects[2])),
        ("toggle_on", (target, objects[1], objects[2])),
        ("done", (target, objects[1], objects[2])),
    ]
    return Problem(objects, (toggle_on, toggle_off, done), init, goal, constraints, {"flag", "noise", "finished"}), valid, invalid
