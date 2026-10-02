"""The skills must actually be reached, and the claim must be checkable.

This exists because it was not true. A redesign was delivered with a summary asserting
twelve skills had been consulted; one had never been opened, five had been read only as
far as their frontmatter, and four explicit instructions inside those files — fetch the
guidelines URL, run the context setup, run the search tool, honour the manual-invocation
flag — had been skipped. Nothing in the build noticed, because "did you consult the design
expertise" was a claim rather than a check.

So it is a check now. A frontend file that changes without a current, specific entry in
`docs/ui-skill-log.md` fails the build. "Specific" means naming the rule that was pulled
out of the skill, the decision it changed and where that decision lives — a list of names is
the artefact that made the original claim uncheckable.

Two things this deliberately does **not** do:

* It does not verify that a skill was *invoked*. Codebuff loads skills through the `skill`
  tool and `/skill:name`; a `SKILL.md` read is neither. Whether that happened lives in the
  transcript, and this suite has no access to it. So the log is required to carry an
  explicit `invoked:` / `mechanism:` receipt naming which channel was used, and the session
  must declare whether the harness exposes invocation history at all. That forces the
  distinction to be stated; it cannot confirm the statement is true.
* It does not judge the design. A green suite means the expertise was consulted and
  recorded, nothing more. Visual quality is established by looking at the rendered app.
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
LOG = ROOT / "docs" / "ui-skill-log.md"

# Any change to the rendered surface counts. CSS and templates obviously; the JS because
# the drawer, the lightbox and the keyboard layer live there.
UI_GLOBS = (
    "src/vinted_sniper/web/static/*.css",
    "src/vinted_sniper/web/static/*.js",
    "src/vinted_sniper/web/templates/*.html",
)

DATE_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$", re.M)
SKILL_ENTRY = re.compile(r"^- \*\*([a-z0-9-]+)\*\*", re.M)
# A log field is a bullet under a skill entry, so it is indented and colon-terminated.
FIELD = r"^\s*-\s*{name}:"
MECHANISM_DECLARED = re.compile(FIELD.format(name="mechanism") + r"\s*(.+)$", re.M)

# The skills that must be reached before ANY frontend change, per AGENTS.md §2.
#
# Three govern quality and correctness; the four after them are the visual direction
# this product is built on. They are here, not in the conditional tier, because
# visual quality is a core requirement of this product and a UI change here is a
# visual-direction task rather than a mechanical one. An earlier version put them in
# a conditional tier to keep the mandate cheap to read; that made the skills that
# matter most optional, which is the opposite of what the tiering is for.
ALWAYS = (
    "impeccable",
    "ui-ux-pro-max",
    "web-design-guidelines",
    "frontend-design",
    "hallmark",
    "design-taste-frontend",
    "high-end-visual-design",
)

# Conditional: log these when the task actually touched that ground. They are not
# required, because requiring them on a copy change is the reading overhead the
# tiering exists to remove — but nothing stops a run from logging them anyway.
CONDITIONAL = ("animate", "review-animations", "improve-animations", "superdesign", "grill-me")

# How a skill can legitimately be reached. Kept closed on purpose: an open-ended
# mechanism field is a free-text field, and free text is where unverified claims go.
MECHANISMS = ("skill-tool", "slash-command", "file-read")

# Each Tier 1 entry owes the reader a full chain: how the skill was reached, what was
# taken from it, what changed because of it, and where that change can be seen.
REQUIRED_FIELDS = ("invoked", "extracted", "decided", "where")

# The false statement this suite exists partly to make impossible.
OVERCLAIMS = (
    r"gate (?:verifies|proves|confirms) (?:the )?invocation",
    r"verif(?:y|ied) (?:the )?skill (?:tool )?invocation by the (?:gate|test|suite)",
    r"invocation (?:is )?(?:machine[- ]checkable|verified) by",
)


@dataclass(frozen=True)
class Entry:
    day: dt.date
    skill: str
    body: str


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _entries(text: str) -> list[Entry]:
    """Every skill bullet in the log, with the block of sub-bullets beneath it.

    A block stops at the next skill bullet *or* the next date heading, so a later
    session's fields can never satisfy an earlier session's entry.
    """
    dates = [(m.start(), dt.date.fromisoformat(m.group(1))) for m in DATE_HEADING.finditer(text)]
    heads = [m.start() for m in DATE_HEADING.finditer(text)]
    entries: list[Entry] = []
    for match in SKILL_ENTRY.finditer(text):
        above = [day for pos, day in dates if pos < match.start()]
        if not above:
            continue
        end = min(
            [nxt.start() for nxt in SKILL_ENTRY.finditer(text) if nxt.start() > match.start()]
            + [pos for pos in heads if pos > match.start()],
            default=len(text),
        )
        entries.append(Entry(day=max(above), skill=match.group(1), body=text[match.end() : end]))
    return entries


def _newest(text: str) -> dt.date | None:
    days = [entry.day for entry in _entries(text)]
    return max(days) if days else None


def _missing_fields(entries: list[Entry], skills: tuple[str, ...]) -> dict[str, list[str]]:
    """{skill: [fields some entry of it did not record]}.

    Every entry is checked, not just the newest. A carried-forward note that skips the
    chain would otherwise borrow the chain from a fuller entry written earlier the same
    day, which is the borrowing habit this file exists to stop.
    """
    gaps: dict[str, list[str]] = {}
    for skill in skills:
        bodies = [e.body for e in entries if e.skill == skill]
        if not bodies:
            gaps[skill] = list(REQUIRED_FIELDS)
            continue
        gaps[skill] = sorted(
            {
                name
                for body in bodies
                for name in REQUIRED_FIELDS
                if not re.search(FIELD.format(name=name), body, re.M)
            }
        )
    return gaps


def test_the_log_exists_and_records_the_full_chain_for_every_always_skill() -> None:
    """A name is not a receipt. Each Tier 1 skill owes four things, or the entry is noise."""
    assert LOG.exists(), (
        f"{LOG.relative_to(ROOT)} is missing. Frontend work needs a record of which skills "
        f"were reached and what was taken from them — see AGENTS.md §2."
    )
    gaps = _missing_fields(_entries(LOG.read_text(encoding="utf-8")), ALWAYS)
    thin = {skill: names for skill, names in gaps.items() if names}
    assert not thin, (
        "these Tier 1 entries do not carry the full chain "
        "(invoked / extracted / decided / where), which proves nothing:\n  "
        + "\n  ".join(
            f"{skill}: missing {', '.join(names)}" for skill, names in sorted(thin.items())
        )
        + "\n\nAll seven are mandatory for frontend work in this project, and a name on its own "
        "is the artefact that made the original claim uncheckable."
    )


def test_mechanisms_are_declared_from_a_closed_set() -> None:
    """The mechanism must name a real channel, so a silent log cannot imply a `skill` call."""
    bad = [
        f"{entry.skill}: {line.strip()[:60]}"
        for entry in _entries(LOG.read_text(encoding="utf-8"))
        for line in MECHANISM_DECLARED.findall(entry.body)
        if not any(mech in line for mech in MECHANISMS)
    ]
    assert not bad, (
        f"a skill entry declares a mechanism outside the closed set {MECHANISMS}, so it "
        f"cannot be audited: " + "; ".join(bad)
    )


def test_the_session_declares_whether_invocation_is_observable() -> None:
    """If the harness exposes no invocation history, the log has to say so out loud."""
    text = LOG.read_text(encoding="utf-8")
    assert re.search(FIELD.format(name="observability"), text, re.M), (
        "the log has no `observability:` line. Whether the harness exposes skill-invocation "
        "history changes what an `invoked:` receipt is worth, and the reader cannot tell "
        "which they are looking at without it."
    )
    assert not any(re.search(pattern, text, re.I) for pattern in OVERCLAIMS), (
        "the log claims the gate verifies skill invocation. It cannot: invocation history "
        "lives in the transcript, not on disk, and this suite never sees it. The gate proves "
        "the record exists and is specific — nothing more."
    )


def test_agents_md_distinguishes_invocation_from_reading() -> None:
    """The distinction has to be written down, or the next run repeats the conflation."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "Invocation is not reading" in text, (
        "AGENTS.md no longer separates invoking a skill from reading its SKILL.md. A file "
        "open is not a `skill` call, and without the distinction the log will keep "
        "recording reads as though they were invocations."
    )


