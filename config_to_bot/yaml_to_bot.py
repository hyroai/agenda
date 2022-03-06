import dataclasses
import random
from typing import Awaitable, Callable, Dict, FrozenSet, Iterable, List, Tuple, Union

import gamla
import yaml  # type: ignore
from computation_graph import base_types

import agenda
from config_to_bot import dag_reducer, resolvers

_Triplet = Tuple[str, str, Union[str, Tuple[str]]]

_Node = Union[List, Dict, str, Tuple[str, "_Node"]]  # type: ignore


@dataclasses.dataclass(frozen=True)
class _ObjectAndTriplets:
    obj: Union[str, Tuple[str, ...]]
    triplets: FrozenSet[_Triplet]


_subject_to_object: Callable[[FrozenSet[_Triplet]], Dict] = gamla.compose_left(
    gamla.groupby(gamla.head),
    gamla.valmap(
        gamla.compose_left(
            gamla.mapcat(
                gamla.compose_left(
                    gamla.nth(2),
                    gamla.unless(gamla.is_instance(tuple), gamla.wrap_tuple),
                )
            ),
            set,
        )
    ),
)


_infer_sink: Callable[[Dict], str] = gamla.compose_left(
    gamla.juxt(
        gamla.compose_left(dict.keys, set),
        gamla.compose_left(dict.values, gamla.concat, set),
    ),
    gamla.star(set.difference),
    gamla.head,
)


def _subject_to_relation_object_map(
    triplets: FrozenSet[_Triplet],
) -> Callable[[str], Dict[str, str]]:
    return gamla.pipe(
        triplets,
        gamla.groupby(gamla.head),
        gamla.valmap(
            gamla.compose_left(
                gamla.groupby(gamla.second),
                gamla.valmap(gamla.compose_left(gamla.head, gamla.nth(2))),
            )
        ),
        gamla.attrgetter("__getitem__"),
    )


_RelationAndObjectAndTriplets = Tuple[str, _ObjectAndTriplets]
_ReducerState = Union[_ObjectAndTriplets, _RelationAndObjectAndTriplets]


def _reducer(current: _Node, children: Iterable[_ReducerState]) -> _ReducerState:
    reduced_children = tuple(children)
    if not reduced_children:
        return _ObjectAndTriplets(current, frozenset())  # type: ignore
    if isinstance(current, list):
        return _ObjectAndTriplets(
            tuple(map(lambda c: c.obj, reduced_children)),  # type: ignore
            frozenset(gamla.mapcat(lambda c: c.triplets)(reduced_children)),
        )
    if isinstance(current, dict):
        return _dict_to_triplets(current, reduced_children)
    if isinstance(current, tuple):
        relation, data = current
        assert len(reduced_children) == 1, data
        return relation, reduced_children[0]  # type: ignore
    assert False, current


def _dict_to_triplets(
    current: _Node, children: Iterable[_ReducerState]
) -> _ObjectAndTriplets:
    node_id = gamla.pipe(current, gamla.freeze_deep, gamla.compute_stable_json_hash)
    return _ObjectAndTriplets(
        node_id,
        gamla.pipe(children, gamla.mapcat(_child_to_triplets(node_id)), frozenset),
    )


def _child_to_triplets(
    name: str,
) -> Callable[[_RelationAndObjectAndTriplets], FrozenSet[_Triplet]]:
    return gamla.compose_left(
        lambda child: gamla.suffix((name, child[0], child[1].obj), child[1].triplets),
        frozenset,
    )


def _children(node: _Node) -> Iterable[_Node]:
    if isinstance(node, list):
        yield from node
    if isinstance(node, dict):
        yield from node.items()
    if isinstance(node, str):
        return
    if isinstance(node, tuple):
        relation, d = node
        yield d


def _yaml_dict_to_triplets(yaml_dict: Dict) -> FrozenSet[_Triplet]:
    return gamla.pipe(
        gamla.tree_reduce(_children, _reducer, ("root", yaml_dict)),
        gamla.last,
        gamla.attrgetter("triplets"),
    )


@gamla.curry
def _build_cg(
    remote_function: Callable, triplets: FrozenSet[_Triplet]
) -> base_types.GraphType:
    dependencies = _subject_to_object(triplets)
    return gamla.pipe(
        dag_reducer.reduce_graph(
            dependencies,
            _subject_to_relation_object_map(triplets),
            dag_reducer.reducer(remote_function),
        ),
        gamla.itemgetter(_infer_sink(dependencies)),
    )


def _ack_generator() -> str:
    x = random.choice(["Okay.", "Alright.", "Got it.", "Cool."])
    # TODO(uri): For a reason I don't full understand, unless we have a `print` or `breakpoint` here, it always selects the same option.
    print(x)  # noqa: T001
    return x


sentence_to_str = agenda.sentence_renderer(_ack_generator)


def yaml_to_cg(remote_function: Callable) -> Callable[[str], base_types.GraphType]:
    return gamla.compose_left(
        yaml.safe_load, _yaml_dict_to_triplets, _build_cg(remote_function)
    )


yaml_to_slot_bot: Callable[[str], Callable[[], Awaitable]] = gamla.compose_left(
    yaml_to_cg(resolvers.post_request_with_url_and_params),
    agenda.wrap_up(agenda.sentence_renderer(_ack_generator)),
    gamla.after(gamla.to_awaitable),
    gamla.just,
)
