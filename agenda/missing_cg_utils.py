import dataclasses
from typing import Callable, Dict

import gamla
from computation_graph import base_types, composers, graph


def compose_curry(x):
    def compose_with(y):
        return composers.compose_unary(x, y)

    return compose_with


def compose_left_curry(x):
    def compose_left_with(y):
        return composers.compose_left_unary(x, y)

    return compose_left_with


def edge_destination_equals(x):
    if not isinstance(x, base_types.ComputationNode):
        x = graph.make_computation_node(x)
    return lambda edge: edge.destination == x


edge_source = gamla.attrgetter("source")


@gamla.curry
def equals_literal(graph, literal):
    return composers.compose_unary(lambda x: x == literal, graph)


@gamla.curry
def in_literal(graph, literal):
    return composers.compose_unary(lambda x: literal in x, graph)


def replace_edge_destination(replacement):
    if not isinstance(replacement, base_types.ComputationNode):
        replacement = graph.make_computation_node(replacement)

    def replace_edge_destination(edge):
        return dataclasses.replace(edge, destination=replacement)

    return replace_edge_destination


def remove_nodes(nodes):
    return gamla.compose_left(
        *map(
            lambda x: gamla.remove(
                gamla.anyjuxt(graph.edge_source_equals(x), edge_destination_equals(x))
            ),
            nodes,
        ),
        tuple,
    )


def sink(x: base_types.CallableOrNode):
    return gamla.compose(
        edge_source,
        gamla.assert_that(gamla.not_equals(None)),
        gamla.find(edge_destination_equals(x)),
    )


def conjunction(x, y):
    @composers.compose_left_dict({"x": x, "y": y})
    def conjunction(x, y):
        return x and y

    return conjunction


@gamla.curry
def compose_left_many_to_one(graphs, aggregation):
    return composers.compose_many_to_one(aggregation, graphs)


package_into_dict: Callable[
    [Dict[str, base_types.CallableOrNodeOrGraph]], base_types.GraphType
] = gamla.compose_left(
    dict.items,
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
)


_cg_to_source = gamla.compose_left(
    gamla.bifurcate(
        gamla.mapcat(
            gamla.compose_left(
                gamla.ternary(
                    base_types.edge_source,
                    gamla.compose_left(base_types.edge_source, gamla.wrap_tuple),
                    base_types.edge_args,
                )
            )
        ),
        gamla.map(base_types.edge_destination),
    ),
    gamla.map(set),
    gamla.star(set.difference),
    gamla.assert_that(gamla.len_equals(1)),
    gamla.head,
)

infer_source = gamla.when(base_types.is_computation_graph, _cg_to_source)


def has_source(node):
    if not isinstance(node, base_types.ComputationNode):
        node = graph.make_computation_node(node)
    return gamla.anymap(gamla.compose(gamla.equals(node), edge_source))