def test_the_visual_direction_skills_are_not_tier_two() -> None:
    """Guards the correction that produced this gate.

    The mandate was once tiered to be cheap to read, and the four design skills were
    filed as conditional. That made the skills this product exists to use optional,
    which inverted the point of tiering. If they are demoted again, this fails before
    the coverage quietly disappears.
    """
    text = AGENTS.read_text(encoding="utf-8")
    # Only the Tier 2 section, and only its table rows — the mapping from task type to
    # conditional skills. Prose under the table is allowed to name these skills: it says
    # things like "skipping `hallmark` on a visual redesign is not right", which a bare
    # substring search cannot tell apart from demoting it.
    section = text.split("### Tier 2", 1)[-1].split("### ", 1)[0]
    rows = [line for line in section.splitlines() if line.lstrip().startswith("|")]
    demoted = sorted({skill for skill in ALWAYS for row in rows if skill in row})
    assert not demoted, (
        f"Tier 1 skills are mapped in the conditional tier's table: {', '.join(demoted)}. "
        f"Visual direction is mandatory for this project; tiering exists to skip irrelevant "
        f"skills, not the relevant ones."
    )


def test_agents_md_only_names_skills_that_are_installed() -> None:
    """A mandate naming a missing skill is worse than no mandate: it reads as coverage."""
    text = AGENTS.read_text(encoding="utf-8")
    roots = [ROOT / ".agents" / "skills", Path.home() / ".agents" / "skills"]
    for name in sorted(set(re.findall(r"`([a-z][a-z0-9-]{2,})`", text))):
        if name not in ALWAYS and name not in CONDITIONAL:
            continue
        if any((root / name / "SKILL.md").exists() for root in roots):
            continue
        pytest.fail(
            f"AGENTS.md mandates '{name}', which is not installed in .agents/skills or "
            f"~/.agents/skills. Install it or drop it from the mandate."
        )


