from typing import Callable, Dict, FrozenSet, Generator, Iterable, Tuple, Union

import dag_reducer
import gamla
import yaml
from computation_graph import run

_Object = str

_Relation = str

_Triplet = Tuple[str, str, str]


_subject_to_object: Callable[[FrozenSet[_Triplet]], Dict] = gamla.compose_left(
    gamla.groupby(gamla.head),
    gamla.valmap(gamla.compose_left(gamla.map(gamla.nth(2)), set)),
)


_infer_sink = gamla.compose_left(
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


def parse_yaml_file(file_name: str):
    with open(file_name) as f:
        config_dict = yaml.safe_load(f)
    return config_dict


def yaml_to_slot_bot(path: str):
    return gamla.compose_left(
        gamla.just(path),
        parse_yaml_file,
        yaml_dict_to_triplets,
        _build_cg,
        run.to_callable(handled_exceptions=frozenset()),
        gamla.after(gamla.to_awaitable),
    )


def _reducer(
    current: Tuple[str, Dict],
    children: Iterable[Tuple[_Relation, _Object, FrozenSet[_Triplet]]],
) -> Tuple[_Relation, _Object, FrozenSet[_Triplet]]:
    reduced_children = tuple(children)
    relation, d = current
    node_id = _find_name(d) or gamla.pipe(
        d, gamla.freeze_deep, gamla.compute_stable_json_hash
    )
    return (
        relation,
        node_id,
        gamla.pipe(
            [
                _make_triplets_from_literals(node_id, current),
                *map(
                    lambda child: gamla.pipe(
                        gamla.suffix((node_id, child[0], child[1]), child[2]), tuple
                    ),
                    reduced_children,
                ),
            ],
            gamla.concat,
            frozenset,
        ),
    )


def _make_triplets_from_literals(name: str, current: Tuple[str, Dict]):
    return gamla.pipe(
        current,
        gamla.second,
        dict.items,
        gamla.remove(
            gamla.anyjuxt(
                gamla.compose_left(gamla.head, gamla.equals("name")),
                gamla.compose_left(gamla.second, gamla.is_instance(list)),
            )
        ),
        gamla.map(lambda pair: (name, pair[0], pair[1])),
        frozenset,
    )


_find_name = gamla.ternary(
    gamla.is_instance(str), gamla.just(None), gamla.itemgetter_or_none("name")
)


def _children(node: Tuple[str, Union[Dict, str]]) -> Generator:
    relation, d = node
    yield from gamla.pipe(
        d, dict.items, gamla.filter(gamla.on_second(gamla.is_instance(dict))), tuple
    )

    yield from gamla.pipe(
        d,
        dict.items,
        gamla.filter(gamla.on_second(gamla.is_instance(list))),
        gamla.mapcat(gamla.explode(1)),
        gamla.filter(gamla.on_second(gamla.is_instance(dict))),
    )


def yaml_dict_to_triplets(yaml_dict: Dict) -> FrozenSet[_Triplet]:
    return gamla.last(gamla.tree_reduce(_children, _reducer, ("root", yaml_dict)))


def _build_cg(triplets: FrozenSet[_Triplet]):
    dependencies = _subject_to_object(triplets)
    return gamla.pipe(
        dag_reducer.reduce_graph(
            dependencies, _subject_to_relation_object_map(triplets), dag_reducer.reducer
        ),
        gamla.itemgetter(_infer_sink(dependencies)),
    )
