# design

A Claude Code skill for any visual design or UI/UX task — designing or redesigning screens, components, landing pages, dashboards, or mockups; auditing existing UI; implementing a Figma file as code; choosing color, typography, layout, motion, or spacing.

Synthesizes four lineages — *impeccable*, *ui-ux-pro-max*, *taste-skill*, *huashu-design* — and wires them to a Playwright verification loop. Loads reference files on demand, not all at once.

## Why this exists

Most AI-generated UI fails on a handful of reflex moves: Inter for everything, purple→blue gradients, identical 3-card grids, pure black on saturated color. This skill refuses those by default and forces a defensible direction before any markup is written.

## What's inside

- `SKILL.md` — the entry point. The six-step workflow (ground → direction → category check → build → verify → ship) and request patterns.
- `reference/anti-slop.md` — the full catalog of patterns to refuse.
- `reference/brand-protocol.md` — what to do when there's no brand spec.
- `reference/industry-rules.md` — category-aware defaults (legal ≠ wellness ≠ fintech).
- `reference/color.md` · `typography.md` · `space.md` · `motion.md` · `interaction.md` · `responsive.md` · `copy.md` — load on demand.
- `reference/audit.md` — three-issues-max critique format.
- `reference/checklist.md` — pre-delivery gate.

## Install

Drop the folder into your Claude Code skills directory:

```bash
git clone https://github.com/sboghossian/design-skill.git ~/.claude/skills/design
```

The skill auto-loads when Claude Code starts. Invoke by asking for any design work, or with `/design` if your harness supports skill slash commands.

## Workflow at a glance

1. **Ground in reality** — find `brand-spec.md`, tokens, Figma, or screenshots before designing. Never start blank.
2. **State the direction** — one line: color strategy, type stance, density/motion/variance dials.
3. **Category check** — refuse the cliché for the industry.
4. **Build** — pull reference files as needed.
5. **Verify in browser** — Playwright screenshots at 375 / 768 / 1440. No "looks great" without evidence.
6. **Ship** — run the pre-delivery checklist.

## License

MIT.
