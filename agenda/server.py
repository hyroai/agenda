from typing import Any, Callable

import agenda
import logging
import fastapi
import gamla
from starlette import websockets
from computation_graph import graph
from agenda import composers


def _error_message(error):
    return {"type": "error", "data": str(error)}


def create_socket_handler(bot: Callable):
    async def message_handler(websocket: fastapi.WebSocket):
        state: dict = {}

        async def responder_with_state(request):
            nonlocal state
            try:
                computation_result = await bot({composers.event: request, **state})
                state = computation_result
                return state[graph.make_computation_node(composers.utter)]
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
