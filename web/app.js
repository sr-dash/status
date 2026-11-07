// The status page in the browser. The HTML arrives complete from the build;
// this adds: theme and view switching, filters and search, live times, a
// progress line and countdown to the next check, folding panels, tooltips on
// the charts, copying badges, keyboard shortcuts, and fetching a newer page
// in place (with a notice when a site changes state).
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const root = document.documentElement;
  const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => (t.hidden = true), 2800); };

  // Theme: light, dark, or the system's, remembered for this reader.
  const isDark = () => root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  const themeLabel = () => { const b = $("#theme"), l = isDark() ? "Switch to light theme" : "Switch to dark theme"; b.setAttribute("aria-label", l); b.title = l + " (T)"; };
  const toggleTheme = () => { root.dataset.theme = isDark() ? "light" : "dark"; store.set("status.theme", root.dataset.theme); themeLabel(); };
  $("#theme").onclick = toggleTheme;
  themeLabel();

  // View: every check with charts, or one compact card per site.
  const setView = (v) => {
    if (v === "compact") root.dataset.view = "compact"; else delete root.dataset.view;
    store.set("status.view", v);
    $$(".view").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === v)));
  };

  // Times: "3 min ago" beside the absolute time, kept current; the line
  // under the top bar fills toward the next check.
  const ago = (t) => {
    const s = (Date.now() - Date.parse(t)) / 1000;
    if (s < 90) return "just now";
    if (s < 5400) return `${Math.round(s / 60)} min ago`;
    if (s < 172800) return `${Math.round(s / 3600)} h ago`;
    return `${Math.round(s / 86400)} days ago`;
  };
  const tick = () => {
    $$("time.ago").forEach((el) => { el.textContent = ago(el.dateTime); el.title = new Date(el.dateTime).toUTCString(); });
    const app = $("#app"), done = Date.parse(app.dataset.checked), next = Date.parse(app.dataset.next), left = next - Date.now();
    const cd = $("#countdown");
    if (cd) cd.textContent = left > 90000 ? `${Math.round(left / 60000)} min` : left > 0 ? "a minute" : "a few minutes (it is due)";
    $("#nextFill").style.width = `${Math.max(0, Math.min(100, 100 * (Date.now() - done) / (next - done)))}%`;
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
      sec.hidden = n === 0 && (filter !== "all" || q);
      shown += n;
    });
    $("#noMatch").hidden = shown > 0;
  };
  const setFilter = (f) => { filter = f; $$(".filter").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.filter === f))); apply(); };

  // Copy: badges and their Markdown.
  const copy = async (btn) => {
    const text = btn.dataset.copy;
    try { await navigator.clipboard.writeText(text); }
    catch (e) { const r = document.createRange(); const el = btn.parentElement.querySelector("code") || btn; r.selectNodeContents(el); getSelection().removeAllRanges(); getSelection().addRange(r); }
    const was = btn.textContent; btn.textContent = "Copied"; btn.classList.add("done");
    setTimeout(() => { btn.textContent = was; btn.classList.remove("done"); }, 1600);
  };

  const wire = (first) => {
    $$(".filter").forEach((b) => b.onclick = () => setFilter(b.dataset.filter));
    $$(".view").forEach((b) => b.onclick = () => setView(b.dataset.view));
    $$(".view").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === (root.dataset.view || "detailed"))));
    $("#q").oninput = apply;
    $$(".copy").forEach((b) => b.onclick = () => copy(b));
    $$(".fold").forEach((b) => b.onclick = () => {
      const body = document.getElementById(b.getAttribute("aria-controls")), open = b.getAttribute("aria-expanded") !== "true";
      b.setAttribute("aria-expanded", String(open)); body.hidden = !open;
    });
    // Arrival: blocks rise into place in turn; counts run up from zero.
    if (first && !reduce) {
      $$("#app > *, .tile, .repo").forEach((el, i) => { el.classList.add("rise"); el.style.setProperty("--i", Math.min(i, 14)); });
      $$(".stats dd[data-count]").forEach((dd) => {
        const end = +dd.dataset.count; if (!end) return;
        const t0 = performance.now();
        const step = (t) => { const f = Math.min(1, (t - t0) / 800); dd.textContent = Math.round(end * (1 - (1 - f) ** 3)); if (f < 1) requestAnimationFrame(step); };
        requestAnimationFrame(step);
      });
    }
    apply(); tick();
  };

  // Tooltips on anything that carries data-tip (strips, ring, charts).
  const tip = $("#tip");
  const place = (x, y) => { tip.style.left = Math.max(8, Math.min(innerWidth - tip.offsetWidth - 8, x + 12)) + "px"; tip.style.top = Math.min(innerHeight - tip.offsetHeight - 8, y + 16) + "px"; };
  document.addEventListener("pointerover", (ev) => {
    const r = ev.target.closest && ev.target.closest("[data-tip]");
    if (!r) { tip.hidden = true; return; }
    tip.textContent = r.dataset.tip; tip.hidden = false; place(ev.clientX, ev.clientY);
  });
  document.addEventListener("pointermove", (ev) => { if (!tip.hidden) place(ev.clientX, ev.clientY); });
  addEventListener("scroll", () => (tip.hidden = true), { passive: true });

  // A newer check: fetch the page, swap the content, keep the reader's place,
  // and say which sites changed.
  const states = () => Object.fromEntries($$(".repo").map((s) => [s.querySelector("h2").firstChild.textContent.trim(), s.dataset.state]));
  const refresh = async (manual) => {
    const btn = $("#refresh"); btn.classList.add("spin");
    try {
      const html = await fetch(`./?t=${Date.now()}`, { cache: "no-store" }).then((r) => r.text());
      const doc = new DOMParser().parseFromString(html, "text/html");
      const fresh = doc.getElementById("app");
      if (fresh && fresh.dataset.checked !== $("#app").dataset.checked) {
        const before = states();
        const folded = $$('.fold[aria-expanded="false"]').map((b) => b.getAttribute("aria-controls"));
        const q = $("#q").value;
        $("#app").replaceWith(fresh);
        root.dataset.state = doc.documentElement.dataset.state;
        document.title = doc.title;
        $("#q").value = q;
        folded.forEach((id) => { const b = $(`.fold[aria-controls="${id}"]`); if (b) { b.setAttribute("aria-expanded", "false"); document.getElementById(id).hidden = true; } });
        $$(".filter").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.filter === filter)));
        wire(false);
        const after = states(), label = { ok: "operational", warn: "needs a look", fail: "failing" };
        const changed = Object.keys(after).filter((k) => before[k] && before[k] !== after[k]);
        toast(changed.length ? changed.map((k) => `${k} is now ${label[after[k]] || after[k]}`).join(" · ") : "Updated to the latest check");
      } else if (manual) toast("Already the latest check");
    } catch (e) {
      if (manual) toast("Could not reach the page; try again shortly");
    } finally { btn.classList.remove("spin"); }
  };
  $("#refresh").onclick = () => refresh(true);

  // Keyboard.
  const help = $("#help");
  $("#keys").onclick = () => help.showModal();
  const jump = (d) => {
    const secs = $$(".repo:not([hidden])"); if (!secs.length) return;
    const y = 90, i = secs.findIndex((s) => s.getBoundingClientRect().top > y + 4);
    const cur = i === -1 ? secs.length : i;
    const t = secs[Math.max(0, Math.min(secs.length - 1, d > 0 ? cur : cur - 2))];
    t.scrollIntoView({ block: "start" }); t.classList.add("flash"); setTimeout(() => t.classList.remove("flash"), 900);
  };
  document.addEventListener("keydown", (ev) => {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.target.matches("input, textarea")) { if (ev.key === "Escape") { ev.target.value = ""; apply(); ev.target.blur(); } return; }
    if (help.open) return;
    const k = ev.key.toLowerCase();
    if (k === "/") { ev.preventDefault(); $("#q").focus(); }
    else if (k === "?") help.showModal();
    else if (k === "r") refresh(true);
    else if (k === "t") toggleTheme();
    else if (k === "v") setView(root.dataset.view === "compact" ? "detailed" : "compact");
    else if (k === "p") setFilter("problems");
    else if (k === "a") setFilter("all");
    else if (k === "j") jump(1);
    else if (k === "k") jump(-1);
  });

  wire(true);
  setInterval(tick, 15000);
  setInterval(() => refresh(false), 5 * 60000);
})();
