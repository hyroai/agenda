import asyncio
import logging
import sys
import traceback

import fastapi
import gamla
import immutables
import uvicorn
from computation_graph import graph
from starlette import websockets
from uvicorn.main import Server

from agenda import composers, sentence
from config_to_bot import resolvers, yaml_to_bot


def _bot_utterance(utterance, state):
    return {
        "type": "botUtterance",
        "utterance": utterance,
        **({"state": state} if state else {}),
    }


def _error_message(error):
    return {"type": "botError", "message": str(error), "trace": traceback.format_exc()}


def _create_socket_handler(path: str):
    async def message_handler(websocket: fastapi.WebSocket):
        state: dict = {}
        bot = yaml_to_bot.yaml_to_slot_bot(path)()

        @gamla.excepts(
            Exception,
            gamla.compose_left(gamla.side_effect(logging.exception), _error_message),
        )
        async def responder_with_state(request):
            nonlocal state
            nonlocal bot

            if request["type"] == "reload":
                state = {}
                bot = yaml_to_bot.yaml_to_slot_bot(path)()
                return _bot_utterance("Reloading bot", None)
            if request["type"] == "reset":
                state = {}
                return _bot_utterance("Starting Over", None)

            state = await bot(state, {composers.event: request["utterance"]})
            return _bot_utterance(
                state[graph.make_computation_node(composers.utter)],
                gamla.pipe(
                    graph.make_computation_node(resolvers.debug_states),
                    gamla.dict_to_getter_with_default({}, state),
                    gamla.valmap(
                        gamla.valmap(
                            gamla.case_dict(
                                {
                                    gamla.equals(composers.UNKNOWN): gamla.just(None),
                                    gamla.is_instance(
                                        immutables.Map
                                    ): gamla.compose_left(
                                        gamla.itemgetter("text"),
                                        gamla.when(
                                            gamla.is_instance(sentence.GenericAck),
                                            gamla.just(""),
                                        ),
                                    ),
                                    gamla.just(True): gamla.identity,
                                }
                            )
                        )
                    ),
                ),
            )

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
