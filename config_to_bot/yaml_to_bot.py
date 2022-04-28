import random
from typing import IO, Awaitable, Callable, Union

import gamla
import yaml
from computation_graph import base_types

import agenda
from config_to_bot import build_kg, dag_reducer, resolvers


def _ack_generator() -> str:
    x = random.choice(["Okay.", "Alright.", "Got it.", "Cool."])
    # TODO(uri): For a reason I don't fully understand, unless we have a `print` or `breakpoint` here, it always selects the same option.
    print(x)  # noqa: T001
    return x


def _anti_ack_generator() -> str:
    x = random.choice(
        [
            "I am sorry I did not get that.",
            "I could not understand you.",
            "Please rephrase.",
        ]
    )
    # TODO(uri): For a reason I don't fully understand, unless we have a `print` or `breakpoint` here, it always selects the same option.
    print(x)  # noqa: T001
    return x


sentence_to_str = agenda.sentence_renderer(_ack_generator, _anti_ack_generator)

_YAML_STREAM = Union[str, bytes, IO[str], IO[bytes]]


def yaml_to_cg(
    remote_function: Callable,
) -> Callable[[_YAML_STREAM], base_types.GraphType]:
    return gamla.compose_left(
        yaml.safe_load,
        build_kg.yaml_dict_to_triplets,
        gamla.prepare_and_apply(
            lambda triplets: build_kg.reduce_kg(
                dag_reducer.reducer(
                    resolvers.build_cg(remote_function, build_kg.adapt_kg(triplets))
                )
            )
        ),
    )


yaml_to_slot_bot: Callable[
    [_YAML_STREAM], Callable[[], Awaitable]
] = gamla.compose_left(
    yaml_to_cg(resolvers.post_request_with_url_and_params),
    agenda.wrap_up(agenda.sentence_renderer(_ack_generator, _anti_ack_generator)),
    gamla.after(gamla.to_awaitable),
    gamla.just,
)
