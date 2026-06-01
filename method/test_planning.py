from planning import Action, Effect, Literal, TRUE, lifted_gamma


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
