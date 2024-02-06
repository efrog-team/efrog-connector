from fastapi import WebSocket
from asyncio import Event
from copy import deepcopy

class CurrentWebSocket():
    def __init__(self, websocket: WebSocket | None, flag: Event | None, messages: list[str]) -> None:
        self.websocket: WebSocket | None = websocket
        self.flag: Event | None = flag
        self.messages = deepcopy(messages)
        self.messages_index = 0

    async def safe_send_text(self, text: str) -> bool:
        if self.websocket is not None:
            try:
                await self.websocket.send_text(text)
                return True
            except:
                self.websocket = None
                self.flag = None
                return False
        else:
            return False

    async def send_accumulated(self) -> None:
        while self.messages_index < len(self.messages):
            if not await self.safe_send_text(self.messages[self.messages_index]):
                break
            self.messages_index += 1

    async def send_message(self, message: str) -> None:
        self.messages.append(message)
        await self.send_accumulated()

    def safe_set_flag(self) -> bool:
        if self.flag is not None:
            try:
                self.flag.set()
                return True
            except:
                return False
        else:
            return False