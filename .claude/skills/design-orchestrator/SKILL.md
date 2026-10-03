---
name: design-orchestrator
description: >-
  The design-system orchestrator for this repository. Invoke this FIRST on any design
  task — new screen, redesign, new component, or UI review. Routes the installed design
  skill stack through one 16-stage workflow, owns the token contract (type, color, space,
  radius, elevation, motion), and decides which skill is authoritative at each stage so
  no two skills contradict each other. Also use when a design decision must stay
  consistent with what already exists, or when reviewing drift between DESIGN.md and
  the implementation. Not for backend-only or non-UI tasks.
user-invocable: true
argument-hint: "[stage or task]"
---

# Design Orchestrator

This repository has one design language. ~88 design skills are installed under
`.claude/skills/`. Individually they are strong and mutually unaware: several define
their own radius scale, their own easing curves, their own type scales. Loaded at
random they produce exactly the drift this repository must not have.

**Your job is to make them one voice.** You do not re-teach design. You decide
*which* skill owns *which* decision at *which* stage, and you hold the token contract
so every stage inherits the previous stage's decisions instead of inventing new ones.

## The contract already exists — read it before designing

This app (vinted-sniper) already ships a token layer as CSS custom properties in
`src/vinted_sniper/web/templates/base.html`: `--bg`, `--panel`, `--ink`, `--muted`,
`--line`, `--accent`, `--ok`, `--warn`, `--bad`, each with a light and a dark value.

That is the seed contract. **Read `base.html` before any design work.** `DESIGN.md` at
the repo root is the written form of that contract and is what stages 5–8 formalize.
If `DESIGN.md` and the CSS disagree, the CSS is currently the truth — reconcile them
and say which you changed.

## Non-negotiables

1. **Never invent a token inline.** No hardcoded `#1a1a1a`, no ad-hoc `10px`, no
   one-off `cubic-bezier` in a component. Reference the contract.
2. **Skills propose, the contract decides.** When a skill's default conflicts with the
   contract, the contract wins. Note the conflict in your summary, don't silently
   override.
3. **Reuse before creating.** Search for an existing component, token, or pattern first.
   Extending beats adding; adding beats diverging.
4. **Mobile and desktop are one product.** A breakpoint is not a second design. Same
   tokens, same hierarchy, same motion language — only layout responds.
5. **Dark mode is the same design.** The palette already has two sets of values. Never
   introduce a token that only exists in one theme; add it to both or neither.
6. **Accessibility is a constraint, not a stage.** WCAG 2.2 AA is checked while
   implementing and again at QA, never deferred to the end.

## The workflow

Run in order. Skip a stage only when its output already exists and is current, and say
so. Never run two design-authoring skills against the same surface in one turn — pick
the one that owns that stage.

| # | Stage | Primary skill | Supporting | Gate to pass |
|---|-------|---------------|-----------|--------------|
| 1 | Research | `user-researcher` | `usability-psychologist`, web search | Users, jobs, constraints written down |
| 2 | Product understanding | `shape`, `impeccable teach` | `product-designer` | PRODUCT.md / DESIGN.md exist, non-placeholder |
| 3 | Information architecture | `information-architect`, `ux-map-maker` | `journey-map`, `ux-flow-planner` | Flows cover happy, edge, fringe, error |
| 4 | Design direction | `frontend-design` | `design-taste-frontend`, `high-end-visual-design` | One aesthetic chosen, defensible in one sentence |
| 5 | Design system | `design-system`, `ui-ux-pro-max` | `design`, `brandkit` | Token contract written to `DESIGN.md` |
| 6 | Typography | `better-typography` | `typeset` | Scale, pairing, loading fixed in contract |
| 7 | Color | `better-colors` | `colorize`, `brand` | Palette + contrast pass AA in **both** themes |
| 8 | Layout | `better-layout` | `layout` | Spacing scale + breakpoints fixed |
| 9 | Component design | `component-builder`, `better-ui` | `design-engineer`, `page-designer` | States: rest/hover/active/focus-visible/disabled/loading/empty/error |
| 10 | UI implementation | `ui-implementer`, `frontend-implementation` | `image-to-code`, `frontend-ui`, `ui-styling` | Pixels match; tokens referenced not hardcoded |
| 11 | Motion / micro-interactions | `animate` | `review-animations`, `creative-coder`, `find-animation-opportunities` | Contract curves; `prefers-reduced-motion` honored |
| 12 | Accessibility | `accessibility-engineer`, `better-accessibility` | `accessibility-auditor`, `mobile-native` | Keyboard, focus, contrast, semantics pass |
| 13 | Visual QA | `frontend-visual-qa` | `audit`, `break`, `break-ui` | Rendered screenshots inspected at ≥3 viewports |
| 14 | UX review | `ux-heuristics`, `usability-psychologist` | `design-critique`, `interface-review` | Findings triaged P0–P3, P0 fixed |
| 15 | Polish | `polish`, `distill` | `quieter` / `bolder`, `delight` | Optical alignment, no decorative filler |
| 16 | Final review | `better-interface`, `design-reviewer` | `critique`, `interface-review` | Contract honored; drift report clean |

