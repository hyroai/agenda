from typing import Callable, Dict, FrozenSet, List, Iterable, Tuple, Union, Any

import inspect
from types import MappingProxyType
import agenda
import gamla
import toposort
import httpx
import duckling
import spacy
import pyap
from computation_graph import base_types, composers
from computation_graph.composers import lift


_d = duckling.DucklingWrapper()

_duckling_wrapper = gamla.ternary(
    gamla.nonempty,
    gamla.compose_left(
        gamla.map(gamla.get_in(["value", "value"])), gamla.sort, gamla.head
    ),
    gamla.just(agenda.UNKNOWN),
)

_nlp = spacy.load("en_core_web_lg")

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
    "none",
    "none of the above",
    "i disagree",
    "disagree",
}


def _sentences_similarity(user_utterance: str, examples: Tuple[str, ...]) -> int:
    user_sentence = _nlp(user_utterance)
    return gamla.pipe(
        examples,
        gamla.map(
            gamla.compose_left(
                lambda example: _nlp(example),
                lambda sentence: sentence.similarity(user_sentence),
            )
        ),
        gamla.sort,
        gamla.last,
    )


_name_detector: Callable[[str], str] = gamla.compose_left(
    lambda user_utterance: " ".join(
        word[0].upper() + word[1:] for word in user_utterance.split()
    ),
    lambda capitalized_user_utterance: _nlp(capitalized_user_utterance),
    tuple,
    gamla.filter(
        gamla.compose_left(gamla.attrgetter("ent_type_"), gamla.equals("PERSON"))
    ),
    gamla.map(gamla.attrgetter("text")),
    tuple,
    lambda names: " ".join(names),
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


def _listen_to_bool_or_intent(examples: Tuple[str, ...]) -> Union[bool, agenda.Unknown]:
    def parse_bool(user_utterance: str):
        if examples and _sentences_similarity(user_utterance, examples) >= 0.9:
            return True
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

    return parse_bool


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
    "email": gamla.compose_left(_d.parse_email, _duckling_wrapper),
    "phone": gamla.compose_left(_d.parse_phone_number, _duckling_wrapper),
    "amount": gamla.compose_left(_d.parse_number, _duckling_wrapper),
    "bool": _listen_to_bool_or_intent,
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
        "bool",
        "amount",
        "name",
        "address",
        "multiple-choice",
        "single-choice",
    }
)

_TYPES_TO_LISTEN_AFTER_ASKING = frozenset({"amount", "bool"})


def _listen_to_type(type: str) -> base_types.GraphType:

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type(user_utterance: str):
        return _FUNCTION_MAP.get(type)(user_utterance)

    if type in _TYPES_TO_LISTEN_AFTER_ASKING:
        return agenda.listener_with_memory_when_participated(
            agenda.consumes_external_event(listen_to_type)
        )
    return gamla.pipe(
        agenda.consumes_external_event(listen_to_type),
        agenda.mark_state,
        agenda.remember,
    )


def _listen_to_type_with_examples(
    type: str, examples: Tuple[str, ...]
) -> base_types.GraphType:

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type_or_intent(user_utterance):
        return _FUNCTION_MAP.get(type)(examples)(user_utterance)

    return gamla.pipe(
        agenda.consumes_external_event(listen_to_type_or_intent),
        agenda.mark_state,
        agenda.remember,
    )


def _listen_to_type_with_options(
    type: str, options: Tuple[str, ...]
) -> base_types.GraphType:
    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type_with_options(user_utterance):
        return _FUNCTION_MAP.get(type)(options)(user_utterance)

    return gamla.pipe(
        agenda.consumes_external_event(listen_to_type_with_options),
        agenda.mark_state,
        agenda.remember,
    )


def _complement(complement: base_types.GraphType) -> base_types.GraphType:
    return agenda.complement(complement)


def _kv(
    key: str, value: Union[str, base_types.GraphType]
) -> Tuple[str, Union[str, base_types.GraphType]]:
    if value == "incoming_utterance":
        return (key, agenda.event)
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

    return agenda.optionally_needs(remote_function, dict(needs))


def _ask_about(listen: base_types.GraphType, ask: str) -> base_types.GraphType:
    return agenda.slot(
        base_types.merge_graphs(listen, agenda.ask(ask)), agenda.ack("Got it.")
    )


def _slot(ack: str, listen: base_types.GraphType, ask: str) -> base_types.GraphType:
    return agenda.slot(
        base_types.merge_graphs(listen, agenda.ask(ask)), agenda.ack(ack)
    )


def _goals(
    goals: Tuple[base_types.GraphType, ...], slots: Tuple[base_types.GraphType, ...]
) -> base_types.GraphType:
    return agenda.combine_utterances(*goals)


_COMPOSERS_FOR_DAG_REDUCER = frozenset(
    {
        _listen_to_type,
        _listen_to_type_with_examples,
        _listen_to_type_with_options,
        _complement,
        _kv,
        _remote,
        _say_with_needs,
        _when,
        _when_with_needs,
        _remote_with_needs,
        _ask_about,
        _slot,
        _goals,
    }
)


_functions_to_case_dict: Callable[
    Iterable[Callable], Callable[[Dict], Any]
] = gamla.compose_left(
    gamla.map(
        lambda f: (
            gamla.equals(
                frozenset(
                    gamla.pipe(
                        f,
                        inspect.signature,
                        gamla.attrgetter("parameters"),
                        MappingProxyType.values,
                        gamla.map(gamla.attrgetter("name")),
                        tuple,
                    )
                )
            ),
            gamla.double_star(f),
        )
    ),
    gamla.suffix((gamla.equals(None), gamla.identity)),
    dict,
    gamla.keymap(gamla.before(gamla.compose_left(dict.keys, frozenset))),
    gamla.case_dict,
)


def reducer(
    state: Dict[str, base_types.GraphType],
    current: str,
    node_to_neighbors: Callable[[str], Dict[str, str]],
) -> Any:
    try:
        cg_dict = gamla.pipe(
            current,
            node_to_neighbors,
            gamla.valmap(
                gamla.ternary(
                    gamla.is_instance(tuple),
                    gamla.compose_left(gamla.map(state.__getitem__), tuple),
                    state.__getitem__,
                )
            ),
        )
    except KeyError:
        return current
    return _functions_to_case_dict(_COMPOSERS_FOR_DAG_REDUCER)(cg_dict)


def reduce_graph(
    depenedencies: Dict[str, FrozenSet[str]],
    node_to_neighbors: Callable[[str], Dict[str, str]],
    reducer: Callable[
        [Dict[str, base_types.GraphType], str, Callable[[str], Dict[str, str]]],
        Dict[str, base_types.GraphType],
    ],
) -> Dict[str, base_types.GraphType]:
    return gamla.pipe(
        toposort.toposort_flatten(depenedencies, False),
        gamla.reduce_curried(
            lambda state, current: gamla.pipe(
                reducer(state, current, node_to_neighbors),
                gamla.assoc_in(state, [current]),
            ),
            {},
        ),
    )
