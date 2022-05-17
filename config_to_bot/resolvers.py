import datetime
import inspect
import keyword
import string
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, Set, Tuple, Union

import gamla
import httpx
import knowledge_graph
from computation_graph import base_types, composers, graph
from computation_graph.composers import lift

import agenda
from agenda import events, missing_cg_utils
from config_to_bot import extract
from config_to_bot.jina_faq import jina_faq

_TYPE_TO_LISTENER = gamla.valmap(agenda.consumes_user_utterance(None))(
    {
        "email": extract.email,
        "phone": extract.phone,
        "amount": extract.amount,
        "boolean": extract.yes_no,
        "intent": extract.intent,
        "name": extract.person_name,
        "address": extract.address,
        "multiple-choice": extract.multiple_choices,
        "single-choice": extract.single_choice,
        "date": agenda.consumes_time("relative_to", extract.future_date),
        "time": agenda.consumes_time("relative_to", extract.time),
    }
)
_TYPES_TO_LISTEN_AFTER_ASKING = frozenset({"amount", "boolean", "date", "time"})
is_supported_type = gamla.contains(_TYPE_TO_LISTENER)

_mark_as_state_and_remember = gamla.compose_left(agenda.mark_state, agenda.remember)


def parse_type(type: str) -> Callable:
    return _TYPE_TO_LISTENER.get(type)


def _complement(not_: base_types.GraphType) -> base_types.GraphType:
    return agenda.complement(not_)


def _equals(is_: base_types.GraphType, equals: Union[str, int]):
    return agenda.equals(equals)(is_)


def _greater_equals(is_: base_types.GraphType, greater_equals: int):
    return agenda.greater_equals(greater_equals)(is_)


def _all(all: Iterable[base_types.GraphType]) -> base_types.GraphType:
    return agenda.combine_slots(
        agenda.all,
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        all,
    )


def _any(any: Iterable[base_types.GraphType]) -> base_types.GraphType:
    return agenda.combine_slots(
        agenda.any,
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        any,
    )


def _kv(
    key: str, value: Union[str, base_types.GraphType]
) -> Tuple[str, Union[str, base_types.GraphType]]:
    if value == "incoming_utterance":
        return (
            key,
            agenda.mark_state(agenda.consumes_user_utterance("x", lambda x: x)),
        )
    return (key, value)


async def post_request_with_url_and_params(url, params):
    return gamla.pipe(
        await gamla.post_json_with_extra_headers_and_params_async(
            {}, {"Content-Type": "application/json"}, 30, url, params
        ),
        httpx.Response.json,
    )


def _remote_utter(request):
    url_to_func = _build_remote_resolver(request)

    def remote_utter(say_remote, needs):
        return agenda.utter_optionally_needs(
            agenda.say(
                gamla.compose_left(
                    url_to_func(say_remote),
                    gamla.when(gamla.equals(None), gamla.just("")),
                )
            ),
            dict(needs),
        )

    return remote_utter


def _remote_state(request):
    url_to_func = _build_remote_resolver(request)

    def remote_state(state_remote, needs):
        return agenda.composers.state_optionally_needs(
            agenda.mark_state(
                gamla.compose_left(
                    url_to_func(state_remote),
                    gamla.when(gamla.equals(None), gamla.just(agenda.UNKNOWN)),
                )
            ),
            dict(needs),
        )

    return remote_state


_to_json_serializable = gamla.map_dict(
    gamla.identity,
    gamla.case_dict(
        {
            gamla.equals(agenda.UNKNOWN): gamla.just(None),
            gamla.is_instance(datetime.date): gamla.apply_method("isoformat"),
            gamla.is_instance(datetime.time): gamla.apply_method("isoformat"),
            gamla.just(True): gamla.identity,
        }
    ),
)


def _build_remote_resolver(request: Callable):
    def remote(url: str):
        async def post_request(params: Dict[str, Any]):
            return gamla.pipe(
                await gamla.to_awaitable(request(url, _to_json_serializable(params))),
                gamla.freeze_deep,
            )

        return post_request

    return remote


def _event_is(event_is: str):
    return agenda.mark_state(
        agenda.consumes_external_event(
            None,
            gamla.alljuxt(
                gamla.is_instance(events.ConversationEvent),
                gamla.attr_equals("type", event_is.replace(" ", "_").upper()),
            ),
        )
    )


def _say(say: str):
    return agenda.say(say)


