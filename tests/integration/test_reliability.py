"""Reliability fixes: stranded notifications, sessions that lose their route, filters.

Each test here covers a specific failure that was possible before, and each names the
behaviour it protects rather than the function it calls.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from pathlib import Path

from tests.conftest import ScriptedTransport
from vinted_sniper.config import Settings
from vinted_sniper.db import Database
from vinted_sniper.db.repo import Query, Repo
from vinted_sniper.deliver.dispatcher import Dispatcher
from vinted_sniper.engine import filters
from vinted_sniper.vinted.models import Item
from vinted_sniper.vinted.proxies import ProxyRotation
from vinted_sniper.vinted.session import SessionManager
from vinted_sniper.vinted.transport import TransportPool

# --- Outbox leases ------------------------------------------------------------------


async def _a_claimed_notification(repo: Repo) -> tuple[int, int]:
    """A search and a destination with one notification claimed but never resolved."""
    query_id = await repo.add_query(
        name="test",
        url="https://www.vinted.fr/catalog?search_text=x",
        tld="fr",
        params={},
        poll_interval_s=60,
    )
    query = await repo.get_query(query_id)
    assert query is not None
    destination_id = await repo.add_destination(
        kind="webhook", name="sink", config={"url": "http://127.0.0.1:9/hook"}
    )
    await repo.record_new_items(
        query,
        [
            Item(
                item_id=1,
                tld="fr",
                title="Item 1",
                url="https://www.vinted.fr/items/1",
                price=Decimal("10.00"),
                photo_ts=int(time.time()),
            )
        ],
        [destination_id],
    )
    await repo.claim_batch(destination_id, 10)
    return query_id, destination_id


async def test_a_claimed_notification_sits_in_sending_until_its_lease_ends(
    repo: Repo,
) -> None:
    await _a_claimed_notification(repo)

    assert await repo.recover_expired_leases() == 0
    assert await repo.destinations_with_work() == [], "a live lease is not yet recoverable"


async def test_an_expired_lease_puts_the_notification_back_in_the_queue(repo: Repo) -> None:
    _, destination_id = await _a_claimed_notification(repo)
    db = repo._db  # the test asserts on stored state on purpose
    await db.execute("UPDATE outbox SET lease_expires_at = 1 WHERE status = 'sending'")

    assert await repo.recover_expired_leases() == 1
    assert await repo.destinations_with_work() == [destination_id]


async def test_a_recovered_notification_can_be_claimed_again(repo: Repo) -> None:
    _, destination_id = await _a_claimed_notification(repo)
    db = repo._db
    await db.execute("UPDATE outbox SET lease_expires_at = 1 WHERE status = 'sending'")
    await repo.recover_expired_leases()

    batch = await repo.claim_batch(destination_id, 10)

    assert [notification.outbox_id for notification in batch] == [1]


async def test_a_lease_still_in_flight_is_left_alone(repo: Repo) -> None:
    await _a_claimed_notification(repo)
    db = repo._db
    await db.execute(
        "UPDATE outbox SET lease_expires_at = ? WHERE status = 'sending'",
        (int(time.time()) + 300,),
    )

    assert await repo.recover_expired_leases() == 0
    assert await repo.outbox_depth() == 1


async def test_the_dispatcher_recovers_a_stranded_send_during_a_normal_run(
    repo: Repo, settings: Settings
) -> None:
    """The case that mattered: a worker died mid-send and nothing else noticed.

    Recovery at startup cannot help, because the process is perfectly healthy. The
    destination simply stops receiving anything, silently, until someone restarts.
    """
    _, destination_id = await _a_claimed_notification(repo)
    db = repo._db
    await db.execute("UPDATE outbox SET lease_expires_at = 1 WHERE status = 'sending'")

    dispatcher = Dispatcher(
        repo=repo,
        settings=settings,
        stop=asyncio.Event(),
        work_available=asyncio.Event(),
    )
    try:
        await dispatcher.drain()
    finally:
        await dispatcher.aclose()

    row = await db.fetch_one("SELECT status FROM outbox WHERE id = 1")
    assert row is not None
    assert row["status"] in ("pending", "failed", "sent"), row["status"]
    assert (await repo.get_destination(destination_id)) is not None


# --- Session proxy persistence ------------------------------------------------------


def _proxies(tmp_path: Path) -> ProxyRotation:
    path = tmp_path / "proxies.txt"
    path.write_text("http://one.test:8080\nhttp://two.test:8080\n", encoding="utf-8")
    return ProxyRotation.from_file(path)


async def test_a_session_keeps_its_route_across_a_restart(
    db: Database, tmp_path: Path, transport: ScriptedTransport
) -> None:
    """A cookie minted through a proxy must not be replayed direct after a restart."""
    proxies = _proxies(tmp_path)
    pool = TransportPool(lambda _proxy: transport)
    first = SessionManager(db, pool, proxies=proxies)
    await first.get("fr")
    assert first._cache["fr"].proxy is not None, "the fixture must actually route through a proxy"

    # A brand new manager over the same database stands in for the next process.
    second = SessionManager(db, pool, proxies=proxies)
    session = await second.get("fr")

    assert session.proxy == first._cache["fr"].proxy


async def test_a_session_created_directly_stays_direct(db: Database) -> None:
    manager = SessionManager(db, ScriptedTransport())
    await manager.get("fr")

    assert (await SessionManager(db, ScriptedTransport()).get("fr")).proxy is None


async def test_the_stored_route_is_the_one_the_transport_is_taken_from(
    db: Database, tmp_path: Path, transport: ScriptedTransport
) -> None:
    """Not just remembered — actually used to pick the client for the request."""
    proxies = _proxies(tmp_path)
    built_for: list[str | None] = []

    def build(proxy: str | None) -> ScriptedTransport:
        built_for.append(proxy)
        return transport

    pool = TransportPool(build)
    await SessionManager(db, pool, proxies=proxies).get("fr")
    route_when_minted = built_for[-1]
    assert route_when_minted is not None, "the fixture must actually route through a proxy"
    client_when_minted = pool.get(route_when_minted)

    manager = SessionManager(db, pool, proxies=proxies)
    session = await manager.get("fr")

    assert session.proxy == route_when_minted, "the reloaded session changed route"
    assert manager.transport_for(session) is client_when_minted


# --- Filters ------------------------------------------------------------------------


def _query(**kwargs: object) -> Query:
    defaults: dict[str, object] = {
        "id": 1,
        "name": "test",
        "url": "https://www.vinted.fr/catalog?search_text=x",
        "tld": "fr",
        "params": {},
        "poll_interval_s": 60,
        "paused": False,
    }
    defaults.update(kwargs)
    return Query(**defaults)  # type: ignore[arg-type]


def _item(**kwargs: object) -> Item:
    defaults: dict[str, object] = {
        "item_id": 1,
        "tld": "fr",
        "title": "Item 1",
        "url": "https://www.vinted.fr/items/1",
    }
    defaults.update(kwargs)
    return Item(**defaults)  # type: ignore[arg-type]


def test_a_listing_with_no_condition_is_dropped_said_too_honestly() -> None:
    rejection = filters.check(_item(condition=None), _query(conditions=["New"]))

    assert rejection is not None
    assert rejection.reason == "condition_unknown"
    assert "does not state a condition" in rejection.detail


def test_a_listing_with_an_unwanted_condition_is_rejected_as_before() -> None:
    rejection = filters.check(_item(condition="Worn"), _query(conditions=["New"]))

    assert rejection is not None
    assert rejection.reason == "condition"


def test_a_listing_with_no_condition_is_kept_when_no_conditions_were_asked_for() -> None:
    """The optional-filter case: narrowing nothing must not narrow anything."""
    assert filters.check(_item(condition=None), _query()) is None
