import asyncio
from vinted_sniper.config import Settings
from vinted_sniper.db import Database, apply_pending
from vinted_sniper.db.repo import Repo

async def main():
    settings = Settings()
    async with Database(settings.db_path) as db:
        await apply_pending(db)
        await Repo(db).route(1, 3)
    print("Fertig: Suche 1 ist mit Telegram-Ziel 3 verknüpft.")

asyncio.run(main())
