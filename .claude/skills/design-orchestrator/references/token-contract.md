# Token Contract

Companion to `../SKILL.md`. The architecture every stage inherits, plus the quality
gates that stop this UI from regressing into generic output.

---

## Current state (vinted-sniper)

The app is server-rendered Jinja2. All CSS lives in a single inline `<style>` block in
`src/vinted_sniper/web/templates/base.html`. Tokens are CSS custom properties on
`:root` with a dark-mode block. This is a **good** foundation — flat, greppable, no
build step. Keep it.

### The seed palette

```css
:root {
  --bg:    #fbfbfa;  --panel: #ffffff;  --ink: #1a1a1a;  --muted: #6b6b6b;
  --line:  #e4e4e1;  --accent: #09b1ba;
  --ok:    #2e7d32;  --warn: #b26a00;  --bad: #c62828;
}
```

The dark block redefines the same nine names with lighter values. **This symmetry is the
rule**: a token that exists in only one theme is a bug.

Current components: `.card`, `.pill` (`.ok` / `.warn` / `.failing`), `button` and
`button.quiet`, `.listing`, `.tag`, `.error`, `.muted`, plus form `label` + input.

### What the seed contract still lacks

Stage 5 formalizes these; until then, treat them as open and do not invent per-component
values:

- **Spacing scale.** Padding/gap are currently ad-hoc (`0.75rem`, `0.5rem 0.6rem`,
  `0.02rem 0.4rem`). Define a 4px-based scale and map every existing value onto it.
- **Radius scale.** Currently ad-hoc: `10px` (`.card`), `7px` (`.pill`), `6px`
  (`.tag`), `999px` (fully rounded), `0` (image reset). Define concentric steps.
- **Type scale.** Sizes are ad-hoc: `0.72rem`, `0.8rem`, `0.82rem`, `0.85rem`, `1rem`.
  Define a scale with a ratio and snap every size onto it.
- **Elevation.** Currently flat — `1px solid var(--line)` everywhere. Define 0–3
  elevation steps, most of which are border-only.
- **Motion.** No durations or curves defined at all. Define a 2–3 step duration scale
  and 2 curves (standard, emphasized).
- **Font stack.** `base.html:21` sets `font: 15px/1.55 ui-sans-serif, system-ui,
  -apple-system, "Segoe UI", sans-serif`. A system stack is a deliberate,
  zero-latency choice — but it is currently undocumented, so stage 6 must either
  record it as intentional or replace it. See below.

---

## Three-layer token architecture

Follow the `design-system` skill (ui-ux-pro-max) convention. Layers may only reference
the layer above them, never skip.

```css
/* 1. PRIMITIVE — raw values, no meaning */
--teal-500: #09b1ba;
--stone-50: #fbfbfa;
--space-1: 0.25rem;
--radius-md: 0.5rem;

/* 2. SEMANTIC — meaning, theme-aware */
--color-accent: var(--teal-500);
--surface-bg: var(--stone-50);
--space-gap-inline: var(--space-1);

/* 3. COMPONENT — scoped to one component */
--button-bg: var(--color-accent);
--button-radius: var(--radius-md);
```

**Why it matters here:** swapping `--teal-500` in the dark block re-themes every
semantic and component token at once. Hardcoded values in `dashboard.html` bypass all of
it — that is the drift this architecture exists to prevent.

Rules:
- Never reference a primitive from a component. Component → semantic → primitive only.
- Never hardcode a hex, radius, or duration in a component rule.
- Semantic names describe *role* (`--color-danger`), never *hue* (`--color-red`).

---

## Typography: the Inter question

`base.html:21` sets a system stack via the `font:` shorthand —
`ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` — so the UI renders
in the platform's UI sans-serif, not the Times browser default. That is a real choice
and an efficient one for a self-hosted tool: no webfont request, no layout shift, no
FOUT, works offline.

The gap is that the choice is *undocumented* and *inconsistent in how it is applied*.
It is applied once on `body` through the `font:` shorthand, while every control then
re-declares `font: inherit` — which works, but means the stack lives in a shorthand
rather than as a token. Stage 6 should lift it into a `--font-sans` token, record the
reasoning, and then decide whether it stays.

Inter is not *forbidden* — it is the **unjustified default**. It is acceptable when it
is chosen deliberately and paired well. It is not acceptable as "whatever the framework
ships." Justify the pairing in `DESIGN.md` in one sentence, or choose something with
more character.

