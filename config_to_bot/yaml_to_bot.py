from typing import Callable, Dict, FrozenSet, Iterable, Tuple, Union, List, Awaitable

from . import dag_reducer
import gamla
import yaml
import agenda
import dataclasses
from computation_graph import run, base_types

_Object = str

_Relation = str

_Triplet = Tuple[str, str, Union[str, Tuple[str]]]

_Node = Union[List, Dict, str, Tuple[str, "_Node"]]


@dataclasses.dataclass(frozen=True)
class _ObjectAndTriplets:
    obj: Union[str, Tuple[str, ...]]
    triplets: _Triplet


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


def _parse_yaml_file(file_name: str) -> Dict:
    with open(file_name) as f:
        config_dict = yaml.safe_load(f)
    return config_dict


_RelationAndObjectAndTriplets = Tuple[str, _ObjectAndTriplets]
_ReducerState = Union[_ObjectAndTriplets, _RelationAndObjectAndTriplets]


def _reducer(current: _Node, children: Iterable[_ReducerState]) -> _ReducerState:
    reduced_children = tuple(children)
    if not reduced_children:
        return _ObjectAndTriplets(current, frozenset())
    if isinstance(current, list):
        return _ObjectAndTriplets(
            tuple(map(lambda c: c.obj, reduced_children)),
            frozenset(gamla.mapcat(lambda c: c.triplets)(reduced_children)),
        )
    if isinstance(current, dict):
        return _dict_to_triplets(current, reduced_children)
    if isinstance(current, tuple):
        relation, data = current
        assert len(reduced_children) == 1, data
        return relation, reduced_children[0]
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


def _build_cg(triplets: FrozenSet[_Triplet]) -> base_types.GraphType:
    dependencies = _subject_to_object(triplets)
    return gamla.pipe(
        dag_reducer.reduce_graph(
            dependencies, _subject_to_relation_object_map(triplets), dag_reducer.reducer
        ),
        gamla.itemgetter(_infer_sink(dependencies)),
    )


yaml_to_slot_bot: Callable[[str], Callable[[], Awaitable]] = gamla.compose_left(
    _parse_yaml_file,
    _yaml_dict_to_triplets,
    _build_cg,
    agenda.wrap_up,
    gamla.after(gamla.to_awaitable),
    gamla.just,
)
