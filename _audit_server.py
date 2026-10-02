"""Throwaway harness for rendering. Deleted after."""

import asyncio
from pathlib import Path

import uvicorn

from vinted_sniper.config import Settings
from vinted_sniper.db.connection import Database
from vinted_sniper.db.repo import Repo
from vinted_sniper.web.server import create_app

PREVIEW_DB = Path("data/preview.db").resolve()


async def main() -> None:
    settings = Settings(db_path=PREVIEW_DB, web_auth_token="audit-token", web_port=8124)
    async with Database(settings.db_path) as db:
        app = create_app(settings, Repo(db))
        config = uvicorn.Config(app, host="127.0.0.1", port=8124, log_config=None, access_log=False)
        await uvicorn.Server(config).serve()


if __name__ == "__main__":
    asyncio.run(main())
