# UI skill log

One entry per session that touched the frontend. This file is read by
`tests/visual/test_skill_gate.py`, which fails the build when a UI file is committed
without a current entry.

**What counts as an entry.** Four things, per skill, or the entry proves nothing:

```markdown
## YYYY-MM-DD
- observability: machine-checkable | not-machine-checkable — one line, why

- **skill-name** (version, project | global)
  - invoked: how the skill was reached, in one line
  - mechanism: skill-tool | slash-command | file-read
  - extracted: the specific rule, in your own words
  - decided: what changed because of it
  - where: path:line in the implementation
```

`invoked:` and `mechanism:` are separate because **reading a `SKILL.md` is not invoking a
skill**. Codebuff loads skills through the `skill` tool and `/skill:name`; a file open is a
degraded substitute and has to be labelled as one. `mechanism` comes from a closed set so it
cannot be free text, because free text is where unverified claims go.

`observability:` is the honest boundary. If the harness keeps no invocation history, the
gate cannot confirm any of it — the receipt is on the honour system and the file says so
rather than implying a machine checked it. **A green gate is not a design review.** It proves
the expertise was consulted and recorded. Whether the interface is any good is settled by
looking at the rendered app.

Skills the mandate **excludes** do not belong here — this file records what was reached, and
`AGENTS.md` records what is out of scope.

## 2026-10-02

- observability: not-machine-checkable — this session was given no `skill` tool and no
  `/skill:` command list, and the workspace has no invocation log on disk. Nothing outside
  the transcript records a skill call, so every entry below is an honest `file-read`. The
  gate checks that this is declared and self-consistent; it cannot check the declaration.

### Pass one — the rebuild

- **impeccable** (4.4.0, global)
  - invoked: read the file plus `reference/operate.md` and `reference/craft-floor.md`
  - mechanism: file-read
  - extracted: `--ink-3` is the last tier that may carry text; a further tier does not clear
    4.5:1 and stops reading as a level, it reads as an artefact.
  - extracted: declare elevation once per layer — a hairline border *under* a wide soft
    shadow is a ghost card, and this stylesheet had exactly that on `.card` and `.listing`.
  - extracted: a product UI read dozens of times a day ships no page-load sequence.
  - decided: removed ten `--ink-4` text uses, retightened `--ink-3` to clear 4.5:1 on all
    three surfaces, and made `--ink-4` graphic-only with a named exemption for `.empty > svg`.
  - where: `src/vinted_sniper/web/static/app.css:36-44` (light), `:138-146` (dark);
    the ban is enforced in `tests/visual/test_contrast.py`.
  - not done: `scripts/impeccable context` was never run, and `craft-floor.md` was read
    before the concept rather than immediately before the edits. `new-work.md` was never
    opened. Recorded because the mandate says so, not because it is comfortable.

- **ui-ux-pro-max** (global)
  - invoked: ran `scripts/search.py` — having previously read only the header
  - mechanism: file-read
  - extracted: never convey state by colour alone; pair it with a shape or a word.
  - extracted: a modular type scale, no arbitrary sizes in the middle of it.
  - decided: the decay rule encodes freshness as *width and colour* together, the rail pulse
    pairs its dot with the word `Läuft`, and every readout carries a text label.
  - where: `src/vinted_sniper/web/static/app.css:1030-1053`;
    `src/vinted_sniper/web/templates/base.html` (rail pulse).
  - not applicable: its `--stack` lookup. All 22 stacks are frameworks and there is no
    vanilla-CSS/Jinja entry, so the lookup returns nothing usable. The design *data* still
    applies; the stack table does not. Saying so beats inventing a mapping.

