from typing import Any, Callable, Dict, FrozenSet, Iterable, Tuple, Union

import gamla
import httpx
from computation_graph import base_types, composers, graph
from computation_graph.composers import duplication, lift

import agenda
from agenda import missing_cg_utils
from config_to_bot import extract

_TYPE_TO_LISTENER = {
    "email": extract.email,
    "phone": extract.phone,
    "amount": extract.amount,
    "boolean": extract.yes_no,
    "intent": extract.intent,
    "name": extract.person_name,
    "address": extract.address,
    "multiple-choice": extract.multiple_choices,
    "single-choice": extract.single_choice,
}
_TYPES_TO_LISTEN_AFTER_ASKING = frozenset({"amount", "boolean"})
is_supported_type = gamla.contains(_TYPE_TO_LISTENER)


def parse_type(type: str) -> Callable:
    def parse_type(user_utterance: str):
        return _TYPE_TO_LISTENER.get(type)(user_utterance)  # type: ignore

    return parse_type


def _complement(not_: base_types.GraphType) -> base_types.GraphType:
    return agenda.complement(not_)


def _equals(is_: base_types.GraphType, equals: int):
    return agenda.equals(equals)(is_)


def _greater_equals(is_: base_types.GraphType, greater_equals: int):
    return agenda.greater_equals(greater_equals)(is_)


def _all(all: Iterable[base_types.GraphType]) -> base_types.GraphType:
    return agenda.combine_slots(agenda.all, agenda.ack(agenda.GENERIC_ACK), all)


def _any(any: Iterable[base_types.GraphType]) -> base_types.GraphType:
    return agenda.combine_slots(agenda.any, agenda.ack(agenda.GENERIC_ACK), any)


def _kv(
    key: str, value: Union[str, base_types.GraphType]
) -> Tuple[str, Union[str, base_types.GraphType]]:
    if value == "incoming_utterance":
        return (key, agenda.consumes_external_event(lambda x: x))
    return (key, value)


async def post_request_with_url_and_params(url, params):
    return gamla.pipe(
        await gamla.post_json_with_extra_headers_and_params_async(
            {}, {"Content-Type": "application/json"}, 30, url, params
        ),
        httpx.Response.json,
    )


def _build_remote_resolver(request: Callable):
    def remote(url: str):
        async def post_request(params: Dict[str, Any]):
            return gamla.pipe(
                await request(
                    url,
                    gamla.pipe(
                        params,
                        gamla.valmap(
                            gamla.when(gamla.equals(agenda.UNKNOWN), gamla.just(None))
                        ),
                    ),
                ),
                gamla.freeze_deep,
                gamla.when(gamla.equals(None), gamla.just("")),
            )

        return post_request

    return remote


def _say_with_needs(
    say, needs: Iterable[Tuple[str, base_types.GraphType]]
) -> base_types.GraphType:
    return agenda.optionally_needs(agenda.say(say), dict(needs))


def _when(say: Union[str, Callable], when: base_types.GraphType):
    return agenda.when(when, agenda.say(say))


def _when_with_needs(
    say: Union[str, Callable],
    needs: Iterable[Tuple[str, base_types.GraphType]],
    when: base_types.GraphType,
) -> base_types.GraphType:
    return agenda.when(when, agenda.optionally_needs(agenda.say(say), dict(needs)))


def _remote_with_needs(needs: Iterable[Tuple[str, base_types.GraphType]], url: str):
    async def remote_function(params: Dict[str, Any]):
        return gamla.pipe(
            await gamla.post_json_with_extra_headers_and_params_async(
                {}, {"Content-Type": "application/json"}, 30, url, params
            ),
            httpx.Response.json,
            gamla.when(gamla.equals(None), gamla.just(agenda.UNKNOWN)),
        )

    return agenda.optionally_needs(
        lift.function_to_graph(remote_function),
        gamla.pipe(dict(needs), gamla.valmap(agenda.mark_state)),
    )


def _listen_to_intent(intent: Tuple[str, ...]):
    return gamla.pipe(
        parse_type("intent")(intent),
        agenda.listener_with_memory,
        agenda.ever,
        duplication.duplicate_graph,
    )


def _question_and_answer_dict(question: str, answer: str) -> Tuple[str, str]:
    return (question, answer)


