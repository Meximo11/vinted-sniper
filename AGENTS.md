# AGENTS.md — Vinted Sniper

Standing rules for every change in this repository. This file is binding. If a rule here
and a habit of yours disagree, this file wins; if two skills and this file disagree, the
override ledger below settles it.

---

## 1. The product, in one paragraph

A self-hosted desktop tool that watches Vinted search results around the clock and pushes
matches to Telegram, Discord, webhooks or ntfy. It is run by **one reseller, on their own
machine, on a second monitor, for hours at a time.** They glance dozens of times a day.
They lose money when the tool misses a drop, and they lose money when it floods them with
noise. Full product truth lives in `PRODUCT.md` and is binding.

**It is an application, not a website.** Browser-hosted, desktop-first, control-centre. Not a
landing page, not a SaaS homepage, not a portfolio piece, not a dribbble concept.

---

## 2. Mandatory design skills

**Visual quality is a core requirement of this product.** A UI change here is a
visual-direction task, not a mechanical one. The tiering below exists to stop you reading
skills about ground you are not working on — it exists **not** to make the design expertise
optional.

### Tier 1 — read before ANY frontend change

Seven skills. The first three govern quality and correctness; the four after them are the
visual direction this product is built on.

| Skill | Why it is always on |
|---|---|
| `impeccable` | The quality floor, plus `reference/operate.md` and `reference/craft-floor.md`. |
| `ui-ux-pro-max` | Has a **search tool**. Run it — do not just read the file. `scripts/search.py "<outcome>" --domain ux`. |
| `web-design-guidelines` | Its rules live at a URL and change. **Fetch them**; do not work from memory. |
| `frontend-design` | Visual direction: typography, palette, and making choices that are not defaults. |
| `hallmark` | Anti-slop gates, structural variety, the locked-token rule, the responsive floor. |
| `design-taste-frontend` | Brief inference, the dials, the banned-list, the pre-flight check. |
| `high-end-visual-design` | Depth, motion curves, and the explicit list of what reads as cheap. |

**Do not demote any of these.** An earlier version of this file put the four design skills in
a conditional tier, on the reasoning that the mandate had grown expensive to read. That was
wrong for this project: it made the skills that matter most optional, which is the opposite of
what the tiering was for. `tests/visual/test_skill_gate.py` enforces all seven.

### Tier 2 — read when the task actually touches that ground

| The task is about… | Then read |
|---|---|
| Motion, animation, transitions, timing | `animate`, `review-animations`, `improve-animations` |
| Exploring alternatives before committing to a direction | `superdesign` (direction only — see §4) |
| Challenging a direction before you build it | `grill-me` — **the user must type this one** |
| Reviewing motion in a diff | `review-animations` — **the user must type this one** |

This tier is for **genuinely irrelevant** skills. Skipping `improve-animations` on a copy
change is right; skipping `hallmark` on a visual redesign is not.

### Excluded

`apple-design` is **explicitly out of scope** and must not be used.

### Invocation is not reading

Codebuff loads skills two ways: the `skill` tool (`skill({ name: "hallmark" })`) and the
`/skill:name` command. **Reading a `SKILL.md` off disk is not either of those.** A file
open is not a skill invoked: the tool call is what loads a skill into the working context,
and the two are separately auditable. Treat a manual read as a degraded substitute and say
so — never let a log entry imply a `skill` call happened when only a file read did.

Where the `skill` tool is exposed, use it. Where it is not, the file read is the only
mechanism available, and the correct response is to **state that limitation in the log**,
not to write `invoked: yes` and hope nobody looks. An agent that cannot invoke a tool must
not imply it did.

### The rules

- **Read the `SKILL.md`, not just its frontmatter.** Reading the description is how a skill
  gets claimed without being read.
- **Do not skip a skill because another appears to overlap.** The overlap is where the
  useful part usually is.
- **Treat skills as constraints and intelligence, not templates.** Do not paste a skill's
  visual examples into this product.
- **Resolve contradictions against the product**, and record the resolution in §4.
- **Never claim a skill was used unless its `SKILL.md` was actually read.**
- **Never claim a skill was invoked unless it was loaded through the `skill` tool or a
  `/skill:name` command.** If you only read the file, log `mechanism: file-read` and say the
  tool was unavailable.
- **Never claim visual QA unless the rendered UI was actually inspected.**
- **A passing gate is not a design review.** `tests/visual/test_skill_gate.py` proves the
  expertise was *consulted and recorded*. It cannot judge whether the resulting interface is
  any good. Visual quality is established by looking at the rendered app and critiquing it
  against the brief — a green suite is a floor, never a verdict.
- **Log the read with what you extracted.** Every frontend change needs an entry in
  `docs/ui-skill-log.md` naming each Tier 1 skill and, for each, the **rule pulled out of
  it**, the **decision it changed**, and **where that decision lives in the code** — plus the
  `invoked:` / `mechanism:` receipt. A bare list of names is not evidence of use and the gate
  rejects it. Where a skill's advice genuinely does not fit this product, write that down
  with the reason; an invented connection is worse than an honest rejection.

