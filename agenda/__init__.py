import gamla

from agenda import composers, sentence, state_aggregators, test_utils

UNKNOWN = composers.UNKNOWN
Unknown = composers.Unknown

GENERIC_ACK = sentence.GENERIC_ACK
combine_utter_sinks = composers.combine_utter_sinks
listener_with_memory = composers.listener_with_memory
if_participated = composers.if_participated
optionally_needs = composers.optionally_needs
slot = composers.slot
when = composers.when
remember = composers.remember
mark_state = composers.mark_state
participated = composers.participated

wrap_up = composers.wrap_up

complement = composers.complement
equals = composers.equals
less_than = composers.less_than
less_equals = composers.less_equals
greater_equals = composers.greater_equals
not_equals = composers.not_equals
inside = composers.inside
contains = composers.contains
any = state_aggregators.any_true
all = state_aggregators.all_true
first_known = state_aggregators.first_known
str_to_statement = sentence.str_to_statement
expect_convos = test_utils.expect_convos
ever = composers.ever
combine_slots = composers.combine_slots
state_sink = composers.state_sink
state_sink_or_none = composers.state_sink_or_none
utter_sink = composers.utter_sink


def _value_to_function_if_needed(value_or_function):
    if callable(value_or_function):
        return value_or_function
    return lambda: value_or_function


def _generic(inner):
    return gamla.compose(
        composers.mark_utter, gamla.after(inner), _value_to_function_if_needed
    )


ask = _generic(sentence.str_to_question)
say = _generic(sentence.str_to_statement)
ack = _generic(sentence.str_to_ack)

consumes_external_event = composers.consumes_external_event


def sentence_renderer(ack_renderer):
    return lambda x: sentence.sentence_to_str(ack_renderer, x)
