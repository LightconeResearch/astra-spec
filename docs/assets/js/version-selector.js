/*
 * ASTRA spec version selector.
 *
 * On any page under /specification/<version>/..., loads versions.json,
 * injects a dropdown that switches version while preserving the trailing
 * sub-path (falling back to format/ if the target version lacks the page),
 * and shows a banner when not viewing the latest stable version.
 *
 * Robust to Material/Zensical instant navigation: the injection is
 * idempotent (a single .astra-version-selector node per article) and
 * re-runs on every relevant DOM/navigation event, debounced to one call
 * per animation frame.
 */
(function () {
  "use strict";

  const SPEC_PREFIX = "/specification/";
  const SELECTOR_CLASS = "astra-version-selector";
  const BANNER_CLASS = "astra-version-banner";

  let cachedData = null;
  let cachedFetchUrl = null;
  let pendingFrame = false;

  injectStyles();
  scheduleSetup();

  // Belt-and-suspenders triggers — any one of these can carry us through
  // initial load, instant-nav swaps, hash navigation, or bfcache restores.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleSetup, { once: true });
  }
  window.addEventListener("popstate", scheduleSetup);
  window.addEventListener("pageshow", scheduleSetup);
  window.addEventListener("hashchange", scheduleSetup);

  // Watch for content swaps anywhere under <body>. The rAF debounce keeps
  // this cheap even with subtree:true.
  new MutationObserver(scheduleSetup).observe(document.body, {
    childList: true,
    subtree: true,
  });

  function scheduleSetup() {
    if (pendingFrame) return;
    pendingFrame = true;
    requestAnimationFrame(() => {
      pendingFrame = false;
      try { setup(); } catch (err) { console.warn("[astra] version selector:", err); }
    });
  }

  function setup() {
    const ctx = parsePath(window.location.pathname);
    if (!ctx) return;

    const article = document.querySelector("article");
    if (!article) return;
    if (article.querySelector("." + SELECTOR_CLASS)) return; // already injected

    const fetchUrl = ctx.baseUrl + "versions.json";
    if (cachedData && cachedFetchUrl === fetchUrl) {
      render(article, ctx, cachedData);
      return;
    }

    fetch(fetchUrl, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((data) => {
        cachedData = data;
        cachedFetchUrl = fetchUrl;
        // Article reference may be stale after async hop — re-resolve.
        const a = document.querySelector("article");
        if (a && !a.querySelector("." + SELECTOR_CLASS)) render(a, ctx, data);
      })
      .catch((err) => console.warn("[astra] version selector:", err));
  }

  function parsePath(pathname) {
    const idx = pathname.indexOf(SPEC_PREFIX);
    if (idx === -1) return null;
    const after = pathname.slice(idx + SPEC_PREFIX.length);
    const slash = after.indexOf("/");
    const version = slash === -1 ? after.replace(/\/$/, "") : after.slice(0, slash);
    if (!version) return null;
    return {
      version,
      trailing: slash === -1 ? "" : after.slice(slash + 1),
      baseUrl: pathname.slice(0, idx + SPEC_PREFIX.length),
    };
  }

  function render(article, ctx, data) {
    if (article.querySelector("." + SELECTOR_CLASS)) return;

    const wrapper = document.createElement("div");
    wrapper.className = SELECTOR_CLASS;

    const label = document.createElement("label");
    label.textContent = "Spec version:";

    const select = document.createElement("select");
    select.setAttribute("aria-label", "Specification version");
    let knownVersion = false;
    for (const v of data.versions) {
      const opt = document.createElement("option");
      opt.value = v.id;
      const isLatest = v.id === data.latest;
      opt.textContent = v.label + (isLatest ? " — latest" : "");
      if (v.id === ctx.version) {
        opt.selected = true;
        knownVersion = true;
      }
      select.appendChild(opt);
    }
    if (!knownVersion) return; // URL version not in registry; bail silently

    select.addEventListener("change", () => switchVersion(ctx, select.value));

    label.appendChild(select);
    wrapper.appendChild(label);

    const banner = buildBanner(ctx, data);

    // Insert the selector at the very top of the article (before the H1).
    article.insertBefore(wrapper, article.firstChild);
    if (banner) article.insertBefore(banner, wrapper.nextSibling);
  }

  function buildBanner(ctx, data) {
    if (ctx.version === "draft") {
      const div = document.createElement("div");
      div.className = BANNER_CLASS + " " + BANNER_CLASS + "--draft";
      div.appendChild(document.createTextNode(
        "You are viewing the in-development draft of the specification. "
      ));
      if (data.latest) {
        const a = document.createElement("a");
        a.href = ctx.baseUrl + data.latest + "/" + ctx.trailing;
        a.textContent = "View the latest stable version (" + data.latest + ") →";
        div.appendChild(a);
      }
      return div;
    }
    if (data.latest && ctx.version !== data.latest) {
      const div = document.createElement("div");
      div.className = BANNER_CLASS + " " + BANNER_CLASS + "--outdated";
      div.appendChild(document.createTextNode(
        "You are viewing version " + ctx.version +
        " of the specification. The latest is " + data.latest + ". "
      ));
      const a = document.createElement("a");
      a.href = ctx.baseUrl + data.latest + "/" + ctx.trailing;
      a.textContent = "View latest →";
      div.appendChild(a);
      return div;
    }
    return null;
  }

  function switchVersion(ctx, target) {
    if (target === ctx.version) return;
    const targetUrl = ctx.baseUrl + target + "/" + ctx.trailing;
    const fallbackUrl = ctx.baseUrl + target + "/format/";
    // Try the equivalent path first; fall back to the version's format page
    // if the trailing sub-path doesn't exist there.
    fetch(targetUrl, { method: "HEAD" })
      .then((r) => {
        window.location.href = r.ok ? targetUrl : fallbackUrl;
      })
      .catch(() => {
        window.location.href = fallbackUrl;
      });
  }

  function injectStyles() {
    if (document.getElementById("astra-version-selector-styles")) return;
    const style = document.createElement("style");
    style.id = "astra-version-selector-styles";
    style.textContent = `
      .${SELECTOR_CLASS} {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0 0 1rem 0;
        padding: 0.4rem 0.75rem;
        font-size: 0.85rem;
        background: var(--md-default-fg-color--lightest, #f5f5f5);
        border-radius: 0.4rem;
      }
      .${SELECTOR_CLASS} label {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0;
        font-weight: 500;
      }
      .${SELECTOR_CLASS} select {
        font: inherit;
        padding: 0.2rem 0.4rem;
        border-radius: 0.3rem;
        border: 1px solid var(--md-default-fg-color--light, #ccc);
        background: var(--md-default-bg-color, #fff);
        color: var(--md-default-fg-color, inherit);
      }
      .${BANNER_CLASS} {
        margin: 0 0 1rem 0;
        padding: 0.6rem 0.85rem;
        border-radius: 0.4rem;
        border-left: 3px solid;
        font-size: 0.9rem;
      }
      .${BANNER_CLASS}--draft {
        background: rgba(255, 193, 7, 0.12);
        border-left-color: #f0a500;
      }
      .${BANNER_CLASS}--outdated {
        background: rgba(244, 67, 54, 0.10);
        border-left-color: #d32f2f;
      }
      .${BANNER_CLASS} a {
        font-weight: 600;
      }
    `;
    document.head.appendChild(style);
  }
})();