- **web-design-guidelines** (vercel 1.0.0, global)
  - invoked: read the file, then **fetched the rules from the URL it names**
  - mechanism: file-read
  - extracted: `scroll-margin-top` on anchor targets.
  - extracted: `<meta name="theme-color">` per theme; `touch-action: manipulation`;
    `text-wrap: balance` on headings.
  - decided: added all four. The real bug was the anchor: the sticky header was covering
    `#neu`, which is where "Neue Suche" jumps to. It now lands 366px down against a header
    that ends at 63px.
  - where: `src/vinted_sniper/web/static/app.css:244-262`;
    `src/vinted_sniper/web/templates/base.html` (theme-color metas).
  - deviation: no `width`/`height` on listing `<img>`. The intrinsic size is unknown and
    `aspect-ratio` already reserves the box; fabricated attributes would encode a false
    ratio, which is worse than a layout shift on a cached image.

- **frontend-design** (global)
  - invoked: read in full
  - mechanism: file-read
  - extracted: spend the boldness in one place and keep everything around it disciplined;
    a hover transition on every card and a fade-up on every section is the generic default
    that reads as generated.
  - extracted: structural devices — rules, numbering, labels — must encode something about
    the content rather than decorate it.
  - decided: one signature (the decay rule), everything else quiet; the builder's stepper
    numbers are the only numbering in the app, because that form really is a sequence.
  - where: `src/vinted_sniper/web/static/app.css:1020-1053` (the one loud element);
    `src/vinted_sniper/web/static/app.css:2243` (motion block, gated on
    `prefers-reduced-motion: no-preference`).
  - unresolved: it also names all-caps labels and default type families as tells. Both are
    present in the build and both are carried into the visual review as open findings.

- **hallmark** (global)
  - invoked: read in full, **after** the first implementation pass — too late to shape it
  - mechanism: file-read
  - extracted: locked tokens — every colour outside the token block is a violation.
  - extracted: mobile is a hard floor at 320 / 375 / 414 / 768, with `overflow-x: clip` on
    root rather than `hidden`, which silently kills `position: sticky`.
  - extracted: a pre-emit self-critique scored across six axes, anything under 3 revised.
  - decided: lifted eight inline `rgb()`/`#fff` values into named overlay tokens; added
    `overflow-x: clip`; verified all four widths instead of only 390.
  - where: `src/vinted_sniper/web/static/app.css` (token block `:23-113`, overlay tokens
    added, `overflow-x: clip` on html and body).
  - not done: the pre-emit critique was produced in chat, not stamped into the artifact the
    way the skill asks. A deviation, not a compliance.

- **design-taste-frontend** (global + project 1206-line copy)
  - invoked: read in full
  - mechanism: file-read
  - extracted: its own scope statement excludes dashboards — it is written for landing
    pages, portfolios and redesigns. Its *output* (macro-whitespace, scroll reveals,
    magnetic buttons, 2rem radii) is therefore the wrong target for a triage tool.
  - extracted: the anti-slop list and the token discipline survive the scope mismatch.
  - decided: took the banned-list, the token rule and the copy audit; rejected the
    aesthetics wholesale. Recorded as a resolution rather than a partial read.
  - where: the ledger at `AGENTS.md` §4; the resulting tokens at
    `src/vinted_sniper/web/static/app.css:23-113`.

- **high-end-visual-design** (global)
  - invoked: read in full
  - mechanism: file-read
  - extracted: GPU-safe motion — animate only `transform` and `opacity`, and keep blur on
    fixed and sticky elements only.
  - extracted: never emit the same layout twice; pick an archetype deliberately.
  - decided: the motion budget is transform/opacity only and `backdrop-filter` appears on
    the sticky header alone.
  - where: `src/vinted_sniper/web/static/app.css:2243-2266`.
  - **mostly not applicable, and honestly so.** Its "absolute zero" list bans generic 1px
    borders, edge-to-edge sticky headers, dense grids, demands `py-24` section padding,
    `rounded-[2rem]` double-bezel nesting and scroll reveals on every element. Every one of
    those is the opposite of what `PRODUCT.md` asks for from an operator tool. Applying this
    skill faithfully would produce a worse product. Its banned-fonts clause and its
    variance mandate are the two parts that survive; the rest is rejected on the record
    rather than quietly ignored.

