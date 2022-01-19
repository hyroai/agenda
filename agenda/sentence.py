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
    question_obj = sentence.get(_QUESTION)
    question = question_obj.get(_TEXT) if question_obj else ""
    ack_obj = sentence.get(_ACK)
    ack = ack_obj.get(_TEXT) if ack_obj else ""
    return " ".join(filter(gamla.identity, [ack, statements, question]))


def str_to_statement(text):
    if not text:
        return EMPTY_SENTENCE
    return immutables.Map({_TYPE: _STATEMENT, _TEXT: text})


def str_to_question(text):
    if not text:
        return EMPTY_SENTENCE
    return immutables.Map({_TYPE: _QUESTION, _TEXT: text})


def str_to_ack(text):
    if not text:
        return EMPTY_SENTENCE
    return immutables.Map({_TYPE: _ACK, _TEXT: text})


def _set_question(sentence, element):
    assert element != EMPTY_SENTENCE
    return sentence.set(_QUESTION, element)


def _add_statement(sentence, element):
    assert element != EMPTY_SENTENCE
    return sentence.set(_STATEMENT, sentence.get(_STATEMENT, frozenset()) | {element})


def _add_constituent(sentence, element):
    return sentence.set(_CONSTITUENTS, sentence[_CONSTITUENTS] | {element})


def _add_ack(sentence, element):
    assert element != EMPTY_SENTENCE
    if _has_ack(sentence):
        return sentence.set(_ACK, str_to_ack("Got it."))
    return sentence.set(_ACK, element)


def _merge_sentences(sentence1, sentence2):
    new_sentence = sentence1.set(
        _CONSTITUENTS, frozenset([*constituents(sentence1), sentence2])
    )
    if _has_ack(sentence2):
        new_sentence = _add_ack(new_sentence, sentence2.get(_ACK))
        assert _has_ack(new_sentence)
    for s in sentence2.get(_STATEMENT, ()):
        new_sentence = _add_statement(new_sentence, s)
    if _has_question(sentence2):
        new_sentence = _set_question(new_sentence, sentence2.get(_QUESTION))
    return new_sentence


def _sentence_part_reducer(
    sentence_so_far: SentenceOrPart, current: SentenceOrPart
) -> SentenceOrPart:
    assert EMPTY_SENTENCE not in constituents(sentence_so_far), constituents(
        sentence_so_far
    )
    if (
        current is EMPTY_SENTENCE
        or _is_question(current)
        and _has_question(sentence_so_far)
    ):
        return sentence_so_far
    if _is_question(current):
        return _add_constituent(_set_question(sentence_so_far, current), current)
    if _is_ack(current):
        return _add_constituent(_add_ack(sentence_so_far, current), current)
    if _is_statement(current):
        return _add_constituent(_add_statement(sentence_so_far, current), current)
    if _is_sentence(current):
        if _has_question(sentence_so_far) and _has_question(current):
            return sentence_so_far
        return _merge_sentences(sentence_so_far, current)

    assert False, f"This should cover all cases {current}."


combine = gamla.reduce(_sentence_part_reducer, EMPTY_SENTENCE)
