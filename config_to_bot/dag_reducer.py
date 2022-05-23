from typing import Any, Callable, Dict, FrozenSet

import gamla
import toposort
from computation_graph import base_types


@gamla.curry
async def reducer(
    process_children_dict: Callable,
    state: Dict[str, base_types.GraphType],
    current: str,
    node_to_neighbors: Callable[[str], Dict[str, str]],
) -> Any:
    try:
        return await gamla.pipe(
            current,
            node_to_neighbors,
            gamla.valmap(
                gamla.ternary(
                    gamla.is_instance(tuple),
                    gamla.compose_left(gamla.map(state.__getitem__), tuple),
                    state.__getitem__,
                )
            ),
            process_children_dict,
            gamla.to_awaitable,
        )
    except KeyError:
        return current


async def reduce_graph(
    depenedencies: Dict[str, FrozenSet[str]],
    node_to_neighbors: Callable[[str], Dict[str, str]],
    reducer: Callable[
        [Dict[str, base_types.GraphType], str, Callable[[str], Dict[str, str]]],
        Dict[str, base_types.GraphType],
    ],
) -> Dict[str, base_types.GraphType]:
    async def graph_reducer(state, current):
        return gamla.pipe(
            await reducer(state, current, node_to_neighbors),
            gamla.assoc_in(state, [current]),
        )

    return await gamla.pipe(
        toposort.toposort_flatten(depenedencies, False),
        gamla.reduce_curried(graph_reducer, {}),
    )