### Pass two — visual-direction review

No implementation changes. This pass reads the rendered app and criticises it against the
brief, which is a separate exercise from having read the skills — per the mandate, a green
gate is a floor and not a verdict.

- **frontend-design** (global) — re-read for the critique, not for edits
  - invoked: read in full again, immediately before writing the review, specifically to
    pull the calibration list as a measuring instrument rather than as a build guide
  - mechanism: file-read
  - extracted: the calibration list names "the SaaS-card kit — content chopped into
    identical rounded cards, one border-radius on everything regardless of hierarchy" and
    "a tracked-out ALL-CAPS eyebrow label above every heading" as *traits that appear
    regardless of subject*, i.e. defaults rather than choices.
  - extracted: "choose your typefaces deliberately, not the default families you would
    reach for on any other project."
  - decided: these three became the measuring sticks for the review, and the app fails all
    three. Reported as findings rather than acted on.
  - where: the findings are in the review, anchored at `app.css:59`, `app.css:733`,
    `app.css:828` and `app.css:706`.

- **hallmark** (global) — re-opened `references/anti-patterns.md` in full
  - invoked: read the skill and its anti-pattern catalogue end to end before judging
  - mechanism: file-read
  - extracted: the uppercase-eyebrow-on-every-section tell, the product-card-grid default,
    default-attractor sameness, tabular data without tabular numerals, hover-only
    affordances, and pure black/white as a non-choice.
  - decided: used as the naming vocabulary for the findings, so each one is traceable to a
    named gate rather than to taste.
  - where: the findings are in the review. Tabular numerals are the one pass — verified
    present at `app.css:519, 567, 772, 910, 932, 939, 1016, 1092`.

- **impeccable**, **ui-ux-pro-max**, **web-design-guidelines**, **design-taste-frontend**,
  **high-end-visual-design** — carried forward from pass one, **not re-read**
  - invoked: not invoked or re-read in this pass. The mandate requires them to be reached
    before visual work; they were reached earlier in the same session, and the extractions
    are above. Re-reading a file to be able to say it was re-read is the exact habit this
    log exists to catch, so it is not done.
  - mechanism: file-read
  - extracted: no new extraction, because no new read.
  - decided: their pass-one decisions stand unchanged; the critique was measured against
    them, which is how three of the findings below (the locked-token check, the
    never-colour-alone check and the contrast floor) were able to be *passed* rather than
    merely re-asserted.
  - where: see the pass-one entries; the findings that use them are anchored at
    `app.css:23-113` (tokens), `app.css:1030-1053` (decay encoding) and
    `tests/visual/test_contrast.py` (the floor).

### Review findings (pass two)

Measured on the rendered app at 1280 and 375, both themes, with the decay window populated
across its real range (15s → 24h) so the signature could be seen rather than assumed.

| # | Finding | Evidence |
|---|---|---|
| 1 | Typeface is `system-ui` — the default family, and `frontend-design` names default families as a tell. No typographic voice at all. | `app.css:59` |
| 2 | The accent does three jobs: primary action, active nav, freshness. Hue alone cannot separate them. | `app.css:44`, `:146`, `:1039` |
| 3 | Uppercase 11px micro-labels, two levels deep in one 130px strip (`GEWINN` over `HEUTE`/`7 TAGE`/`ZUGESTELLT`). | `app.css:733`, `:764`; `dashboard.html:27-51` |
| 4 | Two activity charts, same pixel height, no y-axis, no scale: 2.923 and 7.220 are not comparable by eye. | `activity.html:11` |
| 5 | Zero-height days render as dashed grey stubs that read as a broken rule, not as "none". | `activity.html:11` |
| 6 | `.source` is `Nicht zugeordnet` on 24/24 tiles; the foot's left slot is a repeated dead string. | `_listing_card.html` |
| 7 | At 375 the price wraps: `10,00` / `€` / `11,20 € gesamt` — three lines, primary datum broken, row rhythm lost. | `app.css:923-940` |
| 8 | At 375 `.source` elides to `Nicht zuge…`. | `app.css:1004-1008` |
| 9 | The two triage zones stack below 60rem, so the hairline comparison the brief rests on stops working. | `app.css:715`, `:2067` |
| 10 | Rail: nav ends at ~258px, status at ~800px. ~540px of dead column. | `app.css:433`, `:527` |
| 11 | Card-in-card on /activity: an outer white card holds two inner plots. | `activity.html:11` |
| 12 | Centred dashed empty-state box on two pages; one has an orphan line (`ganz weg.`). | `searches.html`, `activity.html:84` |
| 13 | The search form has no column grid: 978 / 225 / 225 / 225 / 225. | `searches.html` |
| 14 | Duplicate destination rendered twice (`Telegram`, `Vinted Sniper`, `Telegram`). | `searches.html` — data, not design |