Whatever is chosen:
- Define the stack with real fallbacks (`"X", system-ui, -apple-system, "Segoe UI", sans-serif`).
- Load with `font-display: swap` and subset. Never block first paint on a webfont.
- Pair a display face with a text face, or use one family across three weights.
- Keep measure at 60–75ch for body copy. This app has long listing titles — they must
  wrap, not overflow.

`ui-ux-pro-max` ships `data/typography.csv` (75 pairings) and
`data/google-fonts.csv` (1935 faces) for lookup. `better-typography` supplies the rules.

---

## Anti-slop gates

These are pass/fail checks for any design work in this repo. They map to the user's
stated premium-quality bar.

### Banned

- **Purple/blue gradient clichés.** No `linear-gradient(135deg, #6366f1, #a855f7)` as
  decoration. A gradient must encode something — a direction, a state, a temperature.
- **Random glassmorphism.** `backdrop-filter: blur()` only over genuinely moving
  content (an overlay above a scrolling list). Never on a static card.
- **Excessive rounded cards.** Cards are for repeated items and grouped content, not
  every paragraph. If everything is a card, nothing is.
- **Excessive shadows.** Prefer `1px solid var(--line)`. Reserve shadow for true
  elevation — overlays and popovers.
- **Meaningless gradients and decorative shapes.** If removing it loses no information,
  remove it.
- **Decorative elements without purpose.** No blob backgrounds, no floating circles.
- **Unnecessary animation.** Motion that doesn't explain a state change is noise. See
  `find-animation-opportunities`, which explicitly rejects what should *not* move.

### Required

- **One visual identity.** Every surface derives from the same palette, type, radius,
  and motion language. A screen that looks imported from another product is a failure.
- **Consistent component states.** Any new interactive element gets all states
  including `:focus-visible`. The existing `.pill` has no hover and no focus — fix when
  touching it.
- **Mobile and desktop feel like one product.** Same tokens, same hierarchy. Check at
  375px, 768px, 1280px.
- **Empty, loading, and error states** for every data surface. `harden` (taste) covers
  this; `frontend-visual-qa` verifies it in the render.

---

## Motion language

Undefined today. Define at stage 11, using `animate` and `review-animations`.

| Token | Value | Use |
|---|---|---|
| `--duration-fast` | ~120ms | Hover, focus, color/opacity |
| `--duration-base` | ~200ms | Most transitions, disclosure |
| `--duration-slow` | ~320ms | Larger surfaces, page-level |
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Default |
| `--ease-emphasized` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | Enter/exit, attention |

Hard rules:
- Enter animations **ease out**, exit animations **ease in**. Getting this backwards is
  the single most common motion bug (`review-animations` catches it).
- Animate `transform` and `opacity` only. Animating `width`, `height`, `top`, or
  `left` forces layout on every frame.
- Respect `prefers-reduced-motion`: disable transforms and long transitions. Reduce,
  don't remove — opacity cross-fades are usually fine.
- Touch targets ≥ 44×44px (`better-accessibility/hit-areas.md`).

---

## Accessibility gates

WCAG 2.2 AA. Verify in **both** themes — the dark palette was checked less
historically and is likelier to fail.

- Text contrast ≥ 4.5:1; UI boundaries and focus rings ≥ 3:1.
- `--muted` on `--bg` is the highest-risk pairing in the palette. Verify both themes.
- Every form field has a real `<label>`. `login.html` and the dashboard's form fields
  must be checkable by clicking the label.
- Status is never conveyed by color alone — `.pill` must carry text, not just
  `--ok`/`--warn`/`--bad` hue.
- Every interactive element is keyboard reachable with a visible focus indicator.
- Images have `alt`; decorative images have `alt=""`.
- Zoom to 200% without loss of content or function.

---

## Verification commands

```bash
# Contract validation (design-system skill)
node .claude/skills/design-system/scripts/validate-tokens.cjs --dir src/

# Full skill-stack integrity
python3 .claude/verify_skills.py

# Hardcoded value hunt — expect matches, then confirm each is intentional
grep -rnE '#[0-9a-fA-F]{3,8}|cubic-bezier\(|[0-9]+px' src/vinted_sniper/web/templates/
```

Run these at stage 16. The grep is expected to find the `:root` block itself — every
match *outside* it is drift.
