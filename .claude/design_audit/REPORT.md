# vinted-sniper — Design Analysis Report

Produced by `/design-orchestrator` (STEP 1: research + initial analysis).
Evidence: rendered-browser measurement (Playwright/Chromium, 3 viewports × 2 themes),
computed WCAG contrast, and source audit. Reproduce with:

```bash
python3 .claude/design_audit/contrast.py      # WCAG + scale audit
python3 .claude/design_audit/render_audit.py   # screenshots + rendered measurements
```

**Verdict:** the foundation is genuinely good — better than most self-hosted tools.
The problems are all in the *system*, not the screens. This is a design-system debt
problem, and it is cheap to fix because there is only **156 lines of CSS** to fix it in.

**Headline numbers:** WCAG contrast **15/24 pairs pass, 9 fail** — 5 light-theme text
pairs and 4 border pairs (2 per theme). Dark mode has *no* failing text pairs.
**0 `:focus-visible` rules.** **0 transitions.** **0 breakpoints.** **0 overflow** at
375/768/1440.

---

## 1. Stage 1 — Research: product, users, jobs

| | |
|---|---|
| **Product** | Self-hosted watcher. Paste a Vinted search URL → poller checks it ~1/min → new listings go to an outbox → delivered to Discord / Telegram / ntfy / RSS / webhook. |
| **Primary user** | One person, on their own hardware (Pi, NAS, VPS) or Docker Desktop. Comfortable with a terminal. Not a team, not an admin console. |
| **Core job** | "Tell me the moment something matches, without me refreshing." |
| **Trust model** | The dashboard shows webhook URLs and can post to the user's own channels. Exposure without a password is treated as a real risk by the codebase itself (`web_is_exposed_without_a_password`). |
| **Hard constraint** | Runs headless on a Raspberry Pi behind a possibly-blocked IP, offline-tolerant, no accounts, no external services. |

**What this implies for design:** dense, utilitarian, and legible at a glance wins over
decorative. The app should feel like a well-made tool, not a product page. The
`impeccable`/`gpt-taste`/`high-end-visual-design` register is wrong here; the
`better-*` and `minimalist-ui` register is right.

---

## 2. What already works — keep it

These are real strengths, not politenesses:

- **A token layer exists and is disciplined.** 9 semantic tokens, each with a light and
  a dark value, in one `:root` block. Most self-hosted apps hardcode hex in components.
  The orchestrator's "dark mode is the same design" rule is already satisfied.
- **Dark mode genuinely renders.** Verified by pixel sampling the screenshots:
  bar `rgb(31,32,35)` = `#1f2023`, page `rgb(23,24,26)` = `#17181a` — exact token match.
- **Semantic HTML throughout.** `<header>`/`<main>`/`<section>`, one `<h1>`, three
  `<h2>`, no heading-level skips. 17 `<label for=…>` correctly bound.
- **Buttons are typed** (11/11 have `type=`), forms are POST with real actions.
- **Focus is never suppressed.** No `outline:none` anywhere, so keyboard users are not
  stranded.
- **Empty and loading states exist and are useful.** "Nothing being watched yet. Add a
  search below: open Vinted, set up the search you want, and copy the address bar once
  results are showing." That is a genuinely instructive empty state.
- **Zero horizontal overflow at every viewport.** I expected the 7-column table to
  break at 375px; it does not. The `auto-fit`/`auto-fill` grids and collapsing table
  hold up.
- **156 lines of CSS for a complete dashboard.** No framework, no build step, no
  client-side library. This is a feature.

---

## 3. Findings, ranked

### P0 — Light-theme links fail WCAG AA

```
--accent #09b1ba on --bg #fbfbfa  →  2.53:1   (needs 4.5)
--accent #09b1ba on --panel #fff  →  2.62:1   (needs 4.5)
```

Links are the single most-used interactive element in the app (`a { color: var(--accent) }`
covers listing titles, seller links, meta links, breadcrumbs, chips). In **dark** mode
the same token scores **8.82:1** and passes comfortably — so the light theme, which is
the default on most machines, is the broken one.

