from typing import Callable, Dict, FrozenSet, List, Iterable, Tuple, Union

import agenda
import gamla
import toposort
import httpx
import duckling
from computation_graph import base_types, composers
from computation_graph.composers import lift
from agenda import composers as agenda_composers

d = duckling.DucklingWrapper()

duckling_wrapper = gamla.ternary(
    gamla.nonempty,
    gamla.compose_left(
        gamla.map(gamla.get_in(["value", "value"])), gamla.sort, gamla.head
    ),
    gamla.just(agenda.UNKNOWN),
)


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


def _parse_bool(user_utterance: str):
    if user_utterance.strip() in _AFFIRMATIVE:
        return True
    if user_utterance.strip() in _NEGATIVE:
        return False
    return agenda.UNKNOWN


_FUNCTION_MAP = {
    "email": gamla.compose_left(d.parse_email, duckling_wrapper),
    "phone": gamla.compose_left(d.parse_phone_number, duckling_wrapper),
    "amount": gamla.compose_left(d.parse_number, duckling_wrapper),
    "bool": _parse_bool,
}

_INFORMATION_TYPES = frozenset({"phone", "email", "bool", "amount"})


def _determine_composer(keys: FrozenSet[str]) -> Callable[..., base_types.GraphType]:
    if not keys:
        return gamla.identity
    if keys == frozenset({"say"}):

        def say_composer(say):
            return agenda.state(say)

        return say_composer

    if keys == frozenset({"ack"}):

        def ack_composer(ack):
            return agenda.ack(ack)

        return ack_composer

    if keys == frozenset({"ask"}):

        def ask_composer(ask):
            return agenda.ask(ask)

    if keys == frozenset({"type"}):

        def function_composer(type):

            assert (
                type in _INFORMATION_TYPES
            ), f"We currently do not support {type} type"

            def listen_to_type(user_utterance):
                return _FUNCTION_MAP.get(type)(user_utterance)

            return agenda.mark_event(listen_to_type)

        return function_composer
    if keys == frozenset({"key", "value"}):

        def kv_composer(key, value):
            if value == "incoming_utterance":
                return (key, agenda.event)
            return (key, value)

        return kv_composer

    if keys == frozenset({"url"}):

        def url_composer(url):
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
                                gamla.when(
                                    gamla.equals(agenda.UNKNOWN), gamla.just(None)
                                )
                            ),
                        ),
                    ),
                    httpx.Response.json,
                    gamla.freeze_deep,
                )

            return post_request

        return url_composer

    if keys == frozenset({"say", "needs"}):

        def say_remote(say, needs: Iterable[Tuple[str, base_types.GraphType]]):
            return agenda.optionally_needs(agenda.state(say), dict(needs))

        return say_remote
    if keys == frozenset({"say", "needs", "when"}):

        def when_composer(say, needs, when):
            return agenda.when(
                when, agenda.optionally_needs(agenda.state(say), dict(needs))
            )

        return when_composer
    if keys == frozenset({"url", "needs"}):

        def remote(needs: Iterable[Tuple[str, base_types.GraphType]], url: str):
            async def remote_function(params: Dict):
                return gamla.pipe(
                    await gamla.post_json_with_extra_headers_and_params_async(
                        {}, {"Content-Type": "application/json"}, 30, url, params
                    ),
                    httpx.Response.json,
                    gamla.when(gamla.equals(None), gamla.just(agenda.UNKNOWN)),
                )

            return agenda.optionally_needs(remote_function, dict(needs))

        return remote

    if keys == frozenset({"listen", "ask"}):

        def ask_about_composers(listen, ask):
            return agenda.slot(
                gamla.pipe(listen, agenda.mark_state, agenda.remember),
                agenda.ask(ask),
                agenda.ack("Got it."),
            )

        return ask_about_composers
    if keys == frozenset({"ack", "listen", "ask"}):

        def slot_composer(ack, listen, ask):
            return agenda.slot(
                gamla.pipe(listen, agenda.mark_state, agenda.remember),
                agenda.ask(ask),
                agenda.ack(ack),
            )

        return slot_composer
    if keys == frozenset({"goals", "slots"}):

        def goals_composer(goals, slots):
            return base_types.merge_graphs(*goals)

        return goals_composer
    assert False, keys


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
    to_cg = _determine_composer(frozenset(cg_dict))
    return to_cg(**cg_dict)


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