What held up, and is worth not throwing away: the decay math is linear and correct
(15s→227px, 7min→109px, 12min→34px, 14min→3px, 16min→0); price baselines align across a row
because the title is clamped to a fixed box; `tabular-nums` is on every numeric run; there
is no horizontal overflow at 375; and the mobile rail has a real `aria-label`'d toggle.


### Pass three — the redesign

- **frontend-design** (global)
  - invoked: the harness delivered the whole SKILL.md into the turn as an activation
    block. That is a real load on a third channel — not a file read, and not a
    `skill` tool call, which this environment still does not expose.
  - mechanism: file-read
  - deviation: the gate's closed set has no name for a harness-delivered activation,
    so this entry records `file-read` — the closest honest label, which understates
    rather than overstates. Adding a fourth token for one session would be a token
    invented to make one log line pass.
  - extracted: the calibration list names the SaaS-card kit, the tracked-out
    ALL-CAPS eyebrow, and default type families as traits that appear regardless of
    subject. The previous design was all three.
  - extracted: "ground the design in the subject's vernacular." The subject is a
    shelf of second-hand clothes that appear and then vanish; the only question a
    reseller actually has is "can I still take this one?".
  - decided: the whole direction. Monochrome chrome so the photography is the only
    colour on screen; one warm hue reserved for "alive"; ink buttons rather than
    accent buttons, so the accent ends up with exactly one meaning.
  - decided: two roles from one family tree — `--font` for text, `--font-display`
    for anything large enough to want optical sizing. No webfont, because the app
    runs behind a login with no build step and a download would be a network
    dependency the product does not have. Recorded as a real constraint rather than
    papered over.
  - where: `app.css` sections 1 and 2; `base.html` nav.

- **impeccable** (global), **hallmark** (global)
  - invoked: not re-read this pass; the pass-one extractions above stand.
  - mechanism: file-read
  - extracted: the contrast floor is not negotiable, and a quiet fourth ink tier is a
    trap, because no value of it both clears 4.5:1 and still reads as a tier.
  - decided: their guard caught six real regressions in the new sheet — placeholders,
    photo fallbacks, chart date labels, pager gaps, the dead-find chip and the status
    timestamp were all painted in the graphic-only ink. They moved to the legible
    tier, and the ink-3 tokens were re-picked until they cleared 4.5:1 on all three
    grounds in both themes.
  - where: `app.css` `--ink-3` in both blocks;
    `tests/visual/test_contrast.py::test_ink_four_is_never_used_as_text`.

- **web-design-guidelines** (global)
  - invoked: the rules were fetched and applied in pass one; nothing here contradicted
    them.
  - mechanism: file-read
  - extracted: a link colour is text and gets the text bar.
  - decided: the old rule required the accent to clear 4.5:1 as a link colour. This
    design has no accent to speak of — the warm hue is graphic-only at 1.6:1 on
    white — so the rule was replaced with a stronger one: `--live` may never be a
    text colour, and links are ink. That encodes the decision that made the sheet
    coherent rather than merely re-checking a number.
  - where: `tests/visual/test_contrast.py::test_live_is_graphic_only_and_never_carries_a_word`.

