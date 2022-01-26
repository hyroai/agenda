from typing import Collection, Dict, Optional

import gamla
from computation_graph import base_types, composers
from computation_graph import graph
from computation_graph import graph as cg_graph
from computation_graph import run
from computation_graph.composers import logic, memory
from computation_graph.trace import graphviz

from agenda import missing_cg_utils, sentence


class Unknown:
    pass


# sources:


def forget():
    raise NotImplementedError


def participated():
    raise NotImplementedError


event = graph.make_source_with_name("event")

UNKNOWN = Unknown()


def utter(x) -> str:
    return sentence.sentence_to_str(x)


def state(x):
    return x


def consumes_external_event(x):
    return composers.compose_source(x, event, None)


mark_utter = missing_cg_utils.compose_curry(utter)
mark_state = missing_cg_utils.compose_curry(state)

utter_sink = missing_cg_utils.sink(utter)
state_sink = missing_cg_utils.sink(state)


def _combine_edges_to_disjunction(edges: Collection[base_types.ComputationEdge]):
    assert len(edges) > 1

    def any_node(*args):
        return any(args)

    return (
        graph.make_standard_edge(
            source=tuple(map(base_types.edge_source, edges)),
            key=None,
            destination=any_node,
        ),
        graph.make_standard_edge(
            source=any_node,
            key=base_types.edge_key(gamla.head(edges)),
            destination=base_types.edge_destination(gamla.head(edges)),
        ),
    )


def _resolve_ambiguity_using_logical_or(graph):
    groups = base_types.ambiguity_groups(graph)
    return base_types.merge_graphs(
        tuple(gamla.mapcat(_combine_edges_to_disjunction)(groups)),
        gamla.pipe(
            graph, gamla.remove(gamla.contains(frozenset(gamla.concat(groups))))
        ),
    )


def _utter_sink_or_empty_sentence(g: base_types.GraphType) -> base_types.CallableOrNode:
    try:
        return utter_sink(g)
    except AssertionError:
        return lambda: sentence.EMPTY_SENTENCE


def _replace_participated(replacement, graph):
    return gamla.pipe(
        graph,
        gamla.filter(missing_cg_utils.edge_source_equals(participated)),
        gamla.map(missing_cg_utils.replace_edge_source(replacement)),
        tuple,
    )


@gamla.curry
def _handle_participation(condition_fn, g):
    if not missing_cg_utils.has_source(participated)(g):
        return base_types.EMPTY_GRAPH
    indicator_graph = missing_cg_utils.conjunction(participated, condition_fn(g))
    return base_types.merge_graphs(
        _replace_participated(cg_graph.infer_graph_sink(indicator_graph), g),
        indicator_graph,
    )


@gamla.curry
def _composer(markers, f):
    def composer(*graphs):
        return base_types.merge_graphs(
            f(*graphs),
            _resolve_ambiguity_using_logical_or(
                base_types.merge_graphs(
                    *map(missing_cg_utils.remove_nodes(markers), graphs)
                )
            ),
        )

    return composer


@_composer([utter, participated])
def slot(asker_listener, acker):
    @composers.compose_left_dict(
        {
            "listener_state": state_sink(asker_listener),
            "listener_output_changed_to_known": missing_cg_utils.conjunction(
                memory.changed(state_sink(asker_listener)),
                logic.complement(
                    missing_cg_utils.equals_literal(state_sink(asker_listener), UNKNOWN)
                ),
            ),
        }
    )
    def who_should_speak(
        listener_state, listener_output_changed_to_known
    ) -> Optional[base_types.GraphType]:
        if listener_output_changed_to_known:
            return acker
        if listener_state is not UNKNOWN:
            return None
        return asker_listener

    @mark_utter
    @composers.compose_left_dict(
        {
            "who_should_speak": who_should_speak,
            "listener_utter": _utter_sink_or_empty_sentence(asker_listener),
            "acker_utter": utter_sink(acker),
        }
    )
    def final_utter(who_should_speak, listener_utter, acker_utter):
        if who_should_speak == asker_listener:
            return listener_utter
        if who_should_speak == acker:
            return acker_utter
        return sentence.EMPTY_SENTENCE

    return base_types.merge_graphs(
        *map(
            _handle_participation(missing_cg_utils.equals_literal(who_should_speak)),
            [asker_listener, acker],
        ),
        final_utter,
    )


