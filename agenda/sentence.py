from typing import Dict

import gamla
import immutables

SentenceOrPart = Dict

_TEXT = "text"
_QUESTION = "question"
_SENTENCE = "sentence"
_STATEMENT = "statement"
_ACK = "ack"
_CONSTITUENTS = "constituents"
_TYPE = "type"
_GENERIC_ACK = "Got it."

EMPTY_SENTENCE = immutables.Map({_TYPE: _SENTENCE, _CONSTITUENTS: frozenset()})

constituents = gamla.itemgetter(_CONSTITUENTS)

_is_question = gamla.compose(gamla.equals(_QUESTION), gamla.itemgetter(_TYPE))
_is_sentence = gamla.compose(gamla.equals(_SENTENCE), gamla.itemgetter(_TYPE))
_is_ack = gamla.compose(gamla.equals(_ACK), gamla.itemgetter(_TYPE))
_is_statement = gamla.compose(gamla.equals(_STATEMENT), gamla.itemgetter(_TYPE))

_has_question = gamla.inside(_QUESTION)
_has_ack = gamla.inside(_ACK)


def sentence_to_str(sentence: SentenceOrPart) -> str:
    if not _is_sentence(sentence):
        sentence = _sentence_part_reducer(EMPTY_SENTENCE, sentence)
    statements = " ".join(map(gamla.itemgetter(_TEXT), sentence.get(_STATEMENT, [])))
    question_obj = sentence.get(_QUESTION, None)
    question = question_obj.get(_TEXT) if question_obj else ""
    ack_obj = sentence.get(_ACK, "")
    ack = ack_obj.get(_TEXT) if ack_obj else ""
    return f"{ack} {statements} {question}".strip()


def str_to_statement(text):
    if not text:
        return EMPTY_SENTENCE
    return immutables.Map({_TYPE: _STATEMENT, _TEXT: text})


def str_to_question(text):
    assert text
    return immutables.Map({_TYPE: _QUESTION, _TEXT: text})


def str_to_ack(text):
    assert text
    return immutables.Map({_TYPE: _ACK, _TEXT: text})


def _set_question(sentence, element):
    return sentence.set(_QUESTION, element).set(
        _CONSTITUENTS, sentence[_CONSTITUENTS] | {element}
    )


def _add_statement(sentence, element):
    return sentence.set(
        _STATEMENT, sentence.get(_STATEMENT, frozenset()) | {element}
    ).set(_CONSTITUENTS, sentence[_CONSTITUENTS] | {element})


def _add_ack(sentence, element):
    if _has_ack(sentence):
        return sentence.set(_ACK, _GENERIC_ACK).set(
            _CONSTITUENTS, sentence[_CONSTITUENTS] | {element}
        )
    return sentence.set(_ACK, element).set(
        _CONSTITUENTS, sentence[_CONSTITUENTS] | {element}
    )


def _merge_sentences(sentence1, sentence2):
    statements = sentence2.get(_STATEMENT, frozenset())
    ack = sentence2.get(_ACK, None)
    if ack:
        sentence1 = _add_ack(sentence1, ack)
    for s in statements:
        sentence1 = _add_statement(sentence1, s)
    return sentence1


def _sentence_part_reducer(
    sentence_so_far: SentenceOrPart, current: SentenceOrPart
) -> SentenceOrPart:
    if (
        current is EMPTY_SENTENCE
        or _is_question(current)
        and _has_question(sentence_so_far)
    ):
        return sentence_so_far
    if _is_question(current):
        return _set_question(sentence_so_far, current)
    if _is_ack(current):
        return _add_ack(sentence_so_far, current)
    if _is_statement(current):
        return _add_statement(sentence_so_far, current)
    if _is_sentence(current):
        if _has_question(current):
            return sentence_so_far
        return _merge_sentences(sentence_so_far, current)

    assert False, f"This should cover all cases {current}."


combine = gamla.reduce(_sentence_part_reducer, EMPTY_SENTENCE)
