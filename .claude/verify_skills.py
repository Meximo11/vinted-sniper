#!/usr/bin/env python3
"""Verify every installed skill under .claude/skills is a valid, self-contained
Claude skill: SKILL.md present, YAML frontmatter with a name matching the
directory and a non-empty description, and no dangling internal references."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "skills"
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
RAW_REF = re.compile(r"`((?:reference|references|scripts|evals|assets)/[A-Za-z0-9._/-]+)`")
SIBLING = re.compile(r"`\.\./([a-z0-9-]+)/SKILL\.md`")

errors: list[str] = []
warns: list[str] = []
cross_skill: list[str] = []
output_paths = 0
rows: list[tuple[str, int, int, int]] = []  # name, skill_lines, ref_files, skill_files

FRONTMATTER_PARTS = 3  # opening '---', frontmatter block, body
MIN_BODY_CHARS = 200

for d in sorted(p for p in ROOT.iterdir() if p.is_dir()):
    skill = d / "SKILL.md"
    if not skill.is_file():
        errors.append(f"{d.name}: missing SKILL.md")
        continue

    text = skill.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        errors.append(f"{d.name}: no YAML frontmatter")
        continue
    parts = text.split("---", FRONTMATTER_PARTS)
    if len(parts) < FRONTMATTER_PARTS:
        errors.append(f"{d.name}: unterminated frontmatter")
        continue
    fm, body = parts[1], parts[2]

    name_m = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
    desc_m = re.search(r"^description:\s*(.+?)\s*$", fm, re.M | re.S)
    if not name_m:
        errors.append(f"{d.name}: frontmatter has no 'name'")
    elif name_m.group(1).strip().strip("\"'") != d.name:
        errors.append(f"{d.name}: frontmatter name '{name_m.group(1).strip()}' != directory name")
    if not desc_m or not desc_m.group(1).strip():
        errors.append(f"{d.name}: frontmatter has no 'description'")
    if len(body.strip()) < MIN_BODY_CHARS:
        warns.append(f"{d.name}: body is only {len(body.strip())} chars")

    # dangling internal references
    refs: set[str] = set()
    for m in MD_LINK.finditer(text):
        refs.add(m.group(1))
    for m in RAW_REF.finditer(text):
        refs.add(m.group(1))
    for m in SIBLING.finditer(text):
        refs.add(f"__sibling__{m.group(1)}")

    ref_files = sum(1 for p in d.rglob("*") if p.is_file())
    skill_files = sum(1 for p in d.rglob("*.md"))

    for raw in sorted(refs):
        if raw.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if raw.startswith("__sibling__"):
            sib = d.parent / raw[len("__sibling__") :] / "SKILL.md"
            if not sib.is_file():
                errors.append(f"{d.name}: dangling sibling -> {raw[len('__sibling__') :]}/SKILL.md")
            continue
        r = raw.strip("<>").split("#", 1)[0]  # unwrap <path>, drop heading anchors
        if not r:
            continue
        if (d / r).exists():
            continue
        # Several skills cite files that live in a sibling skill, naming the
        # sibling in prose (e.g. taste's layout -> impeccable's spatial-design).
        # Resolve against any installed skill that actually ships that file.
        target = Path(r).name
        owners = [
            sib.name for sib in ROOT.iterdir() if sib.is_dir() and sib != d and (sib / r).is_file()
        ] or [
            sib.name
            for sib in ROOT.iterdir()
            if sib.is_dir() and sib != d and any(p.name == target for p in sib.rglob(target))
        ]
        if owners:
            cross_skill.append(f"{d.name} -> {r}  (found in: {', '.join(sorted(owners))})")
            continue
        # `assets/...` in these skills are files the skill *writes into the
        # user's project*, not files the skill ships. Not a packaging defect.
        if r.startswith(("assets/", "docs/", "src/")):
            output_paths += 1
            continue
        errors.append(f"{d.name}: dangling reference -> {r}")

    rows.append((d.name, text.count("\n"), ref_files, skill_files))

total_md = sum(r[3] for r in rows)
total_files = sum(r[2] for r in rows)
print(f"Skills installed : {len(rows)}")
print(f"Markdown files   : {total_md}")
print(f"Total files      : {total_files}")
print()
for n, lines, rf, sf in rows:
    print(f"  {n:<42} SKILL.md {lines:>4} lines   {sf:>3} md   {rf:>3} files")
print()
if warns:
    print(f"WARNINGS ({len(warns)}):")
    for w in warns:
        print("  -", w)
    print()
if cross_skill:
    print(f"CROSS-SKILL REFERENCES ({len(cross_skill)}) - resolve to a sibling skill:")
    for c in cross_skill:
        print("  -", c)
    print()
print(f"PROJECT-OUTPUT PATHS ({output_paths}) - files the skill writes, not ships.")
print()
if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("OK: all skills valid, no dangling references.")
