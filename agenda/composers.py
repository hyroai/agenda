import operator
from typing import Callable, Collection, Dict, FrozenSet, Iterable

import gamla
from computation_graph import base_types, composers, graph, run
from computation_graph.composers import lift, logic, memory

from agenda import missing_cg_utils, sentence


class Unknown:
    pass


forget = graph.make_source_with_name("forget")
participated = graph.make_source_with_name("participated")
event = graph.make_source_with_name("event")
now = graph.make_source_with_name("now")

UNKNOWN = Unknown()


@graph.make_terminal("utter")
def utter(x) -> str:
    return x


@graph.make_terminal("state")
def state(state):
    return state


@gamla.curry
def consumes_external_event(at, x):
    return composers.compose_source(x, at, event)


@gamla.curry
def consumes_time(at, x):
    return composers.compose_source(x, at, now)


utter_sink = missing_cg_utils.sink(utter)
state_sink = missing_cg_utils.sink(state)
state_sink_or_none = gamla.excepts((AssertionError,), gamla.just(None), state_sink)


mark_utter = missing_cg_utils.compose_curry(utter)
mark_state = missing_cg_utils.compose_curry(state)


def _combine_edges_to_disjunction(edges: Collection[base_types.ComputationEdge]):
    assert len(edges) > 1

    def any_node(args):
        return any(args)

    return base_types.merge_graphs(
        missing_cg_utils.compose_left_many_to_one(
            tuple(map(base_types.edge_source, edges)), any_node
        ),
        composers.compose_left(
            any_node,
            base_types.edge_destination(gamla.head(edges)),
            key=base_types.edge_key(gamla.head(edges)),
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


def _replace_participated(replacement, graph_instance):
    return gamla.pipe(
        graph_instance,
        gamla.filter(graph.edge_source_equals(participated)),
        gamla.map(graph.replace_edge_source(replacement)),
        tuple,
    )


@gamla.curry
def _handle_participation(condition_fn, g):
    if not missing_cg_utils.has_source(participated)(g):
        return base_types.EMPTY_GRAPH
    indicator_graph = missing_cg_utils.conjunction(participated, condition_fn(g))
    return base_types.merge_graphs(
        _replace_participated(
            gamla.pipe(indicator_graph, graph.get_leaves, gamla.head), g
        ),
        indicator_graph,
    )


@gamla.curry
def _remove_sinks_and_sources_and_resolve_ambiguity(markers, f):
    def _remove_sinks_and_sources_and_resolve_ambiguity(*graphs):
        return base_types.merge_graphs(
            f(*graphs),
            _resolve_ambiguity_using_logical_or(
                base_types.merge_graphs(
                    *map(missing_cg_utils.remove_nodes(markers), graphs)
                )
            ),
        )

    return _remove_sinks_and_sources_and_resolve_ambiguity


def slot(listener, asker, acker, anti_acker):
    # If the listener has an utter sink then we need to combine it with asker. Otherwise, we just merge the graphs.
    try:
        utter_sink(listener)
        return _utter_unless_known_and_ack(
            combine_utter_sinks(listener, asker), acker, anti_acker
        )
    except AssertionError:
        return _utter_unless_known_and_ack(
            base_types.merge_graphs(listener, asker), acker, anti_acker
        )


def combine_slots(
    aggregator: Callable, acker, anti_acker, graphs: Iterable[base_types.GraphType]
):
    return _utter_unless_known_and_ack(
        aggregator(*graphs),
        acker,
        mark_utter(lift.any_to_graph(sentence.EMPTY_SENTENCE)),
    )


def combine_state(aggregator: Callable):
    @_remove_sinks_and_sources_and_resolve_ambiguity([state, utter, participated])
    def combine_state(*graphs):
        return base_types.merge_graphs(
            _combine_utter_graphs(*graphs),
            mark_state(
                composers.aggregation(
                    aggregator, gamla.pipe(graphs, gamla.map(state_sink), tuple)
                )
            ),
        )

    return combine_state


@_remove_sinks_and_sources_and_resolve_ambiguity([utter, participated])
def _utter_unless_known_and_ack(asker_listener, acker, anti_acker):
    def who_should_speak(
        listener_state,
        listener_output_changed_to_known,
        listener_participated_last_turn,
    ) -> FrozenSet[base_types.GraphType]:
        if listener_output_changed_to_known:
            return frozenset({acker})
        if listener_state is not UNKNOWN:
            return frozenset()
        if listener_participated_last_turn:
            return frozenset({anti_acker, asker_listener})
        return frozenset({asker_listener})

    is_participated_last_turn = missing_cg_utils.conjunction(
        participated, missing_cg_utils.in_literal(who_should_speak, asker_listener)
    )

    who_should_speak_with_participated = base_types.merge_graphs(
        composers.make_compose_future(
            who_should_speak,
            is_participated_last_turn,
            "listener_participated_last_turn",
            False,
        ),
        composers.compose_left_dict(
            {
                "listener_state": state_sink(asker_listener),
                "listener_output_changed_to_known": missing_cg_utils.conjunction(
                    memory.changed(state_sink(asker_listener)),
                    logic.complement(
                        missing_cg_utils.equals_literal(
                            state_sink(asker_listener), UNKNOWN
                        )
                    ),
                ),
            },
            who_should_speak,
        ),
    )

    @mark_utter
    @composers.compose_left_dict(
        {
            "who_should_speak": who_should_speak,
            "listener_utter": _utter_sink_or_empty_sentence(asker_listener),
            "acker_utter": utter_sink(acker),
            "anti_acker_utter": utter_sink(anti_acker),
        }
    )
    def final_utter(who_should_speak, listener_utter, acker_utter, anti_acker_utter):
        if anti_acker in who_should_speak:
            return sentence.combine([listener_utter, anti_acker_utter])
        if asker_listener in who_should_speak:
            return listener_utter
        if acker in who_should_speak:
            return acker_utter
        return sentence.EMPTY_SENTENCE

    return base_types.merge_graphs(
        *map(
            _handle_participation(missing_cg_utils.in_literal(who_should_speak)),
            [asker_listener, acker, anti_acker],
        ),
        who_should_speak_with_participated,
        final_utter,
    )


@_remove_sinks_and_sources_and_resolve_ambiguity([state])
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


@_remove_sinks_and_sources_and_resolve_ambiguity([state])
def ever(graph):
    @mark_state
    @composers.compose_left_dict({"value": state_sink(graph)})
    @memory.with_state("state", None)
    def ever_inner(state, value):
        return state or value

    return ever_inner


@_remove_sinks_and_sources_and_resolve_ambiguity([state])
def compose_on_state(stateful_graph, tranformer_graph):
    return gamla.pipe(
        tranformer_graph,
        missing_cg_utils.compose_left_curry(state_sink(stateful_graph)),
        mark_state,
    )


def _map_state(func):
    @_remove_sinks_and_sources_and_resolve_ambiguity([state])
    def map_state(graph):
        @mark_state
        @missing_cg_utils.compose_left_curry(state_sink(graph))
        def apply_func_unless_unknown(value):
            if UNKNOWN is value:
                return UNKNOWN
            return func(value)

        return apply_func_unless_unknown

    return map_state


complement = _map_state(operator.not_)
equals = gamla.compose(_map_state, gamla.equals)
less_than = gamla.compose(_map_state, gamla.less_than)
less_equals = gamla.compose(_map_state, gamla.less_equals)
greater_equals = gamla.compose(_map_state, gamla.greater_equals)
not_equals = gamla.compose(_map_state, gamla.not_equals)
inside = gamla.compose(_map_state, gamla.inside)
contains = gamla.compose(_map_state, gamla.contains)

listener_with_memory = gamla.compose(
    remember, mark_state, consumes_external_event(None)
)


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


combine_utter_sinks = _remove_sinks_and_sources_and_resolve_ambiguity(
    [utter, participated]
)(_combine_utter_graphs)


@gamla.curry
def _dict_composer(markers, f):
    def _remove_sinks_and_sources_and_resolve_ambiguity(graph, d):
        return base_types.merge_graphs(
            f(graph, d),
            *map(missing_cg_utils.remove_nodes(markers), [graph, *d.values()]),
        )

    return _remove_sinks_and_sources_and_resolve_ambiguity


@_dict_composer([state, utter, participated])
def state_optionally_needs(
    recipient: base_types.GraphType, dependencies: Dict[str, base_types.GraphType]
):
    return base_types.merge_graphs(
        _combine_utter_graphs(recipient, *dependencies.values()),
        mark_state(state_sink(recipient)),
        _compose_state_dict(dependencies, recipient),
    )


@_dict_composer([state, utter, participated])
def utter_optionally_needs(
    recipient: base_types.GraphType, dependencies: Dict[str, base_types.GraphType]
):
    return base_types.merge_graphs(
        _combine_utter_graphs(recipient, *dependencies.values()),
        _compose_state_dict(dependencies, recipient),
    )


def _compose_state_dict(
    dependencies: Dict[str, base_types.GraphType], recipient: base_types.GraphOrCallable
):
    return gamla.pipe(
        dependencies,
        gamla.valmap(state_sink),
        missing_cg_utils.package_into_dict,
        missing_cg_utils.compose_curry(missing_cg_utils.infer_source(recipient)),
        gamla.remove(gamla.contains(set(recipient))),
        tuple,
    )


@_remove_sinks_and_sources_and_resolve_ambiguity([state, utter, participated])
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


def _replace_destination(x, y):
    return graph.transform_edges(
        missing_cg_utils.edge_destination_equals(x),
        missing_cg_utils.replace_edge_destination(y),
    )


def _interject(old, new):
    return gamla.compose_left(
        _replace_destination(old, new),
        lambda g: base_types.merge_graphs(g, composers.compose_unary(old, new)),
    )


def wrap_up(sentence_renderer: Callable[[sentence.SentenceOrPart], str]):
    return gamla.compose_left(
        gamla.assert_that_with_message(
            base_types.ambiguity_groups,
            gamla.compose(gamla.empty, base_types.ambiguity_groups),
        ),
        graph.replace_source(participated, lambda: True),
        graph.replace_source(forget, lambda: False),
        _interject(utter, sentence_renderer),
        lambda g: run.to_callable(g, frozenset()),
    )
