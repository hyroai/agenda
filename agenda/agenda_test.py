import gamla

import agenda

_listen_with_memory_when_participated = gamla.compose_left(
    agenda.consumes_user_utterance(None),
    agenda.if_participated,
    agenda.mark_state,
    agenda.remember,
)


_either = gamla.compose_left(
    gamla.lazyjuxt, gamla.after(gamla.compose(gamla.head, gamla.filter(gamla.identity)))
)


@agenda.expect_convos([[["Hi", "say hello"], ["hello", "you said it"], ["Hello", ""]]])
def test_slot():
    what_needs_to_be_said = "hello"
    return agenda.slot(
        agenda.listener_with_memory(
            _either(gamla.equals(what_needs_to_be_said), gamla.just(agenda.UNKNOWN))
        ),
        agenda.ask(f"say {what_needs_to_be_said}"),
        agenda.ack("you said it"),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


@agenda.expect_convos([[["Hi", "say dog or cat"], ["cat", "Got it. You have a cat."]]])
def test_needs():
    options = ["dog", "cat"]
    return agenda.utter_optionally_needs(
        agenda.say(
            gamla.double_star(
                lambda pet: "" if pet == agenda.UNKNOWN else f"You have a {pet}."
            )
        ),
        {
            "pet": agenda.slot(
                agenda.listener_with_memory(
                    lambda x: x in options and x or agenda.UNKNOWN
                ),
                agenda.ask(f"say {' or '.join(options)}"),
                agenda.ack(agenda.GENERIC_ACK),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            )
        },
    )


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
            [
                "Hi",
                "I'm sorry I couldn't get that. Please rephrase. what can i do for you today?",
            ],
        ],
    ]
)
def test_when1():
    topping = agenda.listener_with_memory(
        lambda incoming: next(
            filter(gamla.contains(incoming), ["mushroom", "olives"]), agenda.UNKNOWN
        )
    )
    return agenda.when(
        agenda.slot(
            agenda.listener_with_memory(
                _either(gamla.inside("pizza"), gamla.just(agenda.UNKNOWN))
            ),
            agenda.ask("what can i do for you today?"),
            agenda.ack("okay."),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        ),
        agenda.slot(
            topping,
            agenda.ask("what kind of topping would you like?"),
            agenda.utter_optionally_needs(
                agenda.ack(
                    gamla.double_star(
                        lambda topping: ""
                        if topping is agenda.UNKNOWN
                        else f"got it, {topping} pizza."
                    )
                ),
                {"topping": topping},
            ),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        ),
    )


@agenda.expect_convos(
    [
        [
            ["Hi", "what can i do for you today?"],
            ["i would like to order pizza", "okay. what's your phone?"],
            ["123", "okay. what's your email?"],
            ["bla@bla.com", "okay. your email is bla@bla.com and your phone is 123"],
        ]
    ]
)
def test_when2():
    return agenda.when(
        agenda.slot(
            agenda.listener_with_memory(
                _either(gamla.inside("pizza"), gamla.just(agenda.UNKNOWN))
            ),
            agenda.ask("what can i do for you today?"),
            agenda.ack("okay."),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        ),
        agenda.utter_optionally_needs(
            agenda.say(
                gamla.double_star(
                    lambda phone, email: ""
                    if agenda.UNKNOWN in [phone, email]
                    else f"your email is {email} and your phone is {phone}"
                )
            ),
            {
                "phone": agenda.slot(
                    agenda.listener_with_memory(
                        lambda incoming: incoming if "1" in incoming else agenda.UNKNOWN
                    ),
                    agenda.ask("what's your phone?"),
                    agenda.ack("okay."),
                    agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
                ),
                "email": agenda.slot(
                    agenda.listener_with_memory(
                        lambda incoming: incoming if "@" in incoming else agenda.UNKNOWN
                    ),
                    agenda.ask("what's your email?"),
                    agenda.ack("okay."),
                    agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
                ),
            },
        ),
    )


def _good_or_bad(text):
    if "good" in text:
        return True
    if "bad" in text:
        return False
    return agenda.UNKNOWN


