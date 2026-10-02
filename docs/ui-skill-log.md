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