Where they live:

| Scope | Path |
|---|---|
| Project-pinned | `.agents/skills/<name>/SKILL.md` |
| Global | `~/.agents/skills/<name>/SKILL.md` |
| Mirrored for Claude Code | `.claude/skills/<name>` (symlinks, except `impeccable`) |

`grill-me` and `review-animations` carry `disable-model-invocation: true`. You cannot
self-invoke them. If the user has not typed them, say so rather than implying you ran them.

---

## 3. The process

1. **Design-first.** No frontend edit before the design question is answered.
2. **Research.** Real products, real interfaces, and this product's actual data. If the
   research is useless, say so — do not pad it with SEO content farms.
3. **Design system before scale.** Tokens and component grammar before large implementation.
4. **Anti-slop.** Everything in §5.
5. **Accessibility** is not a pass at the end. It is a state of every component.
6. **Motion quality** — purposeful, restrained, interruptible.
7. **Visual QA is mandatory** — §7.
8. **Iterate.** Implement → render → inspect → critique → fix → render again. Do not stop
   at the first pass.
9. **Preserve the backend** — §6.

---

## 4. The override ledger

Twelve skills genuinely contradict each other and this product. A bare mandate would
guarantee the same argument every session. These are the settled decisions.

| Rule | Decision | Why |
|---|---|---|
| `high-end-visual-design`: `py-24` section padding, 2rem radii, double-bezel nesting | **Rejected** | Operate mode. A dense instrument cannot show data at that padding. |
| `high-end-visual-design`: scroll-entry reveals, magnetic buttons, staggered nav | **Rejected** | `animate`'s own frequency gate: 100+/day gets no animation. This rail is used 100+/day. |
| `high-end-visual-design`: banned shadows, banned Inter | **Rejected** | Tinted elevation is a real depth system. The offline, no-build constraint fixes the typeface question. |
| `design-taste-frontend`: "Landing pages, portfolios, and redesigns. Not dashboards" | **Discipline only** | Its banned-list, token lock, copy audit and em-dash ban apply. Its agency aesthetics do not. |
| `craft-floor`: card radii 12–16px | **Overridden** | `PRODUCT.md` says "small radii". impeccable's own rule: *the brief wins*. |
| `craft-floor`: self-host a display face | **Rejected** | Offline tool, no build step. `operate.md` endorses one family. |
| `craft-floor`: hero-metric template, ghost cards, coloured `border-left` >1px, eyebrows | **Adopted as fixes** | All four were live violations before 2026-10. |
| `operate.md`: no page-load sequence, skeleton loaders | **Adopted as fixes** | The 380ms page-enter is gone. Loading states exist. |
| `operate.md`: "modals are usually laziness" | **Adopted** | The photo lightbox is the one justified overlay: it interrupts nothing and carries no form. |
| `animate` + `review-animations`: frequency gate, sub-300ms | **Adopted strictly** | Budget is 120–180ms. One authored moment only. |
| `superdesign`: generate canvas artifacts | **Excluded** | External service, output is not shippable code for a local Jinja + CSS app. Read for direction. |
| `ui-ux-pro-max` `--stack` lookup | **Partly unavailable** | 22 stacks, none for vanilla CSS / Jinja. Its design data still applies. |
| `impeccable`: bounded verification passes | **Adopted** | Build fully, inspect once, fix in one batch, confirm once, stop. Open-ended self-QA burns the user's money. |

Anything new that wants to change this table must be argued in the PR description. Silent
drift is how a design system dies.

---

## 5. Anti-slop — refuse these

Page scaffolds:

- Same-size cards of icon + heading + text as the page structure. Cards are the lazy
  container; **nested cards are always wrong.**
- The hero-metric template: big number, small label, supporting stats, accent.
- An eyebrow or kicker above a heading. **This one is a ban, not a default.**
- Section numbers (01 / 02 / 03) unless the sequence itself carries information.
- A modal for a task that needs neither interruption nor protected focus.

Surface habits:

- Gradient text. Emphasis comes from weight or size.
- Glass and blur as decoration rather than as a specific effect.
- A coloured `border-left`/`border-right` above 1px on a card, list item, callout or alert.
- Hard offset shadows (`box-shadow: 4px 4px 0`).
- Sparklines, progress rings, or soft-shadowed rounded rectangles standing in for content.
- Monospace as a costume for "technical" rather than for code, data, or measurement.
- Unicode glyphs or emoji standing in for an icon system. Icons are drawn SVG, one stroke
  weight, one size scale.
- Background textures with no canvas, map, blueprint or measuring tool under them.

Colour: **the interface is grey until it isn't.** The resting state is greyscale. Accent
means hot or active. Semantic red means broken. Colour is information, never decoration.