- **animate**, **improve-animations**, **review-animations** (global)
  - invoked: not re-read. The motion budget they set is the one this pass spent.
  - mechanism: file-read
  - extracted: 120–180ms, transform and opacity only, nothing on scroll, nothing that
    loops, and an action taken a hundred times a day gets no entrance.
  - decided: the whole animation budget is three transitions that answer something the
    user did (button press, drawer, hover), one 1.1s arrival sweep for a find that
    landed in the last thirty seconds, and a 140ms cross-fade between pages. No
    scroll-triggered reveal anywhere.
  - where: `app.css` section 13; the sweep at `.tile.is-arriving`; the transition block
    in `app.js`.

- **ui-ux-pro-max**, **design-taste-frontend**, **high-end-visual-design** (global)
  - invoked: not re-read this pass; their pass-one resolutions stand.
  - mechanism: file-read
  - extracted: nothing new — the pass-one rejections were not revisited.
  - decided: `high-end-visual-design`'s double-bezel and 2rem radii stay rejected for a
    dense tool, and `design-taste-frontend`'s scope statement still excludes
    dashboards. `ui-ux-pro-max`'s never-by-colour-alone rule is now satisfied a second
    way: the freshness signal changes the *form* of the chip and not only its hue, so
    it survives greyscale and colour blindness.
  - where: `_listing_card.html` tier thresholds; `app.css` `.chip-age`.

### Pass four — the two pages the redesign never touched

- **frontend-design**, **impeccable** (global)
  - invoked: not re-read this pass. This was a regression repair, not a new
    direction, and the decisions it was repaired against are the ones already
    recorded above.
  - mechanism: file-read
  - extracted: nothing new. The two things this pass had to get right were both
    already written down: the chrome is monochrome and `--live` is graphic-only,
    and a screen that is not the app still has to look like the app.
  - decided: the redesign rewrote `app.css` and left `login.html` and
    `error.html` referencing five classes the new sheet does not define, so the
    front door and every error page — including the 403 a form post lands on
    after a stale session — rendered as bare full-bleed markup. Rather than
    patch five rules back, the two templates were brought under the design
    language: one card, the existing radius scale, existing tokens only, the
    status code set as a readout in the dashboard's own hero numerals, and the
    login button wired to the loading state that already existed in `app.js`
    and had simply never been reached from this page. `app.css` gained one
    appended section and was not restructured.
  - where: `app.css` §14; `login.html`; `error.html`.

### Pass five — the card order and the button that finishes

- **frontend-design**, **web-design-guidelines** (global)
  - invoked: not re-read this pass. Both gaps were named by the audit as deviations
    from decisions already on the record above, not as new direction.
  - mechanism: file-read
  - extracted: nothing new. What the two fixes share is already written down — the
    freshness signal is the reason the product exists, and a control has to report
    what actually happened to it.
  - decided: two gaps the redesign left. The tile rendered price → title → meta →
    foot, which put freshness last; it is now image → price → freshness → title →
    total → metadata, with the total on its own reserved line so the metadata
    below it keeps one baseline across a grid row. And the search button could only
    ever go to `loading`, because a form post redirects and takes the button with
    it, so the sheet's `done` rule was unreachable. `POST /searches` now answers a
    fetch with the outcome as data and the button finishes its own sentence. The
    count on it is `repo.listing_count`, read from the database — never a literal —
    which is why it honestly reads zero for a search nobody has polled yet. Every
    other form still posts and redirects, and the failures fall back to that path
    so the server's own sentence reaches the user.
  - where: `_listing_card.html` field order; `_search_form.html` `data-report-done`;
    `app.js` the `data-report-done` block and the rAF guard; `server.py` `add_search`;
    `app.css` `.tile-total`, `.ico-done`; `tests/integration/test_web.py`.

