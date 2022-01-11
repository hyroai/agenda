import gamla
from computation_graph import base_types

from agenda import composers


@gamla.curry
def expect_convo(convo, f):
    cg = composers.wrap_up(f())

    def inner():
        result = base_types.ComputationResult(None, None)
        for input_event, output_event in convo:
            result = cg(event=input_event, state=result.state)
            assert result.result[composers.utter] == output_event

    return inner
