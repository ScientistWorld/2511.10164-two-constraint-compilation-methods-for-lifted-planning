from planning import (
    Action,
    Atom,
    Constraint,
    Effect,
    Literal,
    Problem,
    TRUE,
    compile_ground_tcore,
    compile_lcc,
    compile_lifted_tcore,
    lifted_gamma,
    plan_valid,
)


def test_lifted_gamma_repeated_effect_variable_adds_equality() -> None:
    action = Action("pair", ("?a",), TRUE, (Effect(TRUE, Literal("linked", ("?a", "?a"))),))

    gamma = lifted_gamma(Literal("linked", ("?x", "?y")), action)

    assert gamma.substitute({"?x": "o0", "?y": "o1", "?a": "o0"}).eval(set(), ("o0", "o1")) is False
    assert gamma.substitute({"?x": "o0", "?y": "o0", "?a": "o0"}).eval(set(), ("o0", "o1")) is True


def test_lifted_gamma_repeated_query_variable_adds_equality() -> None:
    action = Action(
        "pair",
        ("?a", "?b"),
        TRUE,
        (Effect(TRUE, Literal("linked", ("?a", "?b"))),),
    )

    gamma = lifted_gamma(Literal("linked", ("?x", "?x")), action)

    assert gamma.substitute({"?x": "o0", "?a": "o0", "?b": "o1"}).eval(set(), ("o0", "o1")) is False
    assert gamma.substitute({"?x": "o0", "?a": "o0", "?b": "o0"}).eval(set(), ("o0", "o1")) is True


def test_sometime_before_initial_witness_is_seen_by_lifted_compilers() -> None:
    problem = Problem(
        ("o0",),
        (Action("make_p", (), TRUE, (Effect(TRUE, Literal("p")),)),),
        {("q", ())},
        Atom(Literal("p")),
        (Constraint("sometime_before", Atom(Literal("p")), Atom(Literal("q")), name="q_before_p"),),
        {"p", "q"},
    )
    plan = [("make_p", ())]

    assert plan_valid(problem, plan)
    assert plan_valid(compile_lifted_tcore(problem), plan)
    assert plan_valid(compile_lcc(problem), plan + [("fin", ())])
    assert plan_valid(compile_ground_tcore(problem), [("make_p_", ())])


def test_at_most_once_initial_truth_blocks_reentry_in_lifted_tcore() -> None:
    problem = Problem(
        ("o0",),
        (
            Action("clear_p", (), Atom(Literal("p")), (Effect(TRUE, Literal("p", (), True)),)),
            Action("make_p", (), TRUE, (Effect(TRUE, Literal("p")),)),
            Action("finish", (), TRUE, (Effect(TRUE, Literal("done")),)),
        ),
        {("p", ())},
        Atom(Literal("done")),
        (Constraint("at_most_once", Atom(Literal("p")), name="p_once"),),
        {"p", "done"},
    )
    valid_plan = [("finish", ())]
    invalid_plan = [("clear_p", ()), ("make_p", ()), ("finish", ())]

    assert plan_valid(problem, valid_plan)
    assert not plan_valid(problem, invalid_plan)
    assert plan_valid(compile_lifted_tcore(problem), valid_plan)
    assert not plan_valid(compile_lifted_tcore(problem), invalid_plan)
    assert plan_valid(compile_lcc(problem), valid_plan + [("fin", ())])
    assert not plan_valid(compile_lcc(problem), invalid_plan + [("fin", ())])


if __name__ == "__main__":
    test_lifted_gamma_repeated_effect_variable_adds_equality()
    test_lifted_gamma_repeated_query_variable_adds_equality()
    test_sometime_before_initial_witness_is_seen_by_lifted_compilers()
    test_at_most_once_initial_truth_blocks_reentry_in_lifted_tcore()
    print("planning regression tests passed")
