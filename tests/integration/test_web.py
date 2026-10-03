"""The dashboard.

Worth testing properly because it is the part most people will actually touch, and because
it holds webhook URLs and chat ids — so "is it locked" is a correctness question.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.conftest import ScriptedTransport
from vinted_sniper.config import Settings
from vinted_sniper.db import Database
from vinted_sniper.db.repo import Repo
from vinted_sniper.vinted.models import parse_item
from vinted_sniper.vinted.session import SessionManager
from vinted_sniper.vinted.taxonomy import Taxonomy
from vinted_sniper.vinted.transport import Response
from vinted_sniper.web.server import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    _masked_target,
    create_app,
)

TOKEN = "test-token-please-ignore"


@pytest.fixture
def web_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        db_path=tmp_path / "app.db",
        web_enabled=True,
        web_auth_token=SecretStr(TOKEN),
    )


@pytest.fixture
def client(web_settings: Settings, repo: Repo) -> Iterator[TestClient]:
    with TestClient(create_app(web_settings, repo)) as test_client:
        yield test_client


def _arm_csrf(client: TestClient) -> TestClient:
    """Do what a browser does: load a page, then keep its token for later posts.

    The token is sent as a header rather than a form field, which is the channel a
    script uses; the field in every template is the same value and is covered by its
    own test below.
    """
    client.get("/login")
    client.headers[CSRF_HEADER] = client.cookies.get(CSRF_COOKIE) or ""
    return client


@pytest.fixture
def signed_in(client: TestClient) -> TestClient:
    _arm_csrf(client)
    client.cookies.set(SESSION_COOKIE, TOKEN)
    return client


# --- Access -------------------------------------------------------------------------


def test_the_dashboard_sends_you_to_the_login_page(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/health"),
        ("post", "/searches"),
        ("post", "/destinations"),
        ("post", "/searches/1/delete"),
    ],
)
def test_nothing_useful_works_without_the_token(client: TestClient, method: str, path: str) -> None:
    response = getattr(client, method)(path, follow_redirects=False)

    assert response.status_code in (401, 303, 422)
    assert response.status_code != 200


def test_the_wrong_token_is_refused(client: TestClient) -> None:
    response = client.post("/login", data={"access_token": "not-it"}, follow_redirects=False)

    assert response.status_code == 401
    assert SESSION_COOKIE not in response.cookies


def test_the_right_token_signs_you_in(client: TestClient) -> None:
    response = client.post("/login", data={"access_token": TOKEN}, follow_redirects=False)

    assert response.status_code == 303
    assert response.cookies[SESSION_COOKIE] == TOKEN


def test_the_health_check_needs_no_token(client: TestClient) -> None:
    """The container's health check has no way to sign in."""
    response = client.get("/healthz")

    assert response.status_code in (200, 503)
    assert "alive" in response.json()


def test_a_url_that_matches_nothing_gets_the_german_error_page(signed_in: TestClient) -> None:
    """A mistyped URL is typed by a human, so it gets a page and not a JSON blob.

    The router raises Starlette's HTTPException, which is not the subclass FastAPI raises
    from a route — registering the handler on the subclass alone left this path answering
    `{"detail": "Not Found"}` in English.
    """
    response = signed_in.get("/gibt-es-diese-seite-nicht", headers={"accept": "text/html"})

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "Diese Seite gibt es nicht." in response.text
    assert "Zurück zur Übersicht" in response.text
    assert "Not Found" not in response.text