Fix: darken `--accent` for light mode only. **`#0a7d84` → 4.74:1 on `--bg`,
4.91:1 on `--panel`** (verified) clears AA on both. Keep the bright `#09b1ba` for dark
mode — this is exactly the asymmetry the token contract is supposed to prevent.

### P0 — No `:focus-visible` anywhere in the app

```
grep -cE ":focus" base.html dashboard.html login.html  →  0, 0, 0
```

Measured after two Tab presses: `outline: auto 1px rgb(16,16,16)` — the browser
default. So keyboard users are **not** stranded, but the app has no designed focus
state at all. Consequences:

- Appearance varies by browser and OS, and is untested.
- `.crumb` and `.chip button` set `border: 0; padding: 0`, so the default ring is the
  *only* affordance — and it is the one place a missed focus is most likely.
- Dark mode relies on the UA picking a light ring. Chromium does; other engines may not.

Fix: one `--focus-ring` token and a single `:focus-visible` rule on `a, button, input,
select, [tabindex]`. This is ~6 lines and closes the app's largest accessibility gap.

### P1 — Status pill text fails AA in light theme

| Pill | Light | Dark |
|---|---|---|
| `.ok` | **4.03:1** FAIL | 5.40:1 pass |
| `.warn` | **3.38:1** FAIL | 5.27:1 pass |
| `.bad` | **4.20:1** FAIL | 4.54:1 pass |

All three fail only because `color-mix(…, 18%, transparent)` lightens the backing behind
a mid-tone foreground. Verified replacements (light theme only):

| Token | Current | Replacement | New ratio |
|---|---|---|---|
| `--ok` | `#2e7d32` → 4.03 | `#256b28` | **4.98:1** |
| `--warn` | `#b26a00` → 3.38 | `#8f5600` | **4.64:1** |
| `--bad` | `#c62828` → 4.20 | `#a81e1e` | **5.36:1** |

Note the pill *does* carry text (`ok`/`stale`/`failing`), so status is not conveyed by
colour alone — that part is correct and should be preserved.

### P1 — Borders fail the 3:1 non-text requirement

```
--line #e4e4e1 on --panel #fff   →  1.27:1   (needs 3.0)
--line #e4e4e1 on --bg   #fbfbfa →  1.23:1
--line #313337 on --panel #1f2023 →  1.29:1
--line #313337 on --bg   #17181a →  1.40:1
```

Low-risk in practice (borders are structural, not the only cue), but it is a real
AA failure, and input borders at 1.23:1 do weaken the perceived affordance of a form
field. Add a `--line-strong` for interactive boundaries only — it must clear 3:1 on
**both** `--panel` and `--bg`, and `--bg` is the harder surface. Verified:

| Candidate | vs `--panel` | vs `--bg` | |
|---|---|---|---|
| `#94948e` | 3.05 | **2.95** | fails on `--bg` |
| `#8e8e88` | 3.29 | 3.18 | **passes both** |
| `#85857f` | 3.71 | 3.58 | passes both, stronger |

Keep `--line` for decorative rules (table dividers, card edges) and add `--line-strong`
only for input and focus boundaries.

### P1 — No motion language exists

```
grep -cE "transition|animation|@keyframes"  →  0
```

Not "bad motion" — *no* motion. The lightbox and combo dropdown appear instantly.
`prefers-reduced-motion` is also absent (currently moot, since there is nothing to
reduce). The orchestrator requires a consistent motion language; today there is none to
inherit. Fix is cheap: two duration tokens, one curve, applied to the four things that
genuinely change on screen.

### P2 — No scales: spacing, radius, type

| System | Distinct values in use | Scale? |
|---|---|---|
| Spacing | **19** (0.1 … 2.25) | none |
| Radius | **5** (0, 6, 7, 10, 999) | none |
| Type | **9** sizes, 5 under 14px, 1 under 12px (`.tag` = 11.52px) | none |
| Elevation | **1** shadow in the whole app (`.combo-list`) | none |
| Motion | 0 | none |

