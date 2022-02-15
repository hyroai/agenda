import asyncio
import logging
import sys

import fastapi
import gamla
import uvicorn
from computation_graph import graph
from starlette import websockets
from uvicorn.main import Server

import config_to_bot
from agenda import composers


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
                return {"botUtterance": "Reloading bot"}
            if request.lower() == "reset":
                state = {}
                return {"botUtterance": "Starting Over"}
            try:
                state = await bot(state, {composers.event: request})
                return {
                    "botUtterance": state[graph.make_computation_node(composers.utter)],
                    "state": gamla.pipe(
                        graph.make_computation_node(composers.debug_states),
                        gamla.dict_to_getter_with_default({}, state),
                        gamla.valmap(
                            gamla.when(
                                gamla.equals(composers.UNKNOWN), gamla.just(None)
                            )
                        ),
                    ),
                }
            except Exception as err:
                logging.exception(err)
                return gamla.wrap_tuple(_error_message(err))

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