@pytest.mark.skipif(_git("rev-parse", "--git-dir") is None, reason="not a git checkout")
def test_the_log_is_current_with_the_last_frontend_commit() -> None:
    """The teeth: a UI commit dated after the newest logged read fails."""
    log_date = _newest(LOG.read_text(encoding="utf-8"))
    assert log_date is not None, "the log has no dated entries"

    out = _git("log", "-1", "--format=%cI", "--", *UI_GLOBS)
    if not out:
        pytest.skip("no commits touching the frontend yet")
    committed = dt.datetime.fromisoformat(out).date()
    assert log_date >= committed, (
        f"the last frontend commit is {committed}, but the newest skill-log entry is "
        f"{log_date}. Reach the Tier 1 skills, log what you took from them, and commit "
        f"both together."
    )


@pytest.mark.skipif(_git("rev-parse", "--git-dir") is None, reason="not a git checkout")
def test_uncommitted_frontend_work_carries_a_logged_read() -> None:
    """Uncommitted work is the common state. It needs the entry too, or the commit will
    land without one and fail the check above."""
    dirty = _git("diff", "--name-only", "--", *UI_GLOBS)
    if not dirty:
        pytest.skip("no uncommitted frontend changes")
    log_dirty = _git("status", "--porcelain", "--", str(LOG.relative_to(ROOT)))
    assert log_dirty, (
        "there are uncommitted frontend changes but docs/ui-skill-log.md is untouched. "
        "Log the skills you reached before you commit."
    )


def test_the_ledger_still_records_why_the_mandate_is_tiered() -> None:
    """The tiering exists because the flat twelve-skill list was not being read. If
    someone re-flattens it without saying so, this fails."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "Tier 1" in text and "Tier 2" in text, (
        "AGENTS.md no longer tiers the mandate. The flat list is what got skipped; put it "
        "back only with a reason recorded in docs/ui-skill-log.md."
    )
