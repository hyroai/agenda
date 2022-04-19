from typing import Dict, Union

import gamla

SentenceOrPart = Union[Dict, gamla.frozendict]

_TEXT = "text"
_QUESTION = "question"
_SENTENCE = "sentence"
_STATEMENT = "statement"
_ACK = "ack"
_CONSTITUENTS = "constituents"
_TYPE = "type"
_ANTI_ACK = "anti_ack"


class _GenericAck:
    pass


class _GenericAntiAck:
    pass


GENERIC_ANTI_ACK = _GenericAntiAck()
GENERIC_ACK = _GenericAck()
EMPTY_SENTENCE = gamla.frozendict({_TYPE: _SENTENCE, _CONSTITUENTS: frozenset()})

constituents = gamla.itemgetter(_CONSTITUENTS)

_is_question = gamla.compose(gamla.equals(_QUESTION), gamla.itemgetter(_TYPE))
_is_sentence = gamla.compose(gamla.equals(_SENTENCE), gamla.itemgetter(_TYPE))
_is_ack = gamla.compose(gamla.equals(_ACK), gamla.itemgetter(_TYPE))
_is_statement = gamla.compose(gamla.equals(_STATEMENT), gamla.itemgetter(_TYPE))
_is_anti_ack = gamla.compose(gamla.equals(_ANTI_ACK), gamla.itemgetter(_TYPE))

_has_question = gamla.inside(_QUESTION)
_has_ack = gamla.inside(_ACK)
_has_anti_ack = gamla.inside(_ANTI_ACK)
_has_statement = gamla.inside(_STATEMENT)

is_sentence_or_part = gamla.alljuxt(
    gamla.is_instance(gamla.frozendict),
    gamla.inside(_TYPE),
    gamla.anyjuxt(_is_question, _is_sentence, _is_statement, _is_ack, _is_anti_ack),
)


def sentence_to_str(
    generic_ack_renderer, generic_anti_ack_renderer, sentence: SentenceOrPart
) -> str:
    if not _is_sentence(sentence):
        sentence = _sentence_part_reducer(EMPTY_SENTENCE, sentence)
    statements = " ".join(map(gamla.itemgetter(_TEXT), sentence.get(_STATEMENT, [])))
    question_obj = sentence.get(_QUESTION)
    question = question_obj.get(_TEXT) if question_obj else ""
    ack_obj = sentence.get(_ACK)
    anti_ack_obj = sentence.get(_ANTI_ACK)
    ack = ack_obj.get(_TEXT) if ack_obj else ""
    anti_ack = anti_ack_obj.get(_TEXT) if anti_ack_obj else ""
    return " ".join(
        filter(
            gamla.identity,
            [
                generic_ack_renderer() if ack == GENERIC_ACK else ack,
                generic_anti_ack_renderer()
                if anti_ack == GENERIC_ANTI_ACK
                else anti_ack,
                statements,
                question,
            ],
        )
    )


def str_to_statement(text):
    assert isinstance(text, str), text
    if not text:
        return EMPTY_SENTENCE
    return gamla.frozendict({_TYPE: _STATEMENT, _TEXT: text})


def str_to_question(text):
    assert isinstance(text, str)
    if not text:
        return EMPTY_SENTENCE
    return gamla.frozendict({_TYPE: _QUESTION, _TEXT: text})


def str_to_ack(ack_represntation: Union[str, _GenericAck]) -> SentenceOrPart:
    if not ack_represntation:
        return EMPTY_SENTENCE
    return gamla.frozendict({_TYPE: _ACK, _TEXT: ack_represntation})


def str_to_anti_ack(
    anti_ack_represntation: Union[str, _GenericAntiAck]
) -> SentenceOrPart:
    if not anti_ack_represntation:
        return EMPTY_SENTENCE
    return gamla.frozendict({_TYPE: _ANTI_ACK, _TEXT: anti_ack_represntation})


def _set_question(sentence, element):
    assert element != EMPTY_SENTENCE
    return gamla.freeze_deep(gamla.assoc_in(sentence, [_QUESTION], element))


def _add_statement(sentence, element):
    assert element != EMPTY_SENTENCE
    return gamla.freeze_deep(
        gamla.update_in(sentence, [_STATEMENT], {element}.union, frozenset())
    )


def _add_constituent(sentence, element):
    return gamla.freeze_deep(
        gamla.update_in(sentence, [_CONSTITUENTS], {element}.union, frozenset())
    )


def _add_ack(sentence, element):
    assert element != EMPTY_SENTENCE
    if _has_ack(sentence):
        return gamla.freeze_deep(
            gamla.assoc_in(sentence, [_ACK], str_to_ack(GENERIC_ACK))
        )
    return gamla.freeze_deep(gamla.assoc_in(sentence, [_ACK], element))


def _add_anti_ack(sentence, element):
    assert element != EMPTY_SENTENCE
    if _has_anti_ack(sentence):
        return gamla.freeze_deep(
            gamla.assoc_in(sentence, [_ANTI_ACK], str_to_ack(GENERIC_ANTI_ACK))
        )
    return gamla.freeze_deep(gamla.assoc_in(sentence, [_ANTI_ACK], element))


def _merge_sentences(sentence1, sentence2):
    new_sentence = _add_constituent(sentence1, sentence2)
    if _has_ack(sentence2):
        new_sentence = _add_ack(new_sentence, sentence2.get(_ACK))
        assert _has_ack(new_sentence)
    if _has_anti_ack(sentence2):
        new_sentence = _add_anti_ack(new_sentence, sentence2.get(_ANTI_ACK))
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
    if _has_anti_ack(sentence_so_far) and _is_statement(current):
        sentence = gamla.freeze_deep(
            gamla.keyfilter(gamla.not_equals(_ANTI_ACK))(sentence_so_far)
        )
        return _add_constituent(_add_statement(sentence, current), current)
    if _is_statement(current):
        return _add_constituent(_add_statement(sentence_so_far, current), current)
    if (
        _is_anti_ack(current)
        and not _has_statement(sentence_so_far)
        and not _has_ack(sentence_so_far)
    ):
        return _add_constituent(_add_anti_ack(sentence_so_far, current), current)

    if _is_anti_ack(current):
        return sentence_so_far

    if _is_sentence(current):
        if _has_question(sentence_so_far) and _has_question(current):
            return sentence_so_far
        return _merge_sentences(sentence_so_far, current)
    assert False, f"This should cover all cases {current}."


combine = gamla.reduce(_sentence_part_reducer, EMPTY_SENTENCE)
