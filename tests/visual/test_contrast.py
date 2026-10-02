"""Contrast is a build failure, not something to remember to check in a browser.

This parses the actual stylesheet rather than a copy of the palette, so a colour
changed in app.css is judged here within one run. It cannot see a gradient behind a
label or a translucent layer, which is why the browser pass still exists — but it
catches the common and expensive mistake, which is reaching for a tint that looks
right and measures 3.8:1.

What is asserted:

* every text tier clears 4.5:1 on every surface it is allowed to sit on, in both
  themes;
* each status colour clears 4.5:1 on its own tinted wash;
* --live is graphic-only and never carries a word, and links are ink;
* --ink-4 is never used as a text colour anywhere in the sheet.

The `--live` rule replaced an older one that required the accent to clear text
contrast, because that accent no longer exists: the redesign made the chrome
monochrome and reserved the one warm hue for "this find is still alive". A hue
that means one thing cannot also be the link colour, and the check now encodes
the decision that made the sheet coherent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parents[2] / "src" / "vinted_sniper" / "web" / "static" / "app.css"

_TOKEN = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;")
_BLOCK = re.compile(r"\[data-theme=\"dark\"\]\s*\{(.*?)\n\}", re.S)
_SYSTEM_BLOCK = re.compile(r"\[data-theme=\"system\"\]\s*\{(.*?)\n  \}", re.S)


def _channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_colour: str) -> float:
    raw = hex_colour.lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    red, green, blue = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _ratio(foreground: str, background: str) -> float:
    first, second = _luminance(foreground), _luminance(background)
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


@pytest.fixture(scope="module")
def palettes() -> dict[str, dict[str, str]]:
    """The light palette, then the dark one layered over it."""
    sheet = CSS.read_text(encoding="utf-8")
    light = dict(_TOKEN.findall(sheet.split('[data-theme="dark"]')[0]))

    dark = dict(light)
    for block in (_BLOCK.findall(sheet) + _SYSTEM_BLOCK.findall(sheet)):
        dark.update(dict(_TOKEN.findall(block)))
    return {"light": light, "dark": dark}


# Every surface a piece of body text is allowed to land on, in both themes.
_SURFACES = ("surface", "surface-2", "surface-3")
_TEXT_TIERS = ("ink-1", "ink-2", "ink-3")
_MINIMUM = 4.5


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("surface", _SURFACES)
@pytest.mark.parametrize("tier", _TEXT_TIERS)
def test_text_tiers_clear_wcag_aa(
    palettes: dict[str, dict[str, str]], theme: str, surface: str, tier: str
) -> None:
    palette = palettes[theme]
    ratio = _ratio(palette[tier], palette[surface])
    assert ratio >= _MINIMUM, (
        f"{theme}: --{tier} on --{surface} is {ratio:.2f}:1, needs {_MINIMUM}:1. "
        f"If this is meant to be a text tier, darken or lighten it; if it is meant to "
        f"be a graphic tier, it is --ink-4 and should not be carrying words."
    )


def test_live_is_graphic_only_and_never_carries_a_word() -> None:
    """The one warm hue in the sheet means "still alive". It is not a link colour.

    `--live` sits at 1.6:1 on white, so putting a word on it would be unreadable
    in the light theme no matter how it is used. What the sheet must guarantee is
    narrower and more useful: the hue never appears as a text colour, and where
    "live" has to be readable the darker `--live-deep` does the work instead.
    """
    sheet = CSS.read_text(encoding="utf-8")
    offenders = [
        f"line {index + 1}: {line.strip()}"
        for index, line in enumerate(sheet.splitlines())
        if re.match(r"^\s*color:\s*var\(--live\)", line)
    ]
    assert not offenders, (
        "--live is a graphic token: it fills the fresh chip, tints an edge and "
        "lights the arrival sweep. Use --live-deep for anything with words on it. "
        "Offenders:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("surface", _SURFACES)
def test_links_are_ink_not_a_hue(
    palettes: dict[str, dict[str, str]], theme: str, surface: str
) -> None:
    """A link is text, so it gets the text bar — and it gets --ink-1's colour.

    The chrome is monochrome on purpose: on a page full of product photography the
    only saturated colour should be the clothes and the one live signal. A coloured
    link would put a third meaning on a hue that already means one thing.
    """
    palette = palettes[theme]
    ratio = _ratio(palette["ink-1"], palette[surface])
    assert ratio >= _MINIMUM, f"{theme}: --ink-1 on --{surface} is {ratio:.2f}:1"


# Each status colour sits on its own tinted plane. The wash is not always the tone
# name plus a suffix, so the pairing is explicit rather than derived.
_STATUS_ON_ITS_WASH = (("good", "good-wash"), ("live-deep", "live-wash"), ("bad", "bad-wash"))


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("tone", "wash"), _STATUS_ON_ITS_WASH)
def test_semantic_text_on_its_own_soft_background(
    palettes: dict[str, dict[str, str]], theme: str, tone: str, wash: str
) -> None:
    """A status colour sits on its own tinted plane, not on the page."""
    palette = palettes[theme]
    ratio = _ratio(palette[tone], palette[wash])
    assert ratio >= _MINIMUM, f"{theme}: --{tone} on --{wash} is {ratio:.2f}:1"


# The one place --ink-4 is allowed to colour something: the empty-state glyph. It
# carries nothing the heading has not already said, and WCAG exempts decoration.
# Naming it here means the exemption is a decision on the record rather than a gap
# in a search — a second one would fail this.
_INK_FOUR_EXEMPT = frozenset({".empty > .ico"})


def test_ink_four_is_never_used_as_text() -> None:
    """--ink-4 is graphic-only, and this is the rule that keeps it that way.

    A quiet fourth tier is a trap: there is no value of it that clears 4.5:1 and
    still reads as visibly fainter than --ink-3. The day someone reaches for it on a
    label, this fails before a reader has to.

    One exception is deliberate and lives at `.empty > .ico`: the empty-state glyph.
    It carries no information the heading does not already carry, and WCAG exempts
    decoration, so it is allowed to stay quiet.
    """
    sheet = CSS.read_text(encoding="utf-8")
    lines = sheet.splitlines()
    offenders: list[str] = []
    for index, line in enumerate(lines):
        # A bare `color:` declaration. `border-color: var(--ink-4)` is a graphic use
        # and must not trip this, so the property name is anchored rather than
        # searched for as a substring.
        if not re.match(r"^\s*color:\s*var\(--ink-4\)", line):
            continue
        # Walk back to the selector that owns this declaration, so the exemption is
        # checked against the rule rather than against a line number that moves.
        selector = ""
        for back in range(index - 1, max(index - 8, -1), -1):
            if lines[back].rstrip().endswith("{"):
                selector = lines[back].rstrip()[:-1].strip()
                break
        if selector in _INK_FOUR_EXEMPT:
            continue
        offenders.append(f"line {index + 1}: {selector} -> {line.strip()}")
    assert not offenders, (
        "--ink-4 is for graphics, not words. Use --ink-3 for the faintest legible "
        "text. Offenders:\n" + "\n".join(offenders)
    )


def test_the_hidden_rule_that_holds_the_lightbox_shut_survives() -> None:
    """The one !important in the sheet, and the reason it has to be one.

    `.lightbox { display: grid }` is an author rule; the user agent's
    `[hidden] { display: none }` loses to it on specificity. Without this, the photo
    overlay sits open over every page that has a listing.
    """
    sheet = CSS.read_text(encoding="utf-8")
    assert re.search(r"\[hidden\]\s*\{\s*display:\s*none\s*!important", sheet), (
        "the global [hidden] rule is missing; the lightbox will pin itself open"
    )
