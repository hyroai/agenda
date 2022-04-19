import gamla
from computation_graph import base_types
from computation_graph import composers as cg_composers
from computation_graph.composers import duplication

from agenda import composers, sentence, state_aggregators, test_utils

UNKNOWN = composers.UNKNOWN
Unknown = composers.Unknown

GENERIC_ACK = sentence.GENERIC_ACK
GENERIC_ANTI_ACK = sentence.GENERIC_ANTI_ACK
combine_utter_sinks = composers.combine_utter_sinks
listener_with_memory = composers.listener_with_memory
if_participated = composers.if_participated
state_optionally_needs = composers.state_optionally_needs
utter_optionally_needs = composers.utter_optionally_needs
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
# TODO(uri): I'm not sure why mypy doesn't like this.
expect_convos = test_utils.expect_convos  # type: ignore
ever = composers.ever
combine_slots = composers.combine_slots
state_sink = composers.state_sink
state_sink_or_none = composers.state_sink_or_none
utter_sink = composers.utter_sink


def _generic(transformation):
    def inner(x):
        if base_types.is_computation_graph(x):
            return composers.mark_utter(
                cg_composers.compose_left_unary(
                    x, duplication.duplicate_function(transformation)
                )
            )
        if callable(x):
            return composers.mark_utter(gamla.compose(transformation, x))
        return inner(lambda: x)

    return inner


ask = _generic(sentence.str_to_question)
say = _generic(sentence.str_to_statement)
ack = _generic(sentence.str_to_ack)
anti_ack = _generic(sentence.str_to_anti_ack)

consumes_external_event = composers.consumes_external_event
consumes_time = composers.consumes_time


def sentence_renderer(ack_renderer, anti_ack_renderer):
    return lambda x: sentence.sentence_to_str(ack_renderer, anti_ack_renderer, x)