### Pass six — Verlauf as history

- **frontend-design**, **impeccable** (global)
  - invoked: not re-read this pass. The brief's requirement — that this page answer
    "what happened" rather than "what is the system doing right now" — was carried
    out with the decisions already on the record: counters are not events, and a
    chart whose two series cannot be compared is a chart that lies.
  - mechanism: file-read
  - extracted: nothing new.
  - decided: the page was reshaped around a timeline of the three things that
    actually happen here — a listing is found, a notification is delivered, a
    check fails — each on a real timestamp, newest first. `Blocksperren`,
    `Rate-Limits` and `Ohne Treffer` are gone: `count_403`, `count_429` and
    `stale_cycles` only ever increase and describe the present, which is the
    dashboard's job. The separate "Letzte Fehler" table went too, because failures
    are events now and having them in two places was the same duplication the tile
    once had. The two charts became one chart with both series on a shared scale,
    which is what makes "are the notifications keeping up with the finds" a
    question the page can answer at all.
  - deviation: permanently failed notifications are *not* in the timeline.
    `mark_failed` writes the error and no timestamp, so there is no honest "when"
    for one. That gap belongs in a migration, not in a template, and it is the one
    thing this page still cannot tell you.
  - where: `repo.recent_events`; `server._event_views`; `activity.html`;
    `app.css` `.events`, `.bars`, `.chart-foot`.

### Pass seven — the pruning pass

- **frontend-design**, **impeccable** (global)
  - invoked: not re-read this pass. A deletion pass has no new direction to pull
    out of a skill; what it needs is the record of what was already decided, which
    is what the entries above are.
  - mechanism: file-read
  - extracted: nothing new.
  - decided: the button count from pass five is *gone*, and that entry is wrong
    where it claims the count is read from the database and "honestly reads
    zero". It could never read anything else: `data-report-done` sits on one form
    only, the create form, and a search created in that same request has no
    items. The one way to get a number was a recycled `queries.id` —
    `INTEGER PRIMARY KEY` without `AUTOINCREMENT`, and `delete_query` leaves the
    `items` rows behind — which would have announced a deleted search's history
    as the new one's finds. A number that is zero or wrong is not worth a field,
    so `found` is deleted and the button says "Wird beobachtet", which is true.
    Everything else the fetch path does stays: it names the search from the
    server's own answer and it falls back to the plain post for any refusal.
    Also removed: the `ok` key, which no caller read, and with it the JS branch
    that could never fire; a third test whose assertion (`303` plus a flash on a
    plain post) the existing create test now carries. Two tests that could not
    fail were repaired rather than deleted — one asserted labels that only ever
    render once a search exists, the other asserted "newest first" on a page
    with nothing on it; both now set up the state they claim to check.
  - deviation: the finished button states "Wird beobachtet" instead of a count
    of finds. The count needs a first poll to exist, and a poll inside the
    request that creates the search is a different feature with its own cost.
  - where: `server.py` `add_search`; `app.js` the `data-report-done` block;
    `tests/integration/test_web.py` the `/searches` and `/activity` tests;
    `app.css` §9.

### Pass eight — what nobody asked for

