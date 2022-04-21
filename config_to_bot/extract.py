import datetime
import re
from typing import Callable, Iterable, Tuple, Union, cast

import dateparser
import gamla
import number_parser
import pyap
import spacy

import agenda

_nlp = spacy.load("en_core_web_lg")


def _remove_punctuation(text: str) -> str:
    return re.sub(r"[.,!?;]", "", text)


def _analyze(text: str):
    return _nlp(text)


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
    "i disagree",
    "disagree",
}


def _sentences_similarity(user_utterance: str, examples: Tuple[str, ...]) -> float:
    user_sentence = _analyze(user_utterance)
    return gamla.pipe(
        examples,
        gamla.map(
            gamla.compose_left(
                _analyze, lambda sentence: sentence.similarity(user_sentence)
            )
        ),
        gamla.sort,
        gamla.last,
    )


def faq_score(question: str, user_utternace: str) -> float:
    return gamla.pipe(
        user_utternace,
        _analyze,
        lambda sentence: sentence.similarity(_analyze(question)),
    )


email: Callable[[str], str] = gamla.compose_left(
    _analyze,
    gamla.filter(gamla.attrgetter("like_email")),
    gamla.map(gamla.attrgetter("text")),
    tuple,
    gamla.ternary(gamla.nonempty, gamla.head, gamla.just(agenda.UNKNOWN)),
)

phone: Callable[[str], str] = gamla.compose_left(
    gamla.regex_match(re.compile(r"((?:\(\d{3}\) ?|\d{3}-?)?\d{3}[- ]?\d{4})")),
    gamla.ternary(
        gamla.identity, gamla.apply_method("group", 1), gamla.just(agenda.UNKNOWN)
    ),
)

person_name: Callable[[str], str] = gamla.compose_left(
    _remove_punctuation,
    _analyze,
    tuple,
    gamla.filter(
        gamla.compose_left(gamla.attrgetter("ent_type_"), gamla.equals("PERSON"))
    ),
    gamla.map(gamla.attrgetter("text")),
    tuple,
    " ".join,
    gamla.when(gamla.equals(""), gamla.just(agenda.UNKNOWN)),
)


address: Callable[[str], str] = gamla.compose_left(
    lambda user_utterance: pyap.parse(user_utterance, country="US"),
    gamla.ternary(
        gamla.nonempty,
        gamla.compose_left(gamla.head, gamla.attrgetter("full_address")),
        gamla.just(agenda.UNKNOWN),
    ),
)


_text_to_lower_case_words: Callable[[str], Iterable[str]] = gamla.compose_left(
    lambda text: re.findall(r"[\w']+|[.,!?;]", text.lower())
)


def intent(examples: Tuple[str, ...]) -> Callable[[str], bool]:
    def parse_bool(user_utterance: str):
        return bool(examples) and _sentences_similarity(user_utterance, examples) >= 0.9

    return parse_bool


def yes_no(user_utterance: str):
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


def multiple_choices(
    options: Tuple[str, ...]
) -> Callable[[str], Tuple[str, agenda.Unknown]]:
    return gamla.compose_left(
        _text_to_lower_case_words,
        gamla.filter(gamla.contains([*options, "none"])),
        tuple,
        gamla.when(gamla.empty, gamla.just(agenda.UNKNOWN)),
        gamla.when(
            gamla.alljuxt(
                gamla.is_instance(tuple),
                gamla.len_equals(1),
                gamla.compose_left(gamla.head, gamla.equals("none")),
            ),
            gamla.just(()),
        ),
    )


_single_timeslot_or_unknown = gamla.ternary(
    gamla.len_equals(1),
    gamla.compose_left(gamla.head, gamla.apply_method("isoformat")),
    gamla.just(agenda.UNKNOWN),
)


def datetime_choice(options, relative_to):
    def extract_datetime_choice(user_utterance: str) -> Union[str, agenda.Unknown]:
        d = future_date(relative_to, user_utterance)
        t = time(relative_to, user_utterance)
        if agenda.UNKNOWN not in (d, t):
            choice = datetime.datetime.combine(
                cast(datetime.date, d), cast(datetime.time, t)
            )
            return choice.isoformat() if choice in options else agenda.UNKNOWN

        if d is not agenda.UNKNOWN:
            return gamla.pipe(
                options,
                gamla.filter(lambda o: o.date() == cast(datetime.date, d)),
                tuple,
                _single_timeslot_or_unknown,
            )
        if t is not agenda.UNKNOWN:
            return gamla.pipe(
                options,
                gamla.filter(lambda o: o.time().hour == cast(datetime.time, t).hour),
                tuple,
                _single_timeslot_or_unknown,
            )

        return agenda.UNKNOWN

    return extract_datetime_choice


def single_choice(options: Tuple[str, ...]) -> Callable[[str], str]:
    return gamla.compose_left(
        _text_to_lower_case_words,
        gamla.filter(gamla.contains(options)),
        tuple,
        gamla.ternary(gamla.len_equals(1), gamla.head, gamla.just(agenda.UNKNOWN)),
    )


amount = gamla.compose_left(
    _remove_punctuation,
    number_parser.parse_number,
    gamla.unless(gamla.identity, gamla.just(agenda.UNKNOWN)),
)


def amount_of(noun: str):
    analyzed_noun = _analyze(noun)

    def amount_of(user_utterance):
        return gamla.pipe(
            user_utterance,
            _remove_punctuation,
            number_parser.parse,
            _analyze,
            gamla.filter(lambda t: t.similarity(analyzed_noun) > 0.5),
            gamla.mapcat(gamla.attrgetter("children")),
            gamla.filter(
                gamla.compose_left(gamla.attrgetter("dep_"), gamla.equals("nummod"))
            ),
            gamla.map(gamla.attrgetter("text")),
            tuple,
            gamla.ternary(
                gamla.len_greater(0),
                gamla.compose_left(gamla.head, number_parser.parse_number),
                gamla.just(agenda.UNKNOWN),
            ),
        )

    return amount_of


def _parse_datetime(relative_to):
    def parse_datetime(date_str):
        return dateparser.parse(
            date_str,
            settings={
                "RELATIVE_BASE": relative_to,
                "PREFER_DATES_FROM": "future",
                "TIMEZONE": "UTC",
            },
        )

    return parse_datetime


def _entities_of_type(date):
    return gamla.compose_left(
        _analyze,
        gamla.attrgetter("ents"),
        gamla.filter(
            gamla.compose_left(gamla.attrgetter("label_"), gamla.equals(date))
        ),
    )


def future_date(
    relative_to: datetime.datetime, user_utterance
) -> Union[datetime.date, agenda.Unknown]:
    return gamla.pipe(
        user_utterance,
        _entities_of_type("DATE"),
        gamla.map(
            gamla.compose_left(gamla.attrgetter("text"), _parse_datetime(relative_to))
        ),
        gamla.filter(gamla.identity),
        gamla.excepts(
            StopIteration,
            gamla.just(agenda.UNKNOWN),
            gamla.compose_left(gamla.head, gamla.apply_method("date")),
        ),
    )


def time(
    relative_to: datetime.datetime, user_utterance
) -> Union[datetime.time, agenda.Unknown]:
    return gamla.pipe(
        user_utterance,
        _entities_of_type("TIME"),
        gamla.map(
            gamla.compose_left(gamla.attrgetter("text"), _parse_datetime(relative_to))
        ),
        gamla.filter(gamla.identity),
        gamla.excepts(
            StopIteration,
            gamla.just(agenda.UNKNOWN),
            gamla.compose_left(gamla.head, gamla.apply_method("time")),
        ),
    )