@_composer([state])
def remember(graph):
    @mark_state
    @composers.compose_left_dict({"value": state_sink(graph), "should_forget": forget})
    @memory.with_state("memory", UNKNOWN)
    def remember_or_forget(value, memory, should_forget):
        if should_forget:
            return UNKNOWN
        if value is UNKNOWN:
            return memory
        return value

    return remember_or_forget


@_composer([state])
def complement(graph):
    @mark_state
    @missing_cg_utils.compose_left_curry(state_sink(graph))
    def complement(value):
        if value is UNKNOWN:
            return UNKNOWN
        return not value

    return complement


listener_with_memory = gamla.compose(remember, mark_state, consumes_external_event)


def if_participated(graph):
    def combined(value, is_participated_last_turn: bool):
        return value if is_participated_last_turn else UNKNOWN

    return base_types.merge_graphs(
        composers.make_compose_future(
            combined, participated, "is_participated_last_turn", False
        ),
        composers.compose_left(graph, combined, key="value"),
    )


def _make_gate(gate_logic, origin_graphs):
    return base_types.merge_graphs(
        mark_utter(composers.compose_unary(lambda x: x[1], gate_logic)),
        *map(
            _handle_participation(
                missing_cg_utils.in_literal(
                    composers.compose_unary(lambda x: x[0], gate_logic)
                )
            ),
            origin_graphs,
        ),
    )


def _combine_utterances_track_source(graphs, utterances):
    return gamla.pipe(
        utterances,
        sentence.combine,
        gamla.pair_with(
            gamla.compose(
                frozenset,
                gamla.map(gamla.compose(graphs.__getitem__, utterances.index)),
                sentence.constituents,
            )
        ),
    )


def _combine_utter_graphs(*utter_graphs: base_types.GraphType) -> base_types.GraphType:
    return _make_gate(
        missing_cg_utils.compose_left_many_to_one(
            map(_utter_sink_or_empty_sentence, utter_graphs),
            lambda args: _combine_utterances_track_source(utter_graphs, args),
        ),
        utter_graphs,
    )


combine_utterances = _composer([utter, participated])(_combine_utter_graphs)


@gamla.curry
def _dict_composer(markers, f):
    def composer(graph, d):
        return base_types.merge_graphs(
            f(graph, d),
            *map(missing_cg_utils.remove_nodes(markers), [graph, *d.values()]),
        )

    return composer


@_dict_composer([state, utter, participated])
def optionally_needs(
    recipient: base_types.GraphType, dependencies: Dict[str, base_types.GraphType]
):
    return base_types.merge_graphs(
        _combine_utter_graphs(recipient, *dependencies.values()),
        gamla.pipe(
            dependencies,
            gamla.valmap(state_sink),
            missing_cg_utils.package_into_dict,
            missing_cg_utils.compose_curry(missing_cg_utils.infer_source(recipient)),
            gamla.remove(gamla.contains(set(recipient))),
            tuple,
        ),
    )


@_composer([state, utter, participated])
def when(condition, do):
    return _make_gate(
        composers.compose_dict(
            lambda condition_state, condition_utter, do_utter: (
                frozenset([condition]),
                condition_utter,
            )
            if condition_state is UNKNOWN or not condition_state
            else _combine_utterances_track_source(
                [condition, do], [condition_utter, do_utter]
            ),
            {
                "condition_state": state_sink(condition),
                "condition_utter": _utter_sink_or_empty_sentence(condition),
                "do_utter": utter_sink(do),
            },
        ),
        [condition, do],
    )


def _final_replace(x, y):
    return missing_cg_utils.transform_edges(
        missing_cg_utils.edge_source_equals(x), missing_cg_utils.replace_edge_source(y)
    )


wrap_up = gamla.compose_left(
    gamla.assert_that_with_message(
        base_types.ambiguity_groups,
        gamla.compose(gamla.empty, base_types.ambiguity_groups),
    ),
    gamla.side_effect(graphviz.visualize_graph),
    _final_replace(participated, lambda: True),
    _final_replace(forget, lambda: False),
    lambda g: run.to_callable(g, frozenset()),
)
