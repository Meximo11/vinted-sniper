"""How the poller behaves when things go wrong.

These are the cases that decide whether the app survives a week unattended, so they run
against the real poller, session manager and database rather than stand-ins.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest

from tests.conftest import ScriptedTransport
from vinted_sniper.config import Settings
from vinted_sniper.db.repo import Repo
from vinted_sniper.engine.poller import Poller
from vinted_sniper.vinted.client import VintedClient
from vinted_sniper.vinted.proxies import ProxyRotation
from vinted_sniper.vinted.session import SessionManager
from vinted_sniper.vinted.transport import Response, TransportPool


async def make_poller(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    *,
    db: Any,
    max_total_price: str | None = None,
) -> tuple[Poller, asyncio.Event]:
    query_id = await repo.add_query(
        name="test search",
        url="https://www.vinted.fr/catalog?search_text=nike",
        tld="fr",
        params={"search_text": "nike", "order": "newest_first"},
        poll_interval_s=60,
        max_total_price=Decimal(max_total_price) if max_total_price else None,
    )
    query = await repo.get_query(query_id)
    assert query is not None
    return poller_for(query, transport, repo, settings, db=db)


def poller_for(
    query: Any,
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    *,
    db: Any,
) -> tuple[Poller, asyncio.Event]:
    """Build a poller over an existing search, as a restarted process would."""
    sessions = SessionManager(db, transport)
    client = VintedClient(transport, sessions)
    work = asyncio.Event()
    poller = Poller(
        query,
        repo=repo,
        client=client,
        sessions=sessions,
        settings=settings,
        stop=asyncio.Event(),
        work_available=work,
    )
    return poller, work


async def test_empty_results_are_a_success_not_a_failure(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any
) -> None:
    poller, work = await make_poller(transport, repo, settings, db=db)
    transport.queue_catalog([])

    delay = await poller.tick()

    state = await repo.get_state(poller.query.id)
    assert state.last_status == "ok"
    assert state.last_success_at is not None
    assert await repo.outbox_depth() == 0
    assert not work.is_set()
    assert delay >= settings.poll_default_interval_s


async def test_first_check_records_without_announcing(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    poller, work = await make_poller(transport, repo, settings, db=db)
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    transport.queue_catalog([make_item(i, photo_ts=now - i) for i in range(1, 6)])

    await poller.tick()

    assert await repo.outbox_depth() == 0, "a new search must not replay the catalog"
    assert len(await repo.known_item_ids([1, 2, 3, 4, 5])) == 5, "but it must remember them"
    assert not work.is_set()


async def test_first_check_in_newest_mode_announces_exactly_one(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    """A regression guard.

    The whole page has to be recorded so none of it is ever mistaken for new, but only one
    listing may be announced. Queueing a notification per recorded listing is exactly the
    opening flood this mode exists to avoid, and it is an easy mistake to make because the
    two lists differ only here.
    """
    poller, _ = await make_poller(
        transport, repo, settings.model_copy(update={"first_run_mode": "newest"}), db=db
    )
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    # Includes listings far outside the freshness window, as a real first page does.
    transport.queue_catalog([make_item(i, photo_ts=now - i * 3600) for i in range(1, 31)])

    await poller.tick()

    assert await repo.outbox_depth() == 1
    assert len(await repo.known_item_ids(list(range(1, 31)))) == 30

    queued = await repo.claim_batch(destination_id, 50)
    assert [n.item.item_id for n in queued] == [1], "the newest listing, and only that"


async def test_only_listings_newer_than_the_last_check_are_announced(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    poller, work = await make_poller(transport, repo, settings, db=db)
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    transport.queue_catalog([make_item(1, photo_ts=now - 300)])
    await poller.tick()
    assert await repo.outbox_depth() == 0

    # The same listing again, plus one genuinely new one.
    transport.queue_catalog([make_item(2, photo_ts=now - 10), make_item(1, photo_ts=now - 300)])
    await poller.tick()

    assert await repo.outbox_depth() == 1
    assert work.is_set()


async def test_a_blocked_request_backs_off_and_replaces_the_session(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)
    transport.queue_status(403, "Forbidden")
    homepage_visits_before = sum(1 for r in transport.requests if "/api/v2/" not in r["url"])

    delay = await poller.tick()

    state = await repo.get_state(poller.query.id)
    assert state.last_status == "http_403"
    assert state.count_403 == 1
    assert delay > settings.poll_default_interval_s, "a block must slow us down, not speed us up"

    homepage_visits_after = sum(1 for r in transport.requests if "/api/v2/" not in r["url"])
    assert homepage_visits_after > homepage_visits_before, (
        "being refused should start a fresh session rather than reuse the refused one"
    )

    # And the search keeps running rather than dying.
    transport.queue_catalog([])
    assert await poller.tick() > 0
    assert (await repo.get_state(poller.query.id)).last_status == "ok"


async def test_a_blocked_proxy_is_set_aside_and_the_next_one_is_used(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any, tmp_path: Any
) -> None:
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text("http://one.test\nhttp://two.test")
    rotation = ProxyRotation.from_file(proxy_file)

    query_id = await repo.add_query(
        name="proxied",
        url="https://www.vinted.fr/catalog?search_text=x",
        tld="fr",
        params={"search_text": "x"},
        poll_interval_s=60,
    )
    query = await repo.get_query(query_id)
    assert query is not None

    sessions = SessionManager(db, TransportPool(lambda _proxy: transport), proxies=rotation)
    poller = Poller(
        query,
        repo=repo,
        client=VintedClient(None, sessions),
        sessions=sessions,
        settings=settings,
        stop=asyncio.Event(),
    )

    transport.queue_status(403, "Forbidden")
    await poller.tick()

    assert rotation.available() == 1, "the route that was refused should sit out"


async def test_backoff_grows_with_repeated_blocks(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)

    delays = []
    for _ in range(3):
        transport.queue_status(403, "Forbidden")
        delays.append(await poller.tick())

    assert delays[0] < delays[1] < delays[2]


async def test_rate_limiting_waits_exactly_as_long_as_asked(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)
    transport.queue_status(429, "slow down", **{"retry-after": "42"})

    delay = await poller.tick()

    assert delay == 42.0
    state = await repo.get_state(poller.query.id)
    assert state.count_429 == 1
    assert await db.fetch_one("SELECT 1 FROM sessions WHERE tld = 'fr'") is not None, (
        "a rate limit is not a reason to throw away a working session"
    )


async def test_an_expired_token_is_replaced_and_the_next_check_works(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)

    # Vinted reports this inside a 200 body as well as with a 401.
    transport.queue(_json_response({"code": 100, "message": "invalid_authentication_token"}))
    delay = await poller.tick()

    assert (await repo.get_state(poller.query.id)).last_status == "http_401"
    assert delay <= 60, "a stale token should be retried promptly, not backed off"
    assert await db.fetch_one("SELECT 1 FROM sessions WHERE tld = 'fr'") is None

    transport.queue_catalog([make_item(1, photo_ts=int(time.time()))])
    await poller.tick()
    assert (await repo.get_state(poller.query.id)).last_status == "ok"


async def test_a_response_that_is_not_a_catalog_is_reported_not_announced(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any
) -> None:
    poller, work = await make_poller(transport, repo, settings, db=db)
    transport.queue_status(200, "<html>are you a robot?</html>")

    await poller.tick()

    state = await repo.get_state(poller.query.id)
    assert state.last_status == "malformed"
    assert state.last_error is not None
    assert await repo.outbox_depth() == 0
    assert not work.is_set()


async def test_listings_over_the_total_price_limit_are_skipped(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db, max_total_price="20")
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    transport.queue_catalog([make_item(1, photo_ts=now - 600)])
    await poller.tick()

    # 18.00 asking price becomes 20.50 with buyer protection, which is over the limit even
    # though Vinted's own price filter would have let it through.
    transport.queue_catalog(
        [make_item(2, photo_ts=now, price="18.0"), make_item(3, photo_ts=now, price="10.0")]
    )
    await poller.tick()

    queued = await repo.claim_batch(destination_id, 10)
    assert [n.item.item_id for n in queued] == [3]


async def test_a_restart_does_not_resend_what_was_already_sent(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    transport.queue_catalog([make_item(1, photo_ts=now - 500)])
    await poller.tick()

    transport.queue_catalog([make_item(2, photo_ts=now - 5)])
    await poller.tick()
    first_batch = await repo.claim_batch(destination_id, 10)
    await repo.mark_sent([n.outbox_id for n in first_batch])

    # A fresh poller over the same database, as if the process had restarted.
    restarted, _ = poller_for(poller.query, transport, repo, settings, db=db)
    transport.queue_catalog([make_item(2, photo_ts=now - 5)])
    await restarted.tick()

    assert await repo.outbox_depth() == 0


def _json_response(payload: dict[str, Any]) -> Response:
    return Response(status_code=200, text=json.dumps(payload), headers={}, cookies={})


@pytest.mark.parametrize("status", [500, 502, 503])
async def test_server_errors_are_transient(
    transport: ScriptedTransport, repo: Repo, settings: Settings, db: Any, status: int
) -> None:
    poller, _ = await make_poller(transport, repo, settings, db=db)
    transport.queue_status(status, "oops")

    delay = await poller.tick()

    assert delay > 0
    assert (await repo.get_state(poller.query.id)).last_status == "network"


async def test_newest_mode_announces_one_listing_and_then_only_new_ones(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    """The smoke test must stay a smoke test.

    FIRST_RUN_MODE=newest promises one listing so you can see delivery works. If the
    first check also announced anything else — or if later checks kept announcing from
    the first page — the promise is worthless and the flood it exists to prevent is back.
    """
    poller, _ = await make_poller(
        transport, repo, settings.model_copy(update={"first_run_mode": "newest"}), db=db
    )
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    now = int(time.time())
    transport.queue_catalog([make_item(i, photo_ts=now - i * 3600) for i in range(1, 31)])
    await poller.tick()
    assert await repo.outbox_depth() == 1, "the smoke test is exactly one notification"

    # Second check, same page. Nothing here is new, so nothing should be announced.
    transport.queue_catalog([make_item(i, photo_ts=now - i * 3600) for i in range(1, 31)])
    await poller.tick()
    assert await repo.outbox_depth() == 1, "the shelf must not be re-announced"


async def test_a_search_that_fails_then_recovers_is_still_a_first_run(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    """A first check that errored never seeded anything, so the next one is still the first.

    is_first_run is derived from last_success_at, which a failure leaves alone. Getting
    this wrong the other way would announce the whole catalog to someone whose first poll
    was a 403.
    """
    poller, _ = await make_poller(
        transport, repo, settings.model_copy(update={"first_run_mode": "newest"}), db=db
    )
    destination_id = await repo.add_destination(kind="webhook", name="test", config={"url": "x"})
    await repo.route(poller.query.id, destination_id)

    transport.queue_status(403, "blocked")
    await poller.tick()

    now = int(time.time())
    transport.queue_catalog([make_item(i, photo_ts=now - i * 3600) for i in range(1, 6)])
    await poller.tick()

    queued = await repo.claim_batch(destination_id, 50)
    assert [n.item.item_id for n in queued] == [1], "still the first successful check"


async def test_a_search_added_while_the_app_runs_gets_its_own_smoke_test(
    transport: ScriptedTransport,
    repo: Repo,
    settings: Settings,
    db: Any,
    make_item: Callable[..., dict[str, Any]],
) -> None:
    """Each search is first-run on its own terms, not once per process.

    FIRST_RUN_MODE is a per-setting, but the seed is per-search: a search added to a
    running app has never been seeded, so it gets its one listing like any other.
    """
    newest = settings.model_copy(update={"first_run_mode": "newest"})
    first, _ = await make_poller(transport, repo, newest, db=db)
    first_destination = await repo.add_destination(
        kind="webhook", name="first", config={"url": "x"}
    )
    await repo.route(first.query.id, first_destination)

    now = int(time.time())
    transport.queue_catalog([make_item(i, photo_ts=now - i * 3600) for i in range(1, 4)])
    await first.tick()

    second_id = await repo.add_query(
        name="second search",
        url="https://www.vinted.fr/catalog?search_text=adidas",
        tld="fr",
        params={"search_text": "adidas", "order": "newest_first"},
        poll_interval_s=60,
    )
    second_query = await repo.get_query(second_id)
    assert second_query is not None
    second, _ = poller_for(second_query, transport, repo, newest, db=db)
    second_destination = await repo.add_destination(
        kind="webhook", name="second", config={"url": "y"}
    )
    await repo.route(second.query.id, second_destination)
    transport.queue_catalog([make_item(100 + i, photo_ts=now - i * 3600) for i in range(1, 4)])
    await second.tick()

    queued = await repo.claim_batch(second_destination, 50)
    assert len(queued) == 1, "a new search gets its own smoke test"
