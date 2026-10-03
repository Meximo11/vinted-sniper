# Stage Map — full routing, entry/exit criteria, overlap resolution

Companion to `../SKILL.md`. This file is the operational detail: which installed skill
opens each stage, what must be true before you start, what must be true before you
leave, and which skills deliberately overlap.

Every skill named here is installed under `.claude/skills/` and validated.

---

## Stage 1 — Research

**Opens:** `user-researcher` (richhemsley3). **Support:** `usability-psychologist`
(mae616) for the evaluation frame.

**Entry:** a product question, not a screen request. **Exit:** users, jobs, constraints,
and success criteria written down.

For market research, `user-researcher` covers competitive analysis. `deep-research` is
**not** installed — use web search directly.

## Stage 2 — Product understanding

**Opens:** `shape` (taste) or `impeccable teach`. **Support:** `product-designer`.

**Entry:** research output in hand. **Exit:** PRODUCT.md (users, brand, principles) and
DESIGN.md (visual system) exist and are not placeholders. `impeccable` gates on this —
it will refuse to edit files until PRODUCT.md is real.

## Stage 3 — Information architecture

**Opens:** `information-architect`, `ux-map-maker`. **Support:** `journey-map`,
`ux-flow-planner`, `screen-flow-diagram`, `interactive-flow-diagram`.

**Entry:** personas. **Exit:** flows covering happy path, edge cases, fringe cases, and
error states. `ux-heuristics` and `qa-specialist` are later-stage consumers.

## Stage 4 — Design direction

**Opens:** `frontend-design` (Anthropic). **Support:** `design-taste-frontend`,
`high-end-visual-design`, `gpt-taste`, `stitch-design-taste`, `minimalist-ui`,
`industrial-brutalist-ui` (taste).

**Entry:** IA settled. **Exit:** exactly one aesthetic chosen, defensible in one
sentence.

The taste "design language" skills are **mutually exclusive** — pick one, or none.
`design-taste-frontend` and `high-end-visual-design` are craft disciplines that compose
with any direction; `minimalist-ui`, `industrial-brutalist-ui`, `gpt-taste`,
`stitch-design-taste` are full aesthetic replacements.

## Stage 5 — Design system

**Opens:** `design-system` (ui-ux-pro-max — three-layer token architecture, CSS
variables, validators), `ui-ux-pro-max`. **Support:** `design` (sboghossian),
`brandkit`, `brand`.

**Entry:** direction chosen. **Exit:** three-layer token set (primitive → semantic →
component) written to `DESIGN.md`, implemented in `base.html`'s `:root` and dark-mode
blocks, and passing `design-system/scripts/validate-tokens.cjs`.

`design-system/scripts/generate-tokens.cjs` emits CSS from a config;
`html-token-validator.py` checks the HTML against it.

## Stage 6 — Typography

**Opens:** `better-typography` (jakubkrehel). **Support:** `typeset` (taste).

**Entry:** contract exists. **Exit:** type scale, pairing rationale, loading strategy
(`font-display`, subsetting), and line-length rules recorded in the contract.

`better-typography` cites `reference/typography.md`, which resolves to the sibling
`design` / `impeccable` skill.

## Stage 7 — Color

**Opens:** `better-colors`. **Support:** `colorize` (taste), `brand`.

**Entry:** type fixed. **Exit:** palette with named roles, verified contrast ratios, and
**both** light and dark values — this app already ships two sets
(`--bg`/`--panel`/`--ink`/`--muted`/`--line`/`--accent`/`--ok`/`--warn`/`--bad`).

Status colors (`--ok`, `--warn`, `--bad`) are used as `.pill` backgrounds via
`color-mix`, so verify the mixed result, not just the base token.

## Stage 8 — Layout

**Opens:** `better-layout`. **Support:** `layout` (taste), `wireframe-agent`.

**Entry:** color fixed. **Exit:** spacing scale, grid, container widths, and breakpoints
in the contract.

`layout` cites `reference/spatial-design.md`, which resolves to the sibling `impeccable`
skill.

## Stage 9 — Component design

**Opens:** `component-builder`, `better-ui`. **Support:** `design-engineer`,
`page-designer`, `break` / `break-ui` / `variant`.

**Entry:** layout fixed. **Exit:** every component specifies rest, hover, active,
`:focus-visible`, disabled, loading, empty, and error states.

This app's real components to hold to that bar: `.card`, `.pill` (`.ok`/`.warn`/
`.failing`), `button` / `button.quiet`, `.listing`, `.tag`, `.error`, form `label`+input.
`break-ui` (emilkowalski) and `break` (jakubkrehel) both stress-test with worst-case
data; `break-ui` is the more thorough one.

## Stage 10 — UI implementation

**Opens:** `ui-implementer` (MadAppGang — screenshot/Figma-to-code with fidelity
validation), `frontend-implementation` (mae616). **Support:** `image-to-code` (taste),
`frontend-ui` (WomenDefiningAI), `ui-styling` (ui-ux-pro-max, shadcn/Tailwind),
`frontend-design`, `pick-ui-library`.

**Entry:** design artifacts exist. **Exit:** implementation matches, and every value
comes from the contract.

**Stack reality check:** this project is server-rendered Jinja2 with an inline `<style>`
block — no React, no Tailwind, no shadcn. `ui-styling` and `pick-ui-library` assume a
component framework; use their *rules* (token discipline, component anatomy), not their
install steps. `pick-ui-library` is for React projects — skip here.

