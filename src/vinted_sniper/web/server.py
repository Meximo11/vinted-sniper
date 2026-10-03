"""The web UI.

On by default, bound to localhost unless you say otherwise. It exists
because editing a config file is where most people give up: pasting a Vinted URL into a box
is not.

It also answers the question the issue trackers of similar tools are full of — "why did it
stop?" — by showing, per search, when it last succeeded, what the last error was, and
whether the catalog has gone quiet. Nothing here is guessed from silence.

It listens on localhost and opens straight onto the dashboard — nothing to sign in to.
Setting VINTED_SNIPER_WEB_AUTH_TOKEN puts a password on it, which is the right move before
exposing it beyond your own machine: the database holds your webhook URLs and chat ids,
and an open dashboard on a public port would be a way to hand them out.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
import time
from collections import Counter
from collections.abc import Awaitable, Callable, Iterator
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any, Final
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

import uvicorn
from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import SecretStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from vinted_sniper.config import MIN_POLL_INTERVAL_S, Settings
from vinted_sniper.db.repo import DeliveryStats, Query, Repo
from vinted_sniper.engine import health
from vinted_sniper.log import get_logger
from vinted_sniper.vinted import urls
from vinted_sniper.vinted.errors import VintedError
from vinted_sniper.vinted.taxonomy import FACET_CODES, Taxonomy

log = get_logger(__name__)

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
STATIC_DIR = Path(__file__).parent / "static"
SESSION_COOKIE = "vinted_sniper_session"
CSRF_COOKIE = "vinted_sniper_csrf"
CSRF_FIELD = "csrf_token"
# Forms are the normal way in, so the token travels as a field. Fetch/XHR callers send
# the header instead: reading a response body from another origin is not something a
# browser will let them do, so a header is the only channel they could use anyway.
CSRF_HEADER = "x-csrf-token"
# How long a browser may keep a token without asking for another. Same as the session.
CSRF_MAX_AGE_S = 30 * 86_400
# secrets.token_urlsafe(32) is 43 characters. Anything shorter is not ours.
CSRF_MIN_LEN = 32

# How many listings one page of the browser holds. 24 fills a wide grid twice over and
# keeps a page's HTML small enough that the gallery thumbnails do not make it sluggish.
LISTINGS_PER_PAGE = 24

# How long a find stays worth acting on. Fifteen minutes is the window a Vinted drop
# realistically lives: past that the item has been seen by everyone watching the same
# search, and the tool's whole value was catching it early. The listing tile's decay rule
# spends this window — accent at the moment of the catch, neutral at the end of it. It is
# a value, not a law: change it here and every listing surface follows.
DECAY_WINDOW_S = 15 * 60

# What each destination kind is addressed by, and how much of it to show. A webhook URL
# is a credential: anyone holding it can post to your channel, so the dashboard shows
# enough to tell two of them apart and no more.
_TARGET_KEYS = {
    "discord": "webhook_url",
    "telegram": "chat_id",
    "ntfy": "topic",
    "webhook": "url",
}


# Shorter than this and even a partly-shown address gives nothing away, so it is
# hidden entirely rather than trimmed.
_MASK_BELOW = 8
# How much of a webhook address to show. Long enough to name the service and the bot,
# short enough that the credential — which lives in the path — is never on screen.
_MASK_HEAD = 28


def _masked_target(config: dict[str, Any]) -> str:
    """A destination's address, with the secret middle replaced."""
    for key in ("webhook_url", "url", "chat_id", "topic"):
        value = config.get(key)
        if isinstance(value, str) and value:
            if len(value) <= _MASK_BELOW:
                return "•" * len(value)
            if key in ("chat_id", "topic"):
                return value
            # Only the head. The tail of a Discord webhook URL is the token itself, and
            # four characters of it are four characters less entropy for anyone reading
            # over a shoulder or looking at a screen share.
            return f"{value[:_MASK_HEAD]}…" if len(value) > _MASK_HEAD else value
    if config.get("pairing_code"):
        return f"pairing link · {config['pairing_code']}"
    return "not configured"


TEMPLATES.env.filters["masked_target"] = _masked_target


def _csrf_ok(cookie: str | None, supplied: str | None) -> bool:
    if not cookie or not supplied:
        return False
    return secrets.compare_digest(cookie, supplied)


def _looks_like_csrf(token: str | None) -> bool:
    """Whether a cookie already holds a token this app would have minted.

    Anything shorter than what `secrets.token_urlsafe(32)` produces is somebody else's
    cookie — an empty string from a browser that cleared it, or a value planted by
    another site. Either way it is replaced rather than trusted.
    """
    return token is not None and len(token) >= CSRF_MIN_LEN


