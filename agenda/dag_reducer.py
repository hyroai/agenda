from typing import Callable, Dict, FrozenSet, List, Iterable, Tuple, Union

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


d = duckling.DucklingWrapper()

duckling_wrapper = gamla.ternary(
    gamla.nonempty,
    gamla.compose_left(
        gamla.map(gamla.get_in(["value", "value"])), gamla.sort, gamla.head
    ),
    gamla.just(agenda.UNKNOWN),
)

nlp = spacy.load("en_core_web_lg")

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
    user_sentence = nlp(user_utterance)
    return gamla.pipe(
        examples,
        gamla.map(
            gamla.compose_left(
                lambda example: nlp(example),
                lambda sentence: sentence.similarity(user_sentence),
            )
        ),
        gamla.sort,
        gamla.last,
    )


_name_detector = gamla.compose_left(
    lambda user_utterance: " ".join(
        word[0].upper() + word[1:] for word in user_utterance.split()
    ),
    lambda capitalized_user_utterance: nlp(capitalized_user_utterance),
    tuple,
    gamla.filter(
        gamla.compose_left(gamla.attrgetter("ent_type_"), gamla.equals("PERSON"))
    ),
    gamla.map(gamla.attrgetter("text")),
    tuple,
    lambda names: " ".join(names),
)


_address_detector = gamla.compose_left(
    lambda user_utterance: pyap.parse(user_utterance, country="US"),
    gamla.ternary(
        gamla.nonempty,
        gamla.compose_left(gamla.head, gamla.attrgetter("full_address")),
        gamla.just(agenda.UNKNOWN),
    ),
)


_text_to_lower_case_words = gamla.compose_left(str.split, gamla.map(str.lower))


def _listen_to_bool_or_intent(examples: Tuple[str, ...]):
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


_FUNCTION_MAP = {
    "email": gamla.compose_left(d.parse_email, duckling_wrapper),
    "phone": gamla.compose_left(d.parse_phone_number, duckling_wrapper),
    "amount": gamla.compose_left(d.parse_number, duckling_wrapper),
    "bool": _listen_to_bool_or_intent,
    "name": gamla.compose_left(
        _name_detector, gamla.when(gamla.equals(""), gamla.just(agenda.UNKNOWN))
    ),
    "address": gamla.compose_left(
        _address_detector, gamla.when(gamla.equals(""), gamla.just(agenda.UNKNOWN))
    ),
}

_INFORMATION_TYPES = frozenset({"phone", "email", "bool", "amount", "name", "address"})

_TYPES_TO_LISTEN_AFTER_ASKING = frozenset({"amount", "bool"})


def say(say):
    return agenda.say(say)


def ack(ack):
    return agenda.ack(ack)


def ask(ask):
    return agenda.ask(ask)


def listen_to_type(type):

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type(user_utterance):
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


def listen_to_type_with_examples(type, examples):

    assert type in _INFORMATION_TYPES, f"We currently do not support {type} type"

    def listen_to_type_or_intent(user_utterance):
        return _FUNCTION_MAP.get(type)(examples)(user_utterance)

    return gamla.pipe(
        agenda.consumes_external_event(listen_to_type_or_intent),
        agenda.mark_state,
        agenda.remember,
    )


def complement(complement):
    return agenda.complement(complement)


def kv(key, value):
    if value == "incoming_utterance":
        return (key, agenda.event)
    return (key, value)


def remote(url):
    async def post_request(params):

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


def say_with_needs(say, needs: Iterable[Tuple[str, base_types.GraphType]]):
    return agenda.optionally_needs(agenda.say(say), dict(needs))


def when(say, when):
    return agenda.when(when, agenda.say(say))


def when_with_needs(say, needs, when):
    return agenda.when(when, agenda.optionally_needs(agenda.say(say), dict(needs)))


def remote_with_needs(
    needs: Iterable[Tuple[str, base_types.GraphType]], url: str
):
    async def remote_function(params: Dict):
        return gamla.pipe(
            await gamla.post_json_with_extra_headers_and_params_async(
                {}, {"Content-Type": "application/json"}, 30, url, params
            ),
            httpx.Response.json,
            gamla.when(gamla.equals(None), gamla.just(agenda.UNKNOWN)),
        )

    return agenda.optionally_needs(remote_function, dict(needs))


def ask_about(listen, ask):
    return agenda.slot(
        base_types.merge_graphs(listen, agenda.ask(ask)), agenda.ack("Got it.")
    )


def slot(ack, listen, ask):
    return agenda.slot(
        base_types.merge_graphs(listen, agenda.ask(ask)), agenda.ack(ack)
    )


def goals(goals, slots):
    return agenda.combine_utterances(*goals)


_COMPOSERS_FOR_DAG_REDUCER = frozenset(
    {
        say,
        ack,
        ask,
        listen_to_type,
        listen_to_type_with_examples,
        complement,
        kv,
        remote,
        say_with_needs,
        when,
        when_with_needs,
        remote_with_needs,
        ask_about,
        slot,
        goals,
    }
)


functions_to_case_dict = gamla.compose_left(
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
):
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
    return functions_to_case_dict(_COMPOSERS_FOR_DAG_REDUCER)(cg_dict)


def reduce_graph(
    depenedencies: Dict[str, FrozenSet[str]],
    node_to_neighbors: Callable[[str], Dict[str, str]],
    reducer: Callable[
        [Dict[str, base_types.GraphType], str, Callable[[str], Dict[str, str]]],
        Dict[str, base_types.GraphType],
    ],
):
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
