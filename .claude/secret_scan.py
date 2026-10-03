#!/usr/bin/env python3
"""Approximate the CI gitleaks 'detect' pass locally, since the secrets job runs
gitleaks in Docker and Docker is unavailable in this sandbox.

Scans the untracked working tree for the patterns that actually matter here:
live provider credential formats, and keyword-style assignments whose value is
long, high-entropy and not an obvious placeholder.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGETS = [ROOT / "skills", ROOT / "SKILLS.md"]

# Real provider credential formats. A hit on any of these is a true positive.
LIVE = [
    ("github classic", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("github fine-grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai", re.compile(r"\bsk-(proj-)?[A-Za-z0-9]{32,}")),
    ("aws access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# gitleaks 'generic' rule: KEY = "value". Value must be long and high-entropy,
# and must not be an obvious placeholder or a runtime lookup.
KEYWORD = re.compile(
    r"(?i)\b[\"']?[A-Za-z0-9_.-]*(?:secret|token|api_?key|passwd|password)"
    r"[\"']?\s*[:=]\s*[\"']([^\"'\n]{8,})[\"']"
)
PLACEHOLDER = re.compile(
    r"(?i)(example|placeholder|your[_-]|xxxx|dummy|fake|sample|redact|"
    r"todo|changeme|notreal|abc123|test|mock|spec|<[A-Z_]+>|\$\{|\{\{|"
    r"process\.env|os\.environ|getenv|env\.|none|null|true|false)"
)
# Secret-looking words in prose ("the token is stored in...") are not secrets.
ALLOWED_WORDS = {"true", "false", "none", "null", "undefined", "required", "optional", "string"}

# Every text-bearing extension actually shipped under .claude/, so nothing is
# silently skipped. Binary fonts/images are skipped via the null-byte check.
TEXT_SUFFIXES = {
    ".cfg",
    ".cjs",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sample",
    ".sh",
    ".svg",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

# A generic-rule hit needs a value this long and this mixed to count as a secret.
MIN_VALUE_CHARS = 12
MIN_ENTROPY_BITS = 3.5


def shannon(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def scan_text(text: str, rel: str) -> list[str]:
    """Return every finding in one file's text. Split out to keep main simple."""
    out = []
    for label, pattern in LIVE:
        for m in pattern.finditer(text):
            out.append(f"LIVE {label} -> {rel}:{text[: m.start()].count(chr(10)) + 1}")
    for m in KEYWORD.finditer(text):
        value = m.group(1).strip()
        if value.lower() in ALLOWED_WORDS or PLACEHOLDER.search(value):
            continue
        if len(value) >= MIN_VALUE_CHARS and shannon(value) >= MIN_ENTROPY_BITS:
            out.append(f"GENERIC keyword -> {rel}:{text[: m.start()].count(chr(10)) + 1}")
    return out


def main() -> int:
    findings: list[str] = []
    scanned = 0

    for target in TARGETS:
        files = [target] if target.is_file() else list(target.rglob("*"))
        for f in files:
            if not f.is_file() or f.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                raw = f.read_bytes()
            except OSError:
                continue
            # Fonts and images carry no text; scanning them as text is noise.
            if b"\x00" in raw[:4096]:
                continue
            scanned += 1
            findings.extend(
                scan_text(raw.decode("utf-8", errors="replace"), str(f.relative_to(ROOT)))
            )

    print(f"files scanned: {scanned}")
    print(f"findings     : {len(findings)}")
    for f in findings[:50]:
        print("  -", f)
    if findings:
        return 1
    print("CLEAN: no live credentials or high-entropy keyword values found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
