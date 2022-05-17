import functools
from typing import Callable, Iterator, Tuple

import async_lru
import gamla
import torch
from jina import AsyncFlow, Document, DocumentArray

_question_answer_mapper: Callable[
    [Tuple[Tuple[str, str], ...]], Callable[[str], str]
] = gamla.compose_left(dict, gamla.attrgetter("__getitem__"))


def _input_generator(faq: Tuple[Tuple[str, str], ...]) -> Iterator[Document]:
    for question, answer in faq:
        yield Document(text=question)


@async_lru.alru_cache
async def index(faq: Tuple[Tuple[str, str], ...]) -> None:
    flow = make_index_flow()
    with flow:
        result = flow.post(on="/index", inputs=DocumentArray(_input_generator(faq)))
        results = [r async for r in result]  # noqa
    flow = make_query_flow()


@functools.cache
def make_index_flow():
    return (
        AsyncFlow()
        .add(
            uses="jinahub://TransformerTorchEncoder/latest",
            uses_with={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        )
        .add(uses="jinahub://SimpleIndexer/latest")
    )


@functools.cache
def make_query_flow():
    return make_index_flow().add(
        uses="jinahub://SimpleRanker/latest", uses_with={"metric": "cosine"}
    )


async def query(
    user_utterance: str, faq: Tuple[Tuple[str, str], ...]
) -> Tuple[str, float]:
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
                    gamla.juxt(
                        gamla.compose_left(
                            gamla.attrgetter("text"), _question_answer_mapper(faq)
                        ),
                        gamla.compose_left(
                            gamla.attrgetter("scores"),
                            gamla.itemgetter("cosine"),
                            gamla.attrgetter("value"),
                        ),
                    ),
                ),
                gamla.just(("", 1)),
            ),
        )