Read `references/stage-map.md` for full per-stage routing, entry/exit criteria, and the
overlap resolution table. Read `references/token-contract.md` for the token architecture
every stage inherits and the anti-slop rules this app must not regress into.

## Which skill wins when they disagree

This is the most important table in the repository.

| Decision | Authoritative | Others are advisory |
|---|---|---|
| End-to-end sequence | this skill + `design-pipeline` | `impeccable craft` is the build branch |
| Aesthetic direction | `frontend-design` | taste skills may propose, contract decides |
| Tokens, scales, variables | `design-system`, `ui-ux-pro-max` | everything else consumes |
| Typography rules | `better-typography` | `typeset` for the taste-level pass |
| Color rules and contrast | `better-colors` | `colorize`, `brand` |
| Spacing, grid, layout | `better-layout` | `layout`, `responsive-design` ref |
| Component polish, depth, radii | `better-ui` | `design-engineer` while writing code |
| Motion correctness | `review-animations`, `animate` | `creative-coder` for immersive work |
| A11y semantics | `accessibility-engineer` | `better-accessibility` for review |
| Rendered-output defects | `frontend-visual-qa` | `audit` for static scoring |
| Change-scoped review | `interface-review` → `better-interface` | `design-reviewer` for artifacts |
| Data-viz correctness | `data-visualization-discipline` | `frontend-visual-qa` for render defects |

**Known overlap, deliberately kept.** `better-*` (jakubkrehel) and `design-engineer`
both cover craft: use `better-*` for rule-level review, `design-engineer` while writing
code. `design-reviewer`, `design-critique` and `critique` all score work but differ in
kind — `critique` is quantitative UX scoring, `design-critique` is artifact critique,
`design-reviewer` is checklist review. Run them at different stages, never stacked on
the same surface in one turn.

## Contract drift check

Before finishing any design task, answer these. If any answer is no, the work isn't done.

- Did I reference contract tokens, or did I hardcode a value?
- Does every new component define all interaction states, including `:focus-visible`?
- Is contrast ≥ 4.5:1 for text and ≥ 3:1 for UI boundaries — in dark mode too?
- Does `prefers-reduced-motion` disable transforms and long transitions?
- Does the mobile layout use the same tokens and hierarchy as desktop?
- Did I reuse an existing component instead of creating a near-duplicate?
- Is anything decorative that carries no meaning? Cut it.

## Updating the contract

When a stage legitimately needs a new token, add it to `DESIGN.md` **in the same turn**
as the code that uses it, and note in your summary that the contract grew and why. A
token that exists only in a component is drift — `interface-review` finds it at stage 16
and it gets re-litigated.

## Repository constraint

This project's templates are server-rendered Jinja2 with an inline `<style>` block in
`base.html`. Token changes belong in that `:root` block (and its dark-mode counterpart),
not scattered through `dashboard.html`. When stage 5–8 grows the token set, keep it in
one place so stage 13 can audit it and stage 16 can diff it.