def _faq_intent(faq: Tuple[Tuple[str, str], ...]):
    def highest_ranked_faq_with_score(user_utterance: str):
        return gamla.pipe(
            faq,
            gamla.map(
                gamla.pair_right(
                    gamla.compose_left(
                        gamla.head,
                        lambda question: extract.faq_score(question, user_utterance),
                    )
                )
            ),
            tuple,
            gamla.sort_by(gamla.nth(2)),
            gamla.last,
            gamla.packstack(gamla.identity, gamla.identity, lambda score: score >= 0.9),
        )

    return agenda.when(
        agenda.consumes_external_event(
            gamla.compose_left(highest_ranked_faq_with_score, gamla.nth(2))
        ),
        agenda.say(
            agenda.consumes_external_event(
                gamla.compose_left(highest_ranked_faq_with_score, gamla.second)
            )
        ),
    )


def _ask_about_choice(choice: Tuple[str, ...], ask: base_types.GraphType):
    return agenda.slot(
        gamla.pipe(
            parse_type("single-choice")(choice),
            agenda.listener_with_memory,
            duplication.duplicate_graph,
        ),
        agenda.ask(ask),
        agenda.ack(agenda.GENERIC_ACK),
    )


def _ask_about_multiple_choice(
    multiple_choice: Tuple[str, ...], ask: base_types.GraphType
):
    return agenda.slot(
        gamla.pipe(
            parse_type("multiple-choice")(multiple_choice),
            agenda.listener_with_memory,
            duplication.duplicate_graph,
        ),
        agenda.ask(ask),
        agenda.ack(agenda.GENERIC_ACK),
    )


def _ask_about(type: str, ask: str) -> base_types.GraphType:
    return agenda.slot(
        _typed_state(type), agenda.ask(ask), agenda.ack(agenda.GENERIC_ACK)
    )


def _ask_about_and_ack(ack: str, type: str, ask: str) -> base_types.GraphType:
    typed_state = _typed_state(type)
    return agenda.slot(
        typed_state,
        agenda.ask(ask),
        composers.compose_left(
            agenda.state_sink(typed_state),
            agenda.ack(lambda value: ack.format(value=value)),
            key="value",
        ),
    )


def _typed_state(type):
    assert is_supported_type(type), f"We currently do not support {type} type"

    return gamla.pipe(
        parse_type(type),
        agenda.consumes_external_event,
        agenda.if_participated
        if type in _TYPES_TO_LISTEN_AFTER_ASKING
        else gamla.identity,
        agenda.mark_state,
        agenda.remember,
        duplication.duplicate_graph,
    )


def _goals(
    goals: Tuple[base_types.GraphType, ...],
    definitions: Tuple[base_types.GraphType, ...],
) -> base_types.GraphType:
    del definitions
    return agenda.combine_utter_sinks(*goals)


@graph.make_terminal("debug_states")
def debug_states(args):
    return args


def _debug_dict(cg: base_types.GraphType):
    return {
        "state": agenda.state_sink(cg),
        "utter": gamla.excepts(
            AssertionError, gamla.just(lambda: ""), agenda.utter_sink
        )(cg),
        "participated": gamla.excepts(
            StopIteration,
            gamla.just(lambda: agenda.UNKNOWN),
            gamla.compose_left(
                gamla.filter(missing_cg_utils.edge_source_equals(agenda.participated)),
                gamla.map(base_types.edge_destination),
                gamla.head,
            ),
        )(cg),
    }


def _goals_with_debug(
    goals: Tuple[base_types.GraphType, ...],
    definitions: Tuple[base_types.GraphType, ...],
    debug: Union[
        Tuple[Tuple[str, base_types.GraphType], ...], Tuple[base_types.GraphType, ...]
    ],
) -> base_types.GraphType:
    del definitions
    return base_types.merge_graphs(
        agenda.combine_utter_sinks(*goals),
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
        (
            agenda.listener_with_memory(extract.amount_of(amount_of)),
            agenda.slot(
                _typed_state("amount"), agenda.ask(ask), agenda.ack(agenda.GENERIC_ACK)
            ),
        ),
    )


def composers_for_dag_reducer(remote_function: Callable) -> FrozenSet[Callable]:
    return frozenset(
        {
            _amount_of,
            _first_known,
            _complement,
            _all,
            _any,
            _kv,
            _build_remote_resolver(remote_function),
            _listen_to_intent,
            _ask_about_choice,
            _ask_about_multiple_choice,
            _say_with_needs,
            _when,
            _when_with_needs,
            _remote_with_needs,
            _ask_about,
            _ask_about_and_ack,
            _goals,
            _goals_with_debug,
            _equals,
            _greater_equals,
            _question_and_answer_dict,
            _faq_intent,
        }
    )
