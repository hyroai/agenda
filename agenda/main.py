import asyncio
import sys
from typing import Callable, Any

import config_to_bot
import fastapi
import gamla
import logging
import uvicorn
from agenda import composers
from uvicorn.main import Server
from starlette import websockets
from computation_graph import graph


def _error_message(error):
    return {"type": "error", "data": str(error)}


def _create_socket_handler(bot: Callable):
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


async def _make_app(bot: Callable) -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.websocket("/converse")(_create_socket_handler(bot()))
    original_handler = Server.handle_exit

    async def handle_exit(*args, **kwargs):
        original_handler(*args, **kwargs)

    def exit(*args, **kwargs):
        asyncio.ensure_future(handle_exit(*args, **kwargs))

    Server.handle_exit = exit
    return app


def app(path: str):
    return asyncio.get_event_loop().run_until_complete(
        _make_app(config_to_bot.yaml_to_slot_bot(path))
    )


if __name__ == "__main__":
    uvicorn.run(
        app(sys.argv[1]),
        host="0.0.0.0",
        port=9000,
        log_level="debug",
        timeout_keep_alive=1200,
    )
