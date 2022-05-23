import datetime

import gamla
from computation_graph import graph

import agenda
from agenda import composers


@gamla.curry
async def expect_convos(convos, cg):
    bot = gamla.pipe(
        cg,
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
            state = (
                await bot(
                    state,
                    {composers.event: input_event[0], composers.now: input_event[1]},
                )
                if isinstance(input_event, tuple)
                else await bot(
                    state,
                    {
                        composers.event: input_event,
                        composers.now: datetime.datetime.now(),
                    },
                )
            )
            result = state[graph.make_computation_node(composers.utter)]
            assert result == expected, f"expected: {expected} actual: {result}"
