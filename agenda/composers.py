from typing import Optional

import gamla
from computation_graph import base_types, composers
from computation_graph import graph as cg_graph
from computation_graph import run
from computation_graph.composers import logic, memory

from agenda import missing_cg_utils, sentence


class Unknown:
    pass


# initials:


def forget():
    raise NotImplementedError


def participated():
    raise NotImplementedError


def event():
    raise NotImplementedError


# terminals:


@cg_graph.make_terminal("utter")
def utter(x) -> str:
    return sentence.sentence_to_str(x)


@cg_graph.make_terminal("state")
def state(x):
    return x


mark_event = missing_cg_utils.compose_left_curry(event)
mark_utter = missing_cg_utils.compose_curry(utter)
mark_state = missing_cg_utils.compose_curry(state)

utter_sink = missing_cg_utils.sink(utter)
state_sink = missing_cg_utils.sink(state)


def utter_sink_or_empty_sentence(g):
    return utter_sink(g) or (lambda: sentence.EMPTY_SENTENCE)


UNKNOWN = Unknown()


def _replace_participated(replacement, graph):
    return gamla.pipe(
        graph,
        gamla.filter(missing_cg_utils.edge_source_equals(participated)),
        # TODO(uri): need to resolve ambiguity, if we created more than one sources for destination here
        gamla.map(missing_cg_utils.replace_edge_source(replacement)),
        tuple,
    )


@gamla.curry
def _handle_participation(condition_fn, g):
    indicator_graph = missing_cg_utils.conjunction(participated, condition_fn(g))
    return base_types.merge_graphs(
        _replace_participated(cg_graph.infer_graph_sink(indicator_graph), g),
        indicator_graph,
    )


@gamla.curry
def _composer(markers, f):
    def composer(*graphs):
        return base_types.merge_graphs(
            f(*graphs), *map(missing_cg_utils.remove_nodes(markers), graphs)
        )

    return composer


@_composer([utter, participated])
def slot(listener, asker, acker):
    @composers.compose_left_dict(
        {
            "listener_state": state_sink(listener),
            "listener_utter": utter_sink_or_empty_sentence(listener),
            "listener_output_changed_to_known": missing_cg_utils.conjunction(
                memory.changed(state_sink(listener)),
                logic.complement(
                    missing_cg_utils.equals_literal(state_sink(listener), UNKNOWN)
                ),
            ),
        }
    )
    def who_should_speak(
        listener_state, listener_utter, listener_output_changed_to_known
    ) -> Optional[base_types.GraphType]:
        if listener_output_changed_to_known:
            return acker
        if listener_state is not UNKNOWN:
            return None
        if listener_utter is not sentence.EMPTY_SENTENCE:
            return listener
        return asker

    @mark_utter
    @composers.compose_left_dict(
        {
            "who_should_speak": who_should_speak,
            "listener_utter": utter_sink_or_empty_sentence(listener),
            "asker_utter": utter_sink(asker),
            "acker_utter": utter_sink(acker),
        }
    )
    def final_utter(who_should_speak, listener_utter, asker_utter, acker_utter):
        if who_should_speak == listener:
            return listener_utter
        if who_should_speak == asker:
            return asker_utter
        if who_should_speak == acker:
            return acker_utter
        return sentence.EMPTY_SENTENCE

    return base_types.merge_graphs(
        *map(
            _handle_participation(missing_cg_utils.equals_literal(who_should_speak)),
            [listener, asker, acker],
        ),
        final_utter,
    )


@_composer([state])
def remember(graph):
    @mark_state
    @composers.compose_left_dict({"value": state_sink(graph), "should_forget": forget})
    @memory.with_state("memory")
    def remember_or_forget(value, memory, should_forget):
        if should_forget:
            return UNKNOWN
        if value is UNKNOWN:
            return memory or UNKNOWN
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


function_to_listener_with_memory = gamla.compose(remember, mark_state, mark_event)


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
    combined_utter = sentence.combine(utterances)
    return (
        gamla.compose(
            frozenset,
            gamla.map(gamla.compose(graphs.__getitem__, utterances.index)),
            sentence.constituents,
        )(combined_utter),
        combined_utter,
    )


def _combine_utter_graphs(*utter_graphs):
    return _make_gate(
        missing_cg_utils.compose_left_many_to_one(
            map(utter_sink_or_empty_sentence, utter_graphs),
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
def optionally_needs(recipient, dependencies):
    return base_types.merge_graphs(
        _combine_utter_graphs(recipient, *dependencies.values()),
        gamla.pipe(
            dependencies,
            gamla.valmap(state_sink),
            composers.compose_dict(recipient),
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
                "condition_utter": utter_sink_or_empty_sentence(condition),
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
    _final_replace(participated, lambda: True),
    _final_replace(forget, lambda: False),
    _final_replace(event, lambda event: event),
    lambda g: run.to_callable(g, frozenset()),
)