def _say_with_needs(
    say: str, needs: Iterable[Tuple[str, base_types.GraphType]]
) -> base_types.GraphType:
    return agenda.utter_optionally_needs(
        agenda.say(_render_template(say) if _is_format_string(say) else say),
        dict(needs),
    )


def _when(say: Union[str, base_types.GraphOrCallable], when: base_types.GraphType):
    return agenda.when(when, agenda.say(say) if isinstance(say, str) else say)


def _say_needs_when(
    say: str,
    needs: Iterable[Tuple[str, base_types.GraphType]],
    when: base_types.GraphType,
):
    return _when(_say_with_needs(say, needs), when)


def _is_format_string(say):
    if not isinstance(say, str):
        return False
    parsed_format = tuple(string.Formatter().parse(say))
    return (
        len(parsed_format) > 1
        or len(parsed_format) == 1
        and parsed_format[0][1] is not None
    )


def _render_template(template):
    assert _is_format_string(template), "template must be a valid python string format."
    return gamla.ternary(
        gamla.compose_left(dict.values, gamla.inside(agenda.UNKNOWN)),
        gamla.just(""),
        lambda kw: template.format(*kw.values(), **kw),
    )


def _listen_to_intent(intent: Tuple[str, ...]):
    return gamla.pipe(extract.intent(intent), agenda.listener_with_memory, agenda.ever)


def _question_and_answer_dict(question: str, answer: str) -> Tuple[str, str]:
    return (question, answer)


async def _faq_intent(faq: Tuple[Tuple[str, str], ...]) -> base_types.GraphType:
    await jina_faq.index(faq)

    async def highest_ranked_faq_with_score(user_utterance: str):
        return gamla.pipe(
            await jina_faq.query(user_utterance),
            gamla.ternary(
                gamla.compose_left(gamla.second, gamla.less_than(0.6)),
                gamla.head,
                gamla.just(""),
            ),
        )

    return agenda.say(
        agenda.consumes_user_utterance("user_utterance", highest_ranked_faq_with_score)
    )


_lift_any_to_state_graph = gamla.compose_left(
    lift.any_to_graph, gamla.unless(agenda.state_sink_or_none, agenda.mark_state)
)

_parse_isodatetime_or_none = gamla.excepts(
    ValueError, gamla.just(None), datetime.datetime.fromisoformat
)


def _option_has_more_than_a_single_type(kg) -> Callable[[Tuple[str, ...]], bool]:
    return gamla.anymap(
        gamla.compose_left(
            lambda option: knowledge_graph.find_exactly_bare(option, kg),
            knowledge_graph.get_node_types,
            gamla.len_greater(1),
        )
    )


def _get_options_from_string(
    type_string: str, kg: knowledge_graph.KnowledgeGraph
) -> Tuple[str, ...]:
    return gamla.pipe(
        knowledge_graph.find_exactly_bare(type_string, kg),
        knowledge_graph.get_node_instances,
        gamla.map(knowledge_graph.get_node_title),
        tuple,
    )


@gamla.curry
def _ask_about_choice(
    kg: knowledge_graph.KnowledgeGraph,
    choice: Union[str, base_types.CallableOrNodeOrGraph],
    ask: str,
):
    if isinstance(choice, str):
        options_for_single_choice = _get_options_from_string(choice, kg)
        should_asker_participate = gamla.pipe(
            options_for_single_choice, _option_has_more_than_a_single_type(kg)
        )
    else:
        should_asker_participate = False
    options = _lift_any_to_state_graph(choice)

    @agenda.consumes_user_utterance("user_utterance")
    @agenda.consumes_time("now")
    @composers.compose_left_dict({"options": agenda.state_sink(options)})
    def _parse_dynamic_choice(user_utterance, now, did_participate, options):
        if options is agenda.UNKNOWN:
            return agenda.UNKNOWN
        date_options = gamla.pipe(options, gamla.map(_parse_isodatetime_or_none), tuple)
        if all(date_options):
            if not did_participate:
                return agenda.UNKNOWN
            return extract.datetime_choice(date_options, now)(user_utterance)
        return extract.single_choice(options_for_single_choice)(user_utterance)

    return agenda.combine_utter_sinks(
        missing_cg_utils.remove_nodes([agenda.composers.state])(options),
        agenda.slot(
            agenda.remember(
                agenda.mark_state(
                    composers.compose_left_future(
                        agenda.participated,
                        gamla.pipe(
                            _parse_dynamic_choice,
                            agenda.if_participated
                            if should_asker_participate
                            else gamla.identity,
                        ),
                        "did_participate",
                        False,
                    )
                )
            ),
            agenda.ask(_compose_template(ask, options)),
            agenda.ack(agenda.GENERIC_ACK),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        ),
    )


