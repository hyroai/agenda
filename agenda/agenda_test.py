import agenda


@agenda.expect_convo([["Hi", "say hello"], ["hello", "you said it"], ["Hello", ""]])
def test_slot():
    what_needs_to_be_said = "hello"
    return agenda.slot(
        agenda.function_to_listener_with_memory(
            lambda x: x == what_needs_to_be_said or agenda.UNKNOWN
        ),
        agenda.str_to_asker(f"say {what_needs_to_be_said}"),
        agenda.str_to_acker("you said it"),
    )


@agenda.expect_convo([["Hi", "say dog or cat"], ["cat", "Got it. You have a cat."]])
def test_goal():
    options = ["dog", "cat"]
    return agenda.optionally_needs(
        agenda.function_to_stater(
            lambda pet: "" if pet == agenda.UNKNOWN else f"You have a {pet}.",
        ),
        {
            "pet": agenda.slot(
                agenda.function_to_listener_with_memory(
                    lambda x: x in options and x or agenda.UNKNOWN
                ),
                agenda.str_to_asker(f"say {' or '.join(options)}"),
                agenda.str_to_acker("Got it."),
            )
        },
    )
