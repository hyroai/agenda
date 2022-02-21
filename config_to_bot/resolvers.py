import datetime
from typing import Any, Callable, Dict, FrozenSet, Iterable, Tuple, Union

import duckling
import gamla
import httpx
import pyap
import spacy
from computation_graph import base_types, composers, graph
from computation_graph.composers import duplication, lift

import agenda
from agenda import missing_cg_utils

_duckling_value_or_unknown = gamla.ternary(
    gamla.nonempty,
    gamla.compose_left(
        gamla.map(gamla.get_in(["value", "value"])), gamla.sort, gamla.head
    ),
    gamla.just(agenda.UNKNOWN),
)
_duckling_context = duckling.Context(
    duckling.parse_ref_time(
        duckling.load_time_zones("/usr/share/zoneinfo"),
        "UTC",
        round(datetime.datetime.utcnow().timestamp()),
    ),
    duckling.default_locale_lang(duckling.parse_lang("EN")),
)


def _ducklings_parser(dim: str):
    return gamla.compose_left(
        lambda text: duckling.parse(text, _duckling_context, []),
        gamla.filter(gamla.compose_left(gamla.itemgetter("dim"), gamla.equals(dim))),
        tuple,
        _duckling_value_or_unknown,
    )


_nlp = spacy.load("en_core_web_lg")


def _construct_doc(sentence: str):
    return _nlp(sentence)


_AFFIRMATIVE = {
    "affirmative",
    "agree",
    "cool",
    "definitely",
    "good",
    "i did",
    "i do",
    "i had",
    "i have",
    "i think so",
    "i believe so",
    "obviously",
    "of course",
    "ok",
    "proceed",
    "right",
    "sure",
    "that's great",
    "yeah",
    "yes",
    "yup",
}


_NEGATIVE = {
    "definitely not",
    "didn't",
    "don't",
    "have not",
    "i don't think so",
    "i have not",
    "i haven't",
    "nah",
    "negative",
    "negatory",
    "no",
    "nope",
    "not",
    "nothing",
    "of course not",
    "i disagree",
    "disagree",
}


def _sentences_similarity(user_utterance: str, examples: Tuple[str, ...]) -> int:
    user_sentence = _nlp(user_utterance)
    return gamla.pipe(
        examples,
        gamla.map(
            gamla.compose_left(
                _construct_doc, lambda sentence: sentence.similarity(user_sentence)
            )
        ),
        gamla.sort,
        gamla.last,
    )


_name_detector: Callable[[str], str] = gamla.compose_left(
    _construct_doc,
    tuple,
    gamla.filter(
        gamla.compose_left(gamla.attrgetter("ent_type_"), gamla.equals("PERSON"))
    ),
    gamla.map(gamla.attrgetter("text")),
    tuple,
    " ".join,
)


_address_detector: Callable[[str], Union[str, agenda.Unknown]] = gamla.compose_left(
    lambda user_utterance: pyap.parse(user_utterance, country="US"),
    gamla.ternary(
        gamla.nonempty,
        gamla.compose_left(gamla.head, gamla.attrgetter("full_address")),
        gamla.just(agenda.UNKNOWN),
    ),
)


_text_to_lower_case_words: Callable[[str], Iterable[str]] = gamla.compose_left(
    str.split, gamla.map(str.lower)
)


def _listen_to_intent(
    examples: Tuple[str, ...]
) -> Callable[[str], Union[bool, agenda.Unknown]]:
    def parse_bool(user_utterance: str):
        return bool(examples) and _sentences_similarity(user_utterance, examples) >= 0.9

    return parse_bool


def _listen_to_bool(user_utterance: str):
    if gamla.pipe(
        user_utterance,
        _text_to_lower_case_words,
        gamla.anymap(gamla.contains(_AFFIRMATIVE)),
    ):
        return True
    if gamla.pipe(
        user_utterance,
        _text_to_lower_case_words,
        gamla.anymap(gamla.contains(_NEGATIVE)),
    ):
        return False
    return agenda.UNKNOWN


def _listen_to_multiple_choices(
    options: Tuple[str, ...]
) -> Callable[[str], Union[Tuple[str, ...], agenda.Unknown]]:
    return gamla.compose_left(
        lambda user_utterance: user_utterance.split(),
        gamla.map(str.lower),
        gamla.filter(gamla.contains([*options, "none"])),
        tuple,
        gamla.when(gamla.empty, gamla.just(agenda.UNKNOWN)),
    )


def _listen_to_single_choice(
    options: Tuple[str, ...]
) -> Callable[[str], Union[str, agenda.Unknown]]:
    return gamla.compose_left(
        lambda user_utterance: user_utterance.split(),
        gamla.map(str.lower),
        gamla.filter(gamla.contains(options)),
        tuple,
        gamla.ternary(gamla.len_equals(1), gamla.head, gamla.just(agenda.UNKNOWN)),
    )


