import gamla
from computation_graph import base_types, composers, graph
import dataclasses


def compose_curry(x):
    def compose_with(y):
        return composers.compose_unary(x, y)

    return compose_with


def compose_left_curry(x):
    def compose_left_with(y):
        return composers.compose_left_unary(x, y)

    return compose_left_with


def _split_by_condition(condition):
    return gamla.compose_left(
        gamla.bifurcate(gamla.filter(condition), gamla.remove(condition)),
        gamla.map(tuple),
        tuple,
    )


def _operate_on_subgraph(selector, transformation):
    return gamla.compose(
        gamla.star(
            lambda match, rest: base_types.merge_graphs(rest, transformation(match))
        ),
        selector,
    )


def edge_destination_equals(x):
    if not isinstance(x, base_types.ComputationNode):
        x = graph.make_computation_node(x)
    return lambda edge: edge.destination == x


edge_source = gamla.attrgetter("source")


def edge_source_equals(x):
    if not isinstance(x, base_types.ComputationNode):
        x = graph.make_computation_node(x)
    return lambda edge: edge.source == x


def transform_edges(query, edge_mapper):
    return _operate_on_subgraph(
        _split_by_condition(query), gamla.compose(tuple, gamla.map(edge_mapper))
    )


@gamla.curry
def equals_literal(graph, literal):
    return composers.compose_unary(lambda x: x == literal, graph)


@gamla.curry
def in_literal(graph, literal):
    return composers.compose_unary(lambda x: literal in x, graph)


def replace_edge_source(replacement):
    if not isinstance(replacement, base_types.ComputationNode):
        replacement = graph.make_computation_node(replacement)

    def replace_edge_source(edge):
        return dataclasses.replace(edge, source=replacement)

    return replace_edge_source


def remove_nodes(nodes):
    return gamla.compose_left(
        *map(
            lambda x: gamla.remove(
                gamla.anyjuxt(edge_source_equals(x), edge_destination_equals(x))
            ),
            nodes,
        )
    )


def sink(x):
    return gamla.compose(
        gamla.unless(gamla.equals(None), edge_source),
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
