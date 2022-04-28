import dataclasses
from typing import Callable, Dict, FrozenSet, Iterable, List, Tuple, Union

import gamla
import knowledge_graph
from computation_graph import base_types
from knowledge_graph import primitives

from config_to_bot import dag_reducer

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


def yaml_dict_to_triplets(yaml_dict: Dict) -> FrozenSet[_Triplet]:
    return gamla.pipe(
        gamla.tree_reduce(_children, _reducer, ("root", yaml_dict)),
        gamla.last,
        gamla.attrgetter("triplets"),
    )


@gamla.curry
def reduce_kg(reducer: Callable, triplets: FrozenSet[_Triplet]) -> base_types.GraphType:
    dependencies = _subject_to_object(triplets)
    return gamla.pipe(
        dag_reducer.reduce_graph(
            dependencies, _subject_to_relation_object_map(triplets), reducer
        ),
        gamla.itemgetter(_infer_sink(dependencies)),
    )


def _build_trigger_and_display_triplets(
    subject: str, relation: str, object: str
) -> FrozenSet[knowledge_graph.Triplet]:
    return frozenset(
        {
            knowledge_graph.display_triplet(
                subject, primitives.text_to_textual(object)
            ),
            knowledge_graph.trigger_triplet(
                subject, primitives.text_to_textual(object)
            ),
        }
    )


def _build_instances_triplets(
    subject: str, relation: str, instances: Tuple[str, ...]
) -> FrozenSet[knowledge_graph.Triplet]:
    return gamla.pipe(
        instances,
        gamla.mapcat(
            gamla.compose_left(
                gamla.juxt(
                    lambda instance: knowledge_graph.type_triplet(instance, subject),
                    lambda instance: knowledge_graph.trigger_triplet(
                        instance, primitives.text_to_textual(instance)
                    ),
                    lambda instance: knowledge_graph.display_triplet(
                        instance, primitives.text_to_textual(instance)
                    ),
                ),
                frozenset,
            )
        ),
        frozenset,
    )


_triplet_transformer = gamla.case_dict(
    gamla.keymap(gamla.before(gamla.second))(
        {
            gamla.equals("instances"): gamla.star(_build_instances_triplets),
            gamla.equals("concept"): gamla.star(_build_trigger_and_display_triplets),
            gamla.just(True): gamla.wrap_frozenset,
        }
    )
)


adapt_kg: Callable[
    [FrozenSet[_Triplet]], knowledge_graph.KnowledgeGraph
] = gamla.compose_left(
    gamla.mapcat(_triplet_transformer), frozenset, knowledge_graph.from_triplets
)