Motion: `animate` + `review-animations` + `operate.md` agree — 120–180ms, custom
cubic-beziers, no `linear`, no `ease-in` on UI, `prefers-reduced-motion` honoured, keyboard
initiated actions do not animate at all.

---

## 6. What must not break

The Vinted layer is a working, tuned machine and is a stable API the UI consumes. **Out of
scope for visual work, protected by tests:**

endpoint construction · URL normalisation · polling · session rotation · listing retrieval ·
filter and taxonomy logic · search management · notification delivery (Telegram, Discord,
webhook, ntfy) · deduplication · the database · the background scheduler · authentication
and session behaviour · the public route contract.

The Python changes only where the interface genuinely cannot be expressed otherwise. One
such case is already sanctioned: `_listing_views` exposes `freshness` and
`caught_seconds` so the decay rule can be drawn in CSS from a number, not re-derived from
a formatted string in every template.

Everything the user can see or touch **is** open to redesign. A component that works is an
implementation detail, not a design constraint.

**Product rules that outrank the design:**

- **German**, everywhere the user can read it. Vinted's own listing titles are data and
  stay as they are.
- **Vinted.de is the default country site.**
- **Nothing may claim to have worked when it did not.** A failed notification, a dead
  session and an unreachable destination each say so plainly, in their own words.

---

## 7. Visual QA is mandatory

Code correctness is not UI correctness. After implementing, you must:

1. **Run the app** and open the real rendered pages.
2. **Inspect visually** — screenshot, actually look at it.
3. Cover: desktop, small viewport, and every page. Every state: default, hover, focus,
   active, disabled, loading, empty, error.
4. **Run the contrast/overflow auditor** — `tests/visual/test_contrast.py`. It is a real
   test, not a throwaway script. It fails the build.
5. **Fix every meaningful issue you found.**
6. **Render again and critique again.** At least one confirmation pass.

If you did not do this, say you did not do it. Never claim QA you did not perform.

---

## 8. The design system

**Kontrollzentrale.** An application, not a website. Desktop-first, control-centre, built to
sit on a second monitor all day.

**Architecture — Triage.** The product's news is two kinds: a fresh drop is a win, a dead
destination is a loss. The dashboard's first screen is a two-column decision surface —
*Gewinn* against *Zu tun*. Urgency is visible because the two columns can disagree.

**Visual language — control room.** Persistent rail, application shell, 4px grid,
keyboard-first, borders and hairlines by default, shadow reserved for things that genuinely
float (sticky header, lightbox, popovers). Depth declared once per layer.

**Signature — freshness decay.** Every listing tile carries a 2px rule that depletes from
full accent to neutral as the find ages. Hot items are lit; cold ones recede. It is unique to
this product: nobody else holds a second-precision "when did we catch this" timestamp. If it
ever reads as fussy rather than functional, it is the first thing to cut.

### Tokens

- **Colour** — cool neutrals, six-step surface ramp, one accent (teal `#0a7076` light /
  `#23b2ab` dark), semantic ok / warn / bad spent only on abnormal state. Three themes
  (light, dark, system), both surfaces first-class.
- **Type** — one system sans. Fixed rem scale, ratio ~1.125. `tabular-nums` on every figure.
  German set properly. Seven steps: figure, title, section, body, meta, small, label.
- **Spacing** — 4px grid. Tight intra-component, generous inter-section, more space above a
  heading than below it.
- **Radius** — 2–3px controls, near-zero regions, pill only for status.
- **Borders** — one hairline weight, one stronger for region boundaries.
- **Depth** — base → rail → floating → overlay, each level earned, never a ghost card
  (1px border *plus* a wide soft shadow).
- **Motion** — 120–180ms, custom cubic-beziers. One authored moment: the theme cross-fade.
  Lightbox and disclosure transitions convey state and are allowed. No page-enter, no
  scroll reveals, no nav stagger.
- **Icons** — one inline SVG set, 1.5px stroke, `currentColor`, 20px. See `_icons.html`.
- **Z-index** — a documented scale (`--z-rail`, `--z-header`, `--z-scrim`, `--z-drawer`,
  `--z-pop`, `--z-lightbox`, `--z-skip`). No arbitrary values.
- **Freshness decay** — `--decay-window: 900s`. Above it, a find is cold.

### Every interactive component ships

default · hover · **focus-visible** · active · disabled · loading · error

The focus ring is 2px accent at 2px offset and is **never removed.** Browser surfaces —
selection, caret, scrollbars, underline offset, tabular numerals — are themed from the
palette. That is the cheapest signal that a page was built rather than assembled.

### Responsive

Desktop-first. Narrow screens are a **degraded adaptation of a desktop application**, not a
mobile website. The rail becomes a drawer, the triage header stacks, tables become stacked
key/value rows rather than horizontal scroll.
