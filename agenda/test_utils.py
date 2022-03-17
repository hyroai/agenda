import gamla
from computation_graph import graph

import agenda
from agenda import composers


@gamla.curry
def expect_convos(convos, f):
    async def inner():
        bot = gamla.pipe(
            f(),
            composers.wrap_up(
                agenda.sentence_renderer(
                    lambda: "Got it.",
                    lambda: "I'm sorry I couldn't get that. Please rephrase.",
                )
            ),
            gamla.after(gamla.to_awaitable),
        )
        for convo in convos:
            state = {}
            for input_event, expected in convo:
                state = await bot(state, {composers.event: input_event})
                result = state[graph.make_computation_node(composers.utter)]
                assert result == expected, f"expected: {expected} actual: {result}"

    return inner
