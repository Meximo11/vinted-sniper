"""The Telegram bot, which exists mostly to solve one annoying problem.

Telegram bots cannot message someone first, so before we can send you anything we need your
chat id — and asking people to find their own numeric chat id is where most setup guides
lose them. Instead the app prints a link, you tap it, the bot receives `/start` with a
one-time code, and it records the chat itself. Works the same for a group or a forum topic.

Beyond that it answers `/status`, so you can ask whether everything is still running without
opening the web UI.
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
import time
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from vinted_sniper.db.repo import Repo
from vinted_sniper.engine import health
from vinted_sniper.log import get_logger

log = get_logger(__name__)

# Long enough that a code cannot be guessed, short enough to paste into a URL.
_CODE_BYTES = 8

# A pairing code that goes unused expires, so a link left in a chat log is not a way in.
PAIRING_TTL_S = 1800


def new_pairing_code() -> str:
    return secrets.token_urlsafe(_CODE_BYTES)


async def create_pairing(repo: Repo, name: str) -> tuple[int, str]:
    """Set up a Telegram destination waiting for someone to claim it.

    Asking for a link twice — because the first one expired, or went to the wrong chat —
    refreshes the code on the destination already waiting rather than leaving a second one
    behind. Otherwise the searches stay routed to the abandoned one and the new link
    connects you to a destination nothing feeds.
    """
    code = new_pairing_code()
    config = {"pairing_code": code, "created_at": int(time.time())}

    for destination in await repo.list_destinations():
        if destination.kind == "telegram" and destination.config.get("pairing_code"):
            await repo.update_destination_config(destination.id, config)
            return destination.id, code

    destination_id = await repo.add_destination(kind="telegram", name=name, config=config)
    return destination_id, code


async def claim_pairing(repo: Repo, code: str, chat_id: int, thread_id: int | None) -> int | None:
    """Bind a waiting destination to the chat that presented the code."""
    for destination in await repo.list_destinations():
        config: dict[str, Any] = destination.config
        if destination.kind != "telegram" or config.get("pairing_code") != code:
            continue
        if int(time.time()) - int(config.get("created_at", 0)) > PAIRING_TTL_S:
            return None
        new_config = {"chat_id": str(chat_id)}
        if thread_id is not None:
            new_config["message_thread_id"] = str(thread_id)
        await repo.update_destination_config(destination.id, new_config)

        # Anything queued while this chat did not exist yet is not news to whoever just
        # connected — it is a wall of alerts for listings they never asked about. They want
        # what turns up from now on.
        dropped = await repo.discard_pending_for(
            destination.id, "queued before the chat was connected"
        )
        if dropped:
            log.info("telegram.backlog_dropped", destination_id=destination.id, count=dropped)
        return destination.id
    return None


async def _pending_pairing_exists(repo: Repo) -> bool:
    return any(
        destination.kind == "telegram" and destination.config.get("pairing_code")
        for destination in await repo.list_destinations()
    )


def build_dispatcher(repo: Repo) -> Dispatcher:
    dispatcher = Dispatcher()

    @dispatcher.message(Command("start"))
    async def handle_start(message: Message, command: CommandObject) -> None:
        code = (command.args or "").strip()
        if not code:
            # Typing /start by hand is the common way to arrive here: the code travels in
            # the link, so a typed command carries nothing to match against.
            waiting = await _pending_pairing_exists(repo)
            extra = (
                "\n\nEs wartet eine Verknüpfung. Öffne den Link, den vinted-sniper "
                "ausgegeben hat, oder sende:\n/start <den Code aus diesem Link>"
                if waiting
                else "\n\nFühre `vinted-sniper pair-telegram` aus und öffne den Link, den es "
                "ausgibt, in dem Chat, in dem du Meldungen möchtest."
            )
            await message.answer(f"Hallo. Dieser Bot verschickt Vinted-Meldungen.{extra}")
            return

        thread_id = message.message_thread_id
        destination_id = await claim_pairing(repo, code, message.chat.id, thread_id)
        if destination_id is None:
            await message.answer(
                "Dieser Link ist abgelaufen oder wurde schon benutzt. Erzeuge in "
                "vinted-sniper einen neuen und versuche es noch einmal."
            )
            return

        log.info("telegram.paired", destination_id=destination_id, chat_id=message.chat.id)
        await message.answer(
            "Verbunden. Passende Artikel kommen ab jetzt hier an.\n"
            "Sende jederzeit /status, um zu prüfen, ob alles noch läuft."
        )

    @dispatcher.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(
            "/status: Läuft noch alles?\n"
            "/start <Code>: verbindet diesen Chat mit vinted-sniper\n\n"
            "Suchen und Empfänger verwaltest du in vinted-sniper selbst."
        )

    @dispatcher.message(Command("status"))
    async def handle_status(message: Message) -> None:
        await message.answer(await _status_text(repo), parse_mode="HTML")

    @dispatcher.message(F.text)
    async def handle_anything_else(message: Message) -> None:
        await message.answer("Ich verstehe /status und /help.")

    return dispatcher


def _ago(then: int | None) -> str:
    """How long ago, in the words the interface is written in.

    Kept local rather than shared with the dashboard's `_age`: the two read for
    different jobs. This one answers a single operator question about one clock,
    and importing the web module would point the bot back at the layer that
    serves it.
    """
    if then is None:
        return "nie"
    return f"vor {int(time.time() - then)} s"


async def _status_text(repo: Repo) -> str:
    snapshot = await health.snapshot(repo)
    if not snapshot.searches:
        return "Noch keine Suche angelegt."

    lines = ["<b>vinted-sniper</b>", "Läuft." if snapshot.alive else "Antwortet nicht."]
    for search in snapshot.searches:
        line = (
            f"• {search.name} ({search.state_label}), "
            f"zuletzt geprüft {_ago(search.last_success_at)}"
        )
        if search.state == "failing" and search.last_error:
            line += f"\n  {search.last_error[:120]}"
        lines.append(line)

    if snapshot.queued_notifications:
        lines.append(f"{snapshot.queued_notifications} Meldungen warten noch auf den Versand.")
    return "\n".join(lines)


async def run_bot(token: str, *, repo: Repo, stop: asyncio.Event) -> None:
    """Poll Telegram for commands until the app shuts down."""
    bot = Bot(token=token)
    dispatcher = build_dispatcher(repo)

    polling = asyncio.create_task(dispatcher.start_polling(bot, handle_signals=False))
    try:
        await stop.wait()
    finally:
        await dispatcher.stop_polling()
        polling.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling
        await bot.session.close()
