import asyncio
import sys
from typing import Callable

import config_to_bot
import fastapi
import gamla
from agenda import server
import uvicorn
from uvicorn.main import Server


async def _make_app(bot: Callable) -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.websocket("/converse")(server.create_socket_handler(bot()))
    original_handler = Server.handle_exit

    async def _handle_exit(*args, **kwargs):
        original_handler(*args, **kwargs)

    def _exit(*args, **kwargs):
        asyncio.ensure_future(_handle_exit(*args, **kwargs))

    Server.handle_exit = _exit
    return app


def app(path: str):
    return asyncio.get_event_loop().run_until_complete(
        gamla.compose_left(
            gamla.just(path), config_to_bot.yaml_to_slot_bot, _make_app
        )()
    )


if __name__ == "__main__":
    uvicorn.run(
        app(sys.argv[1]),
        host="0.0.0.0",
        port=9000,
        log_level="debug",
        timeout_keep_alive=1200,
    )