@agenda.expect_convos(
    [
        [["Hi", "how are you?"], ["i am good", "okay. happy to hear."]],
        [["Hi", "how are you?"], ["bad", "okay. sorry to hear."]],
        [
            ["Hi", "how are you?"],
            ["Hi", "I'm sorry I couldn't get that. Please rephrase. how are you?"],
        ],
    ]
)
def test_complement():
    good_or_bad = agenda.slot(
        agenda.listener_with_memory(_good_or_bad),
        agenda.ask("how are you?"),
        agenda.ack("okay."),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )
    return agenda.combine_utter_sinks(
        agenda.when(good_or_bad, agenda.say("happy to hear.")),
        agenda.when(agenda.complement(good_or_bad), agenda.say("sorry to hear.")),
    )


@agenda.expect_convos(
    [[["Hi", "x?"], ["yes", "okay. true"]], [["Hi", "x?"], ["no", "okay. false"]]]
)
def test_listen_if_participated1():
    return agenda.utter_optionally_needs(
        agenda.say(
            gamla.double_star(
                lambda x: "" if x == agenda.UNKNOWN else ("true" if x else "false")
            )
        ),
        {
            "x": agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("x?"),
                agenda.ack("okay."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            )
        },
    )


@agenda.expect_convos(
    [
        [["Hi", "x?"], ["yes", "okay. y?"], ["no", "okay. false"]],
        [["Hi", "x?"], ["no", "okay. y?"], ["no", "okay. false"]],
        [["Hi", "x?"], ["yes", "okay. y?"], ["yes", "okay. true"]],
        [["Hi", "x?"], ["no", "okay. y?"], ["yes", "okay. false"]],
    ]
)
def test_listen_if_participated2():
    return agenda.utter_optionally_needs(
        agenda.say(
            gamla.double_star(
                lambda x, y: ""
                if agenda.UNKNOWN in [x, y]
                else ("true" if (x and y) else "false")
            )
        ),
        {
            "x": agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("x?"),
                agenda.ack("okay."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
            "y": agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("y?"),
                agenda.ack("okay."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
        },
    )


@agenda.expect_convos(
    [[["Hi", "Would you like A?"], ["yes", "I acknowledge your answer"]]]
)
def test_minimal_any_true():
    return agenda.any(
        agenda.slot(
            _listen_with_memory_when_participated(gamla.inside("yes")),
            agenda.ask("Would you like A?"),
            agenda.ack("I acknowledge your answer"),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        )
    )


@agenda.expect_convos(
    [
        [["Hi", "Would you like A?"], ["yes", "You are all set. Happy to hear."]],
        [
            ["Hi", "Would you like A?"],
            ["no", "I got your answer for A. Would you like B?"],
            ["yes", "You are all set. Happy to hear."],
        ],
        [
            ["Hi", "Would you like A?"],
            ["no", "I got your answer for A. Would you like B?"],
            ["no", "You are all set. Have a good day."],
        ],
    ]
)
def test_any_true():
    any_true = agenda.combine_slots(
        agenda.any,
        agenda.ack("You are all set."),
        agenda.anti_ack("Sorry I couldn't understand you. Please rephrase."),
        [
            agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("Would you like A?"),
                agenda.ack("I got your answer for A."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
            agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("Would you like B?"),
                agenda.ack("I got your answer for B."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
        ],
    )
    return agenda.combine_utter_sinks(
        agenda.when(any_true, agenda.say("Happy to hear.")),
        agenda.when(agenda.complement(any_true), agenda.say("Have a good day.")),
    )


@agenda.expect_convos(
    [
        [
            ["Hi", "Would you like A?"],
            ["yes", "Got it that you want A. Would you like B?"],
        ],
        [["Hi", "Would you like A?"], ["no", "You are all set. Have a good day."]],
        [
            ["Hi", "Would you like A?"],
            ["yes", "Got it that you want A. Would you like B?"],
            ["no", "You are all set. Have a good day."],
        ],
        [
            ["Hi", "Would you like A?"],
            ["yes", "Got it that you want A. Would you like B?"],
            ["yes", "You are all set. Happy to hear."],
        ],
    ]
)
def test_all_true():
    all_true = agenda.combine_slots(
        agenda.all,
        agenda.ack("You are all set."),
        agenda.anti_ack("Sorry I couldn't understand you. Please rephrase."),
        [
            agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("Would you like A?"),
                agenda.ack("Got it that you want A."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
            agenda.slot(
                _listen_with_memory_when_participated(gamla.inside("yes")),
                agenda.ask("Would you like B?"),
                agenda.ack("Got it that you want B."),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
        ],
    )
    return agenda.combine_utter_sinks(
        agenda.when(all_true, agenda.say("Happy to hear.")),
        agenda.when(agenda.complement(all_true), agenda.say("Have a good day.")),
    )