@gamla.curry
def _ask_about_multiple_choice(kg, multiple_choice: str, ask: base_types.GraphType):
    options = _get_options_from_string(multiple_choice, kg)
    return agenda.slot(
        gamla.pipe(
            extract.multiple_choices(options),
            agenda.if_participated
            if _option_has_more_than_a_single_type(kg)(options)
            else gamla.identity,
            agenda.listener_with_memory,
        ),
        agenda.ask(ask),
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _slot_with_remote_and_ack(remote: base_types.GraphType, ask: str, ack: str):
    state = agenda.remember(remote)
    return agenda.slot(
        state,
        agenda.ask(ask),
        agenda.ack(_compose_template(ack, state)),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _slot_with_remote(remote: base_types.GraphType, ask: str):
    return agenda.slot(
        agenda.remember(remote),
        agenda.ask(ask),
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _ask_about_name(ack, ask: str):
    name_listener = gamla.pipe(
        extract.person_name_less_strict,
        agenda.if_participated,
        agenda.listener_with_memory,
    )
    # TODO(Yoni): Currently combine states only work on slot + state, but we want it to work on 2 states. It doesn't because the utter sink of a state is an empty sentece which confuses the participation.
    name_slot = agenda.first_known(
        _typed_state("name"),
        agenda.slot(
            name_listener,
            agenda.ask(ask),
            agenda.ack(_compose_template(ack, name_listener)),
            agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        ),
    )
    return agenda.utter_unless_known_and_ack(
        name_slot,
        agenda.ack(_compose_template(ack, name_slot)),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _ask_about(type: str, ask: str) -> base_types.GraphType:
    if type == "name":
        return _ask_about_name(agenda.GENERIC_ACK, ask)
    return agenda.slot(
        _typed_state(type),
        agenda.ask(ask),
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _ask_about_and_ack(ack: str, type: str, ask: str) -> base_types.GraphType:
    if type == "name":
        return _ask_about_name(ack, ask)
    typed_state = _typed_state(type)
    return agenda.slot(
        typed_state,
        agenda.ask(ask),
        agenda.ack(_compose_template(ack, typed_state)),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
    )


def _compose_template(template: str, stateful_graph: base_types.GraphType):
    return (
        composers.compose_left_unary(
            missing_cg_utils.package_into_dict(
                {"value": agenda.state_sink(stateful_graph)}
            ),
            _render_template(template),
        )
        if _is_format_string(template)
        else template
    )


def _typed_state(type):
    assert is_supported_type(type), f"We currently do not support {type} type"

    return gamla.pipe(
        parse_type(type),
        agenda.if_participated
        if type in _TYPES_TO_LISTEN_AFTER_ASKING
        else gamla.identity,
        _mark_as_state_and_remember,
    )


def _slots(slots: Tuple[base_types.GraphType, ...]):
    return agenda.combine_utter_sinks(*slots)


def _actions(actions: Tuple[base_types.GraphType, ...]):
    return agenda.combine_utter_sinks(*actions)


def _knowledge(knowledge: Tuple[base_types.GraphType, ...]):
    return agenda.combine_utter_sinks(*knowledge)


def _actions_with_slots(
    slots: Tuple[base_types.GraphType, ...], actions: Tuple[base_types.GraphType, ...]
) -> base_types.GraphType:
    del slots
    return agenda.combine_utter_sinks(*actions)


def _actions_with_knowledge(
    actions: Tuple[base_types.GraphType, ...],
    knowledge: Tuple[base_types.GraphType, ...],
):
    return agenda.combine_utter_sinks(*actions, *knowledge)


def _slots_with_knowledge(
    slots: Tuple[base_types.GraphType, ...], knowledge: Tuple[base_types.GraphType, ...]
):
    return agenda.combine_utter_sinks(*slots, *knowledge)


def _actions_with_slots_and_knowledge(
    slots: Tuple[base_types.GraphType, ...],
    actions: Tuple[base_types.GraphType, ...],
    knowledge: Tuple[base_types.GraphType, ...],
) -> base_types.GraphType:
    del slots
    return agenda.combine_utter_sinks(*actions, *knowledge)


@graph.make_terminal("debug_states")
def debug_states(args):
    return gamla.pipe(args, _to_json_serializable, gamla.freeze_deep)


_debug_dict = gamla.apply_spec(
    {
        "state": agenda.state_sink,
        "utter": gamla.excepts(
            AssertionError, gamla.just(lambda: ""), agenda.utter_sink
        ),
        "participated": gamla.excepts(
            StopIteration,
            gamla.just(lambda: None),
            gamla.compose_left(
                gamla.filter(graph.edge_source_equals(agenda.participated)),
                gamla.map(base_types.edge_destination),
                gamla.head,
            ),
        ),
    }
)


def _actions_with_slots_and_debug(
    actions: Tuple[base_types.GraphType, ...],
    slots: Tuple[base_types.GraphType, ...],
    debug: Union[
        Tuple[Tuple[str, base_types.GraphType], ...], Tuple[base_types.GraphType, ...]
    ],
) -> base_types.GraphType:
    del slots
    return base_types.merge_graphs(
        agenda.combine_utter_sinks(*actions),
        composers.compose_unary(
            debug_states,
            gamla.pipe(
                debug,
                dict,
                gamla.valmap(
                    gamla.compose_left(_debug_dict, missing_cg_utils.package_into_dict)
                ),
                missing_cg_utils.package_into_dict,
            ),
        )
        if isinstance(gamla.head(debug), tuple)
        else composers.compose_many_to_one(
            debug_states, gamla.pipe(debug, gamla.map(_debug_dict), tuple)
        ),
    )


def _actions_with_slots_and_debug_and_knowledge(
    actions: Tuple[base_types.GraphType, ...],
    slots: Tuple[base_types.GraphType, ...],
    knowledge: Tuple[base_types.GraphType, ...],
    debug: Union[
        Tuple[Tuple[str, base_types.GraphType], ...], Tuple[base_types.GraphType, ...]
    ],
) -> base_types.GraphType:
    del slots
    return base_types.merge_graphs(
        agenda.combine_utter_sinks(*actions, *knowledge),
        composers.compose_unary(
            debug_states,
            gamla.pipe(
                debug,
                dict,
                gamla.valmap(
                    gamla.compose_left(_debug_dict, missing_cg_utils.package_into_dict)
                ),
                missing_cg_utils.package_into_dict,
            ),
        )
        if isinstance(gamla.head(debug), tuple)
        else composers.compose_many_to_one(
            debug_states, gamla.pipe(debug, gamla.map(_debug_dict), tuple)
        ),
    )


def _first_known(first_known: Tuple):
    return agenda.first_known(*first_known)


def _amount_of(amount_of: str, ask: str):
    return agenda.combine_slots(
        agenda.first_known,
        agenda.ack(agenda.GENERIC_ACK),
        agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
        (
            agenda.listener_with_memory(extract.amount_of(amount_of)),
            agenda.slot(
                _typed_state("amount"),
                agenda.ask(ask),
                agenda.ack(agenda.GENERIC_ACK),
                agenda.anti_ack(agenda.GENERIC_ANTI_ACK),
            ),
        ),
    )


def _concept_and_instances(concept: str, instances: Iterable[str]):
    return ()


def _composers_for_dag_reducer(
    remote_function: Callable, kg: knowledge_graph.KnowledgeGraph
) -> Set[Callable]:
    return {
        _amount_of,
        _first_known,
        _complement,
        _all,
        _any,
        _kv,
        _build_remote_resolver(remote_function),
        _listen_to_intent,
        _ask_about_choice(kg),
        _ask_about_multiple_choice(kg),
        _say,
        _say_with_needs,
        _say_needs_when,
        _event_is,
        _when,
        _remote_state(remote_function),
        _remote_utter(remote_function),
        _ask_about,
        _ask_about_and_ack,
        _actions_with_slots,
        _slots_with_knowledge,
        _actions_with_knowledge,
        _actions_with_slots_and_knowledge,
        _actions_with_slots_and_debug,
        _actions_with_slots_and_debug_and_knowledge,
        _equals,
        _greater_equals,
        _question_and_answer_dict,
        _faq_intent,
        _slot_with_remote_and_ack,
        _slot_with_remote,
        _slots,
        _render_template,
        _actions,
        _knowledge,
        _concept_and_instances,
    }


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


build_cg = gamla.compose(_functions_to_case_dict, _composers_for_dag_reducer)
