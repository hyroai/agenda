import inspect
import keyword
from types import MappingProxyType
from typing import Any, Callable, Dict, FrozenSet, Iterable

import gamla
import toposort
from computation_graph import base_types

from config_to_bot import resolvers

_resolver_signature = gamla.compose_left(
    inspect.signature,
    gamla.attrgetter("parameters"),
    MappingProxyType.values,
    gamla.map(gamla.attrgetter("name")),
    frozenset,
)
_preprocess_key = gamla.compose_left(
    gamla.when(keyword.iskeyword, gamla.wrap_str("{}_")),
    gamla.replace_in_text("-", "_"),
)
_functions_to_case_dict: Callable[
    [Iterable[Callable]], Callable[[Dict], Any]
] = gamla.compose_left(
    gamla.map(
        gamla.juxt(gamla.compose(gamla.equals, _resolver_signature), gamla.double_star)
    ),
    gamla.suffix((gamla.equals(None), gamla.identity)),
    dict,
    gamla.keymap(gamla.before(gamla.compose_left(dict.keys, frozenset))),
    gamla.case_dict,
    gamla.before(gamla.keymap(_preprocess_key)),
)


def reducer(
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
    except KeyError:
        return current
    return _functions_to_case_dict(resolvers.COMPOSERS_FOR_DAG_REDUCER)(cg_dict)


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
