from typing import Any, Callable, Dict, FrozenSet

import gamla
import toposort
from computation_graph import base_types


@gamla.curry
def reducer(
    process_children_dict: Callable,
    state: Dict[str, base_types.GraphType],
    current: str,
    node_to_neighbors: Callable[[str], Dict[str, str]],
) -> Any:
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
        return process_children_dict(cg_dict)
    except KeyError:
        return current


def reduce_graph(
    depenedencies: Dict[str, FrozenSet[str]],
    node_to_neighbors: Callable[[str], Dict[str, str]],
    reducer: Callable[
        [Dict[str, base_types.GraphType], str, Callable[[str], Dict[str, str]]],
        Dict[str, base_types.GraphType],
    ],
) -> Dict[str, base_types.GraphType]:
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
