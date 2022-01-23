import gamla
from computation_graph import graph

from agenda import composers


@gamla.curry
def expect_convos(convos, f):
    def inner():
        cg = composers.wrap_up(f())
        for convo in convos:
            prev = {}
            for input_event, expected in convo:
                prev = cg({**prev, composers.event: input_event})
                result = prev[graph.make_computation_node(composers.utter)]
                assert result == expected, f"expected: {expected} actual: {result}"

    return inner
