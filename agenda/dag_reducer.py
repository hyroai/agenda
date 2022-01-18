from typing import Callable, Dict, FrozenSet, List, Iterable, Tuple

import agenda
import gamla
import toposort
import httpx
from computation_graph import base_types, composers
from computation_graph.composers import lift
from agenda import composers as agenda_composers


def _determine_composer(keys: FrozenSet[str]) -> Callable[..., base_types.GraphType]:
    if not keys:
        return gamla.identity
    if keys == frozenset({"say"}):

        def say_composer(say):
            return agenda.state(say)

        return say_composer

    if keys == frozenset({"ack"}):

        def ack_composer(ack):
            return agenda.ack(ack)

        return ack_composer

    if keys == frozenset({"ask"}):

        def ask_composer(ask):
            return agenda.ask(ask)

    if keys == frozenset({"key", "value"}):

        def needs_composer(key, value):
            if value() == "incoming_utterance":
                return (key(), agenda.event)
            return (key(), value())

        return needs_composer

    if keys == frozenset({"url", "needs"}):

        def remote(needs: Tuple[str, base_types.GraphType], url: str):
            async def remote_function(params: Dict):
                return gamla.pipe(
                    await gamla.post_json_with_extra_headers_and_params_async(
                        {}, {"Content-Type": "application/json"}, 30, url(), params
                    ),
                    httpx.Response.json,
                    gamla.when(gamla.equals(None), gamla.just(agenda.UNKNOWN)),
                )

            return composers.compose_left_unary(
                gamla.pipe(
                    needs,
                    gamla.map(
                        gamla.compose_left(
                            gamla.packstack(lambda x: lambda: x, gamla.identity),
                            lambda pair: composers.compose_dict(
                                lambda x, y: (x, y), dict(zip(["x", "y"], pair))
                            ),
                        )
                    ),
                    tuple,
                    lambda cg: composers.compose_many_to_one(
                        lambda args: gamla.frozendict(dict(args)), cg
                    ),
                ),
                remote_function,
            )

        return remote

    if keys == frozenset({"ack", "listen", "ask"}):

        def slot_composer(ack, listen, ask):
            return agenda.slot(
                gamla.pipe(listen, agenda.mark_state, agenda.remember),
                agenda.ask(ask()),
                agenda.ack(ack()),
            )

        return slot_composer
    if keys == frozenset({"goals", "slots"}):

        def goals_composer(goals, slots):
            return base_types.merge_graphs(*goals)

        return goals_composer
    assert False, keys


def reducer(
    state: Dict[str, base_types.GraphType],
    current: str,
    node_to_neighbors: Callable[[str], Dict[str, str]],
):
    try:
        cg_dict = gamla.pipe(
            current,
            node_to_neighbors,
            gamla.valmap(
                gamla.ternary(
                    gamla.is_instance(tuple),
                    gamla.compose_left(gamla.map(state.__getitem__), tuple),
                    state.__getitem__,
                )
            ),
        )
    except KeyError:
        return lift.always(current)
    to_cg = _determine_composer(frozenset(cg_dict))
    return to_cg(**cg_dict)


def reduce_graph(
    depenedencies: Dict[str, FrozenSet[str]],
    node_to_neighbors: Callable[[str], Dict[str, str]],
    reducer: Callable[
        [Dict[str, base_types.GraphType], str, Callable[[str], Dict[str, str]]],
        Dict[str, base_types.GraphType],
    ],
):
    return gamla.pipe(
        toposort.toposort_flatten(depenedencies, False),
        gamla.reduce_curried(
            lambda state, current: gamla.pipe(
                reducer(state, current, node_to_neighbors),
                gamla.assoc_in(state, [current]),
            ),
            {},
        ),
    )