_FUNCTION_MAP = {
    "email": _ducklings_parser("email"),
    "phone": _ducklings_parser("phone-number"),
    "amount": _ducklings_parser("number"),
    "bool": _listen_to_bool,
    "intent": _listen_to_intent,
    "name": gamla.compose_left(
        _name_detector, gamla.when(gamla.equals(""), gamla.just(agenda.UNKNOWN))
    ),
    "address": _address_detector,
    "multiple-choice": _listen_to_multiple_choices,
    "single-choice": _listen_to_single_choice,
}

_INFORMATION_TYPES = frozenset(
    {
        "phone",
        "email",
        "intent",
        "bool",
        "amount",
        "name",
        "address",
        "multiple-choice",
        "single-choice",
    }
)

_TYPES_TO_LISTEN_AFTER_ASKING = frozenset({"amount", "bool"})


def _listen_to_amount_of(type: str, of: str):
    assert type == "amount", f"We currently do not support {type} type"
    noun = _nlp(of)

    @agenda.consumes_external_event
    def listen_to_amount_of(user_utterance):
        return gamla.pipe(
            user_utterance,
            _nlp,
            gamla.filter(lambda t: t.similarity(noun) > 0.5),
            gamla.mapcat(gamla.attrgetter("children")),
            gamla.filter(
                gamla.compose_left(gamla.attrgetter("dep_"), gamla.equals("nummod"))
            ),
            gamla.map(gamla.attrgetter("text")),
            tuple,
            gamla.ternary(
                gamla.len_greater(0),
                gamla.compose_left(gamla.head, _FUNCTION_MAP.get("amount")),
                gamla.just(agenda.UNKNOWN),
            ),
        )

    return listen_to_amount_of


def _listen_to_type(type: str) -> base_types.GraphType:

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type(user_utterance: str):
        return _FUNCTION_MAP.get(type)(user_utterance)  # type: ignore

    if type in _TYPES_TO_LISTEN_AFTER_ASKING:
        return agenda.if_participated(agenda.consumes_external_event(listen_to_type))
    return agenda.consumes_external_event(listen_to_type)


def _listen_to_type_with_examples(
    type: str, examples: Tuple[str, ...]
) -> base_types.GraphType:

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type_or_intent(user_utterance):
        return _FUNCTION_MAP.get(type)(examples)(user_utterance)

    return agenda.consumes_external_event(listen_to_type_or_intent)


def _listen_to_type_with_options(
    type: str, options: Tuple[str, ...]
) -> base_types.GraphType:
    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type_with_options(user_utterance):
        return _FUNCTION_MAP.get(type)(options)(user_utterance)

    return agenda.consumes_external_event(listen_to_type_with_options)


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


def _remote(url: str):
    async def post_request(params: Dict[str, Any]):

        return gamla.pipe(
            await gamla.post_json_with_extra_headers_and_params_async(
                {},
                {"Content-Type": "application/json"},
                30,
                url,
                gamla.pipe(
                    params,
                    gamla.valmap(
                        gamla.when(gamla.equals(agenda.UNKNOWN), gamla.just(None))
                    ),
                ),
            ),
            httpx.Response.json,
            gamla.freeze_deep,
            gamla.when(gamla.equals(None), gamla.just("")),
        )

    return post_request


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


def _listen(listen: base_types.GraphType):
    return gamla.pipe(
        listen,
        gamla.unless(agenda.state_sink_or_none, agenda.mark_state),
        agenda.ever,
        duplication.duplicate_graph,
    )


def _ask_about(listen: base_types.GraphType, ask: str) -> base_types.GraphType:
    return _slot(agenda.GENERIC_ACK, listen, ask)


def _slot(ack, listen: base_types.GraphType, ask: str) -> base_types.GraphType:
    return agenda.slot(
        gamla.pipe(
            listen,
            gamla.unless(agenda.state_sink_or_none, agenda.mark_state),
            agenda.remember,
            duplication.duplicate_graph,
        ),
        agenda.ask(ask),
        agenda.ack(ack),
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
        [
            gamla.pipe(_listen_to_amount_of("amount", amount_of), agenda.mark_state),
            agenda.slot(
                gamla.pipe(
                    "amount", _listen_to_type, agenda.mark_state, agenda.remember
                ),
                agenda.ask(ask),
                agenda.ack(agenda.GENERIC_ACK),
            ),
        ],
    )


COMPOSERS_FOR_DAG_REDUCER: FrozenSet[Callable] = frozenset(
    {
        _amount_of,
        _first_known,
        _listen_to_type,
        _listen_to_type_with_examples,
        _listen_to_type_with_options,
        _listen,
        _complement,
        _all,
        _any,
        _kv,
        _remote,
        _say_with_needs,
        _when,
        _when_with_needs,
        _remote_with_needs,
        _ask_about,
        _slot,
        _goals,
        _goals_with_debug,
        _equals,
        _greater_equals,
    }
)
