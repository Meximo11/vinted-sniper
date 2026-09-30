/* The advanced search builder.
 *
 * The point is to stop the user having to know what a Vinted search URL looks like.
 * They pick categories, brands, condition and size, and the URL — the thing the rest
 * of the app actually stores — fills itself in above. Anything this builds can still
 * be pasted in by hand: the builder is a nicer way to produce the same string, not a
 * new kind of configuration.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const toggle = $("builder-toggle");
  const builder = $("builder");
  if (!toggle || !builder) return;

  const urlInput = $("url");
  const nameInput = $("name");

  const state = {
    tree: [], // category roots for the current site
    path: [], // the walk from a root down to the selected category
    brands: new Map(), // id -> title (brand ids are the same on every country site)
    picked: { status: new Set(), color: new Set(), size: new Set() },
  };
  let nameAuto = ""; // the last name we filled in, so we never overwrite the user's own

  const tld = () => $("b-tld").value;
  const selectedCat = () => state.path[state.path.length - 1] || null;

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || body.detail || res.statusText);
    }
    return res.json();
  }

  function msg(text) {
    const span = document.createElement("span");
    span.className = "muted";
    span.textContent = text;
    return span;
  }

  // --- Categories: drill down the same tree Vinted's own picker shows -------------

  async function loadTree() {
    const cats = $("b-cats");
    cats.replaceChildren(
      msg("Kategorien werden geladen … beim ersten Mal für eine Seite dauert das ein paar Sekunden."),
    );
    try {
      const data = await fetchJSON(`/api/filters/${tld()}/categories`);
      state.tree = data.categories;
      renderCats();
    } catch (err) {
      cats.replaceChildren(msg(`Kategorien konnten nicht geladen werden: ${err.message}`));
    }
  }

  function renderCats() {
    const crumbs = $("b-crumbs");
    crumbs.replaceChildren();
    const all = document.createElement("button");
    all.type = "button";
    all.className = "crumb";
    all.textContent = "Alle Kategorien";
    all.onclick = () => {
      state.path = [];
      onCategoryChange();
    };
    crumbs.append(all);
    state.path.forEach((node, i) => {
      crumbs.append("›");
      const crumb = document.createElement("button");
      crumb.type = "button";
      crumb.className = "crumb";
      crumb.textContent = node.title;
      if (i === state.path.length - 1) crumb.setAttribute("aria-current", "true");
      else {
        crumb.onclick = () => {
          state.path = state.path.slice(0, i + 1);
          onCategoryChange();
        };
      }
      crumbs.append(crumb);
    });

    const cats = $("b-cats");
    cats.replaceChildren();
    const node = selectedCat();
    const children = node ? node.children : state.tree;
    if (!children.length) {
      cats.append(msg("Keine weiteren Unterkategorien."));
      return;
    }
    for (const child of children) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "cat-node";
      button.textContent = child.children.length ? `${child.title} ›` : child.title;
      button.onclick = () => {
        state.path.push(child);
        onCategoryChange();
      };
      cats.append(button);
    }
  }

  function onCategoryChange() {
    renderCats();
    // Sizes only mean something within a category, and they change with it.
    state.picked.size.clear();
    const cat = selectedCat();
    $("b-size-wrap").hidden = !cat;
    if (cat) loadFacet("size", $("b-size"));
    sync();
  }

  // --- Brands: live autocomplete, narrowed to the category when one is picked -----

  let brandTimer = 0;
  $("b-brand").addEventListener("input", () => {
    clearTimeout(brandTimer);
    const q = $("b-brand").value.trim();
    if (q.length < 2) {
      $("b-brand-list").hidden = true;
      return;
    }
    brandTimer = setTimeout(() => searchBrands(q), 250);
  });
  document.addEventListener("click", (event) => {
    if (event.target !== $("b-brand") && !$("b-brand-list").contains(event.target)) {
      $("b-brand-list").hidden = true;
    }
  });

  async function searchBrands(q) {
    const list = $("b-brand-list");
    try {
      const cat = selectedCat();
      const scope = cat ? `&catalog_ids=${cat.id}` : "";
      const data = await fetchJSON(
        `/api/filters/${tld()}/brands?q=${encodeURIComponent(q)}${scope}`,
      );
      list.replaceChildren();
      if (!data.brands.length) list.append(msg("Keine Marke passt dazu."));
      for (const brand of data.brands) {
        const row = document.createElement("button");
        row.type = "button";
        const title = document.createElement("span");
        title.textContent = brand.title;
        row.append(title);
        if (brand.count) {
          const count = document.createElement("span");
          count.className = "muted";
          count.textContent = `${new Intl.NumberFormat("de-DE").format(brand.count)} Artikel`;
          row.append(count);
        }
        row.onclick = () => {
          state.brands.set(brand.id, brand.title);
          $("b-brand").value = "";
          list.hidden = true;
          renderBrandChips();
          sync();
        };
        list.append(row);
      }
      list.hidden = false;
    } catch (err) {
      list.replaceChildren(msg(err.message));
      list.hidden = false;
    }
  }

  function renderBrandChips() {
    const chips = $("b-brand-chips");
    chips.replaceChildren();
    for (const [id, title] of state.brands) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.append(title);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `${title} entfernen`);
      remove.onclick = () => {
        state.brands.delete(id);
        renderBrandChips();
        sync();
      };
      chip.append(remove);
      chips.append(chip);
    }
  }

  // --- Condition, colour, size ----------------------------------------------------

  async function loadFacet(code, container) {
    container.replaceChildren(msg("Wird geladen …"));
    try {
      const cat = selectedCat();
      const scope = code === "size" && cat ? `?catalog_ids=${cat.id}` : "";
      const data = await fetchJSON(`/api/filters/${tld()}/facets/${code}${scope}`);
      renderFacet(code, container, data.options);
    } catch (err) {
      container.replaceChildren(msg(`Konnte nicht geladen werden: ${err.message}`));
    }
  }

  function renderFacet(code, container, options) {
    container.replaceChildren();
    if (!options.length) {
      container.append(msg("Hier gibt es nichts auszuwählen."));
      return;
    }
    let group = null;
    for (const option of options) {
      if (option.group && option.group !== group) {
        group = option.group;
        const label = document.createElement("span");
        label.className = "group-label";
        label.textContent = group;
        container.append(label);
      }
      const label = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = state.picked[code].has(option.id);
      box.onchange = () => {
        if (box.checked) state.picked[code].add(option.id);
        else state.picked[code].delete(option.id);
        sync();
      };
      label.append(box, option.title);
      if (option.count) {
        const count = document.createElement("span");
        count.className = "count";
        count.textContent = new Intl.NumberFormat("de-DE").format(option.count);
        label.append(count);
      }
      container.append(label);
    }
  }

  // --- Composing the URL the user would otherwise have copied ---------------------

  function buildUrl() {
    const params = new URLSearchParams();
    const text = $("b-text").value.trim();
    if (text) params.set("search_text", text);
    const cat = selectedCat();
    if (cat) params.append("catalog[]", cat.id);
    for (const id of state.brands.keys()) params.append("brand_ids[]", id);
    for (const id of state.picked.status) params.append("status_ids[]", id);
    for (const id of state.picked.color) params.append("color_ids[]", id);
    for (const id of state.picked.size) params.append("size_ids[]", id);
    const from = $("b-price-from").value.trim();
    const to = $("b-price-to").value.trim();
    if (from) params.set("price_from", from);
    if (to) params.set("price_to", to);
    const query = params.toString();
    return query ? `https://www.vinted.${tld()}/catalog?${query}` : "";
  }

  function sync() {
    const url = buildUrl();
    urlInput.value = url;
    const preview = $("b-preview");
    preview.replaceChildren();
    if (url) {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Diese Suche zuerst auf Vinted prüfen ↗";
      preview.append(link);
    } else {
      preview.textContent = "Wähle ein paar Filter – die URL oben füllt sich von selbst.";
    }
    // Suggest a name, but never fight the user over one they typed themselves.
    if (nameInput.value === nameAuto) {
      const cat = selectedCat();
      const parts = [
        [...state.brands.values()].join(", "),
        cat ? cat.title : "",
        $("b-text").value.trim(),
      ].filter(Boolean);
      nameAuto = parts.length ? `${parts.join(" · ")} (${tld()})` : "";
      nameInput.value = nameAuto;
    }
  }

  // --- Wiring ---------------------------------------------------------------------

  let opened = false;
  toggle.addEventListener("click", () => {
    builder.hidden = !builder.hidden;
    toggle.setAttribute("aria-expanded", String(!builder.hidden));
    toggle.textContent = builder.hidden
      ? "Selbst zusammenstellen ▾"
      : "Aufbauassistent ausblenden ▴";
    urlInput.readOnly = !builder.hidden;
    if (!builder.hidden && !opened) {
      opened = true;
      init();
    }
  });

  function init() {
    loadTree();
    loadFacet("status", $("b-status"));
    loadFacet("color", $("b-color"));
    sync();
  }

  $("b-tld").addEventListener("change", () => {
    // Category ids differ between country sites; brand ids do not.
    state.path = [];
    state.picked.status.clear();
    state.picked.color.clear();
    state.picked.size.clear();
    $("b-size-wrap").hidden = true;
    init();
  });
  for (const id of ["b-text", "b-price-from", "b-price-to"]) {
    $(id).addEventListener("input", sync);
  }
})();
