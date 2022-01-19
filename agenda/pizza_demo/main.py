import asyncio
import os
from typing import Callable

from agenda import config_to_bot
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


app = asyncio.get_event_loop().run_until_complete(
    gamla.compose_left(
        gamla.just(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "pizza.yaml")
        ),
        config_to_bot.yaml_to_slot_bot,
        _make_app,
    )()
)

if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=9000, log_level="debug", timeout_keep_alive=1200
    )
