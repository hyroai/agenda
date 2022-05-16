import functools
import os
from typing import Iterator, Tuple

import gamla
from jina import Document, DocumentArray, Flow

_DIR_NAME = os.path.dirname(__file__)


def _input_generator(faq: Tuple[Tuple[str, str], ...]) -> Iterator[Document]:
    for question, answer in faq:
        yield Document(text=question)


@functools.cache
async def index(faq: Tuple[Tuple[str, str], ...]) -> None:
    flow = Flow(asyncio=True).load_config(
        os.path.join(_DIR_NAME, "flows/flow-index.yaml")
    )
    with flow:
        result = flow.post(on="/index", inputs=DocumentArray(_input_generator(faq)))
        results = [r async for r in result]  # noqa
    flow = make_query_flow()


@functools.cache
def make_query_flow():
    return Flow(asyncio=True).load_config(
        os.path.join(_DIR_NAME, "flows/flow-query.yaml")
    )


async def query(user_utterance: str) -> Tuple[str, float]:
    flow = make_query_flow()
    with flow:
        result = flow.post(
            on="/search",
            inputs=DocumentArray([Document(content=user_utterance)]),
            parameters={"top_k": 1},
            line_format="text",
            return_results=True,
        )

        results = [answer async for answer in result]
        return gamla.pipe(
            results,
            gamla.head,
            gamla.head,
            gamla.attrgetter("_data"),
            gamla.attrgetter("matches"),
            gamla.ternary(
                gamla.identity,
                gamla.compose_left(
                    gamla.attrgetter("_data"),
                    gamla.head,
                    gamla.juxt(gamla.attrgetter("text"), gamla.attrgetter("scores")),
                ),
                gamla.just(("", 1)),
            ),
        )
