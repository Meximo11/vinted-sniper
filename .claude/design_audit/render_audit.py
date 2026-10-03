#!/usr/bin/env python3
"""Stage 13 (visual QA) + Stage 12 (a11y) evidence, measured in a real browser.

Drives the running preview and records what actually renders: viewport overflow,
tap-target sizes, and whether a keyboard user can see where they are. Writes
screenshots so the findings can be looked at, not just read.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

URL = "http://127.0.0.1:8000/"
OUT = Path(__file__).resolve().parent / "screens"
OUT.mkdir(exist_ok=True)

VIEWPORTS = [("mobile", 375, 667), ("tablet", 768, 1024), ("desktop", 1440, 900)]
TABS = 2
FULL_PAGE = {"desktop"}
CONTEXT_OPTS = {"device_scale_factor": 2}

# Everything the page is measured for, evaluated inside the browser.
PROBE_JS = """() => {
  const de = document.documentElement;
  const res = {
    scrollW: de.scrollWidth, clientW: de.clientWidth,
    overflow: de.scrollWidth - de.clientWidth,
    overflowing: [], smallText: [], smallTargets: [],
  };
  const tag = el => {
    const c = (el.className || '').toString().trim().split(/\\s+/).filter(Boolean);
    return el.tagName.toLowerCase() + (c.length ? '.' + c.join('.') : '');
  };
  for (const el of document.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if ((r.width > de.clientWidth + 1 || r.right > de.clientWidth + 1)
        && res.overflowing.length < 12) {
      res.overflowing.push({el: tag(el), w: Math.round(r.width),
                            right: Math.round(r.right)});
    }
  }
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length) continue;
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!hasText) continue;
    const cs = getComputedStyle(el);
    const px = parseFloat(cs.fontSize);
    const key = el.tagName + el.className + px;
    if (px < 12 && !seen.has(key)) {
      seen.add(key);
      res.smallText.push({el: tag(el), px: Math.round(px * 100) / 100, color: cs.color});
    }
  }
  for (const el of document.querySelectorAll('a,button,input,select,[role=button]')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.height < 44 || r.width < 44) {
      res.smallTargets.push({el: tag(el), w: Math.round(r.width),
                             h: Math.round(r.height),
                             text: (el.textContent || '').trim().slice(0, 22)});
    }
  }
  return res;
}"""

FOCUS_JS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const cs = getComputedStyle(el);
  return {el: el.tagName.toLowerCase(),
          outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor,
          outlineOffset: cs.outlineOffset, boxShadow: cs.boxShadow};
}"""


def probe(page: Page) -> dict:
    return page.evaluate(PROBE_JS)


def capture(theme: str, name: str, width: int, height: int, findings: dict) -> None:
    """Open the app at one viewport/theme, screenshot it, and measure it."""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": width, "height": height}, color_scheme=theme, **CONTEXT_OPTS
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / f"{theme}-{name}.png"), full_page=name in FULL_PAGE)
        findings[f"{theme}-{name}"] = probe(page)

        if theme == "light" and name == "desktop":
            for _ in range(TABS):
                page.keyboard.press("Tab")
            findings["focusAfterTwoTabs"] = page.evaluate(FOCUS_JS)
            page.screenshot(path=str(OUT / "focus-ring.png"))
        ctx.close()
        browser.close()


def report(findings: dict) -> None:
    print("=== RENDERED MEASUREMENTS ===")
    for key, d in findings.items():
        if key == "focusAfterTwoTabs":
            continue
        print(f"\n--- {key}")
        print(
            f"  viewport overflow : {d['overflow']}px  (scrollW {d['scrollW']} vs {d['clientW']})"
        )
        if d["overflowing"]:
            for o in d["overflowing"][:5]:
                print(f"    past right edge: {o['el'][:46]:<46} w={o['w']} right={o['right']}")
        else:
            print("  elements past edge: none")
        print(f"  text under 12px   : {len(d['smallText'])}")
        for s in d["smallText"][:5]:
            print(f"    {s['el'][:30]:<30} {s['px']}px color={s['color']}")
        print(f"  tap targets <44px : {len(d['smallTargets'])}")
        for t in d["smallTargets"][:6]:
            print(f"    {t['el'][:26]:<26} {t['w']}x{t['h']}  '{t['text']}'")

    print("\n=== KEYBOARD FOCUS (after 2x Tab, desktop light) ===")
    print(json.dumps(findings.get("focusAfterTwoTabs"), indent=2))
    print(f"\nscreenshots -> {OUT}")


def main() -> int:
    findings: dict = {}
    for theme in ("light", "dark"):
        for name, w, h in VIEWPORTS:
            capture(theme, name, w, h, findings)
    report(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
