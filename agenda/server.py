from typing import Any, Callable

import agenda
import logging
import fastapi
import gamla
from starlette import websockets


def _error_message(error):
    return {"type": "error", "data": str(error)}


def create_socket_handler(bot: Callable):
    async def message_handler(websocket: fastapi.WebSocket):
        state: Any = None

        async def responder_with_state(request):
            nonlocal state
            try:
                computation_result = await bot(event=request, state=state)
                state = computation_result.state
                return agenda.extract_utterance(computation_result.result)
            except Exception as err:
                logging.exception(err)
                return _error_message(err)

        await websocket.accept()
        while True:
            try:
                await gamla.pipe(
                    await websocket.receive_json(),
                    gamla.throttle(
                        1, gamla.compose_left(responder_with_state, websocket.send_json)
                    ),
                )
            except websockets.WebSocketDisconnect:
                break

    return message_handler
