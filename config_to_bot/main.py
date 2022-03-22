import asyncio
import logging
import os
import traceback

import fastapi
import gamla
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


def _create_socket_handler():
    async def message_handler(websocket: fastapi.WebSocket):
        state: dict = {}
        bot = None

        @gamla.excepts(
            Exception,
            gamla.compose_left(gamla.side_effect(logging.exception), _error_message),
        )
        async def responder_with_state(request):
            nonlocal state
            nonlocal bot
            if request["type"] == "configuration":
                state = {}
                bot = yaml_to_bot.yaml_to_slot_bot(request["data"])()
            if request["type"] == "reset":
                state = {}
                return _bot_utterance("Starting Over", None)
            if not bot:
                return _error_message(
                    "You must provide a yaml in order to build a bot."
                )
            if request["type"] == "userUtterance":
                state = await bot(state, {composers.event: request["utterance"]})
                return _bot_utterance(
                    state[graph.make_computation_node(composers.utter)],
                    gamla.pipe(
                        graph.make_computation_node(resolvers.debug_states),
                        gamla.dict_to_getter_with_default({}, state),
                        gamla.valmap(
                            gamla.valmap(
                                gamla.when(
                                    sentence.is_sentence_or_part,
                                    yaml_to_bot.sentence_to_str,
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


async def _make_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.websocket("/converse")(_create_socket_handler())
    original_handler = Server.handle_exit

    async def handle_exit(*args, **kwargs):
        original_handler(*args, **kwargs)

    def exit(*args, **kwargs):
        asyncio.ensure_future(handle_exit(*args, **kwargs))

    Server.handle_exit = exit
    return app


def main():
    uvicorn.run(
        asyncio.get_event_loop().run_until_complete(_make_app()),
        host="0.0.0.0",
        port=int(os.environ.get("AGENDA_DEBUGGER_BACKEND_PORT", "9000")),
        log_level="debug",
        timeout_keep_alive=1200,
    )


if __name__ == "__main__":
    main()
