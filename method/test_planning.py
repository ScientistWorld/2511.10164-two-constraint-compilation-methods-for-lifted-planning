"""Unit tests for the lifted compilers (run: PYTHONPATH=method python method/test_planning.py)."""
from planning import (Action, Atom, Constraint, Effect, Exists, ForAll, Literal, Not, Problem, TRUE,
                      compile_lcc, compile_lifted_tcore, lifted_gamma, plan_valid, regress)


def test_lifted_gamma_repeated_effect_variable_adds_equality() -> None:
    action = Action("pair", ("?a",), TRUE, (Effect(TRUE, Literal("linked", ("?a", "?a"))),))
    gamma = lifted_gamma(Literal("linked", ("?x", "?y")), action)
    assert gamma.substitute({"?x": "o0", "?y": "o1", "?a": "o0"}).eval(set(), ("o0", "o1")) is False
    assert gamma.substitute({"?x": "o0", "?y": "o0", "?a": "o0"}).eval(set(), ("o0", "o1")) is True


def test_lifted_gamma_repeated_query_variable_adds_equality() -> None:
    action = Action("pair", ("?a", "?b"), TRUE, (Effect(TRUE, Literal("linked", ("?a", "?b"))),))
    gamma = lifted_gamma(Literal("linked", ("?x", "?x")), action)
    assert gamma.substitute({"?x": "o0", "?a": "o0", "?b": "o1"}).eval(set(), ("o0", "o1")) is False
    assert gamma.substitute({"?x": "o0", "?a": "o0", "?b": "o0"}).eval(set(), ("o0", "o1")) is True


def test_regression_is_identity_for_unaffected_formula() -> None:
    action = Action("touch", ("?a",), TRUE, (Effect(TRUE, Literal("touched", ("?a",))),))
    phi = Atom(Literal("other", ("o1",)))
    assert regress(phi, action) == phi
    # paper Section 3.2: such updates are omitted, the ablation keeps them
    problem = Problem(("o0", "o1"), (action,), set(), Atom(Literal("touched", ("o0",))),
                      (Constraint("always", Not(phi)),), {"touched", "other"})
    assert len(compile_lifted_tcore(problem).actions[0].effects) == 1
    assert compile_lifted_tcore(problem).actions[0].precondition == TRUE
    assert compile_lifted_tcore(problem, omit_unchanged=False).actions[0].precondition != TRUE


def test_forall_effect_regression_example_3() -> None:
    # putdown2-like effect: forall topb: on(topb, b) |> clear(topb)
    action = Action("put", ("?b",), TRUE, (Effect(Atom(Literal("on", ("?t", "?b"))), Literal("clear", ("?t",)), ("?t",)),))
    gamma = lifted_gamma(Literal("clear", ("o5",)), action)
    assert gamma.substitute({"?b": "o2"}).eval({("on", ("o5", "o2"))}, ("o2", "o5")) is True
    assert gamma.substitute({"?b": "o2"}).eval({("on", ("o2", "o5"))}, ("o2", "o5")) is False


def test_quantified_constraint_with_clashing_variable_names() -> None:
    # The constraint reuses the action's forall variable name; renaming apart avoids capture.
    action = Action("mark", ("?x0",), Atom(Literal("ready", ("?x0",))),
                    (Effect(Atom(Literal("link", ("?z0", "?x0"))), Literal("bad", ("?z0",)), ("?z0",)),))
    problem = Problem(("a", "b"), (action,), {("ready", ("a",)), ("ready", ("b",)), ("link", ("a", "b"))},
                      Atom(Literal("ready", ("a",))),
                      (Constraint("always", ForAll(("?z0",), Not(Atom(Literal("bad", ("?z0",)))))),), set())
    bad_plan = [("mark", ("b",))]          # makes bad(a) true
    ok_plan = [("mark", ("a",))]           # no link(?, a): nothing becomes bad
    for compiled, suffix in ((compile_lifted_tcore(problem), []), (compile_lcc(problem), [("fin", ())])):
        assert plan_valid(compiled, ok_plan + suffix)
        assert not plan_valid(compiled, bad_plan + suffix)
    assert not plan_valid(problem, bad_plan) and plan_valid(problem, ok_plan)


def test_sometime_before_initial_witness_is_seen_by_lifted_compilers() -> None:
    problem = Problem(("o0",), (Action("make_p", (), TRUE, (Effect(TRUE, Literal("p")),)),), {("q", ())},
                      Atom(Literal("p")), (Constraint("sometime_before", Atom(Literal("p")), Atom(Literal("q"))),),
                      {"p", "q"})
    plan = [("make_p", ())]
    assert plan_valid(problem, plan)
    assert plan_valid(compile_lifted_tcore(problem), plan)
    assert plan_valid(compile_lcc(problem), plan + [("fin", ())])


def test_at_most_once_initial_truth_blocks_reentry() -> None:
    problem = Problem(
        ("o0",),
        (Action("clear_p", (), Atom(Literal("p")), (Effect(TRUE, Literal("p", (), True)),)),
         Action("make_p", (), TRUE, (Effect(TRUE, Literal("p")),)),
         Action("finish", (), TRUE, (Effect(TRUE, Literal("done")),))),
        {("p", ())}, Atom(Literal("done")), (Constraint("at_most_once", Atom(Literal("p"))),), {"p", "done"})
    valid_plan = [("finish", ())]
    invalid_plan = [("clear_p", ()), ("make_p", ()), ("finish", ())]
    assert plan_valid(problem, valid_plan) and not plan_valid(problem, invalid_plan)
    assert plan_valid(compile_lifted_tcore(problem), valid_plan)
    assert not plan_valid(compile_lifted_tcore(problem), invalid_plan)
    assert plan_valid(compile_lcc(problem), valid_plan + [("fin", ())])
    assert not plan_valid(compile_lcc(problem), invalid_plan + [("fin", ())])


def test_lcc_requires_fin() -> None:
    problem = Problem(("o0",), (Action("set_p", (), TRUE, (Effect(TRUE, Literal("p")),)),), set(),
                      Atom(Literal("p")), (Constraint("sometime", Exists(("?v",), Atom(Literal("p")))),), {"p"})
    compiled = compile_lcc(problem)
    assert not plan_valid(compiled, [("set_p", ())])
    assert plan_valid(compiled, [("set_p", ()), ("fin", ())])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("planning regression tests passed")
