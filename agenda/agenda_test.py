import agenda


@agenda.expect_convos([[["Hi", "say hello"], ["hello", "you said it"], ["Hello", ""]]])
def test_slot():
    what_needs_to_be_said = "hello"
    return agenda.slot(
        agenda.function_to_listener_with_memory(
            lambda x: x == what_needs_to_be_said or agenda.UNKNOWN
        ),
        agenda.ask(f"say {what_needs_to_be_said}"),
        agenda.ack("you said it"),
    )


@agenda.expect_convos([[["Hi", "say dog or cat"], ["cat", "Got it. You have a cat."]]])
def test_needs():
    options = ["dog", "cat"]
    return agenda.optionally_needs(
        agenda.state(lambda pet: "" if pet == agenda.UNKNOWN else f"You have a {pet}."),
        {
            "pet": agenda.slot(
                agenda.function_to_listener_with_memory(
                    lambda x: x in options and x or agenda.UNKNOWN
                ),
                agenda.ask(f"say {' or '.join(options)}"),
                agenda.ack("Got it."),
            )
        },
    )


import gamla


@agenda.expect_convos(
    [
        [
            ["Hi", "what can i do for you today?"],
            [
                "i would like to order pizza",
                "okay. what kind of topping would you like?",
            ],
            ["mushroom", "got it, mushroom pizza."],
            ["actually olives", "got it, olives pizza."],
        ],
        [
            ["Hi", "what can i do for you today?"],
            ["Hi", "what can i do for you today?"],
        ],
    ]
)
def test_when():
    topping = agenda.function_to_listener_with_memory(
        lambda incoming: next(
            filter(lambda x: x in incoming, ["mushroom", "olives"]), agenda.UNKNOWN
        )
    )
    return agenda.when(
        agenda.slot(
            agenda.function_to_listener_with_memory(
                lambda x: "pizza" in x or agenda.UNKNOWN
            ),
            agenda.ask("what can i do for you today?"),
            agenda.ack("okay."),
        ),
        agenda.slot(
            topping,
            agenda.ask("what kind of topping would you like?"),
            agenda.optionally_needs(
                agenda.ack(
                    lambda topping: agenda.EMPTY_SENTENCE
                    if topping is agenda.UNKNOWN
                    else f"got it, {topping} pizza."
                ),
                {"topping": topping},
            ),
        ),
    )
