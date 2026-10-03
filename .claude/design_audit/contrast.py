#!/usr/bin/env python3
"""Stage 7 (color) + Stage 12 (accessibility) evidence for vinted-sniper.

Computes exact WCAG 2.x contrast ratios for the token pairs the templates
actually use, in both light and dark themes, including the color-mix() pill
backgrounds. No guessing: every number here is derived from the hex values in
base.html.
"""

from __future__ import annotations

LIGHT = {
    "bg": "#fbfbfa",
    "panel": "#ffffff",
    "ink": "#1a1a1a",
    "muted": "#6b6b6b",
    "line": "#e4e4e1",
    "accent": "#09b1ba",
    "ok": "#2e7d32",
    "warn": "#b26a00",
    "bad": "#c62828",
}
DARK = {
    "bg": "#17181a",
    "panel": "#1f2023",
    "ink": "#ececea",
    "muted": "#9a9a97",
    "line": "#313337",
    "accent": "#35c9d1",
    "ok": "#7dc47f",
    "warn": "#e2a44a",
    "bad": "#ef7b7b",
}
# Hard-coded value in the stylesheet that is deliberately NOT a token.
OFFTOKEN_BUTTON_INK = "#06282a"

TEXT_MIN = 4.5
UI_MIN = 3.0
SRGB_KNEE = 0.03928
PILL_MIX_PCT = 18.0
ROOT_PX = 16

# A pair under these sizes is hard to read regardless of ratio.
TINY_PX = 12
SMALL_PX = 14


def to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def linearise(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= SRGB_KNEE else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (linearise(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    a, b = luminance(to_rgb(fg)), luminance(to_rgb(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def mix(color: str, pct: float, over: str) -> str:
    """color-mix(in srgb, C pct%, transparent) composited over an opaque backdrop.

    This is the colour the text actually sits on, not the nominal one.
    """
    c, o = to_rgb(color), to_rgb(over)
    return "#" + "".join(
        f"{round(c[i] * pct / 100 + o[i] * (1 - pct / 100)):02x}" for i in range(3)
    )


def check(*, label: str, fg: str, bg: str, kind: str, theme: str, where: str) -> bool:
    r = ratio(fg, bg)
    need = TEXT_MIN if kind == "text" else UI_MIN
    ok = r >= need
    print(
        f"  {'PASS' if ok else 'FAIL'}  {r:5.2f}:1  (need {need})  "
        f"{theme:<5} {label:<24} {fg} on {bg}   {where}"
    )
    return ok


def run(theme: str, t: dict[str, str]) -> list[bool]:
    res: list[bool] = []
    print(f"\n=== {theme.upper()} THEME ===")
    pairs = [
        ("body text", t["ink"], t["bg"], "text", "body"),
        ("body text on panel", t["ink"], t["panel"], "text", ".card"),
        ("muted label", t["muted"], t["bg"], "text", "label, th, .muted"),
        ("muted on panel", t["muted"], t["panel"], "text", ".listing .meta"),
        ("link", t["accent"], t["bg"], "text", "a"),
        ("link on panel", t["accent"], t["panel"], "text", "a in .card"),
        ("button label", OFFTOKEN_BUTTON_INK, t["accent"], "text", "button"),
    ]
    for label, fg, bg, kind, where in pairs:
        res.append(check(label=label, fg=fg, bg=bg, kind=kind, theme=theme, where=where))

    for name in ("ok", "warn", "bad"):
        bg = mix(t[name], PILL_MIX_PCT, t["panel"])
        res.append(
            check(
                label=f".pill.{name}",
                fg=t[name],
                bg=bg,
                kind="text",
                theme=theme,
                where=f"{PILL_MIX_PCT:.0f}% color-mix over panel",
            )
        )

    res.append(
        check(
            label="border",
            fg=t["line"],
            bg=t["panel"],
            kind="ui",
            theme=theme,
            where="card/table border",
        )
    )
    res.append(
        check(
            label="border on bg",
            fg=t["line"],
            bg=t["bg"],
            kind="ui",
            theme=theme,
            where="input border",
        )
    )
    return res


def font_size_audit() -> None:
    print("\n=== FONT SIZE AUDIT (root 16px) ===")
    sizes = {
        ".tag / .listing .count": 0.72,
        ".pill": 0.75,
        "th": 0.80,
        "label": 0.82,
        ".listing": 0.84,
        "muted / status": 0.85,
        "body": ROOT_PX - 1,
        "h2": 0.95,
        "header h1": 1.05,
    }
    for name, rem in sizes.items():
        px = rem * ROOT_PX
        note = ""
        if px < TINY_PX:
            note = "  <-- below 12px"
        elif px < SMALL_PX:
            note = "  <-- small"
        print(f"  {px:5.1f}px  {name}{note}")


def scale_audit() -> None:
    print("\n=== SCALE AUDIT ===")
    spacing = [
        0.1,
        0.12,
        0.2,
        0.3,
        0.35,
        0.4,
        0.45,
        0.5,
        0.55,
        0.6,
        0.65,
        0.7,
        0.75,
        0.85,
        1.0,
        1.05,
        1.15,
        1.5,
        2.25,
    ]
    print(f"  spacing values in use : {len(spacing)} distinct -> no scale")
    print(f"  radii in use          : {[0, 6, 7, 10, 999]} -> no scale")
    print("  shadows in use        : 1 (.combo-list) -> no elevation scale")
    print("  transitions/keyframes : 0 -> no motion language")
    print("  font-family           : system stack via `font:` shorthand on body")


def main() -> int:
    print("WCAG 2.x contrast audit - vinted-sniper")
    print(f"text >= {TEXT_MIN}:1, non-text UI >= {UI_MIN}:1\n")
    results = run("light", LIGHT) + run("dark", DARK)
    font_size_audit()
    scale_audit()

    failed = results.count(False)
    print(f"\n=== RESULT: {len(results) - failed}/{len(results)} pairs pass; {failed} FAIL ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
