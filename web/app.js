// The status page in the browser. The HTML arrives complete from the build;
// this adds: theme switching, filters and search, live relative times, a
// countdown to the next check, folding panels, tooltips on the history
// strips, and fetching a newer page in place without reloading.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const root = document.documentElement;
  const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Theme: light, dark, or the system's, remembered for this reader.
  const themeBtn = $("#theme");
  const isDark = () => root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  const label = () => { const l = isDark() ? "Switch to light theme" : "Switch to dark theme"; themeBtn.setAttribute("aria-label", l); themeBtn.title = l; };
  themeBtn.onclick = () => { root.dataset.theme = isDark() ? "light" : "dark"; store.set("status.theme", root.dataset.theme); label(); };
  label();

  // Times: "3 min ago" beside the absolute time, kept current.
  const ago = (t) => {
    const s = (Date.now() - Date.parse(t)) / 1000;
    if (s < 90) return "just now";
    if (s < 5400) return `${Math.round(s / 60)} min ago`;
    if (s < 172800) return `${Math.round(s / 3600)} h ago`;
    return `${Math.round(s / 86400)} days ago`;
  };
  const tick = () => {
    $$("time.ago").forEach((el) => { el.textContent = ago(el.dateTime); el.title = new Date(el.dateTime).toUTCString(); });
    const app = $("#app"), next = Date.parse(app.dataset.next), left = next - Date.now();
    const cd = $("#countdown");
    if (cd) cd.textContent = left > 60000 ? `${Math.round(left / 60000)} min` : left > 0 ? "a minute" : "a few minutes (the check is due)";
  };

  // Filters and search: rows hide; a panel with nothing left hides too.
  let filter = "all";
  const apply = () => {
    const q = ($("#q").value || "").trim().toLowerCase();
    let shown = 0;
    $$(".repo").forEach((sec) => {
      let n = 0;
      $$(".row", sec).forEach((row) => {
        const st = row.dataset.state, kind = row.dataset.kind;
        const okf = filter === "all" || (filter === "problems" ? st === "warn" || st === "fail" : kind === filter);
        const okq = !q || (sec.querySelector("h2").textContent + " " + row.textContent).toLowerCase().includes(q);
        row.hidden = !(okf && okq);
        if (!row.hidden) n++;
      });
      sec.hidden = n === 0;
      shown += n;
    });
    $("#noMatch").hidden = shown > 0;
  };
  const wire = () => {
    $$(".filter").forEach((b) => b.onclick = () => {
      filter = b.dataset.filter;
      $$(".filter").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      apply();
    });
    $("#q").oninput = apply;
    // Folding: one panel, or all of them.
    $$(".fold").forEach((b) => b.onclick = () => {
      const body = document.getElementById(b.getAttribute("aria-controls"));
      const open = b.getAttribute("aria-expanded") !== "true";
      b.setAttribute("aria-expanded", String(open)); body.hidden = !open;
    });
    const fa = $("#foldAll");
    fa.onclick = () => {
      const collapse = fa.getAttribute("aria-pressed") !== "true";
      fa.setAttribute("aria-pressed", String(collapse)); fa.textContent = collapse ? "Expand all" : "Collapse all";
      $$(".fold").forEach((b) => { b.setAttribute("aria-expanded", String(!collapse)); document.getElementById(b.getAttribute("aria-controls")).hidden = collapse; });
    };
    // Counts rise from zero once, on the first load.
    if (!reduce && !wire.done) $$(".stats dd[data-count]").forEach((dd) => {
      const end = +dd.dataset.count; if (!end) return;
      const t0 = performance.now();
      const step = (t) => { const f = Math.min(1, (t - t0) / 700); dd.textContent = Math.round(end * (1 - (1 - f) ** 3)); if (f < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    });
    wire.done = true;
    apply(); tick();
  };

  // Tooltips on the history strips.
  const tip = $("#tip");
  document.addEventListener("pointerover", (ev) => {
    const r = ev.target.closest && ev.target.closest("rect[data-tip]");
    if (!r) { tip.hidden = true; return; }
    tip.textContent = r.dataset.tip; tip.hidden = false;
  });
  document.addEventListener("pointermove", (ev) => {
    if (tip.hidden) return;
    tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, ev.clientX + 12) + "px";
    tip.style.top = (ev.clientY + 16) + "px";
  });

  // A newer check: fetch the page, swap the content, keep filters and folds.
  const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => (t.hidden = true), 2600); };
  const refresh = async (manual) => {
    const btn = $("#refresh"); btn.classList.add("spin");
    try {
      const html = await fetch(`./?t=${Date.now()}`, { cache: "no-store" }).then((r) => r.text());
      const doc = new DOMParser().parseFromString(html, "text/html");
      const fresh = doc.getElementById("app");
      if (fresh && fresh.dataset.checked !== $("#app").dataset.checked) {
        const folded = $$('.fold[aria-expanded="false"]').map((b) => b.getAttribute("aria-controls"));
        const q = $("#q").value;
        $("#app").replaceWith(fresh);
        root.dataset.state = doc.documentElement.dataset.state;
        document.title = doc.title;
        folded.forEach((id) => { const b = $(`.fold[aria-controls="${id}"]`); if (b) { b.setAttribute("aria-expanded", "false"); document.getElementById(id).hidden = true; } });
        $$(".filter").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.filter === filter)));
        $("#q").value = q;
        wire();
        toast("Updated to the latest check");
      } else if (manual) toast("Already the latest check");
    } catch (e) {
      if (manual) toast("Could not reach the page; try again shortly");
    } finally { btn.classList.remove("spin"); }
  };
  $("#refresh").onclick = () => refresh(true);

  // Keys: / to search, r to refresh, Escape to clear.
  document.addEventListener("keydown", (ev) => {
    if (ev.target.matches("input, textarea") ) { if (ev.key === "Escape") { ev.target.value = ""; apply(); ev.target.blur(); } return; }
    if (ev.key === "/") { ev.preventDefault(); $("#q").focus(); }
    else if (ev.key === "r" && !ev.metaKey && !ev.ctrlKey) refresh(true);
  });

  wire();
  setInterval(tick, 30000);
  setInterval(() => refresh(false), 5 * 60000);
})();
