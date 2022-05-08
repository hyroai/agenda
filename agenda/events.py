import dataclasses


@dataclasses.dataclass(frozen=True)
class ConversationEvent:
    type: str


def conversation_start():
    return ConversationEvent("CONVERSATION_START")