`ui-implementer` expects Figma or screenshot references and a component framework; for
Jinja2 templates, pair it with `frontend-implementation`.

## Stage 11 — Motion / micro-interactions

**Opens:** `animate` (taste, user's existing skill — it mandates `/impeccable` context
first). **Support:** `review-animations`, `improve-animations`,
`find-animation-opportunities`, `creative-coder`, `animation-vocabulary`,
`apple-design`, `mobile-native`.

**Entry:** working components. **Exit:** motion uses the contract's curves and
durations; `prefers-reduced-motion` is honored; nothing animates without a purpose.

`animate` (taste) reviews and enhances existing motion. The upstream emilkowalski
`animate` builds from scratch and ships `RECIPES.md` — it was **not** installed to avoid
colliding with the user's existing `animate`. Use `review-animations` to critique a
single diff and `improve-animations` to audit a whole codebase.

`creative-coder` (mae616) covers scroll effects and immersive motion — use sparingly; it
is the most slop-prone skill in the stack.

## Stage 12 — Accessibility

**Opens:** `accessibility-engineer` (mae616), `better-accessibility` (jakubkrehel).
**Support:** `accessibility-auditor` (richhemsley3, WCAG checklist),
`better-accessibility/motion-and-zoom.md`, `mobile-native` (touch targets).

**Entry:** implementation done. **Exit:** semantic HTML, keyboard paths, visible focus,
labels, contrast, reduced-motion all pass.

`accessibility-engineer` is minimal-ARIA: use the native element first, add ARIA only
when there's no semantic equivalent. `better-accessibility` is the review pass with hit
areas, focus, screen reader, and zoom/motion references.

## Stage 13 — Visual QA

**Opens:** `frontend-visual-qa` (daymade — the real-browser/Playwright audit).
**Support:** `audit` (taste), `break`, `break-ui`, `data-visualization-discipline`.

**Entry:** a running app. **Exit:** rendered screenshots inspected at ≥3 viewports,
covering hierarchy, spacing, typography, alignment, responsive/mobile, component states,
empty/loading/error states, clipping, wrapping, and consistency.

`frontend-visual-qa` ships `scripts/visual_layout_audit.mjs` (Playwright viewport and
overflow audit), `scripts/attention_inventory.mjs`, and
`scripts/silent_degradation_probe.mjs`. It requires Playwright and a running server —
neither is wired into this repo yet. Until then, `audit` (taste) provides a static
substitute that does not need a browser.

`data-visualization-discipline` (daymade) is the judgment layer for any chart — load it
*before* drawing, not after.

## Stage 14 — UX review

**Opens:** `ux-heuristics` (Nielsen's 10 + Laws of UX references),
`usability-psychologist`. **Support:** `design-critique`, `interface-review`.

**Entry:** visual QA passed. **Exit:** findings triaged P0–P3 with P0 fixed.

`ux-heuristics` carries `references/laws-of-ux.md` and
`references/nng-heuristics-deep-dive.md`. `design-critique` brings its own pair.

## Stage 15 — Polish

**Opens:** `polish`, `distill` (taste). **Support:** `quieter` / `bolder`,
`delight`, `clarify` + `better-writing`, `optimize`.

**Entry:** UX review passed. **Exit:** optical alignment corrected, copy tightened, no
decorative filler.

Use `quieter` when it's loud, `bolder` when it's safe, and only one of them per pass.

## Stage 16 — Final review

**Opens:** `better-interface` (routes to every `better-*` skill and consolidates one
ranked verdict), `design-reviewer`. **Support:** `critique`, `interface-review`,
`frontend-visual-qa`, `qa-specialist`.

`interface-review` (jakubkrehel) is **change-scoped**: it resolves the diff/branches,
then hands the review to `better-interface`. That hand-off is by design — don't run them
as independent reviews.

**Entry:** everything above passed. **Exit:** contract honored, no drift, verdict is
`Approve`.

---

## Overlap resolution — the complete map

| Overlap | Kept | Dropped / renamed | Why |
|---|---|---|---|
| `ui-ux-pro-max` | ui-ux-pro-max (official) | taste's copy | Official has 3x the CSV data (3061 vs 752 rows) plus tests |
| `emil-design-eng` | emil-design-eng (taste) | emilkowalski upstream | Taste's copy carries the Radix `transform-origin` fix; only 5-line delta otherwise |
| `animate` | animate (taste) | emilkowalski upstream | User's pre-existing skill; it gates on `/impeccable` |
| `ui-designer` | ui-designer (mae616) | daymade's → `design-from-reference` | Name collision. mae616's designs screens; daymade's extracts a system from a reference image |
| `break` / `break-ui` | both | — | Different mechanisms: `break` renders every state, `break-ui` feeds worst-case data |
| `variant` / `prototype` | both | — | `variant` iterates a component; `prototype` renders switchable full variants |
| `better-*` vs `design-engineer` | both | — | Rule-level review vs authoring-time craft |
| `critique` / `design-critique` / `design-reviewer` | all three | — | Quantitative UX scoring / artifact critique / checklist review — different stages |
| `design` (sboghossian) vs `impeccable` | both | — | `design` is the four-ban anti-slop synthesis; `impeccable` is the gated build workflow |
| `accessibility-engineer` vs `accessibility-auditor` vs `better-accessibility` | all three | — | Author-time semantics / WCAG audit pass / rule-level review |
| taste aesthetic languages | pick one | — | Mutually exclusive by design, not duplicates |
