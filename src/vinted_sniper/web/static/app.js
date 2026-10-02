/* Behaviour for the app: the photo lightbox, the navigation drawer, the theme
 * switch, a guard on the actions that cannot be undone, the inline editor
 * panels, and the states a button shows while it works.
 *
 * Everything here is progressive. The page is fully usable with JavaScript off,
 * because the server renders the finds and the forms post normally.
 */
(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // --- Buttons that tell you what they are doing -------------------------------
  // "▶ Suche starten" → "◌ läuft…" → the page comes back with the result. The state
  // lives on the button you pressed rather than in a toast that appears somewhere
  // else, because the interface responding to *me* is the whole point. The label
  // is read out of data-busy-label so the copy stays in the template.
  for (const button of document.querySelectorAll("button[type=submit]")) {
    const form = button.closest("form");
    if (!form) continue;
    form.addEventListener(
      "submit",
      () => {
        if (button.dataset.busy === "off") return;
        // A client-side `confirm` may still cancel this. Check on the next frame,
        // by which point the handler has run and the dialog is closed.
        requestAnimationFrame(() => {
          if (form.dataset.confirm && !window.confirmShown) return;
          // A form that reports its own completion can finish before this frame
          // ever runs — the endpoint is local, so the response is often faster
          // than the next repaint. Without this the spinner would land on top of
          // a result the user is already looking at, and the button would sit on
          // "lädt…" forever.
          if (button.dataset.state) return;
          button.dataset.state = "loading";
          button.setAttribute("aria-busy", "true");
          const label = button.querySelector("span");
          if (label && button.dataset.busyLabel) {
            button.dataset.idleLabel = label.textContent;
            label.textContent = button.dataset.busyLabel;
          }
        });
      },
      true,
    );
  }

  // --- Forms that finish their own sentence -------------------------------------
  // Starting a search is the one action here the user is actually waiting on, and
  // a redirect throws the answer away: the page reloads and the button that was
  // pressed no longer exists. Forms marked `data-report-done` are posted with
  // fetch instead and end on the button — "Suche starten" → "Wird angelegt…" →
  // "✓ 12 neue Treffer". Every other form on the site still posts and redirects.
  //
  // The wording comes from the response. A count written here would be a number
  // the server never agreed to, and this button exists precisely because the
  // answer is worth having.
  for (const form of document.querySelectorAll("form[data-report-done]")) {
    const button = form.querySelector('button[type="submit"]');
    if (!button) continue;
    const label = button.querySelector("span");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      let data;
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error(String(response.status));
        data = await response.json();
        if (!data.ok) throw new Error("rejected");
      } catch {
        // A network drop, a 409, a 422 — anything unexpected goes back through
        // the plain form post, which renders the server's own sentence in the
        // flash at the top of the page. One failure path is better than a
        // second, worse one written just for the fetch.
        form.submit();
        return;
      }

      // A search created a moment ago has not been polled yet, so `found` is
      // honestly 0. Saying "wird beobachtet" is the true outcome; saying "0 neue
      // Treffer" would read as a failure, and inventing "23" would be a lie.
      const done = data.found > 0 ? `${data.found} neue Treffer` : "Wird beobachtet";
      button.dataset.state = "done";
      button.setAttribute("aria-busy", "false");
      if (label) label.textContent = done;

      const status = form.querySelector("[data-run-status]");
      if (status) status.textContent = `${data.name}: ${done}.`;

      // The button has said its piece; now the page has to agree with it. The
      // table of saved searches is server-rendered, and a list that still shows
      // two searches directly under a button that just created a third reads as
      // a failure. So the result stays up long enough to be read, and then the
      // ordinary reload happens — which also brings back the flash at the top.
      window.setTimeout(() => window.location.reload(), 1400);
    });
  }

  // --- Photos that never arrive -------------------------------------------------
  // A Vinted CDN image can 403 at any time, and a find is not worth throwing away
  // over one. The media box has a fixed 4/5 ratio, so the placeholder that replaces
  // a dead image takes exactly the space the image would have and nothing on the
  // page moves. `error` does not bubble but does pass through the capture phase,
  // so one listener on the document covers every photo, including later ones.
  document.addEventListener(
    "error",
    (event) => {
      const image = event.target;
      if (!(image instanceof HTMLImageElement)) return;
      image.closest(".tile-media, .lightbox")?.classList.add("is-broken");
    },
    true,
  );

  // --- Photo lightbox ------------------------------------------------------------
  // An occasional action, so it gets a real entrance: the overlay fades in from
  // just inside its final size, never from scale(0), which looks like it arrived
  // from nowhere. The photograph itself never scales, so it cannot distort.

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
      // Clear the previous photo's broken state first; if this one is dead too the
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
      document.body.style.overflow = "hidden";
      show(0);
      closeBtn.focus();
    }

    function close() {
      if (closing) return;
      const finish = () => {
        box.hidden = true;
        box.classList.remove("is-closing", "is-broken");
        img.removeAttribute("src");
        document.body.style.overflow = "";
        closing = null;
        if (opener) opener.focus();
      };
      // Exits faster than it enters: opening is what you asked for, closing is the
      // system getting out of the way. Under reduced motion, leave immediately.
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

    for (const button of document.querySelectorAll(".tile .tile-media")) {
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

  // --- Navigation drawer --------------------------------------------------------
  // A drawer the user opened on purpose, sliding in from the edge it lives on.

  const menu = document.getElementById("menu-toggle");
  const app = document.getElementById("app");
  const scrim = document.getElementById("nav-scrim");
  if (menu && app) {
    const setOpen = (open) => {
      app.classList.toggle("is-nav-open", open);
      menu.setAttribute("aria-expanded", String(open));
      if (scrim) scrim.hidden = !open;
      document.body.style.overflow = open ? "hidden" : "";
    };
    menu.addEventListener("click", () => setOpen(!app.classList.contains("is-nav-open")));
    if (scrim) scrim.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setOpen(false);
    });
  }

  // --- Theme --------------------------------------------------------------------
  // Three choices, not two: "follow the system" is what most people want and it is
  // the one a light/dark toggle cannot express. The attribute lives on <html> and
  // the stylesheet does the rest, so nothing here needs to know what a theme is.
  //
  // The inline script in the document head already applied the stored choice before
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

  const applyTheme = (choice) => {
    // Always an explicit attribute, including "system": the stylesheet resolves
    // "system" inside a prefers-color-scheme block, so removing the attribute
    // would leave the page with no tokens at all.
    root.setAttribute("data-theme", choice);
    for (const option of options) {
      option.setAttribute("aria-pressed", String(option.dataset.themeChoice === choice));
    }
  };

  // While the choice is "system", follow the machine as it changes at sunset —
  // otherwise the switcher would sit there claiming "system" while contradicting it.
  const followSystem = () => {
    if (readTheme() === "system") applyTheme("system");
  };
  if (systemDark.addEventListener) systemDark.addEventListener("change", followSystem);
  else systemDark.addListener(followSystem);

  applyTheme(readTheme());
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

  // --- Page transitions ---------------------------------------------------------
  // The content column cross-fades between pages, so moving around the app reads as
  // one app changing screen rather than five documents loading. Same-document
  // navigations only, so a form POST is never caught mid-flight.
  if (document.startViewTransition && !reduced) {
    document.addEventListener("click", (event) => {
      const link = event.target.closest?.("a[href]");
      if (!link || link.target === "_blank" || event.metaKey || event.ctrlKey) return;
      const url = new URL(link.href, location.href);
      if (url.origin !== location.origin) return;
      if (url.pathname === location.pathname && url.search === location.search) return;
      event.preventDefault();
      document.startViewTransition(() => {
        location.href = link.href;
      });
    });
  }

  // --- Confirming the actions that cannot be undone -----------------------------
  // Marked in the markup rather than matched on a button's colour or text, so
  // renaming a button can never quietly remove the confirmation.
  for (const form of document.querySelectorAll("form[data-confirm]")) {
    form.addEventListener("submit", (event) => {
      window.confirmShown = false;
      if (!window.confirm(form.dataset.confirm)) {
        window.confirmShown = true;
        event.preventDefault();
      } else {
        window.confirmShown = true;
      }
    });
  }

  // --- Disclosing the optional parts of a form ----------------------------------
  for (const toggle of document.querySelectorAll("[data-disclosure]")) {
    const target = document.getElementById(toggle.dataset.disclosure);
    if (!target) continue;
    toggle.addEventListener("click", () => {
      const open = target.hidden;
      target.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // --- Keyboard ----------------------------------------------------------------
  // This page is read dozens of times a day, so reaching the filter and walking the
  // finds without leaving the home row is the cheapest thing the interface can
  // offer. Nothing here animates: an action taken a hundred times a day does not
  // get an entrance.
  const tiles = [...document.querySelectorAll(".tile")];
  const filter = document.getElementById("q");
  const sheet = document.getElementById("shortcut-sheet");
  let cursor = -1;

  const isTyping = (target) =>
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));

  function select(index) {
    if (!tiles.length) return;
    cursor = (index + tiles.length) % tiles.length;
    tiles.forEach((tile, i) => tile.classList.toggle("is-cursor", i === cursor));
    const tile = tiles[cursor];
    tile.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" });
    tile.focus({ preventScroll: true });
  }

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;

    if (event.key === "Escape") {
      if (sheet) sheet.hidden = true;
      return;
    }

    // "/" is the one people reach for out of habit. It only means something when
    // there is a filter box to put the cursor in.
    if (event.key === "/" && !isTyping(event.target) && filter) {
      event.preventDefault();
      filter.focus();
      filter.select();
      return;
    }

    if (event.key === "?" && !isTyping(event.target) && sheet) {
      event.preventDefault();
      sheet.hidden = !sheet.hidden;
      return;
    }

    if (isTyping(event.target)) return;

    if (event.key === "j" || event.key === "ArrowDown") {
      if (tiles.length) {
        event.preventDefault();
        select(cursor + 1);
      }
      return;
    }
    if (event.key === "k" || event.key === "ArrowUp") {
      if (tiles.length) {
        event.preventDefault();
        select(cursor - 1);
      }
      return;
    }
    if (event.key === "Enter" && cursor >= 0) {
      const link = tiles[cursor]?.querySelector(".tile-title");
      if (link) {
        event.preventDefault();
        link.click();
      }
    }
  });
})();
