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

For **any** frontend/UI task — HTML, Jinja templates, CSS, JavaScript, layout, components,
navigation, forms, cards, interactions, animation, responsive behaviour, visual design,
accessibility, loading/empty/error states, dialogs, notifications, or frontend architecture —
the following are **mandatory**:

1. `ui-ux-pro-max` 2. `impeccable` 3. `frontend-design` 4. `design-taste-frontend`
5. `high-end-visual-design` 6. `hallmark` 7. `superdesign` 8. `web-design-guidelines`
9. `grill-me` 10. `animate` 11. `improve-animations` 12. `review-animations`

`apple-design` is **explicitly excluded** and must not be used.

**The rules:**

- **Read every `SKILL.md` before implementing.** Not the description — the file.
- **Do not skip a skill because another one appears to overlap.** Extract the relevant
  principles from each. They overlap on purpose, and the overlap is where the useful part is.
- **Treat skills as design intelligence and constraints, not as templates.** Do not paste a
  skill's visual examples into this product.
- **Resolve contradictions against the actual product**, and record the resolution in §4.
- **Never claim a skill was used unless its `SKILL.md` was actually read.**
- **Never claim visual QA was performed unless the rendered UI was actually inspected.**

Where they live:

| Scope | Path |
|---|---|
| Project-pinned | `.agents/skills/<name>/SKILL.md` |
| Global | `~/.agents/skills/<name>/SKILL.md` |
| Mirrored for Claude Code | `.claude/skills/<name>` (symlinks, except `impeccable`) |

`grill-me` and `review-animations` carry `disable-model-invocation: true`. You cannot
self-invoke them; the user must type them. If the user has not, say so rather than
pretending to have run them.

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
