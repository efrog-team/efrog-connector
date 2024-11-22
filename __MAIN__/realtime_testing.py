from asyncio import Event
from copy import deepcopy
from typing import Any

class RealtimeTesting():

    def __init__(self, messages: list[str] = []) -> None:
        self.new_messages_flag = Event()
        self.messages = deepcopy(messages)
        self.messages_index = 0
        self.opened_websocket = False
        self.finished = False

    def add_message(self, message: str) -> None:
        self.messages.append(message)
        self.new_messages_flag.set()

    def get_unsent_messages(self) -> list[str]:
        unsent_messages: list[str] = self.messages[self.messages_index:]
        self.messages_index = len(self.messages)
        self.new_messages_flag.clear()
        return unsent_messages

    def to_json(self) -> dict[str, Any]:
        return {
            'new_messages_flag': self.new_messages_flag.is_set(),
            'messages': self.messages,
            'messages_index': self.messages_index,
            'opened_websocket': self.opened_websocket,
            'finished': self.finished
        }