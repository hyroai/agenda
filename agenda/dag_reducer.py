from typing import Callable, Dict, FrozenSet

import agenda
import gamla
import toposort
from computation_graph import base_types
from computation_graph.composers import lift


def _determine_composer(keys: FrozenSet[str]) -> Callable[..., base_types.GraphType]:
    if not keys:
        return gamla.just(gamla.identity)
    if keys == frozenset({"say"}):

        def composer(say):
            return agenda.state(say)

        return composer
    return gamla.just(gamla.identity)


def reducer(
    state: Dict[str, base_types.GraphType],
    current: str,
    node_to_neighbors: Callable[[str], Dict[str, str]],
):
    try:
        cg_dict = gamla.pipe(
            current, node_to_neighbors, gamla.valmap(state.__getitem__)
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
        depenedencies,
        toposort.toposort_flatten,
        gamla.reduce_curried(
            lambda state, current: gamla.pipe(
                reducer(state, current, node_to_neighbors),
                gamla.assoc_in(state, [current]),
            ),
            {},
        ),
    )
