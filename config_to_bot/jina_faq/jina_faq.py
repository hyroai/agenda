import functools
from typing import Awaitable, Callable, Iterator, Tuple

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
async def _index(faq: Tuple[Tuple[str, str], ...]) -> None:
    flow = _make_index_flow(faq)
    with flow:
        result = flow.post(on="/index", inputs=DocumentArray(_input_generator(faq)))
        results = [r async for r in result]  # noqa
    flow = _make_query_flow(faq)


@functools.cache
def _make_index_flow(faq: Tuple[Tuple[str, str], ...]):
    faq_hash = gamla.compute_stable_json_hash(faq)
    return (
        AsyncFlow()
        .add(
            uses="jinahub://TransformerTorchEncoder/latest",
            uses_with={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        )
        .add(uses="jinahub://SimpleIndexer/latest", workspace=f"./workspace_{faq_hash}")
    )


@functools.cache
def _make_query_flow(faq: Tuple[Tuple[str, str], ...]):
    return _make_index_flow(faq).add(
        uses="jinahub://SimpleRanker/latest", uses_with={"metric": "cosine"}
    )


@gamla.curry
async def _query(
    faq: Tuple[Tuple[str, str], ...], user_utterance: str
) -> Tuple[str, float]:
    flow = _make_query_flow(faq)
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


async def make_jina_query(faq: Tuple[Tuple[str, str], ...]) -> Awaitable:
    await _index(faq)
    return _query(faq)