- **frontend-design**, **impeccable** (global)
  - invoked: not re-read this pass. A removal pass has no new direction to pull
    out of a skill; it needs the record of what was already decided, which is
    every entry above.
  - mechanism: file-read
  - extracted: nothing new.
  - decided: an audit named four things in the shipped UI that no brief asked
    for. Three were unrequested features or components and are gone: the
    cross-fade that wrapped every same-origin link in `startViewTransition`, the
    `.switch` toggle component, and the two icons no template ever calls
    (`minus`, `external`). The fourth was a string — the nav label renamed from
    `Aktivität` to `Verlauf` — and that one is *restored*, not kept: the page
    it points at is a history view, so `Aktivität` is now a loose name for it,
    but the rename was never requested and a rename the user did not ask for is
    exactly what this pass exists to undo. The page's own heading still says
    `Verlauf`, because that describes what the page contains rather than naming
    a destination in the shell.
    Removing the cross-fade made three more things dead, and they went with it:
    `view-transition-name` on `.content`, the `::view-transition-*` keyframes in
    section 13, and the clause in the pass-three entry that counted the
    cross-fade in the animation budget. Six class rules with no reference in any
    template, script or test went the same way — `.switch`, `.btn-icon`,
    `.field-error`, `.lede`, `.allclear` — along with two tokens, `--live-edge`
    (defined three times, read never) and `--fresh-cap`, whose comment claimed it
    mirrored the server so the stylesheet could draw the decay. The decay is
    drawn from `--fresh`; the token was a promise nothing kept.
  - deviation: none. The nav label now describes the page less precisely than
    `Verlauf` did; that is a naming question for the next brief, not something
    to settle by editing a string again.
  - where: `app.js` the page-transition block; `app.css` section 13, `.content`,
    the five dead rules, both tokens; `_icons.html`; `base.html` the nav.

## 2026-10-03

- observability: not-machine-checkable — the harness position is unchanged from
  the session above: no `skill` tool, no `/skill:` list, and no invocation log
  on disk. The receipts below are honest `file-read`s, and this suite can only
  check that they are declared and self-consistent.

### Pass nine — proving the deletions, and the diff they were hiding in

- **frontend-design**, **impeccable** (global)
  - invoked: not re-read this pass. Establishing that removed code was dead, and
    normalising line endings, are not direction questions; both need the record
    of what was already decided, which is the entries above.
  - mechanism: file-read
  - extracted: nothing new.
  - decided: nothing was deleted this pass — the pass-eight removals were proved
    dead before they were allowed to stay removed. A `\.switch` pattern would
    have missed `class="switch"` in a template, so the sweep was repeated on
    the bare names, and `.switch` was then disproven from the running app: the
    per-destination control is a `btn btn-quiet btn-sm` inside a `form.inline`,
    and the page reports zero `.switch` nodes against three `notify_status`
    inputs. Two tokens cannot be settled by grep alone. `--fresh-cap` is unread
    because the decay is drawn from `--fresh`, and `--live-edge` is defined
    three times and read nowhere; the 14-day chart still renders, which is the
    check that actually mattered. Added `.gitattributes` (`* text=auto`) and
    renormalised the index, because `activity.html` had been committed with CRLF
    in its blob while every other file was LF: its diff claimed 197 changed
    lines where 9 had changed. It is now 8 insertions and 9 deletions, and the
    stored form no longer depends on which machine committed a file. The nav
    label stays `Aktivität` — still the weaker of the two names for a history
    view, and not to be changed again without being asked.
  - deviation: none.
  - where: `.gitattributes`; `src/vinted_sniper/web/templates/activity.html`;
    `docs/ui-skill-log.md` pass eight.

### Skills deliberately not reached

- **animate**, **review-animations**, **improve-animations** — partially read in pass one
  (first ~40-50 lines each), enough to fix the motion budget. The motion budget has not
  changed since, so there was nothing to re-read.
  - extracted: 100+ actions a day get no animation; UI transitions stay under 300ms; `ease-out`
    only.
  - where: `src/vinted_sniper/web/static/app.css:2243-2266`.
  - deviation: `review-animations` was applied by hand, not invoked, and
    `improve-animations`' prioritised plan set was never produced.
- **grill-me** — `disable-model-invocation: true`. The user has not typed it. It was
  applied by hand in pass one and that is stated here rather than implied. It is the one
  skill in this file whose absence is the user's call, not the agent's.
- **superdesign** — read partially, excluded from generation. It runs entirely through an
  external CLI and returns a canvas artefact; the output is not shippable Jinja and CSS.
- **apple-design** — excluded by `AGENTS.md` §2. Not reached, and its absence is correct.
