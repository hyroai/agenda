import dataclasses
from typing import Optional


@dataclasses.dataclass(frozen=True)
class UserUtterance:
    utterance: str


@dataclasses.dataclass(frozen=True)
class ConversationEvent:
    type: str
    data: Optional[UserUtterance]


def user_utterance(input_event):
    return ConversationEvent("USER_UTTERANCE", UserUtterance(input_event))


def conversation_start():
    return ConversationEvent("CONVERSATION_START", None)