This is the root cause of the whole P1 band. `border-radius: 7px` on inputs and `10px`
on cards are not wrong — they are unchosen. A 4px spacing scale and a 3-step radius
scale would absorb all 19 and 5 values without changing how anything looks.

### P2 — Tap targets are 40px, not 44px

Measured at all three viewports: inputs and `button.quiet` are **40px** tall.
This **passes** WCAG 2.2 AA (SC 2.5.8 requires 24×24) and **fails** AAA (SC 2.5.5,
44×44). Recording it as AAA-only so it is not over-weighted; worth fixing when a
spacing scale lands, since 44px is a scale step away.

### P3 — Flat token architecture

Tokens are semantic-only; there is no primitive → semantic → component layering. Fine
at this size, but it is why the accent-per-theme asymmetry above was possible.

---

## 4. Stage 13 — Visual QA: rendered results

| Viewport | Overflow | Verdict |
|---|---|---|
| 375 × 667 (mobile) | 0px | Clean |
| 768 × 1024 (tablet) | 0px | Clean |
| 1440 × 900 (desktop) | 0px | Clean |

Dark mode verified pixel-exact in both. Screenshots written to
`.claude/design_audit/screens/` (6 viewports + focus state).

**Caveat, stated honestly:** the app currently has **no saved searches**, so the
dashboard renders its empty state. `.tag`, `.pill` and `.listing` are therefore *not*
rendered in these captures. Their 11.52px text and pill contrast are established from
source and computed contrast, not from pixels. Re-run with data present to confirm.

---

## 5. Recommended sequence

Ordered by value-per-effort. All are CSS-only; none require touching the FastAPI layer.

1. **`:focus-visible` + `--focus-ring`** (~6 lines) — closes the P0 gap.
2. **Darken light-mode `--accent`** (~1 line) — fixes 2 failing pairs, the most-used
   element in the app.
3. **Darken light-mode `--ok`/`--warn`/`--bad`** (~3 lines) — fixes 3 failing pairs.
4. **Add `--line-strong`** for input/focus boundaries (~2 lines) — fixes the 3:1 failures.
5. **Lift spacing + radius to scales**, remapping existing values with no visual change.
6. **Add 2 motion tokens + `prefers-reduced-motion`**, apply to lightbox/combo/pill.
7. **Record all of the above in `DESIGN.md`** so stages 7–16 inherit rather than re-decide.

Steps 1–4 are under 15 lines of CSS total and turn 9 failing contrast pairs into
passing ones plus a designed focus state. That is the highest-value work available in
this codebase right now.

---

## 6. Contract drift check (orchestrator gate)

| Check | Result |
|---|---|
| Tokens referenced, not hardcoded | ⚠️ mostly — `#06282a`, `rgb(0 0 0 /.55)`, `rgb(0 0 0 /.8)` are off-token |
| All interaction states incl. `:focus-visible` | ❌ none defined |
| Contrast ≥4.5:1 text, ≥3:1 UI — both themes | ❌ 9/24 pairs fail, all in light theme |
| `prefers-reduced-motion` honoured | ❌ absent (no motion to reduce) |
| Mobile = desktop, same tokens and hierarchy | ✅ verified at 3 viewports, 0 overflow |
| Reused existing components | ✅ no duplication found |
| Nothing decorative without purpose | ✅ nothing decorative at all |

---

## 7. Still open

- **`DESIGN.md` does not exist.** Stages 5–8 have no written contract to inherit. The
  CSS is the de-facto contract; this report should seed the document.
- **Rendered state with data is unverified.** `.pill`, `.listing`, `.tag` were measured
  from source, not pixels, because no searches are saved. Adding one and re-running
  `render_audit.py` would close this.
- **No live comparison against a reference design** was done; this is an internal
  quality audit only.