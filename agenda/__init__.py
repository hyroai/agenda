import gamla

from agenda import composers, sentence, test_utils

UNKNOWN = composers.UNKNOWN
combine_utterances = composers.combine_utterances
function_to_listener_with_memory = composers.function_to_listener_with_memory
optionally_needs = composers.optionally_needs
slot = composers.slot
when = composers.when
complement = composers.complement
str_to_statement = sentence.str_to_statement
listen_if_participated_last_turn = composers.listen_if_participated_last_turn
expect_convos = test_utils.expect_convos


def _value_to_function_if_needed(value_or_function):
    if isinstance(value_or_function, str):
        return lambda: value_or_function
    return value_or_function


def _generic(inner):
    return gamla.compose(
        composers.mark_utter, gamla.after(inner), _value_to_function_if_needed
    )


ask = _generic(sentence.str_to_question)
say = _generic(sentence.str_to_statement)
ack = _generic(sentence.str_to_ack)