def test_the_api_still_answers_with_json_for_an_unknown_route(signed_in: TestClient) -> None:
    """The page is for browsers; the builder fetches with fetch() and wants JSON."""
    response = signed_in.get("/gibt-es-diese-seite-nicht", headers={"accept": "application/json"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_without_a_token_the_dashboard_is_open(tmp_path: Path, repo: Repo) -> None:
    """The default for a localhost dashboard: no password, no sign-in page."""
    settings = Settings(_env_file=None, db_path=tmp_path / "a.db", web_enabled=True)  # type: ignore[call-arg]

    with TestClient(create_app(settings, repo)) as client:
        _arm_csrf(client)
        assert client.get("/", follow_redirects=False).status_code == 200
        assert client.get("/api/health").status_code == 200
        # The sign-in page has nothing to ask for, so it sends you to the dashboard.
        assert client.get("/login", follow_redirects=False).status_code == 303


async def test_without_a_token_the_feed_needs_no_key(tmp_path: Path, repo: Repo) -> None:
    settings = Settings(_env_file=None, db_path=tmp_path / "b.db", web_enabled=True)  # type: ignore[call-arg]

    with TestClient(create_app(settings, repo)) as client:
        _arm_csrf(client)
        client.post(
            "/searches",
            data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
            follow_redirects=False,
        )
        query_id = (await repo.list_queries())[0].id
        assert client.get(f"/rss/{query_id}.xml").status_code == 200


# --- Using it -----------------------------------------------------------------------


async def test_adding_a_search_by_pasting_a_url(signed_in: TestClient, repo: Repo) -> None:
    response = signed_in.post(
        "/searches",
        data={
            "url": "https://www.vinted.fr/catalog?search_text=nike+air&price_to=40&time=999",
            "name": "",
            "interval": "60",
            "max_total_price": "25",
            "banned_keywords": "replica, fake",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    # The JSON answer is an addition to this endpoint; the no-JavaScript path has
    # to keep redirecting to the flash it always did.
    assert "ok=" in response.headers["location"]
    searches = await repo.list_queries()
    assert len(searches) == 1
    assert searches[0].tld == "fr"
    assert searches[0].max_total_price is not None
    assert searches[0].banned_keywords == ["replica", "fake"]
    assert "time=999" not in searches[0].url, "tracking parameters should not survive"


async def test_a_url_that_is_not_a_search_is_rejected_with_advice(
    signed_in: TestClient, repo: Repo
) -> None:
    response = signed_in.post(
        "/searches", data={"url": "https://example.com/nope"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert await repo.list_queries() == []


# --- The same endpoint, asked for data instead of a page ---------------------------
#
# `data-report-done` in the template posts this form with fetch so the button can
# finish its own sentence instead of being thrown away by a redirect. The name the
# button then shows has to be the server's: one written in the browser would be a
# name the server never agreed to.


async def test_starting_a_search_answers_a_fetch_with_the_name_it_created(
    signed_in: TestClient, repo: Repo
) -> None:
    response = signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    # Exactly the name the flash would have carried, and nothing else: the button
    # reads one field, so a second one would only be a promise nobody keeps.
    assert response.json() == {"name": (await repo.list_queries())[0].name}


@pytest.mark.parametrize(
    "url,status",
    [
        ("https://example.com/nope", 422),
        ("https://www.vinted.fr/catalog?search_text=nike", 409),
    ],
)
async def test_a_refused_search_answers_a_fetch_with_a_status_and_a_reason(
    signed_in: TestClient, url: str, status: int
) -> None:
    """The client falls back to a real form post on any non-2xx, and the reason it
    falls back has to be the server's, not a guess made in the browser."""
    if status == 409:
        signed_in.post("/searches", data={"url": url})

    response = signed_in.post(
        "/searches", data={"url": url}, headers={"Accept": "application/json"}
    )

    assert response.status_code == status
    assert response.json()["error"]


async def test_the_same_search_cannot_be_added_twice(signed_in: TestClient, repo: Repo) -> None:
    payload = {"url": "https://www.vinted.fr/catalog?search_text=nike"}
    signed_in.post("/searches", data=payload, follow_redirects=False)
    response = signed_in.post("/searches", data=payload, follow_redirects=False)

    assert "error=" in response.headers["location"]
    assert len(await repo.list_queries()) == 1


async def test_a_search_below_the_interval_floor_is_raised_to_it(
    signed_in: TestClient, repo: Repo
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "interval": "1"},
        follow_redirects=False,
    )

    searches = await repo.list_queries()
    assert searches[0].poll_interval_s >= 10


async def test_pausing_and_deleting_a_search(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )
    query_id = (await repo.list_queries())[0].id

    signed_in.post(f"/searches/{query_id}/pause", data={"paused": "1"}, follow_redirects=False)
    assert (await repo.list_queries())[0].paused is True

    signed_in.post(f"/searches/{query_id}/delete", follow_redirects=False)
    assert await repo.list_queries() == []


async def test_adding_a_discord_destination(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/destinations",
        data={
            "kind": "discord",
            "name": "my server",
            "target": "https://discord.com/api/webhooks/1/abc",
        },
        follow_redirects=False,
    )

    destinations = await repo.list_destinations()
    assert len(destinations) == 1
    assert destinations[0].config["webhook_url"].startswith("https://discord.com/")


async def test_a_discord_destination_that_is_not_a_url_is_refused(
    signed_in: TestClient, repo: Repo
) -> None:
    response = signed_in.post(
        "/destinations",
        data={"kind": "discord", "name": "typo", "target": "my-webhook"},
        follow_redirects=False,
    )

    assert "error=" in response.headers["location"]
    assert await repo.list_destinations() == []


async def test_the_dashboard_shows_what_is_being_watched(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "my search"},
        follow_redirects=False,
    )

    body = signed_in.get("/").text

    assert "my search" in body
    assert "vinted.fr" in body


async def test_found_listings_render_as_cards_with_their_gallery(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "my search"},
        follow_redirects=False,
    )
    query = (await repo.list_queries())[0]
    item = parse_item(make_item(123, photo_ts=1_755_000_000), "fr")
    await repo.record_new_items(query, [item], [])

    body = signed_in.get("/").text

    assert "listing-grid" in body
    # The whole gallery travels to the page so the lightbox needs no more requests.
    assert "https://images.vinted.net/123.jpeg" in body
    assert "123-back.jpeg" in body
    # The photo-count badge: the icon, then how many. It used to carry a "▣" glyph as
    # well, which was a font substitution pretending to be an icon. The class is
    # photo-count, not count: `count` also lives on the nav badge, so asserting the
    # short name here passed for a year on a number that had nothing to do with photos.
    assert '<span class="photo-count">' in body
    assert ">2</span>" in body
    assert "@seller" in body
    assert "★ 4.5" in body  # feedback_reputation 0.9, on the five-star scale
    assert "Nike" in body


def test_the_health_api_answers_with_the_snapshot(signed_in: TestClient) -> None:
    body = signed_in.get("/api/health").json()

    assert set(body) >= {"alive", "searches", "queued_notifications"}


async def test_the_rss_feed_needs_the_token(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )
    query_id = (await repo.list_queries())[0].id

    assert signed_in.get(f"/rss/{query_id}.xml").status_code == 401

    response = signed_in.get(f"/rss/{query_id}.xml?key={TOKEN}")
    assert response.status_code == 200
    assert response.text.startswith("<?xml")


# --- The advanced-search builder ------------------------------------------------------


@pytest.fixture
def builder_client(
    web_settings: Settings, db: Database, repo: Repo, transport: ScriptedTransport
) -> Iterator[TestClient]:
    """A dashboard wired to a taxonomy service that talks to a scripted Vinted."""
    taxonomy = Taxonomy(SessionManager(db, transport), repo)
    with TestClient(create_app(web_settings, repo, taxonomy)) as test_client:
        _arm_csrf(test_client)
        test_client.cookies.set(SESSION_COOKIE, TOKEN)
        yield test_client


def _page_with_tree() -> Response:
    payload = {
        "CSRF_TOKEN": "11112222-3333-4444",
        "catalogTree": [{"id": 1904, "title": "Women", "catalogs": []}],
    }
    html = f"<script>self.__next_f.push([1,{json.dumps(json.dumps(payload))}])</script>"
    return Response(status_code=200, text=html, headers={}, cookies={"access_token_web": "t"})


def test_the_search_page_offers_the_builder_when_the_service_is_wired(
    builder_client: TestClient, signed_in: TestClient
) -> None:
    # The builder lives on /searches. It used to also be pasted into the bottom of
    # the dashboard, where the primary verb of the whole tool sat below the fold and
    # a scroll-jump away. The question this test asks is unchanged: does the
    # assembler appear when the taxonomy service answers, and stay away when it
    # does not.
    assert "Selbst zusammenstellen" in builder_client.get("/searches").text
    assert "Selbst zusammenstellen" not in signed_in.get("/searches").text


def test_the_filter_endpoints_need_a_login(client: TestClient) -> None:
    for path in (
        "/api/filters/fr/categories",
        "/api/filters/fr/brands?q=nike",
        "/api/filters/fr/facets/status",
    ):
        assert client.get(path).status_code == 401, path


def test_without_the_service_the_builder_answers_503(signed_in: TestClient) -> None:
    assert signed_in.get("/api/filters/fr/categories").status_code == 503


def test_categories_come_back_as_a_tree(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    transport.queue_root(_page_with_tree())  # session bootstrap
    transport.queue_root(_page_with_tree())  # the page that carries the tree

    response = builder_client.get("/api/filters/fr/categories")

    assert response.status_code == 200
    assert response.json() == {"categories": [{"id": 1904, "title": "Women", "children": []}]}


def test_an_unknown_site_is_refused_before_talking_to_vinted(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    assert builder_client.get("/api/filters/xx/categories").status_code == 404
    assert transport.requests == []


def test_a_short_brand_query_is_answered_locally(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    response = builder_client.get("/api/filters/fr/brands?q=n")

    assert response.json() == {"brands": []}
    assert transport.requests == []


def test_brands_pass_through_with_ids_and_counts(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    transport.queue(
        Response(
            status_code=200,
            text=json.dumps({"brands": [{"id": 53, "title": "Nike", "item_count": 9}]}),
            headers={},
            cookies={},
        )
    )

    response = builder_client.get("/api/filters/fr/brands?q=nike")

    assert response.json() == {"brands": [{"id": 53, "title": "Nike", "count": 9}]}


def test_junk_in_catalog_ids_never_reaches_vinted(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    transport.queue_root(_page_with_tree())
    transport.queue_root(_page_with_tree())
    transport.queue(
        Response(status_code=200, text=json.dumps({"options": []}), headers={}, cookies={})
    )

    builder_client.get("/api/filters/fr/brands?q=nike&catalog_ids=12,drop%20table,34")

    # The picker still speaks `catalog_ids`; the filter service it forwards to calls it
    # `catalog`. What matters here is that the junk never survives either way.
    assert transport.requests[-1]["params"]["catalog"] == "12,34"


def test_an_unknown_facet_is_a_404(builder_client: TestClient) -> None:
    assert builder_client.get("/api/filters/fr/facets/shoe_smell").status_code == 404


def test_a_refusal_from_vinted_surfaces_as_a_502_with_the_reason(
    builder_client: TestClient, transport: ScriptedTransport
) -> None:
    transport.queue_root(_page_with_tree())
    transport.queue_root(_page_with_tree())
    transport.queue_status(403, "blocked")

    response = builder_client.get("/api/filters/fr/facets/status")

    assert response.status_code == 502
    assert "error" in response.json()


# --- The newer pages -----------------------------------------------------------------


@pytest.mark.parametrize("path", ["/searches", "/destinations", "/activity"])
def test_every_page_needs_a_login(client: TestClient, path: str) -> None:
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize("path", ["/searches", "/destinations", "/activity"])
def test_every_page_renders_when_signed_in(signed_in: TestClient, path: str) -> None:
    response = signed_in.get(path)

    assert response.status_code == 200
    assert "<nav" in response.text


async def test_the_searches_page_offers_an_editor_for_each_search(
    signed_in: TestClient, repo: Repo
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "my search"},
        follow_redirects=False,
    )

    body = signed_in.get("/searches").text

    assert "my search" in body
    assert "Bearbeiten" in body
    assert "data-disclosure" in body


async def test_editing_a_search_saves_the_new_details(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "before"},
        follow_redirects=False,
    )
    destination_id = await repo.add_destination(
        kind="discord",
        name="hook",
        config={"webhook_url": "https://discord.com/api/webhooks/1/abc"},
    )
    query_id = (await repo.list_queries())[0].id
    await repo.route(query_id, destination_id)

    response = signed_in.post(
        f"/searches/{query_id}/edit",
        data={
            "name": "after",
            "interval": "300",
            "max_total_price": "42",
            "banned_keywords": "replica",
            "destination_ids": str(destination_id),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "ok=" in response.headers["location"]
    saved = await repo.get_query(query_id)
    assert saved is not None
    assert saved.name == "after"
    assert saved.poll_interval_s == 300
    assert saved.max_total_price == Decimal("42")
    assert saved.banned_keywords == ["replica"]
    assert await repo.destination_ids_for_query(query_id) == [destination_id]


async def test_editing_a_search_replaces_its_routing(signed_in: TestClient, repo: Repo) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )
    query_id = (await repo.list_queries())[0].id
    await repo.route(
        query_id,
        await repo.add_destination(
            kind="discord",
            name="hook",
            config={"webhook_url": "https://discord.com/api/webhooks/1/abc"},
        ),
    )

    signed_in.post(
        f"/searches/{query_id}/edit",
        data={"name": "kept", "destination_ids": []},
        follow_redirects=False,
    )

    assert await repo.destination_ids_for_query(query_id) == []


async def test_editing_below_the_interval_floor_keeps_the_floor(
    signed_in: TestClient, repo: Repo
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )
    query_id = (await repo.list_queries())[0].id

    signed_in.post(
        f"/searches/{query_id}/edit",
        data={"name": "x", "interval": "1"},
        follow_redirects=False,
    )

    saved = await repo.get_query(query_id)
    assert saved is not None
    assert saved.poll_interval_s >= 10


async def test_editing_a_search_that_is_gone_says_so(signed_in: TestClient) -> None:
    response = signed_in.post("/searches/9999/edit", data={"name": "ghost"}, follow_redirects=False)

    assert response.status_code == 303
    assert "error=" in response.headers["location"]


async def test_the_destinations_page_never_shows_the_secret_half_of_a_webhook(
    signed_in: TestClient, repo: Repo
) -> None:
    secret = "https://discord.com/api/webhooks/123/supersecretvalue"
    await repo.add_destination(kind="discord", name="hook", config={"webhook_url": secret})

    body = signed_in.get("/destinations").text

    assert "supersecretvalue" not in body
    # Enough of the address survives to tell two webhooks apart, no more.
    assert "discord.com" in body
    assert "123" not in body.split("</body>")[0].split('class="target"')[1][:80]


def test_a_webhook_url_is_masked_at_the_middle() -> None:
    masked = _masked_target({"webhook_url": "https://discord.com/api/webhooks/123/supersecret"})

    assert "supersecret" not in masked
    # The tail of a Discord URL is the credential, so it is not shown either.
    assert not masked.endswith("cret")


def test_a_telegram_destination_shows_its_chat_id_in_full() -> None:
    # A chat id is not a secret, and hiding it would make the page useless.
    assert _masked_target({"chat_id": "-1001234567890"}) == "-1001234567890"


def test_a_destination_with_nothing_configured_says_so() -> None:
    assert _masked_target({}) == "not configured"


async def test_a_disabled_destination_offers_a_reconnect_and_says_why(
    signed_in: TestClient, repo: Repo
) -> None:
    destination_id = await repo.add_destination(
        kind="telegram", name="my bot", config={"chat_id": "-1001234567890"}
    )
    await repo.deactivate_destination(destination_id, "bot blocked the chat")

    body = signed_in.get("/destinations").text

    assert "Wieder verbinden" in body
    assert "bot blocked the chat" in body
    assert f"/destinations/{destination_id}/reactivate" in body


async def test_reconnecting_a_destination_turns_it_back_on(
    signed_in: TestClient, repo: Repo
) -> None:
    destination_id = await repo.add_destination(
        kind="telegram", name="my bot", config={"chat_id": "-1001234567890"}
    )
    await repo.deactivate_destination(destination_id, "gone")

    response = signed_in.post(f"/destinations/{destination_id}/reactivate", follow_redirects=False)

    assert response.status_code == 303
    assert "ok=" in response.headers["location"]
    restored = await repo.get_destination(destination_id)
    assert restored is not None
    assert restored.active is True
    assert restored.deactivated_reason is None


@pytest.mark.parametrize("posted,expected", [("1", True), ("0", False)], ids=["on", "off"])
async def test_operational_notices_can_be_switched_per_destination(
    signed_in: TestClient, repo: Repo, posted: str, expected: bool
) -> None:
    destination_id = await repo.add_destination(
        kind="telegram", name="my bot", config={"chat_id": "-1001234567890"}
    )

    response = signed_in.post(
        f"/destinations/{destination_id}/notify-status",
        data={"notify_status": posted},
        follow_redirects=False,
    )

    assert "ok=" in response.headers["location"]
    assert (await repo.get_destination(destination_id)).notify_status is expected  # type: ignore[union-attr]


async def test_the_activity_page_shows_a_full_window_of_days(signed_in: TestClient) -> None:
    body = signed_in.get("/activity").text

    assert 'role="img"' in body
    # One chart of fourteen days, two series in every day: the empty days are the
    # point, and a day with only one bar would make the two incomparable again.
    assert body.count("bar-col") == 14
    assert body.count('class="bar ') == 28
    assert body.count('class="bar is-sent') == 14


async def test_the_activity_page_reads_as_history_not_as_monitoring(
    signed_in: TestClient,
) -> None:
    """The page answers "what happened". `count_403`, `count_429` and the checks
    without a find only ever go up — they describe the present, and that is the
    dashboard's job."""
    signed_in.post("/searches", data={"url": "https://www.vinted.fr/catalog?search_text=nike"})
    body = signed_in.get("/activity").text

    for label in ("Blocksperren", "Rate-Limits", "Ohne Treffer"):
        assert label not in body, f"{label} describes the present, not the past"


async def test_the_activity_page_lists_events_newest_first(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """A timeline whose order is wrong is worse than no timeline: it reads as true.
    The SQL orders by the event's own timestamp, and this pins that."""
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "shoes"},
        follow_redirects=False,
    )
    query = (await repo.list_queries())[0]
    now = int(time.time())
    await repo.record_new_items(
        query,
        [parse_item(make_item(i, photo_ts=now), "fr") for i in (1, 2)],
        [],
    )
    # Both rows were stamped with the same instant, which the timeline would read as
    # one run. An hour apart is what two separate events look like, and item 2 is the
    # newer of the two.
    await repo._db.execute("UPDATE items SET first_seen_at = ? WHERE item_id = 1", (now - 3600,))

    body = signed_in.get("/activity").text

    assert body.index("Item 2") < body.index("Item 1")


async def test_a_flash_message_arrives_as_a_query_parameter(signed_in: TestClient) -> None:
    body = signed_in.get("/", params={"ok": "\u201enike\u201c gespeichert."}).text

    assert "\u201enike\u201c gespeichert." in body
    assert 'role="status"' in body or 'class="flash"' in body


# --- Cross-site request forgery ------------------------------------------------------


def test_a_page_hands_out_a_csrf_token(client: TestClient) -> None:
    client.get("/login")

    assert client.cookies.get(CSRF_COOKIE) is not None


async def test_every_form_on_a_signed_in_page_carries_the_token(signed_in: TestClient) -> None:
    signed_in.post(
        "/destinations",
        data={"kind": "discord", "name": "hook", "target": "https://discord.com/api/webhooks/1/a"},
        follow_redirects=False,
    )
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "shoes"},
        follow_redirects=False,
    )

    for path in ("/", "/searches", "/destinations", "/activity"):
        body = signed_in.get(path).text
        for form in re.findall(r"<form\b.*?</form>", body, re.S):
            assert 'name="csrf_token"' in form, f"{path}: {form[:80]}"


def test_the_embedded_token_is_the_one_in_the_cookie(signed_in: TestClient) -> None:
    body = signed_in.get("/").text

    token = signed_in.cookies.get(CSRF_COOKIE)
    assert token is not None and token in body


async def test_a_post_without_a_token_is_refused(client: TestClient, repo: Repo) -> None:
    """The session cookie alone is not consent: any site can make the browser send it."""
    client.cookies.set(SESSION_COOKIE, TOKEN)

    response = client.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert await repo.list_queries() == []


async def test_a_post_with_the_wrong_token_is_refused(client: TestClient, repo: Repo) -> None:
    client.cookies.set(SESSION_COOKIE, TOKEN)
    client.get("/login")
    client.headers[CSRF_HEADER] = "a" * 43  # right length, wrong value

    response = client.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert await repo.list_queries() == []


async def test_a_post_with_the_right_token_goes_through(signed_in: TestClient, repo: Repo) -> None:
    response = signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert len(await repo.list_queries()) == 1


async def test_a_token_in_the_form_field_is_enough_too(signed_in: TestClient, repo: Repo) -> None:
    """Browsers post the field; scripts post the header. Both are the same token."""
    token = signed_in.cookies.get(CSRF_COOKIE)
    assert token is not None
    signed_in.headers.pop(CSRF_HEADER, None)

    response = signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert len(await repo.list_queries()) == 1


@pytest.mark.parametrize(
    "path,data",
    [
        ("/logout", {}),
        ("/searches", {"url": "https://www.vinted.fr/catalog?search_text=nike"}),
        ("/searches/1/edit", {"name": "x"}),
        ("/searches/1/pause", {"paused": "1"}),
        ("/searches/1/delete", {}),
        ("/searches/1/routes", {}),
        (
            "/destinations",
            {"kind": "discord", "name": "n", "target": "https://discord.com/api/webhooks/1/a"},
        ),
        ("/destinations/1/delete", {}),
        ("/destinations/1/reactivate", {}),
        ("/destinations/1/notify-status", {"notify_status": "1"}),
    ],
)
async def test_no_writing_route_is_left_open(
    client: TestClient, repo: Repo, path: str, data: dict[str, str]
) -> None:
    """Every state change is behind the check, including ones added later.

    New buttons are easy to add and easy to forget to protect, so this asks the app
    rather than the source: post at every mutating URL and expect a refusal.
    """
    client.cookies.set(SESSION_COOKIE, TOKEN)
    client.get("/login")

    response = client.post(path, data=data, follow_redirects=False)

    assert response.status_code == 403, path


async def test_a_refused_post_leaves_the_browser_able_to_retry(signed_in: TestClient) -> None:
    """After a 403 the page it goes on to show must still work."""
    token = signed_in.cookies.get(CSRF_COOKIE)
    assert token is not None

    signed_in.headers[CSRF_HEADER] = "wrong"
    signed_in.post("/searches", data={"url": "https://example.com"}, follow_redirects=False)
    signed_in.headers[CSRF_HEADER] = token

    assert (
        signed_in.post(
            "/searches",
            data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
            follow_redirects=False,
        ).status_code
        == 303
    )


async def test_a_planted_short_cookie_is_replaced_not_trusted(
    client: TestClient, repo: Repo
) -> None:
    """Another site can set a cookie on this host's parent domain; a short one is not ours."""
    client.cookies.set(CSRF_COOKIE, "x")
    client.cookies.set(SESSION_COOKIE, TOKEN)

    embedded = re.search(r'name="csrf_token" value="([^"]*)"', client.get("/").text)

    assert embedded is not None
    assert embedded.group(1) != "x"
    assert len(embedded.group(1)) >= 32


async def test_a_refused_post_shows_a_page_rather_than_json(signed_in: TestClient) -> None:
    signed_in.headers[CSRF_HEADER] = "wrong"

    response = signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "Dieses Formular ist abgelaufen." in response.text
    assert "Zurück zur Übersicht" in response.text


async def test_the_json_api_still_answers_with_json(signed_in: TestClient) -> None:
    signed_in.headers[CSRF_HEADER] = "wrong"

    response = signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        headers={"Accept": "application/json"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "detail" in response.json()


# --- Browsing found listings --------------------------------------------------------


async def _fill_with_listings(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]], count: int
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "shoes"},
        follow_redirects=False,
    )
    query = (await repo.list_queries())[0]
    now = int(time.time())
    items = [parse_item(make_item(i, photo_ts=now - i * 60), "fr") for i in range(1, count + 1)]
    await repo.record_new_items(query, items, [])


async def test_the_listing_browser_pages(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """Twenty-five listings at twenty-four a page is two pages, not one long scroll."""
    await _fill_with_listings(signed_in, repo, make_item, 25)

    first = signed_in.get("/listings")
    second = signed_in.get("/listings", params={"page": 2})

    assert first.status_code == 200
    assert first.text.count("<article") == 24
    assert second.text.count("<article") == 1
    assert "25 gefunden" in first.text
    assert 'aria-current="page"' in first.text


async def test_a_page_past_the_end_lands_on_the_last_one(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """Following a stale "next" should not show an empty grid with no way back."""
    await _fill_with_listings(signed_in, repo, make_item, 30)

    body = signed_in.get("/listings", params={"page": 99}).text

    assert "<article" in body
    assert "Seite 2 von 2" in body


async def test_nonsense_page_numbers_are_clamped(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    await _fill_with_listings(signed_in, repo, make_item, 30)

    for bad in ("0", "-5", "not-a-number"):
        assert "<article" in signed_in.get("/listings", params={"page": bad}).text


async def test_pages_do_not_repeat_or_skip_a_listing(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """The ordering has to be total or a listing can fall between two pages.

    first_seen_at is only to the second, so several listings share a timestamp; the id
    tiebreak is what keeps the order from shuffling between requests.
    """
    await _fill_with_listings(signed_in, repo, make_item, 40)

    seen: list[str] = []
    for page in (1, 2):
        body = signed_in.get("/listings", params={"page": page}).text
        seen.extend(re.findall(r'href="(https://www\.vinted\.fr/items/\d+)"', body))

    assert len(seen) == 40
    assert len(set(seen)) == 40, "no listing appears on two pages"


async def test_the_browser_can_be_filtered_by_search(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "shoes"},
        follow_redirects=False,
    )
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=adidas", "name": "trainers"},
        follow_redirects=False,
    )
    now = int(time.time())
    for name, ids in (("shoes", range(1, 6)), ("trainers", range(100, 103))):
        query = next(q for q in await repo.list_queries() if q.name == name)
        await repo.record_new_items(
            query, [parse_item(make_item(i, photo_ts=now), "fr") for i in ids], []
        )

    shoes, trainers = await repo.list_queries()
    body = signed_in.get("/listings", params={"search": shoes.id}).text

    assert "5 gefunden" in body
    assert "shoes" in body
    # The dropdown offers both searches; the grid must only hold the filtered one.
    assert body.count("<article") == 5
    assert trainers.id not in [
        int(m) for m in re.findall(r'href="/listings\?page=2&amp;search=(\d+)', body)
    ]


async def test_the_browser_can_be_searched_by_text(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    await _fill_with_listings(signed_in, repo, make_item, 5)

    body = signed_in.get("/listings", params={"q": "Nike"}).text

    assert "5 gefunden" in body


async def test_a_search_that_matches_nothing_says_so_rather_than_looking_broken(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    await _fill_with_listings(signed_in, repo, make_item, 5)

    body = signed_in.get("/listings", params={"q": "zzz-nothing-matches"}).text

    # The empty state says what happened and offers a way out of it, rather than
    # leaving the reader on a blank grid wondering whether the filter worked.
    assert "Nichts passt dazu" in body
    assert "Filter zurücksetzen" in body
    assert "<article" not in body


async def test_page_links_carry_the_filter_with_them(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """The classic paging bug: narrow it, click next, get the unfiltered page two."""
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike", "name": "shoes"},
        follow_redirects=False,
    )
    query = (await repo.list_queries())[0]
    now = int(time.time())
    await repo.record_new_items(
        query,
        [parse_item(make_item(i, photo_ts=now - i * 60), "fr") for i in range(1, 31)],
        [],
    )

    body = signed_in.get("/listings", params={"search": query.id, "page": 2}).text

    assert f"search={query.id}" in body


async def test_a_search_term_cannot_reach_the_query(
    signed_in: TestClient, repo: Repo, make_item: Callable[..., dict[str, Any]]
) -> None:
    """The wildcards go in the parameter, so a quote in the search box is just text."""
    await _fill_with_listings(signed_in, repo, make_item, 3)

    assert signed_in.get("/listings", params={"q": "' OR 1=1 --"}).status_code == 200
    assert signed_in.get("/listings", params={"q": "%"}).status_code == 200


async def test_the_browser_needs_a_login(client: TestClient) -> None:
    assert client.get("/listings", follow_redirects=False).status_code == 303


async def test_an_empty_browser_explains_itself(signed_in: TestClient) -> None:
    body = signed_in.get("/listings").text

    assert "Noch nichts gefunden" in body
    assert "pager" not in body


# --- Destination delivery panel ------------------------------------------------------


async def _deliver(
    repo: Repo,
    destination_id: int,
    *,
    count: int,
    latency_s: int,
    status: str = "sent",
) -> None:
    """Write finished notifications with a known queue-to-arrival delay.

    item_id is derived from the arguments rather than a counter or a hash: a salted
    hash would give a different answer on every run, and outbox rows are unique on
    (item_id, destination_id), so two calls that collide silently become one.
    """
    now = int(time.time())
    item_id = (destination_id * 10_000 + count * 97 + len(status)) * 100 + 1
    query = (await repo.list_queries())[0]
    for i in range(count):
        await repo._db.execute(
            "INSERT OR IGNORE INTO items (item_id, query_id, tld, url, first_seen_at) "
            "VALUES (?, ?, 'fr', 'https://www.vinted.fr/items/x', ?)",
            (item_id + i, query.id, now),
        )
        await repo._db.execute(
            "INSERT OR IGNORE INTO outbox (item_id, query_id, destination_id, status, "
            "attempts, next_attempt_at, created_at, sent_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (
                item_id + i,
                query.id,
                destination_id,
                status,
                now,
                now - latency_s,
                now if status == "sent" else None,
            ),
        )


async def _destination_with_deliveries(signed_in: TestClient, repo: Repo, **kwargs: Any) -> int:
    signed_in.post(
        "/searches",
        data={"url": "https://www.vinted.fr/catalog?search_text=nike"},
        follow_redirects=False,
    )
    destination_id = await repo.add_destination(
        kind="webhook", name="hook", config={"url": "https://example.com/hook"}
    )
    await _deliver(repo, destination_id, **kwargs)
    return destination_id


async def test_a_healthy_destination_shows_its_wait_and_success_rate(
    signed_in: TestClient, repo: Repo
) -> None:
    await _destination_with_deliveries(signed_in, repo, count=8, latency_s=2)

    body = signed_in.get("/destinations").text

    assert "Wartezeit" in body
    assert "2,0 s" in body
    assert "Angekommen" in body
    assert "delivery-ok" in body


async def test_a_slow_destination_is_flagged(signed_in: TestClient, repo: Repo) -> None:
    """A backlog shows up as a growing wait long before anything fails."""
    await _destination_with_deliveries(signed_in, repo, count=5, latency_s=300)

    body = signed_in.get("/destinations").text

    assert "delivery-slow" in body
    assert "300,0 s" in body


async def test_a_destination_that_keeps_failing_is_flagged(
    signed_in: TestClient, repo: Repo
) -> None:
    await _destination_with_deliveries(signed_in, repo, count=1, latency_s=1)
    await _deliver(
        repo, (await repo.list_destinations())[0].id, count=9, latency_s=1, status="failed"
    )

    body = signed_in.get("/destinations").text

    assert "delivery-failing" in body


async def test_a_destination_with_nothing_sent_says_nothing_wrong(
    signed_in: TestClient, repo: Repo
) -> None:
    """No deliveries is not a claim about delivery, so no numbers are invented."""
    signed_in.post(
        "/destinations",
        data={"kind": "webhook", "name": "fresh", "target": "https://example.com/new"},
        follow_redirects=False,
    )

    body = signed_in.get("/destinations").text

    # The page's explanatory prose names the field; the card must not claim a value.
    assert 'class="delivery ' not in body
    assert "delivery-ok" not in body


async def test_the_median_is_used_not_the_mean(signed_in: TestClient, repo: Repo) -> None:
    """One slow notification should not paint every normal one as slow.

    Nine quick sends and one that took an hour: the mean says a minute, the median says
    what nearly every alert actually experiences.
    """
    destination_id = await _destination_with_deliveries(signed_in, repo, count=9, latency_s=1)
    await _deliver(repo, destination_id, count=1, latency_s=3600)

    body = signed_in.get("/destinations").text

    assert "1,0 s" in body
    assert "delivery-ok" in body, "one slow send should not condemn the destination"
