import gamla

from agenda import composers, sentence, test_utils, state_aggregators


UNKNOWN = composers.UNKNOWN
Unknown = composers.Unknown

combine_utter_sinks = composers.combine_utter_sinks
listener_with_memory = composers.listener_with_memory
if_participated = composers.if_participated
optionally_needs = composers.optionally_needs
slot = composers.slot
when = composers.when
remember = composers.remember
mark_state = composers.mark_state

wrap_up = composers.wrap_up

complement = composers.complement
any = slots_aggregators.any_true
all = slots_aggregators.all_true
str_to_statement = sentence.str_to_statement
expect_convos = test_utils.expect_convos
mark_state = composers.mark_state
remember = composers.remember
combine_slots = composers.combine_slots


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

consumes_external_event = composers.consumes_external_event
