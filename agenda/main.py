import asyncio
import sys
from typing import Callable, Any, Dict

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


def _create_socket_handler(path: str):
    async def message_handler(websocket: fastapi.WebSocket):
        state: dict = {}
        bot = config_to_bot.yaml_to_slot_bot(path)()

        async def responder_with_state(request):
            nonlocal state
            nonlocal bot
            if request.lower() == "reload":
                bot = config_to_bot.yaml_to_slot_bot(path)()
                state = {}
                return "Reloading bot"
            if request.lower() == "start over":
                state = {}
                return "Starting Over"
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


async def _make_app(path: str) -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.websocket("/converse")(_create_socket_handler(path))
    original_handler = Server.handle_exit

    async def handle_exit(*args, **kwargs):
        original_handler(*args, **kwargs)

    def exit(*args, **kwargs):
        asyncio.ensure_future(handle_exit(*args, **kwargs))

    Server.handle_exit = exit
    return app


def app(path: str):
    return asyncio.get_event_loop().run_until_complete(_make_app(path))


if __name__ == "__main__":
    uvicorn.run(
        app(sys.argv[1]),
        host="0.0.0.0",
        port=9000,
        log_level="debug",
        timeout_keep_alive=1200,
    )
