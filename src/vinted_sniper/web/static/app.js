/* Dashboard behaviour: the photo lightbox, the mobile nav, a guard on the actions
 * that cannot be undone, and the inline editor panels.
 *
 * Everything here is progressive: the page is fully usable with JavaScript off,
 * because the server renders the listings and the forms post normally.
 */
(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // --- Photos that never arrive --------------------------------------------------
  // A Vinted CDN image can 403 at any time, and a listing is not worth throwing away
  // over one. The card frame is a fixed 4/5 box, so the placeholder that replaces a
  // dead image takes exactly the space the image would have, and nothing on the page
  // moves. error does not bubble, but it does pass through the capture phase, so one
  // listener on the document covers every photo, including any added later.
  document.addEventListener(
    "error",
    (event) => {
      const image = event.target;
      if (!(image instanceof HTMLImageElement)) return;
      image.closest(".photo, .lightbox")?.classList.add("is-broken");
    },
    true,
  );

  // --- Photo lightbox -------------------------------------------------------------
  // Occasional action, so it gets a real entrance: the overlay fades and settles
  // from just inside its final size. Never from scale(0), which looks like it came
  // from nowhere. The photograph itself does not scale, so it never distorts.

  const box = document.getElementById("lightbox");
  if (box) {
    const img = document.getElementById("lb-img");
    const counter = document.getElementById("lb-counter");
    const prev = box.querySelector(".lb-prev");
    const next = box.querySelector(".lb-next");
    const closeBtn = box.querySelector(".lb-close");
    let photos = [];
    let index = 0;
    let opener = null;
    let closing = null;

    function show(i) {
      index = (i + photos.length) % photos.length;
      // Clear the previous photo's broken state first. If this one is dead too the
      // error listener puts it straight back.
      box.classList.remove("is-broken");
      img.src = photos[index];
      counter.textContent = `${index + 1} / ${photos.length}`;
      const single = photos.length < 2;
      prev.hidden = next.hidden = counter.hidden = single;
    }

    function open(list, button) {
      photos = list;
      if (!photos.length) return;
      opener = button;
      box.hidden = false;
      box.classList.remove("is-closing");
      // The page must not scroll underneath the overlay.
      document.body.style.overflow = "hidden";
      show(0);
      closeBtn.focus();
    }

    function close() {
      if (closing) return;
      const finish = () => {
        box.hidden = true;
        box.classList.remove("is-closing");
        box.classList.remove("is-broken");
        img.removeAttribute("src");
        document.body.style.overflow = "";
        closing = null;
        if (opener) opener.focus();
      };
      // Exits faster than it enters: opening is the thing you asked for, closing is
      // the system getting out of the way. Under reduced motion, skip straight out.
      if (reduced) {
        finish();
        return;
      }
      box.classList.add("is-closing");
      const done = () => {
        clearTimeout(closing);
        finish();
      };
      closing = window.setTimeout(done, 120);
      box.addEventListener("animationend", done, { once: true });
    }

    for (const button of document.querySelectorAll(".listing .photo")) {
      button.addEventListener("click", () => {
        let list = [];
        try {
          list = JSON.parse(button.dataset.photos);
        } catch {
          list = [];
        }
        open(list, button);
      });
    }

    closeBtn.addEventListener("click", close);
    prev.addEventListener("click", () => show(index - 1));
    next.addEventListener("click", () => show(index + 1));
    box.addEventListener("click", (event) => {
      if (event.target === box) close();
    });
    document.addEventListener("keydown", (event) => {
      if (box.hidden) return;
      if (event.key === "Escape") close();
      if (event.key === "ArrowLeft") show(index - 1);
      if (event.key === "ArrowRight") show(index + 1);
    });
  }

  // --- Mobile navigation ---------------------------------------------------------
  // A drawer the user opened on purpose: 180ms out-ease, and it slides from the edge
  // it lives on, so where it came from is obvious.

  const menu = document.querySelector(".menu-toggle");
  const sidebar = document.querySelector(".sidebar");
  const scrim = document.querySelector(".nav-scrim");
  if (menu && sidebar) {
    const setOpen = (open) => {
      sidebar.classList.toggle("open", open);
      menu.setAttribute("aria-expanded", String(open));
      if (scrim) scrim.hidden = !open;
      document.body.style.overflow = open ? "hidden" : "";
    };
    menu.addEventListener("click", () => setOpen(!sidebar.classList.contains("open")));
    if (scrim) scrim.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setOpen(false);
    });
  }

  // --- Theme --------------------------------------------------------------------
  // Three choices, not two: "follow the system" is the one most people want and it is
  // the one a light/dark toggle cannot express. The attribute is set on <html> and the
  // stylesheet does the rest, so nothing here has to know what a theme looks like.
  //
  // The inline script in the document head has already applied the stored choice before
  // the first paint; this only keeps the control in step and records changes.

  const THEME_KEY = "vinted-sniper-theme";
  const root = document.documentElement;
  const options = [...document.querySelectorAll("[data-theme-choice]")];
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  const readTheme = () => {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      return stored === "light" || stored === "dark" ? stored : "system";
    } catch {
      return "system";
    }
  };

  // Switching theme changes the entire ground under the page at once, which is not a
  // state the person hovered or pressed. Given the stylesheet's normal transitions it
  // would snap; given a blanket transition it would drag every hover state along with
  // it. So it gets its own 320ms window: add a class, let the CSS swap every colour at
  // once, take it off again. No timer survives a theme change started twice.
  let themeTimer = null;
  // Suppressed on the very first application: the inline script in the document head
  // has already set the attribute before the first paint, so there is nothing to
  // animate and putting a class on <html> would only cost a style recalculation.
  let booted = false;
  const crossfade = () => {
    if (reduced || !booted) return;
    root.classList.add("theme-changing");
    window.clearTimeout(themeTimer);
    themeTimer = window.setTimeout(() => root.classList.remove("theme-changing"), 340);
  };

  const applyTheme = (choice) => {
    if (choice === "light" || choice === "dark") {
      root.setAttribute("data-theme", choice);
    } else {
      root.removeAttribute("data-theme");
    }
    crossfade();
    for (const option of options) {
      option.setAttribute("aria-pressed", String(option.dataset.themeChoice === choice));
    }
  };

  // While the choice is "system", follow the machine as it switches at sunset — the
  // switcher would otherwise sit there showing "system" while contradicting it.
  const followSystem = () => {
    if (readTheme() === "system") applyTheme("system");
  };
  if (systemDark.addEventListener) systemDark.addEventListener("change", followSystem);
  else systemDark.addListener(followSystem);

  applyTheme(readTheme());
  booted = true;
  for (const option of options) {
    option.addEventListener("click", () => {
      const choice = option.dataset.themeChoice;
      try {
        if (choice === "system") localStorage.removeItem(THEME_KEY);
        else localStorage.setItem(THEME_KEY, choice);
      } catch {
        /* Storage unavailable: the choice still applies for this page view. */
      }
      applyTheme(choice);
    });
  }

  // --- Confirming the actions that cannot be undone -----------------------------
  // Marked in the markup rather than matched on a button's colour or text, so
  // renaming a button can never quietly remove the confirmation.
  for (const form of document.querySelectorAll("form[data-confirm]")) {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  }

  // --- Disclosing the optional parts of a form -----------------------------------
  // The panel fades in on open. Its entrance animation lives in CSS under
  // prefers-reduced-motion: no-preference, so this only has to move the hidden
  // attribute and the aria state.
  for (const toggle of document.querySelectorAll("[data-disclosure]")) {
    const target = document.getElementById(toggle.dataset.disclosure);
    if (!target) continue;
    toggle.addEventListener("click", () => {
      const open = target.hidden;
      target.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
})();