def _authorised(supplied: str | None, expected: SecretStr | None) -> bool:
    if expected is None:
        return True
    if not supplied:
        return False
    return secrets.compare_digest(supplied, expected.get_secret_value())


def create_app(settings: Settings, repo: Repo, taxonomy: Taxonomy | None = None) -> FastAPI:
    token = settings.web_auth_token  # None means no password: the dashboard just opens

    app = FastAPI(title="vinted-sniper", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def static_files_revalidate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Make the browser ask about the stylesheet and the scripts every time.

        Without this the response carries no Cache-Control, so a browser is free to
        apply heuristic freshness — roughly a tenth of the time since Last-Modified —
        and serve an old stylesheet without asking. On a tool that people run locally
        and restyle, that means editing app.css, pressing reload, and still seeing the
        interface you changed ten minutes ago. `no-cache` does not forbid caching, it
        forbids *using* it without asking; the ETag is still there, so an unchanged file
        costs one 304 and no body.
        """
        if request.url.path.startswith("/static/"):
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-cache"
            return response
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    # Templates ask for "how long ago" constantly, and always against the same instant,
    # so the two are passed together rather than each view re-deriving the clock.
    TEMPLATES.env.globals["_age"] = _age

    async def require_login(
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> None:
        if not _authorised(session, token):
            raise HTTPException(status_code=401, detail="not signed in")

    guard = Depends(require_login)

    async def require_csrf(
        request: Request,
        submitted: Annotated[str | None, Form(alias=CSRF_FIELD)] = None,
    ) -> None:
        """Refuse a state change that did not come from a page we served.

        The session cookie is what makes the browser attach itself to a request, and it
        is attached whether or not the request came from this dashboard. Without this
        check, any page the user visits could quietly pause a search or add a webhook of
        its own by posting to localhost. The token proves the page was rendered here,
        and only a page here can hand it out.
        """
        expected = request.cookies.get(CSRF_COOKIE)
        supplied = submitted or request.headers.get(CSRF_HEADER)
        if not _csrf_ok(expected, supplied):
            raise HTTPException(
                status_code=403,
                detail="Dieses Formular ist abgelaufen. Lade die Seite neu und versuche es erneut.",
            )

    # Declared after `guard` so an anonymous caller still gets a 401 telling it to sign
    # in, rather than a 403 about a token it has never been shown.
    csrf = Depends(require_csrf)

    @app.middleware("http")
    async def _issue_csrf_cookie(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Keep every browser holding a CSRF token, and put it where templates can see it.

        Set before the route runs so a page rendered without one embeds the value that
        is about to be written to the cookie, and written afterwards so a rejected POST
        leaves the browser able to try again.
        """
        cookie = request.cookies.get(CSRF_COOKIE)
        token = cookie if _looks_like_csrf(cookie) else None
        fresh = token is None
        request.state.csrf_token = token = token or secrets.token_urlsafe(32)
        response = await call_next(request)
        if fresh:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                httponly=True,
                samesite="lax",
                max_age=CSRF_MAX_AGE_S,
            )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def _html_errors(request: Request, exc: StarletteHTTPException) -> Response:
        """A refused action gets a page, not a JSON blob: these URLs are typed by hand.

        Registered against Starlette's class rather than FastAPI's, which is a subclass of
        it. The router raises the Starlette one for an unmatched path or a wrong method, and
        a handler keyed on the subclass never sees those — a mistyped URL came back as raw
        `{"detail": "Not Found"}` JSON instead of this page. The routes below still raise
        FastAPI's, which this now catches too. The Accept check keeps the API JSON.
        """
        accepts_html = "text/html" in request.headers.get("accept", "")
        if not accepts_html:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return TEMPLATES.TemplateResponse(
            request,
            "error.html",
            {
                "message": _error_message(str(exc.detail)),
                "status_code": exc.status_code,
                "auth_enabled": token is not None,
            },
            status_code=exc.status_code,
        )

    # --- Health, unauthenticated on purpose: the container check runs it ------------

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        alive = await health.is_alive(repo)
        return JSONResponse({"alive": alive}, status_code=200 if alive else 503)

    # --- Signing in ----------------------------------------------------------------

    @app.get("/login", response_class=HTMLResponse)
    async def login_form(request: Request) -> Response:
        if token is None:
            return RedirectResponse("/", status_code=303)
        return TEMPLATES.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login")
    # Deliberately not behind `csrf`: signing in is the moment before there is anything
    # to protect, and the value being posted is itself the secret. Forcing a victim to
    # sign in only helps an attacker who already knows the token.
    async def login(request: Request, access_token: Annotated[str, Form()]) -> Response:
        if token is None:
            return RedirectResponse("/", status_code=303)
        if not _authorised(access_token, token):
            return TEMPLATES.TemplateResponse(
                request,
                "login.html",
                {"error": "Dieses Token passt nicht."},
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            SESSION_COOKIE,
            access_token,
            httponly=True,
            samesite="lax",
            max_age=30 * 86_400,
        )
        return response

    @app.post("/logout")
    async def logout(_: None = csrf) -> Response:
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    # --- Dashboard -----------------------------------------------------------------

    async def _shell(request: Request, **context: Any) -> dict[str, Any]:
        """The chrome every page shares, gathered in one place.

        The rail shows the queue depth and the search counts, and the body shows
        them again. Reading those from separate queries is how a page ends up
        contradicting itself, so they are fetched once and passed down.

        The running-state figures live here too, for the same reason: there is
        exactly one place in the interface that says whether the thing is alive,
        and it says the same thing on every page.
        """
        snap = context.get("snapshot")
        return {
            "auth_enabled": token is not None,
            "csrf_token": getattr(request.state, "csrf_token", ""),
            "search_counts": await repo.search_counts(),
            "active_destinations": sum(1 for d in await repo.list_destinations() if d.active),
            "unhealthy": (
                sum(1 for s in snap.searches if s.state in ("failing", "stale")) if snap else 0
            ),
            "last_success_at": await repo.last_success_at(),
            **context,
        }

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(
        request: Request,
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Response:
        if not _authorised(session, token):
            return RedirectResponse("/login", status_code=303)

        now = int(time.time())
        snapshot = await health.snapshot(repo)
        destinations = await repo.list_destinations()
        recent = _listing_views(await repo.recent_items(limit=24), now=now)

        return TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            await _shell(
                request,
                nav="dashboard",
                now=now,
                snapshot=snapshot,
                destinations=destinations,
                recent=recent,
                recent_failures=await repo.recent_failures(),
                destinations_off=[d for d in destinations if not d.active],
                **_form_context(settings, snapshot, taxonomy),
            )
            | {
                "found_today": await repo.items_since(now - 86_400),
                "found_week": await repo.items_since(now - 7 * 86_400),
                "outbox": await repo.outbox_status_counts(),
            },
        )

    @app.get("/searches", response_class=HTMLResponse)
    async def searches_page(
        request: Request,
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Response:
        if not _authorised(session, token):
            return RedirectResponse("/login", status_code=303)

        now = int(time.time())
        snapshot = await health.snapshot(repo)
        queries = await repo.list_queries()
        destinations = await repo.list_destinations()

        details: dict[int, Query] = {}
        routes: dict[int, list[int]] = {}
        for query in queries:
            details[query.id] = query
            routes[query.id] = await repo.destination_ids_for_query(query.id)

        return TEMPLATES.TemplateResponse(
            request,
            "searches.html",
            await _shell(
                request,
                nav="searches",
                now=now,
                snapshot=snapshot,
                destinations=destinations,
                search_counts=await repo.search_counts(),
                **_form_context(settings, snapshot, taxonomy),
            )
            | {"details": details, "routes_by_query": routes},
        )

    @app.get("/destinations", response_class=HTMLResponse)
    async def destinations_page(
        request: Request,
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Response:
        if not _authorised(session, token):
            return RedirectResponse("/login", status_code=303)

        snapshot = await health.snapshot(repo)
        destinations = await repo.list_destinations()
        now = int(time.time())
        stats = await repo.destination_delivery_stats()

        return TEMPLATES.TemplateResponse(
            request,
            "destinations.html",
            await _shell(
                request,
                nav="destinations",
                now=now,
                snapshot=snapshot,
                destinations=destinations,
                active_destinations=sum(1 for d in destinations if d.active),
                delivery={
                    d.id: _delivery_view(stats[d.id], now) for d in destinations if d.id in stats
                },
            ),
        )

    @app.get("/listings", response_class=HTMLResponse)
    async def listings_page(
        request: Request,
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
        page: str = "1",
        q: str = "",
        search: int | None = None,
    ) -> Response:
        if not _authorised(session, token):
            return RedirectResponse("/login", status_code=303)

        now = int(time.time())
        snapshot = await health.snapshot(repo)
        queries = await repo.list_queries()

        # A bad page number is a mistyped link, not an attack, so it falls back to the
        # first page instead of answering a browser with a JSON validation error. The
        # clamp has to happen before the query: asking for page 99 of a 2-page list and
        # then discovering the ceiling would render an empty grid.
        wanted = _positive_int(page)
        ceiling = await repo.listing_count(query_id=search, text=q)
        pages = max(1, -(-ceiling // LISTINGS_PER_PAGE))  # ceiling: 25 items, 2.1 pages
        current = min(wanted, pages)
        rows, total = await repo.listing_page(
            page=current, per_page=LISTINGS_PER_PAGE, query_id=search, text=q
        )

        return TEMPLATES.TemplateResponse(
            request,
            "listings.html",
            await _shell(
                request,
                nav="listings",
                now=now,
                snapshot=snapshot,
                listings=_listing_views(rows, now=now),
                total=total,
                page=current,
                pages=pages,
                per_page=LISTINGS_PER_PAGE,
                queries=queries,
                counts=await repo.listing_counts_by_query(),
                filter_query=search,
                filter_text=q.strip(),
            ),
        )

    @app.get("/activity", response_class=HTMLResponse)
    async def activity_page(
        request: Request,
        session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Response:
        if not _authorised(session, token):
            return RedirectResponse("/login", status_code=303)

        now = int(time.time())
        snapshot = await health.snapshot(repo)
        states = {state.query_id: state for state in await repo.all_states()}
        outbox = await repo.outbox_status_counts()

        return TEMPLATES.TemplateResponse(
            request,
            "activity.html",
            await _shell(
                request,
                nav="activity",
                now=now,
                snapshot=snapshot,
                outbox=outbox,
                states=states,
                events=_event_views(await repo.recent_events(), now),
                found_today=await repo.items_since(now - 86_400),
                found_week=await repo.items_since(now - 7 * 86_400),
                listings_series=await repo.listings_per_day(),
                sent_series=await repo.notifications_per_day(),
            ),
        )

    @app.get("/api/health")
    async def api_health(_: None = guard) -> JSONResponse:
        snapshot = await health.snapshot(repo)
        return JSONResponse(snapshot.as_dict())

    # --- Searches ------------------------------------------------------------------

    @app.post("/searches")
    async def add_search(
        request: Request,
        url: Annotated[str, Form()],
        name: Annotated[str, Form()] = "",
        interval: Annotated[int, Form()] = 0,
        max_total_price: Annotated[str, Form()] = "",
        banned_keywords: Annotated[str, Form()] = "",
        destination_ids: Annotated[list[int] | None, Form()] = None,
        _: None = guard,
        __: None = csrf,
    ) -> Response:
        # One endpoint, two answers. A plain form post wants the 303 and the
        # flash; the fetch behind `data-report-done` wants the name back so the
        # button it was pressed on can finish its own sentence.
        wants_json = "application/json" in request.headers.get("accept", "")

        # A refusal tells the fetch path only that it was refused: the status code is
        # the answer, and the reason reaches the user from the flash of the plain
        # post it falls back to.
        try:
            normalised = urls.normalise_search_url(url)
            tld = urls.extract_tld(normalised)
            params = urls.parse_search_params(normalised)
        except urls.InvalidSearchURLError as exc:
            if wants_json:
                return JSONResponse({"error": str(exc)}, status_code=422)
            return _redirect_with_error(str(exc), "/searches")

        if await repo.find_query_by_url(normalised) is not None:
            if wants_json:
                return JSONResponse(
                    {"error": "diese Suche wird bereits beobachtet"}, status_code=409
                )
            return _redirect_with_error("diese Suche wird bereits beobachtet", "/searches")

        query_id = await repo.add_query(
            name=name.strip() or _name_from(params, tld),
            url=normalised,
            tld=tld,
            params=params,
            poll_interval_s=max(interval or settings.poll_default_interval_s, MIN_POLL_INTERVAL_S),
            banned_keywords=[w.strip() for w in banned_keywords.split(",") if w.strip()],
            max_total_price=_decimal_or_none(max_total_price),
        )
        for destination_id in destination_ids or []:
            await repo.route(query_id, destination_id)

        label = name.strip() or _name_from(params, tld)
        if wants_json:
            # Only the name. A search created a moment ago has not been polled, so
            # there is no count to report: anything the button could put on screen
            # here would be a number the database did not produce.
            return JSONResponse({"name": label})
        return _redirect_with_ok(f"„{label}“ wird jetzt beobachtet.")

    @app.post("/searches/{query_id}/edit")
    async def edit_search(
        query_id: int,
        name: Annotated[str, Form()],
        interval: Annotated[int, Form()] = 0,
        max_total_price: Annotated[str, Form()] = "",
        banned_keywords: Annotated[str, Form()] = "",
        destination_ids: Annotated[list[int] | None, Form()] = None,
        _: None = guard,
        __: None = csrf,
    ) -> Response:
        existing = await repo.get_query(query_id)
        if existing is None:
            return _redirect_with_error("diese Suche existiert nicht mehr", "/searches")

        clean_name = name.strip() or existing.name
        await repo.update_query(
            query_id,
            name=clean_name,
            poll_interval_s=max(interval or existing.poll_interval_s, MIN_POLL_INTERVAL_S),
            banned_keywords=[w.strip() for w in banned_keywords.split(",") if w.strip()],
            max_total_price=_decimal_or_none(max_total_price),
        )

        # Routing is replaced wholesale, which is what the checkbox list means: the
        # boxes the user left unticked are the ones that should stop.
        wanted = set(destination_ids or [])
        for destination_id in set(await repo.destination_ids_for_query(query_id)) - wanted:
            await repo.unroute(query_id, destination_id)
        for destination_id in wanted:
            await repo.route(query_id, destination_id)

        return _redirect_with_ok(f"„{clean_name}“ gespeichert.", "/searches")

    @app.post("/searches/{query_id}/pause")
    async def pause_search(
        query_id: int, paused: Annotated[str, Form()], _: None = guard, __: None = csrf
    ) -> Response:
        await repo.set_paused(query_id, paused == "1")
        existing = await repo.get_query(query_id)
        verb = "Fortgesetzt" if paused == "0" else "Angehalten"
        name_of = existing.name if existing else "Suche"
        return _redirect_with_ok(f"„{name_of}“ {verb.lower()}.", "/searches")

    @app.post("/searches/{query_id}/delete")
    async def delete_search(query_id: int, _: None = guard, __: None = csrf) -> Response:
        existing = await repo.get_query(query_id)
        await repo.delete_query(query_id)
        return _redirect_with_ok(
            f"„{existing.name if existing else 'Suche'}“ wird nicht mehr beobachtet.", "/searches"
        )

    # --- Filter data for the advanced search builder -------------------------------
    # Thin JSON pass-throughs the dashboard's picker calls. The taxonomy service does
    # the talking to Vinted; a missing service (bare create_app in tests, or the web UI
    # run without the engine) answers 503 rather than pretending the picker can work.

    def _taxonomy_or_503() -> Taxonomy:
        if taxonomy is None:
            raise HTTPException(status_code=503, detail="the search builder is not available")
        return taxonomy

    def _known_tld(tld: str) -> str:
        if tld not in urls.KNOWN_TLDS:
            raise HTTPException(status_code=404, detail=f"vinted.{tld} is not a known site")
        return tld

    @app.get("/api/filters/{tld}/categories")
    async def filter_categories(tld: str, _: None = guard) -> JSONResponse:
        service = _taxonomy_or_503()
        try:
            tree = await service.categories(_known_tld(tld))
        except VintedError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return JSONResponse({"categories": tree})

    @app.get("/api/filters/{tld}/brands")
    async def filter_brands(
        tld: str, q: str = "", catalog_ids: str = "", _: None = guard
    ) -> JSONResponse:
        service = _taxonomy_or_503()
        if len(q.strip()) < 2:  # noqa: PLR2004 - an autocomplete needs two letters
            return JSONResponse({"brands": []})
        try:
            brands = await service.brands(_known_tld(tld), q, _id_list(catalog_ids))
        except VintedError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return JSONResponse({"brands": brands})

    @app.get("/api/filters/{tld}/facets/{code}")
    async def filter_facet(
        tld: str, code: str, catalog_ids: str = "", _: None = guard
    ) -> JSONResponse:
        service = _taxonomy_or_503()
        if code not in FACET_CODES:
            raise HTTPException(status_code=404, detail=f"no filter called {code!r}")
        try:
            options = await service.facet_options(_known_tld(tld), code, _id_list(catalog_ids))
        except VintedError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return JSONResponse({"options": options})

    # --- Destinations --------------------------------------------------------------

    @app.post("/destinations")
    async def add_destination(
        kind: Annotated[str, Form()],
        name: Annotated[str, Form()] = "",
        target: Annotated[str, Form()] = "",
        _: None = guard,
        __: None = csrf,
    ) -> Response:
        target = target.strip()
        config: dict[str, Any]
        match kind:
            case "discord":
                if not target.startswith("https://"):
                    return _redirect_with_error("die vollständige Discord-Webhook-URL einfügen")
                config = {"webhook_url": target}
            case "telegram":
                if not target:
                    return _redirect_with_error(
                        "die Chat-ID angeben oder den Verknüpfungslink von der Kommandozeile nutzen"
                    )
                config = {"chat_id": target}
            case "webhook":
                config = {"url": target}
            case "ntfy":
                config = {"topic": target}
            case _:
                return _redirect_with_error(f"unbekannter Empfängertyp {kind!r}")

        await repo.add_destination(kind=kind, name=name.strip() or kind, config=config)
        return RedirectResponse("/", status_code=303)

    @app.post("/destinations/{destination_id}/delete")
    async def delete_destination(destination_id: int, _: None = guard, __: None = csrf) -> Response:
        existing = await repo.get_destination(destination_id)
        await repo.deactivate_destination(destination_id, "über das Dashboard entfernt")
        return _redirect_with_ok(
            f"„{existing.name if existing else 'Empfänger'}“ entfernt.", "/destinations"
        )

    @app.post("/destinations/{destination_id}/reactivate")
    async def reactivate_destination(
        destination_id: int, _: None = guard, __: None = csrf
    ) -> Response:
        await repo.reactivate_destination(destination_id)
        return _redirect_with_ok(
            "Wieder verbunden. Es werden wieder Treffer zugestellt.", "/destinations"
        )

    @app.post("/destinations/{destination_id}/notify-status")
    async def set_notify_status(
        destination_id: int,
        notify_status: Annotated[str, Form()],
        _: None = guard,
        __: None = csrf,
    ) -> Response:
        await repo.set_destination_notify_status(destination_id, notify_status == "1")
        verb = "erhält" if notify_status == "1" else "erhält keine"
        return _redirect_with_ok(f"Empfänger {verb} Statusmeldungen.", "/destinations")

    @app.post("/searches/{query_id}/routes")
    async def set_routes(
        query_id: int,
        destination_ids: Annotated[list[int] | None, Form()] = None,
        _: None = guard,
        __: None = csrf,
    ) -> Response:
        wanted = set(destination_ids or [])
        current = set(await repo.destination_ids_for_query(query_id))
        for destination_id in current - wanted:
            await repo.unroute(query_id, destination_id)
        for destination_id in wanted:
            await repo.route(query_id, destination_id)
        return _redirect_with_ok("Zuordnung aktualisiert.", "/searches")

    # --- RSS -----------------------------------------------------------------------

    @app.get("/rss/{query_id}.xml")
    async def rss(query_id: int, key: str = "") -> Response:
        # Feed readers cannot log in, so the token travels in the query string here.
        if not _authorised(key, token):
            raise HTTPException(status_code=401, detail="add ?key=<your token>")
        query = await repo.get_query(query_id)
        if query is None:
            raise HTTPException(status_code=404, detail="no such search")
        rows = [row for row in await repo.recent_items(limit=100) if row["query_id"] == query_id]
        return Response(content=_rss_feed(query.name, rows), media_type="application/rss+xml")

    return app


# The router writes its own English into the exception when it turns a request away
# before a route ever runs. Every other message this app raises is already German, so
# only these exact phrases are swapped: an app-raised detail is passed through untouched
# however it happens to read.
_STATUS_PHRASES: Final[dict[str, str]] = {
    "Not Found": "Diese Seite gibt es nicht.",
    "Method Not Allowed": "Diese Seite beantwortet keine solche Anfrage.",
    "Unauthorized": "Nicht angemeldet.",
    "Forbidden": "Dafür fehlt die Berechtigung.",
    "Internal Server Error": "Da ist etwas schiefgelaufen.",
    "Service Unavailable": "Gerade nicht erreichbar.",
}


def _error_message(detail: str) -> str:
    return _STATUS_PHRASES.get(detail, detail)


def _form_context(
    settings: Settings, snapshot: health.Snapshot, taxonomy: Taxonomy | None
) -> dict[str, Any]:
    """What the add-a-search form needs, whichever page it is sitting on."""
    watched_tlds = [search.tld for search in snapshot.searches]
    return {
        "min_interval": MIN_POLL_INTERVAL_S,
        "default_interval": settings.poll_default_interval_s,
        "builder_enabled": taxonomy is not None,
        "known_tlds": sorted(urls.KNOWN_TLDS),
        # Open the builder on the site the user already watches most. Germany first when
        # there is nothing to go on: the tool is built and translated for vinted.de.
        "default_tld": Counter(watched_tlds).most_common(1)[0][0] if watched_tlds else "de",
    }


def _redirect_with_error(message: str, to: str = "/") -> RedirectResponse:
    return RedirectResponse(f"{to}?error={quote(message)}", status_code=303)


def _redirect_with_ok(message: str, to: str = "/") -> RedirectResponse:
    return RedirectResponse(f"{to}?ok={quote(message)}", status_code=303)


def _delivery_view(stats: DeliveryStats, now: int) -> dict[str, Any]:
    """One destination's delivery record, phrased for the card.

    The latency shown is the median, and it is labelled as a wait rather than a speed:
    what a person wants to know is whether an alert turns up promptly, and a bare
    "0.8s" invites them to read it as the far end's response time when it is mostly
    queue time.
    """
    latency = stats.median_latency_s
    return {
        "health": stats.health,
        "sent": stats.sent,
        "failed": stats.failed,
        "success_rate": stats.success_rate,
        "latency": f"{latency:.1f} s".replace(".", ",") if latency is not None else None,
        "last_sent": _age(
            stats.last_queued_at if stats.sent else None,
            now,
        )
        if stats.sent
        else None,
    }


# How the interface writes money. Germany puts the symbol after the number and separates
# thousands with a dot and decimals with a comma; "10.00 EUR" reads as machine output to
# anyone this app was written for. Currencies that are not the euro keep their ISO code,
# because "EUR" is the only part of an unfamiliar one that is unambiguous.
_EURO_SIGN: Final = "€"
_GROUP_SIZE: Final = 3
# Two events about the same thing less than a minute apart are one event as far as
# a person scrolling back is concerned. A minute is also the finest resolution the
# timestamps in this schema are ever written with, so the window matches the data.
_EVENT_RUN_WINDOW_S: Final = 60


def _money(amount: float, currency: str) -> str:
    """One price, written the way it is written in Germany."""
    code = (currency or "").strip().upper()
    whole, _, frac = f"{amount:.2f}".partition(".")
    grouped = ""
    while len(whole) > _GROUP_SIZE:
        grouped = "." + whole[-_GROUP_SIZE:] + grouped
        whole = whole[:-_GROUP_SIZE]
    number = f"{whole}{grouped},{frac}"
    if code in ("", "EUR"):
        return f"{number} {_EURO_SIGN}"
    return f"{number} {code}"


def _listing_views(rows: list[Any], now: int) -> list[dict[str, Any]]:
    """Rows from the items table as the listing cards want them.

    Photos and formatting are settled here so the template stays declarative, and a row
    from before the gallery migration degrades to its cover photo rather than an error.
    """
    views: list[dict[str, Any]] = []
    for row in rows:
        photos: list[str] = []
        if row["photo_urls_json"]:
            with contextlib.suppress(ValueError):
                photos = [str(url) for url in json.loads(row["photo_urls_json"])]
        if not photos and row["photo_url"]:
            photos = [row["photo_url"]]

        currency = row["currency"] or ""
        price = row["price"]
        total = row["total_price"]
        # The same 0..1-to-stars reading the notifications use.
        stars = round(row["seller_rating"] * 50) / 10 if row["seller_rating"] is not None else None
        views.append(
            {
                "title": row["title"] or f"Artikel {row['item_id']}",
                "url": row["url"],
                "photos": photos,
                "price": _money(price, currency) if price is not None else None,
                "total_price": (
                    _money(total, currency)
                    if total is not None and total != price
                    else None
                ),
                "brand": row["brand"],
                "size": row["size"],
                "condition": row["condition"],
                "seller_login": row["seller_login"],
                "seller_url": (
                    urls.member_url(row["tld"], row["seller_id"]) if row["seller_id"] else None
                ),
                "seller_stars": f"{stars:.1f}" if stars is not None else None,
                "seller_feedback_count": row["seller_feedback_count"],
                "favourite_count": row["favourite_count"] or 0,
                "query_name": row["query_name"],
                "age": _age(row["first_seen_at"], now),
                # The decay rule draws itself from these two. `age` above is a phrase a
                # person reads; the tile needs a proportion it can turn into a width, and
                # a number it can style on. Re-deriving either in the template would mean
                # every listing surface re-implementing the same arithmetic.
                "caught_seconds": _caught_seconds(row["first_seen_at"], now),
                "freshness": _freshness(row["first_seen_at"], now),
            }
        )
    return views


_EVENT_OUTCOME = {
    "gefunden": "gefunden",
    "zugestellt": "zugestellt",
    "fehlgeschlagen": "gescheitert",
}


def _event_views(rows: list[Any], now: int) -> list[dict[str, Any]]:
    """One row of the timeline as the page wants to say it.

    Same reasoning as `_listing_views`: the SQL picks the events, this decides what
    each one is called and how its numbers are written, and the template only
    places them. The outcome is a word rather than a colour, because "failed" and
    "delivered" have to survive greyscale and a screen reader alike.

    Runs of the same thing are collapsed, and that is not tidiness. One find
    produces one delivery per destination, so a busy hour is mostly "zugestellt"
    rows; listed one by one they bury the finds, which are the only events here a
    person actually came for. Forty identical lines is not a history, it is a
    scroll. The count is still the true number of rows it stands for.
    """
    views: list[dict[str, Any]] = []
    # The run currently being extended, and the moment it started. Held out here
    # rather than in the view, so no field has to be written and then taken back
    # out again. A run is measured against its first event, not its last.
    run: dict[str, Any] | None = None
    run_ts = 0

    for row in rows:
        ts = int(row["ts"])
        headline = row["headline"] or ""
        if (
            run is not None
            and abs(ts - run_ts) < _EVENT_RUN_WINDOW_S
            and run["kind"] == row["kind"]
            and run["headline"] == headline
        ):
            run["count"] += 1
            # The newest member of a run carries the freshest moment.
            run["when"] = _age(ts, now)
            continue

        price = row["price"]
        run = {
            "kind": row["kind"],
            "outcome": _EVENT_OUTCOME[row["kind"]],
            "when": _age(ts, now),
            "query_name": row["query_name"] or "",
            "headline": headline,
            "sub": row["sub"] or "",
            "money": _money(price, row["currency"] or "") if price is not None else "",
            "href": row["href"] or "",
            "attempts": row["attempts"] or 0,
            "count": 1,
        }
        views.append(run)
        run_ts = ts

    return views


def _caught_seconds(then: int | None, now: int) -> int:
    """Seconds since we first saw this item, or a very large number if we never did."""
    if then is None:
        return DECAY_WINDOW_S
    return max(now - then, 0)


def _freshness(then: int | None, now: int) -> float:
    """How much of its window a find has left, 1.0 at the moment of the catch.

    Linear, because a linear promise is the only one a user can learn. A find that has
    been open for half its window is exactly half as alive, and after the window it is
    simply cold — the tile stops pretending and greys out. A curved falloff would look
    livelier and mean less.
    """
    if then is None:
        return 0.0
    remaining = 1.0 - (max(now - then, 0) / DECAY_WINDOW_S)
    return max(0.0, min(1.0, remaining))


def _age(then: int | None, now: int) -> str:
    """A found-time a human scans, not arithmetic they have to do."""
    if then is None:
        return "nie"
    seconds = max(now - then, 0)
    if seconds < 60:  # noqa: PLR2004
        return f"vor {seconds} s"
    if seconds < 3600:  # noqa: PLR2004
        return f"vor {seconds // 60} Min."
    if seconds < 86400:  # noqa: PLR2004
        return f"vor {seconds // 3600} Std."
    return f"vor {seconds // 86400} T."


def _positive_int(raw: str) -> int:
    """A page number from a URL, or 1 when it is anything else.

    Hand-edited links and crawler noise produce "?page=banana" constantly, and a
    dashboard that answers that with a stack-trace-shaped JSON blob looks broken.
    """
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def _id_list(raw: str) -> str:
    """Reduce user input to a comma-separated list of numeric ids, dropping the rest."""
    return ",".join(part.strip() for part in raw.split(",") if part.strip().isdigit())


def _decimal_or_none(raw: str) -> Decimal | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _name_from(params: dict[str, str], tld: str) -> str:
    if text := params.get("search_text"):
        return f"{text} ({tld})"
    return f"vinted.{tld} Suche"


def _rss_feed(title: str, rows: list[Any]) -> str:
    entries = []
    for row in rows:
        price = row["total_price"] or row["price"]
        description = f"{price} {row['currency'] or ''}".strip()
        entries.append(
            "<item>"
            f"<title>{xml_escape(row['title'] or 'Listing')}</title>"
            f"<link>{xml_escape(row['url'])}</link>"
            f"<guid isPermaLink='false'>{row['item_id']}</guid>"
            f"<description>{xml_escape(description)}</description>"
            "</item>"
        )
    return (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<rss version='2.0'><channel>"
        f"<title>{xml_escape(title)}</title>"
        "<description>Vinted listings matching this search</description>"
        "<link>https://www.vinted.com/</link>"
        f"{''.join(entries)}"
        "</channel></rss>"
    )


class _QuietServer(uvicorn.Server):
    """A server that leaves signal handling to the application.

    uvicorn would otherwise take over SIGTERM and SIGINT, and two sets of handlers means a
    shutdown that only half happens.
    """

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


async def serve(
    settings: Settings,
    repo: Repo,
    stop: asyncio.Event,
    taxonomy: Taxonomy | None = None,
) -> None:
    """Run the web UI until the app shuts down."""

    config = uvicorn.Config(
        create_app(settings, repo, taxonomy),
        host=settings.web_host,
        port=settings.web_port,
        log_config=None,
        access_log=False,
    )
    server = _QuietServer(config)
    serving = asyncio.create_task(server.serve())
    log.info("web.listening", host=settings.web_host, port=settings.web_port)
    if settings.web_is_exposed_without_a_password:
        log.warning(
            "web.no_password",
            host=settings.web_host,
            hint="the dashboard shows your webhook URLs; keep the published port on "
            "127.0.0.1 or set VINTED_SNIPER_WEB_AUTH_TOKEN",
        )
    await stop.wait()
    server.should_exit = True
    await serving
