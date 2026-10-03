# Skill Stack — Provenance & Maintenance

Professional product-design skill stack for **vinted-sniper**.
88 skills under `.claude/skills/`, all upstream-authored, installed repository-locally
so they work as Claude slash commands (`/skill-name`).

**Start every design task with `/design-orchestrator`.** It routes this stack through
one 16-stage workflow and owns the token contract. Do not invoke design skills at random.

Verify integrity at any time:

```bash
python3 .claude/verify_skills.py
```

---

## Upstream sources

| Source repo | Skills | Notes |
|---|---|---|
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | `ui-ux-pro-max`, `design-system`, `ui-styling`, `brand` | Official upstream. Ships CSV catalogs, token validators |
| [sboghossian/design-skill](https://github.com/sboghossian/design-skill) | `design` | Anti-slop synthesis; 12 `reference/` files |
| [richhemsley3/claude-design-skills](https://github.com/richhemsley3/claude-design-skills) | 18 skills (`design-pipeline` …) | Full suite; `design-pipeline` cross-references siblings via `../`, so it is installed whole |
| [tyfarrago-hub/taste](https://github.com/tyfarrago-hub/taste) | 30 skills | MIT. `impeccable` + `animate` are the pre-existing pair |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | `frontend-design` | Official `plugins/frontend-design`, Apache 2.0 |
| [WomenDefiningAI/claude-code-skills](https://github.com/WomenDefiningAI/claude-code-skills) | `frontend-ui` | |
| [dannyjpwilliams/design-engineer-skill](https://github.com/dannyjpwilliams/design-engineer-skill) | `design-engineer` | |
| [jakubkrehel/skills](https://github.com/jakubkrehel/skills) | 11 skills (`better-*` + reviewers) | `better-interface` routes to the `better-*` family by design |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 10 skills | Upstream home of the pre-existing `improve-animations` + `review-animations` |
| [mae616/design-skills](https://github.com/mae616/design-skills) | 5 skills | UX/human factors |
| [daymade/claude-code-skills](https://github.com/daymade/claude-code-skills) | `frontend-visual-qa`, `design-from-reference`, `data-visualization-discipline` | Playwright-based rendered-UI audit |
| [MadAppGang/claude-code](https://github.com/MadAppGang/claude-code) | `ui-implementer`, `ui-design-review`, `design-references` | |

Full `reference/`, `scripts/`, `evals/`, `templates/`, and `data/` trees are included
wherever the upstream skill ships them.

---

## Pre-existing skills (kept, not replaced)

| Skill | Upstream | Status |
|---|---|---|
| `impeccable` | tyfarrago-hub/taste | Kept as-is, incl. `reference/` + `scripts/` |
| `animate` | tyfarrago-hub/taste | Kept as-is |
| `improve-animations` | emilkowalski/skills | Kept as-is, incl. `AUDIT.md`, `PLAN-TEMPLATE.md` |
| `review-animations` | emilkowalski/skills | Kept as-is, incl. `STANDARDS.md` |

None of the four existed in the repository before this task — `.claude/` was empty.
`improve-animations` and `review-animations` were traced to their upstream
(`emilkowalski/skills`) and installed from the official repository rather than recreated.

---

## Duplicates avoided

| Skill | Kept | Dropped | Reason |
|---|---|---|---|
| `ui-ux-pro-max` | official (nextlevelbuilder) | taste's copy | Official carries 3× the data (3061 vs 752 CSV rows), scripts, and tests |
| `emil-design-eng` | taste's copy | emilkowalski upstream | Taste's includes the Radix `transform-origin` fix. Delta is otherwise 5 lines |
| `animate` | taste's | emilkowalski upstream | Pre-existing skill; gates on `/impeccable` |
| `ui-designer` | mae616's | daymade's → renamed `design-from-reference` | Name collision. mae616 designs screens; daymade's extracts a system from a reference image |
| opencode `agents/openai.yaml` | — | removed from all `better-*` skills | Opencode-specific, not Claude |

Deliberate overlaps that were **kept** (they serve different stages, not duplicates):
`break` / `break-ui`, `variant` / `prototype`, `better-*` vs `design-engineer`,
`critique` / `design-critique` / `design-reviewer`,
`accessibility-engineer` / `accessibility-auditor` / `better-accessibility`,
`design` vs `impeccable`. See `skills/design-orchestrator/references/stage-map.md`
for the full resolution table.

---

## Local modifications

Skills are installed verbatim. Only these deliberate changes were made:

1. **`design-from-reference`** — `name:` changed from `ui-designer` to avoid colliding
   with mae616's `ui-designer`. Body untouched.
2. **`design-orchestrator`** — authored for this repository (not upstream). Owns the
   workflow, the token authority table, and the anti-slop gates.
3. **`harden`** — upstream shipped an unquoted `description` containing `: `, which is
   invalid YAML and would fail to load. Quoted the string. Verified the description
   text and body are byte-identical to upstream.
4. **`user-invocable: false` → `true`** on the five mae616 skills
   (`accessibility-engineer`, `creative-coder`, `frontend-implementation`,
   `ui-designer`, `usability-psychologist`) so they appear as slash commands. Upstream
   ships them model-invocation-only.

---

## Updating a skill

```bash
git clone --depth 1 <upstream> /tmp/src
cp -R /tmp/src/<path-to-skill> .claude/skills/<name>
python3 .claude/verify_skills.py
```

Re-apply the four local modifications above if the update overwrites them.

## Known gaps

- **`frontend-visual-qa`** (stage 13) needs Playwright and a running server; neither is
  wired up. Until then use `audit` (taste) as the static substitute.
- **`ui-styling`** assumes shadcn/Tailwind/React. This project is server-rendered
  Jinja2 with an inline `<style>` block. Use its rules, not its install steps.
- **`ui-implementer`** expects a component framework. Pair with
  `frontend-implementation` for Jinja2 templates.
- **`ui-styling`** carries ~5.5 MB of canvas fonts used only by its poster feature.
  Remove `canvas-fonts/` if repo size matters; nothing else depends on it.
