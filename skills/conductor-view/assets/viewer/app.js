/* Conductor view: renders conductor/ live and writes feedback.md items. */
(function () {
  "use strict";

  const SNAPSHOT = window.CONDUCTOR_SNAPSHOT || null;
  // Opened straight from disk with no server: read a picked folder (local.js), copy feedback instead of saving.
  const LOCAL = !SNAPSHOT && location.protocol === "file:" && !!window.ConductorLocal;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // home: every project's card (/api/projects). state: the open project's full state.
  let home = null, homeVersion = null, state = null, version = null, project = null;
  let current = null, tab = "plan", view = "home", settingsScope = "main";
  let prevStatuses = new Map();
  const ui = { feedbackFilter: "all", focus: {} };
  // Home filters live in the link; null means "no filter". Sort and hidden columns are per browser.
  // Home filters live in the link; the sort order is per browser.
  const homeUi = { q: "", focus: null, filters: {}, openMenu: null, sort: "activity" };
  try { homeUi.sort = localStorage.getItem("conductor-view-sort") || "activity"; } catch {}
  const enc = encodeURIComponent;
  // Focus mode: the plan shows one phase and the spec one section at a time,
  // unless "show all" is on. ui.focus[track] = { plan: index, spec: index }.
  const showAll = { plan: false, spec: false };
  try { Object.assign(showAll, JSON.parse(localStorage.getItem("conductor-view-show-all") || "{}")); } catch {}
  function saveShowAll() { try { localStorage.setItem("conductor-view-show-all", JSON.stringify(showAll)); } catch {} }

  /* ---------------- markdown (escape first, then format) ---------------- */

  function inline(text, ctx) {
    const codes = [];
    let s = esc(text).replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
    s = s
      .replace(/\(diagram:\s*([\w.-]+)\)/g, (_, slug) => diagramChip(slug, ctx))
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => /^(https?:|\.{0,2}\/|#|[\w.-]+(\/|$))/i.test(u) && !/^javascript:/i.test(u) ? `<a href="${u}" target="_blank" rel="noopener">${t}</a>` : t)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^\w*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/(^|[^\w])_([^_\s][^_]*)_(?!\w)/g, "$1<em>$2</em>");
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[+i]}</code>`);
  }

  function diagramChip(slug, ctx) {
    const t = ctx && ctx.track;
    const has = t && t.diagrams.some((d) => d.slug === slug);
    const icon = '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z M9 4v14M15 6v14" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>';
    return has ? `<button class="chip-map" data-diagram="${esc(slug)}" title="Open the ${esc(slug)} map">${icon}${esc(slug)}</button>`
      : `<span class="chip-map missing" title="No diagrams/${esc(slug)}.json yet">${icon}${esc(slug)}</span>`;
  }

  function md(src, ctx) {
    const lines = String(src || "").replace(/\r/g, "").split("\n");
    const out = [];
    let i = 0;
    const isBlockStart = (l) => /^(```|#{1,6}\s|>|\s*([-*+]|\d+\.)\s+|\|)/.test(l) || /^\s*(-{3,}|\*{3,})\s*$/.test(l);
    while (i < lines.length) {
      const l = lines[i];
      if (!l.trim()) { i++; continue; }
      if (/^```/.test(l)) {
        const buf = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++; out.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`); continue;
      }
      let m = l.match(/^(#{1,6})\s+(.*)$/);
      if (m) { const n = m[1].length; out.push(`<h${n}>${inline(m[2], ctx)}</h${n}>`); i++; continue; }
      if (/^\s*(-{3,}|\*{3,})\s*$/.test(l)) { out.push("<hr>"); i++; continue; }
      if (/^>/.test(l)) {
        const buf = [];
        while (i < lines.length && /^>/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
        out.push(`<blockquote>${md(buf.join("\n"), ctx)}</blockquote>`); continue;
      }
      if (/^\|/.test(l)) {
        const rows = [];
        while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
        const cells = (r) => r.replace(/^\||\|\s*$/g, "").split("|").map((c) => c.trim());
        const body = rows.filter((r, j) => !(j === 1 && /^[|\s:-]+$/.test(r)));
        out.push(`<table><thead><tr>${cells(body[0]).map((c) => `<th>${inline(c, ctx)}</th>`).join("")}</tr></thead><tbody>${body.slice(1).map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c, ctx)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
        continue;
      }
      if (/^\s*([-*+]|\d+\.)\s+/.test(l)) {
        const items = [];
        while (i < lines.length) {
          const li = lines[i];
          const mm = li.match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
          if (mm) { items.push({ indent: mm[1].replace(/\t/g, "    ").length, ordered: /\d/.test(mm[2]), text: mm[3] }); i++; continue; }
          if (li.trim() && /^\s+/.test(li) && items.length) { items[items.length - 1].text += " " + li.trim(); i++; continue; }
          break;
        }
        out.push(renderList(items, 0, ctx).html); continue;
      }
      const buf = [];
      while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) buf.push(lines[i++].trim());
      if (!buf.length) buf.push(lines[i++].trim());
      out.push(`<p>${inline(buf.join(" "), ctx)}</p>`);
    }
    return out.join("\n");
  }

  function renderList(items, start, ctx) {
    const base = items[start].indent, tag = items[start].ordered ? "ol" : "ul";
    let html = `<${tag}>`, i = start;
    while (i < items.length && items[i].indent >= base) {
      if (items[i].indent > base) { const sub = renderList(items, i, ctx); html = html.replace(/<\/li>$/, sub.html + "</li>"); i = sub.next; continue; }
      let t = items[i].text, box = "";
      const cb = t.match(/^\[([ ~xX])\]\s+(.*)$/);
      if (cb) { box = `<span class="st st-${{ " ": "pending", "~": "in_progress", x: "done", X: "done" }[cb[1]]}" style="display:inline-block;vertical-align:-2px;margin-right:6px;width:12px;height:12px"></span>`; t = cb[2]; }
      html += `<li>${box}${inline(t, ctx)}</li>`;
      i++;
    }
    return { html: html + `</${tag}>`, next: i };
  }

  /* ---------------- data ---------------- */

  async function getJSON(url, opts) {
    const r = await fetch(url, Object.assign({ cache: "no-store" }, opts || {}));
    let j = {};
    try { j = await r.json(); } catch {}
    if (!r.ok) throw new Error(j.error || `${url} ${r.status}`);
    return j;
  }
  const postJSON = (url, body) => getJSON(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const projectQuery = () => (project ? `?project=${enc(project)}` : "");

  async function loadHome() {
    if (SNAPSHOT || LOCAL) { home = homeFromState(); return; }
    home = await getJSON("api/projects");
    homeVersion = home.version;
  }
  async function loadProject() {
    if (SNAPSHOT) { state = SNAPSHOT; return; }
    if (LOCAL) return;  // state comes from the folder picker
    state = await getJSON("api/state" + projectQuery());
    version = state.version;
    project = state.project_id;
  }
  // Views inside a project need that project's full state.
  async function ensureProject() {
    if (SNAPSHOT || LOCAL || view === "home" || (view === "settings" && settingsScope === "main")) return;
    if (!state || state.project_id !== project) { state = null; await loadProject(); }
  }
  async function load() { await loadHome(); await ensureProject(); }

  // The snapshot and the no-Python view hold one project and no git facts.
  function homeFromState() {
    if (!state) return { projects: [], problems: [] };
    const id = state.project_id || "project";
    const eff = (state.settings && state.settings.effective) || {};
    return {
      projects: [{ id, name: state.project || "project", path: "", active: true, registered: false, missing: false,
        initialized: state.initialized, tracks: state.tracks.map(window.ConductorLocal.summarizeTrack), git: null,
        settings: Object.fromEntries(Object.entries(eff).map(([k, v]) => [k, v.value])),
        exceptions: (state.settings && state.settings.exceptions) || [], same_as_main: [] }],
      problems: [],
    };
  }

  async function poll() {
    try {
      const hv = (await getJSON("api/home-version")).version;
      setLive("on");
      let changed = false;
      if (hv !== homeVersion) { await loadHome(); changed = true; }
      if (state && project && view !== "home") {
        const v = (await getJSON("api/version" + projectQuery())).version;
        if (v !== version) { await loadProject(); changed = true; }
      }
      if (changed) { render(true); setLive("flash"); }
    } catch { setLive("off"); }
    setTimeout(poll, 1500);
  }

  function setLive(mode) {
    const el = $("#live"), txt = $("#live-text");
    el.classList.remove("off", "flash", "snap");
    if (mode === "off") { el.classList.add("off"); txt.textContent = "disconnected"; }
    else if (mode === "snap") { el.classList.add("snap"); txt.textContent = "snapshot"; }
    else if (mode === "local") { el.classList.add("snap"); txt.textContent = state ? "from disk · reopen" : "from disk"; el.title = "Read from the folder you picked. Click to pick it again for changes."; }
    else if (mode === "flash") { el.classList.add("flash"); txt.textContent = "updated"; clearTimeout(setLive.t); setLive.t = setTimeout(() => setLive("on"), 1800); }
    else if (!el.classList.contains("flash")) txt.textContent = "live";
  }

  /* ---------------- helpers ---------------- */

  const STATUS_LABEL = { pending: "Pending", in_progress: "In progress", done: "Done", new: "New" };
  const statusIcon = (s) => `<span class="st st-${s}" role="img" aria-label="${STATUS_LABEL[s] || s}"></span>`;
  const commentIcon = '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>';
  // Snapshots and archived tracks are read-only: no comment or review buttons.
  let readOnly = false;
  const commentBtn = (target, label = "Comment") => readOnly ? "" : `<button class="comment-btn" data-comment="${esc(target)}">${commentIcon}${label}</button>`;

  const shaChips = (x) => (x.shas || (x.sha ? [x.sha] : [])).map((h) => `<span class="sha">${esc(h.slice(0, 7))}</span>`).join("");

  function trackTotals(t) {
    const tasks = t.plan.phases.flatMap((p) => p.tasks);
    return { done: tasks.filter((x) => x.status === "done").length, total: tasks.length, tasks };
  }
  function trackTitle(t) {
    const h1 = (t.spec.match(/^#\s+(.+)$/m) || [])[1];
    return h1 || t.metadata.description || (t.registry && t.registry.description) || t.id;
  }
  function openFeedbackFor(t, target) {
    return t.feedback.filter((f) => f.status !== "resolved" && f.target === target).length;
  }
  // An open change request wins; once the agent resolves it, the last approval (if any) shows again.
  function decision(t, what) {
    const items = t.feedback.filter((f) => f.target === what);
    const last = (kind, open) => items.filter((f) => f.kind === kind && (!open || f.status === "open")).pop() || null;
    return last("revise", true) || last("approve", false);
  }
  // The browser can't message the agent; it only writes feedback.md. Say what unblocks it.
  function waiting(d) {
    if (d.status === "waiting") return `<button class="chip warn wf" data-tab="feedback" title="Answer it on the Feedback tab">the agent asked you something · ${esc(d.id)}</button>`;
    return d.status === "open"
      ? `<span class="chip wait" title="The agent reads feedback.md when it next replies. Say anything in chat (for example “check feedback”) to make that happen now.">waiting for the agent · say “check feedback” in chat</span>`
      : "";
  }
  function phaseTarget(p, i) { return `plan › Phase ${i + 1}: ${p.title.replace(/^Phase\s*\d+\s*:\s*/i, "").replace(/\(diagram:[^)]*\)/g, "").trim()}`; }
  function taskTarget(p, i, task) { return `${phaseTarget(p, i)} › ${task.text.replace(/\(diagram:[^)]*\)/g, "").trim()}`; }

  /* ---------------- render ---------------- */

  function render(fromPoll) {
    renderTopbar();
    renderSidebar();
    const main = $("#main");
    const scroll = window.scrollY;
    main.classList.toggle("wide", view === "home");
    if (view === "home") { main.innerHTML = renderHome(); placeMenus(); }
    else if (view === "settings") main.innerHTML = renderSettings();
    else if (!state) main.innerHTML = `<div class="empty"><strong>Loading…</strong></div>`;
    else if (!state.initialized && !state.tracks.length) {
      main.innerHTML = `<div class="empty"><strong>No Conductor project here yet</strong>Run the <code>conductor-setup</code> skill in this project, then create a track.</div>`;
    } else {
      const tracks = state.tracks;
      if (!current || !tracks.some((t) => t.id === current)) current = tracks[0] && tracks[0].id;
      if (!tracks.length) main.innerHTML = `<div class="empty"><strong>No tracks yet</strong>Ask your agent to start a new track — it will appear here live.</div>`;
      else {
        const t = tracks.find((x) => x.id === current);
        main.innerHTML = renderTrack(t);
        highlightChanges(t);
      }
    }
    if (fromPoll) window.scrollTo(0, scroll);
  }

  const projectById = (id) => home && home.projects.find((p) => p.id === id);
  const projectHref = (id) => `#/${enc(id)}`;
  const trackHref = (pid, tid, tabName = "plan") => `#/${enc(pid)}/${enc(tid)}/${tabName}`;

  function renderTopbar() {
    const el = $("#project");
    const projects = (home && home.projects) || [];
    if (SNAPSHOT || LOCAL || !projects.length) { el.textContent = state && state.project ? `~/${state.project}` : ""; return; }
    const selected = view === "home" && !homeUi.focus ? "" : project || "";
    el.innerHTML = `<label class="switch"><span class="sr-only">Project</span><select id="project-switch" aria-label="Project">
      <option value=""${selected === "" ? " selected" : ""}>All projects</option>
      ${projects.map((p) => `<option value="${esc(p.id)}"${p.id === selected ? " selected" : ""}>${esc(p.name)}${p.missing ? " (not found)" : ""}</option>`).join("")}
    </select></label>`;
  }

  const ago = (sec) => {
    if (!sec) return "";
    const s = Math.max(0, Date.now() / 1000 - sec);
    if (s < 90) return "just now";
    const steps = [[60, "min"], [3600, "h"], [86400, "d"], [604800, "w"], [2629800, "mo"], [31557600, "y"]];
    let label = "";
    for (const [n, u] of steps) if (s >= n) label = `${Math.floor(s / n)}${u === "min" ? " min" : u}`;
    return label + " ago";
  };
  const pct = (done, total) => (total ? Math.round((done / total) * 100) : 0);
  const projectActivity = (p) => Math.max(0, ...p.tracks.map((t) => (t.git && t.git.last_activity) || 0));
  function sortedProjects() {
    return home.projects.slice().sort((a, b) => (b.active - a.active) || (projectActivity(b) - projectActivity(a)) || a.name.localeCompare(b.name));
  }

  // The sidebar lists unfinished tracks (in progress or open), grouped by project. Done and
  // archived ones drop off; the home page table still has them.
  const ACTIVE = new Set(["now", "open"]);
  const GROUP_LABEL = { now: "In progress", open: "Open", done: "Done", archived: "Archived" };
  const groupBadge = (g) => `<span class="gbadge g-${g}">${GROUP_LABEL[g] || g}</span>`;

  function sideTrack(p, t) {
    const here = view === "track" && project === p.id && current === t.id;
    return `<a class="track-link" href="${trackHref(p.id, t.id)}" data-track="${esc(t.id)}" data-project="${esc(p.id)}" aria-current="${here}">
        <span class="ring" style="--p:${pct(t.done, t.total)}" data-label="${pct(t.done, t.total)}%"></span>
        <span class="tl-text"><div class="t-name">${esc(t.title)}</div><div class="t-id">${t.waiting_feedback ? `<span class="side-needs">${t.waiting_feedback} need${t.waiting_feedback === 1 ? "s" : ""} you · </span>` : ""}<span class="mono">${esc(t.id)}</span></div></span></a>`;
  }
  // The open project comes first.
  function activeSection(first) {
    const projects = home ? sortedProjects() : [];
    if (first) projects.sort((a, b) => (b.id === first) - (a.id === first));
    const groups = projects.map((p) => [p, p.tracks.filter((t) => ACTIVE.has(t.group))]).filter(([, ts]) => ts.length);
    const body = groups.map(([p, ts]) => `${projects.length > 1 ? `<h3 class="side-proj"><a href="${projectHref(p.id)}">${esc(p.name)}</a></h3>` : ""}
      ${ts.slice().sort((a, b) => (a.group === "now" ? 0 : 1) - (b.group === "now" ? 0 : 1)).map((t) => sideTrack(p, t)).join("")}`).join("");
    return `<h2>Active tracks</h2>${body || `<p class="side-empty">No unfinished tracks. Done and archived ones are on the home page.</p>`}`;
  }

  function renderSidebar() {
    const sb = $("#sidebar");
    if (view === "home" || (view === "settings" && settingsScope === "main") || !project) {
      const projects = home ? sortedProjects() : [];
      sb.innerHTML = `<a class="track-link" href="#/" aria-current="${view === "home" && !homeUi.focus}">
          <span class="gear">${homeIcon}</span><span><div class="t-name">All projects</div><div class="t-id">${projects.length} project${projects.length === 1 ? "" : "s"}</div></span></a>
        ${SNAPSHOT || LOCAL ? "" : `<a class="track-link settings-link" href="#/settings" aria-current="${view === "settings"}">
          <span class="gear">${gearIcon}</span><span><div class="t-name">Main workflow rules</div><div class="t-id">for every project</div></span></a>`}
        ${activeSection(null)}
        <details class="side-archive side-projects"${projects.length <= 6 ? " open" : ""}><summary><h2>Projects · ${projects.length}</h2></summary>` + projects.map((p) => {
        const live = p.tracks.filter((t) => !t.archived);
        const done = live.reduce((n, t) => n + t.done, 0), total = live.reduce((n, t) => n + t.total, 0);
        const now = p.tracks.filter((t) => t.group === "now").length;
        return `<a class="track-link" href="${projectHref(p.id)}" data-project-link="${esc(p.id)}" aria-current="${view === "home" && homeUi.focus === p.id}">
          <span class="ring" style="--p:${pct(done, total)}" data-label="${pct(done, total)}%"></span>
          <span><div class="t-name">${esc(p.name)}</div><div class="t-id">${p.missing ? "not found" : `${live.length} track${live.length === 1 ? "" : "s"}${now ? ` · ${now} in progress` : ""}`}</div></span></a>`;
      }).join("") + `</details>`;
      return;
    }
    const eff = (state && state.settings && state.settings.effective) || {};
    const label = (key) => optionOf(key, eff[key] && eff[key].value)?.label || "";
    const p = projectById(project);
    sb.innerHTML = `${SNAPSHOT || LOCAL ? "" : `<a class="back-link" href="#/">← All projects</a>`}
      <a class="track-link settings-link" href="#/${enc(project)}/settings" aria-current="${view === "settings"}">
        <span class="gear">${gearIcon}</span>
        <span><div class="t-name">${esc((p && p.name) || (state && state.project) || "Project")} settings</div><div class="t-id">${esc([label("git.strategy"), label("testing.verification")].filter(Boolean).join(" · "))}</div></span></a>
      ${activeSection(project)}`;
  }

  /* ---------------- home page ---------------- */

  const GROUPS = [["now", "In progress"], ["open", "Open"], ["done", "Done"], ["archived", "Archived"]];
  const SAFETY = {
    uncommitted: ["warn", (g) => `● ${g.uncommitted} uncommitted`, "Files in this track have changes that aren't committed. Deleting it would lose them."],
    unpushed: ["warn", (g) => `↑ ${g.unpushed} not pushed`, "Commits for this track exist only on this machine."],
    committed: ["", () => "✓ committed · no remote", "Everything is committed, but the repo has no remote to push to."],
    pushed: ["ok", () => "✓ pushed", "Everything is committed and on the remote (as of the last fetch)."],
    landed: ["ok", () => "✓ landed", "The track's branch is merged into main."],
    nogit: ["", () => "no git", "This project isn't a git repo: nothing protects its files."],
  };
  function safetyChip(g) {
    if (!g || !SAFETY[g.safety]) return "";
    const [cls, text, title] = SAFETY[g.safety];
    return `<span class="chip safety ${cls}" title="${esc(title)}">${esc(text(g))}</span>`;
  }
  function reviewChip(d, what) {
    if (!d) return `<span class="chip review" title="${what} not reviewed yet">${what} ·</span>`;
    return d.kind === "approve" ? `<span class="chip review ok" title="${what} approved (${esc(d.id)})">${what} ✓</span>`
      : `<span class="chip review warn" title="${what}: changes requested (${esc(d.id)})">${what} ↺</span>`;
  }
  function phaseBar(t) {
    if (!t.phases.length) return `<span class="pbar empty" aria-hidden="true"></span>`;
    return `<span class="pbar" role="img" aria-label="${t.done} of ${t.total} tasks done">${t.phases.map((p, i) => `<span class="pseg ${p.status}" style="flex-grow:${Math.max(p.total, 1)}" title="Phase ${i + 1}: ${esc(p.title)} — ${p.done}/${p.total}"><i style="width:${pct(p.done, p.total)}%"></i></span>`).join("")}</span>`;
  }
  const REQ = {
    archive: { verb: "Archive", done: "Archive requested" },
    restore: { verb: "Restore", done: "Restore requested" },
    delete: { verb: "Delete", done: "Delete requested" },
  };
  const replyIcon = '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M10 6 4 12l6 6M4.5 12H15a5 5 0 0 1 5 5v1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const needsYouChip = (pid, t) => (t.waiting_feedback ? `<a class="chip warn needs-you" href="${trackHref(pid, t.id, "feedback")}" title="The agent asked you something">${replyIcon}${t.waiting_feedback} need${t.waiting_feedback === 1 ? "s" : ""} you</a>` : "");
  function requestChips(pid, t) {
    return (t.requests || []).map((r) => `<span class="chip wait req" title="The agent acts on it the next time it reads feedback. Say “check feedback” in chat.">${esc(REQ[r.kind].done)} · waiting for the agent</span>
      ${SNAPSHOT || LOCAL ? "" : `<button class="link-btn" data-withdraw="${esc(r.id)}" data-project="${esc(pid)}" data-track="${esc(t.id)}">Withdraw</button>`}`).join("");
  }
  const REQ_ICON = {
    archive: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4 5h16v4H4zM5.5 9v10h13V9M10 13h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>',
    restore: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>',
    delete: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10.5 11v5.5M13.5 11v5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>',
  };
  function requestButtons(pid, t, icons) {
    const pending = new Set((t.requests || []).map((r) => r.kind));
    const kinds = (t.archived ? ["restore", "delete"] : ["archive", "delete"]).filter((k) => !pending.has(k));
    return kinds.map((k) => `<button class="${icons ? "icon-act" : "link-btn"}${k === "delete" ? " danger" : ""}" data-request="${k}" data-project="${esc(pid)}" data-track="${esc(t.id)}" aria-label="${REQ[k].verb} ${esc(t.title)}"${icons ? ` title="${REQ[k].verb}…"` : ""}>${icons ? REQ_ICON[k] : REQ[k].verb}</button>`).join("");
  }

  function matchesSearch(t, p) {
    const q = homeUi.q.trim().toLowerCase();
    return !q || [t.title, t.id, t.description, p && p.name].some((x) => String(x || "").toLowerCase().includes(q));
  }

  /* One card per project; inside, tracks grouped by status in aligned columns. */
  const SAFETY_ORDER = { uncommitted: 0, unpushed: 1, committed: 2, nogit: 3, pushed: 4, landed: 5 };
  const SAFETY_NAME = { uncommitted: "Uncommitted", unpushed: "Not pushed", committed: "Committed, no remote", nogit: "No git", pushed: "Pushed", landed: "Landed" };
  const safetyOf = (t) => (t.git && t.git.safety) || "nogit";
  const DEFAULT_STATUS = ["now", "open", "done"];
  const FILTERS = {
    project: { label: "Project", of: (t, p) => p.id, name: (v) => (projectById(v) || { name: v }).name },
    git: { label: "Git", of: (t) => safetyOf(t), name: (v) => SAFETY_NAME[v] || v, order: Object.keys(SAFETY_ORDER) },
  };
  const FILTER_KEYS = ["status", ...Object.keys(FILTERS)];
  const SORTS = { activity: "Last activity", progress: "Progress", name: "Name" };

  const statusOn = () => homeUi.filters.status || new Set(DEFAULT_STATUS);
  function projectFilter() {
    if (homeUi.filters.project) return homeUi.filters.project;
    return homeUi.focus ? new Set([homeUi.focus]) : null;
  }
  // Tracks that pass search and every filter except `except`.
  function shownTracks(p, except) {
    const proj = projectFilter();
    if (except !== "project" && proj && !proj.has(p.id)) return [];
    return p.tracks.filter((t) => matchesSearch(t, p)
      && (except === "status" || statusOn().has(t.group))
      && (except === "git" || !homeUi.filters.git || homeUi.filters.git.has(safetyOf(t))));
  }
  function sortTracks(ts) {
    const act = (t) => (t.git && t.git.last_activity) || 0;
    const by = { activity: (a, b) => act(b) - act(a), progress: (a, b) => pct(b.done, b.total) - pct(a.done, a.total),
      name: (a, b) => a.title.localeCompare(b.title) };
    return ts.slice().sort((a, b) => by[homeUi.sort](a, b) || a.title.localeCompare(b.title));
  }
  const anyFilter = () => !!homeUi.q.trim() || !!homeUi.focus || FILTER_KEYS.some((k) => homeUi.filters[k]);

  function filterMenu(key) {
    const f = FILTERS[key];
    const counts = new Map();
    for (const p of sortedProjects()) for (const t of shownTracks(p, key)) { const v = f.of(t, p); counts.set(v, (counts.get(v) || 0) + 1); }
    const values = key === "project" ? sortedProjects().filter((p) => !p.missing).map((p) => p.id) : f.order.filter((v) => counts.has(v));
    const on = key === "project" ? projectFilter() : homeUi.filters[key];
    const active = !!on;
    return `<details class="th-filter" data-menu="${key}"${homeUi.openMenu === key ? " open" : ""}>
      <summary class="fchip${active ? " on" : ""}" aria-label="Filter by ${f.label.toLowerCase()}${active ? " (filtered)" : ""}">${f.label}${active ? ` <span class="count">${on.size}</span>` : ""} <span aria-hidden="true">▾</span></summary>
      <div class="menu" role="group" aria-label="Show ${f.label.toLowerCase()}">
        ${values.map((v) => `<label class="menu-item"><input type="checkbox" data-filter="${key}" value="${esc(v)}"${!on || on.has(v) ? " checked" : ""}>
          <span>${esc(f.name(v))}</span><span class="count">${counts.get(v) || 0}</span></label>`).join("") || `<p class="muted small menu-item">Nothing to filter</p>`}
        <div class="menu-foot"><button class="link-btn" data-filter-set="${key}:all">Select all</button>
          <button class="link-btn" data-filter-set="${key}:none">Clear</button></div>
      </div></details>`;
  }
  function setFilter(key, values) {
    if (key === "project") homeUi.focus = null;
    const all = key === "project" ? sortedProjects().filter((p) => !p.missing).map((p) => p.id)
      : [...new Set(home.projects.flatMap((p) => p.tracks.map((t) => FILTERS[key].of(t, p))))];
    homeUi.filters[key] = all.every((v) => values.has(v)) ? null : values;
    writeHash(); render();
  }
  function toggleStatus(g) {
    const on = new Set(statusOn());
    on.has(g) ? on.delete(g) : on.add(g);
    const isDefault = on.size === DEFAULT_STATUS.length && DEFAULT_STATUS.every((x) => on.has(x));
    homeUi.filters.status = isDefault ? null : on;
    writeHash(); render();
  }

  function trackRow(p, t) {
    const g = t.git || null;
    const revise = ["spec", "plan"].filter((w) => t[w] && t[w].kind === "revise")
      .map((w) => `<span class="chip warn" title="You requested changes to the ${w} (${esc(t[w].id)})">${w === "spec" ? "Spec" : "Plan"} ↺</span>`).join("");
    const fb = needsYouChip(p.id, t) + (t.open_feedback ? `<a class="chip" href="${trackHref(p.id, t.id, "feedback")}" title="Open feedback, with the agent">${commentIcon}${t.open_feedback}</a>` : "") + revise + requestChips(p.id, t);
    return `<li class="trow g-${t.group}" data-row="${esc(p.id)}/${esc(t.id)}">
      <div class="c-track"><a class="trow-title" href="${trackHref(p.id, t.id)}">${esc(t.title)}</a>
        <div class="trow-sub"><span class="mono">${esc(t.id)}</span>${t.current && t.group === "now" ? ` · <span class="trow-now">${t.current.next ? "next:" : "▶"} ${esc(t.current.text)}</span>` : ""}</div></div>
      <div class="c-progress">${phaseBar(t)}<span class="mono small muted">${t.done}/${t.total}</span></div>
      <div class="c-feedback">${fb || `<span class="muted small" aria-label="No open feedback">—</span>`}</div>
      <div class="c-git">${safetyChip(g)}</div>
      <div class="c-activity small">${g && g.last_activity ? `<span title="${esc(new Date(g.last_activity * 1000).toLocaleString())}">${esc(ago(g.last_activity))}</span>` : `<span class="muted">—</span>`}</div>
      <div class="c-actions">${SNAPSHOT ? "" : `<span class="row-actions">${requestButtons(p.id, t, true)}</span>`}</div>
    </li>`;
  }

  function projectCard(p) {
    const tracks = shownTracks(p);
    if (anyFilter() && !tracks.length && !(homeUi.focus === p.id)) return "";
    if (projectFilter() && !projectFilter().has(p.id)) return "";
    const settingsChip = !p.exceptions || !p.exceptions.length
      ? `<a class="chip" href="#/${enc(p.id)}/settings" title="This project uses the main workflow rules">follows main rules</a>`
      : `<a class="chip warn" href="#/${enc(p.id)}/settings" title="${esc(p.exceptions.join(", "))}">${p.exceptions.length} exception${p.exceptions.length === 1 ? "" : "s"}</a>`;
    const live = p.tracks.filter((t) => !t.archived);
    const counts = GROUPS.map(([g, label]) => [g, label, p.tracks.filter((t) => t.group === g).length]).filter(([, , n]) => n);
    const head = `<header class="proj-head">
        <div class="proj-titles">
          <h2 class="proj-name"><a href="${projectHref(p.id)}">${esc(p.name)}</a></h2>
          ${p.path ? `<div class="proj-path mono" title="${esc(p.path)}">${esc(p.path)}</div>` : ""}
          ${p.missing ? "" : `<div class="proj-counts">${counts.map(([g, label, n]) => `<span class="pc g-${g}"><strong>${n}</strong> ${label.toLowerCase()}</span>`).join("")}
            <span class="muted">${live.reduce((n, t) => n + t.done, 0)}/${live.reduce((n, t) => n + t.total, 0)} tasks</span></div>`}
        </div>
        <div class="proj-meta">
          ${p.active ? `<span class="chip ok" title="The viewer was started in this project">this folder</span>` : ""}
          ${p.git && p.git.git && p.git.branch ? `<span class="chip mono" title="Checked-out branch">⎇ ${esc(p.git.branch)}</span>` : ""}
          ${p.missing ? "" : settingsChip}
          ${p.registered && !SNAPSHOT && !LOCAL ? `<button class="link-btn" data-forget="${esc(p.id)}" title="Stop listing this project. Its files are not touched.">Forget</button>` : ""}
        </div>
      </header>`;
    if (p.missing) {
      return `<section class="proj-card missing" id="proj-${esc(p.id)}">${head}
        <div class="empty small"><strong>Folder not found</strong>It may have moved or been deleted. Forget it, or add it again from its new place.</div></section>`;
    }
    const groups = GROUPS.map(([g, label]) => {
      const rows = sortTracks(tracks.filter((t) => t.group === g));
      if (!rows.length) return "";
      return `<div class="tgroup g-${g}"><h3>${label} <span class="count">${rows.length}</span></h3>
        <ul class="trows">${rows.map((t) => trackRow(p, t)).join("")}</ul></div>`;
    }).join("");
    const hidden = p.tracks.filter((t) => matchesSearch(t, p) && !statusOn().has(t.group));
    const more = hidden.length && !homeUi.q.trim()
      ? `<p class="proj-more muted small">${hidden.length} more hidden by the status filter (${[...new Set(hidden.map((t) => GROUPS.find(([g]) => g === t.group)[1].toLowerCase()))].join(", ")}).</p>` : "";
    const colHead = groups ? `<div class="trow trow-head" aria-hidden="true"><div>Track</div><div>Progress</div><div>Feedback</div><div>Git</div><div>Activity</div><div></div></div>` : "";
    return `<section class="proj-card${p.active ? " active" : ""}${homeUi.focus === p.id ? " focused" : ""}" id="proj-${esc(p.id)}">${head}
      ${colHead}${groups || (p.tracks.length ? "" : `<div class="empty small"><strong>No tracks yet</strong>Ask your agent in this project to start one.</div>`)}${more}</section>`;
  }

  function renderHome() {
    if (!home) return `<div class="empty"><strong>Loading…</strong></div>`;
    const problems = (home.problems || []).map((pr) => `<div class="banner warn" role="alert">
        <div><strong>Couldn't read ${esc(pr.name)}</strong> (${esc(pr.error)}). The viewer started fresh and kept your old file as <code>${esc(pr.saved_as)}</code>. Fix it, then Restore.</div>
        <div class="banner-actions"><button class="btn" data-restore="${esc(pr.name)}">Restore</button><button class="btn ghost" data-dismiss="${esc(pr.name)}">Dismiss</button></div></div>`).join("");
    const projects = sortedProjects();
    const base = projects.flatMap((p) => shownTracks(p, "status"));
    const n = (g) => base.filter((t) => t.group === g).length;
    const chips = GROUPS.map(([g, l]) => `<button class="fchip g-${g}" data-status="${g}" aria-pressed="${statusOn().has(g)}">${l} <span class="count">${n(g)}</span></button>`).join("");
    const cards = projects.map(projectCard).join("");
    const live = projects.flatMap((p) => p.tracks.filter((t) => !t.archived));
    const one = projectFilter() && projectFilter().size === 1 ? projectById([...projectFilter()][0]) : null;
    return `${SNAPSHOT ? `<div class="snapshot-banner">Read-only snapshot. Run <code>serve.py</code> for the live view.</div>` : ""}${problems}
      <div class="home-head">
        <div><h1 class="track-title">${projects.length === 1 ? esc(projects[0].name) : one ? esc(one.name) : "Projects"}</h1>
          <p class="track-sub">${projects.length} project${projects.length === 1 ? "" : "s"} · ${live.length} tracks${live.some((t) => t.group === "now") ? ` · ${live.filter((t) => t.group === "now").length} in progress` : ""}</p></div>
        ${SNAPSHOT || LOCAL ? "" : `<div class="home-actions"><button class="btn" data-dialog="find">${searchIcon}Find projects</button><button class="btn" data-dialog="add">＋ Add by path</button></div>`}
      </div>
      <div class="home-tools">
        <input type="search" id="home-search" placeholder="Search tracks by name, id or project" aria-label="Search tracks" value="${esc(homeUi.q)}">
        <div class="fchips" role="group" aria-label="Show statuses">${chips}</div>
        <div class="fchips">${projects.length > 1 ? filterMenu("project") : ""}${filterMenu("git")}</div>
        <label class="sort">Sort <select id="home-sort" aria-label="Sort tracks">${Object.entries(SORTS).map(([k, l]) => `<option value="${k}"${homeUi.sort === k ? " selected" : ""}>${l}</option>`).join("")}</select></label>
        ${anyFilter() ? `<button class="link-btn" data-clear-filters>Clear filters</button>` : ""}
      </div>
      ${cards || (projects.length ? `<div class="empty"><strong>No tracks match</strong>${anyFilter() ? `<button class="link-btn" data-clear-filters>Clear filters</button>` : ""}</div>`
        : `<div class="empty"><strong>No projects yet</strong>Start the viewer inside a Conductor project, or add one.</div>`)}`;
  }

  // Menus are fixed-position so nothing scrolling can clip them.
  function placeMenus() {
    const d = homeUi.openMenu && document.querySelector(`.th-filter[data-menu="${homeUi.openMenu}"][open]`);
    if (!d) return;
    const r = d.querySelector("summary").getBoundingClientRect(), menu = d.querySelector(".menu");
    const w = menu.offsetWidth || 220;
    menu.style.top = `${Math.round(r.bottom + 4)}px`;
    menu.style.left = `${Math.round(Math.max(8, Math.min(r.left, window.innerWidth - w - 8)))}px`;
  }



  function renderTrack(t) {
    const ctx = { track: t };
    readOnly = !!SNAPSHOT || !!t.archived;
    const { done, total, tasks } = trackTotals(t);
    const status = (t.registry && t.registry.status) || t.metadata.status || "new";
    const openFb = t.feedback.filter((f) => f.status === "open").length;
    const needYou = t.feedback.filter((f) => f.status === "waiting").length;
    const dSpec = decision(t, "spec"), dPlan = decision(t, "plan");
    const badge = (d, what) => !d ? "" : d.kind === "approve"
      ? `<span class="chip ok">✓ ${what} approved</span>${waiting(d)}`
      : `<span class="chip warn">↺ ${what}: changes requested</span>${waiting(d)}`;
    const preamble = t.plan.preamble.length ? `<div class="preamble md">${md(t.plan.preamble.join("\n"), ctx)}</div>` : "";
    const created = (t.metadata.created_at || "").slice(0, 10);

    const tabs = [
      ["plan", "Plan", `${done}/${total}`],
      ["spec", "Spec", ""],
      ["diagrams", "Diagrams", t.diagrams.length],
      ["feedback", "Feedback", needYou ? `${needYou} need${needYou === 1 ? "s" : ""} you` : openFb ? `${openFb} open` : t.feedback.length || ""],
    ].map(([id, label, count]) => `<button class="tab" role="tab" data-tab="${id}" aria-selected="${tab === id}">${label}${count !== "" ? `<span class="count${id === "feedback" && (openFb || needYou) ? " hot" : ""}">${count}</span>` : ""}</button>`).join("");

    let body = "";
    const sections = tab === "spec" ? specSections(t.spec) : [];
    if (tab === "plan") body = preamble + renderPlan(t, ctx);
    else if (tab === "spec") body = renderSpec(t, ctx, sections);
    else if (tab === "diagrams") body = renderDiagrams(t);
    else body = renderFeedback(t, ctx);

    return `
      ${SNAPSHOT ? `<div class="snapshot-banner">Read-only snapshot — feedback is disabled. Run <code>serve.py</code> for the live view.</div>` : ""}
      ${t.archived ? `<div class="banner archived-banner"><div><strong>Archived track</strong> · read-only. It lives in <code>conductor/archive/${esc(t.id)}/</code>.</div>
        ${SNAPSHOT ? "" : `<div class="banner-actions">${trackRequestButtons(t)}</div>`}</div>` : ""}
      ${trackRequests(t)}
      <div class="eyebrow">
        <span class="chip type">${esc(t.metadata.type || "track")}</span>
        ${t.archived ? `<span class="chip">Archived</span>` : `<span class="chip st-${esc(status)}">${esc(STATUS_LABEL[status] || status)}</span>`}
        <span class="chip mono">${esc(t.id)}</span>
        ${created ? `<span class="chip mono">${esc(created)}</span>` : ""}
        ${badge(dSpec, "Spec")}${badge(dPlan, "Plan")}
        ${t.metadata_error ? `<span class="chip warn">metadata.json: ${esc(t.metadata_error)}</span>` : ""}
      </div>
      <div class="header-row">
        <div>
          <h1 class="track-title">${esc(trackTitle(t))}</h1>
          <p class="track-sub">${esc((t.registry && t.registry.description) || t.metadata.description || "")}</p>
        </div>
        ${readOnly ? "" : `<div class="review-actions">
          <button class="btn" data-decide="revise">↺ Request changes</button>
          <button class="btn good" data-decide="approve:spec">✓ Approve spec</button>
          <button class="btn primary" data-decide="approve:plan">✓ Approve plan</button>
        </div>`}
      </div>
      ${workflowChips()}
      <div id="overview-anchor"></div>
      <div class="overview" id="overview">
        <div class="progress">
          <div class="progress-meta"><span><strong class="ov-title">${esc(trackTitle(t))}</strong> · ${done} of ${total} tasks done · ${total ? Math.round((done / total) * 100) : 0}%</span>
            ${tab === "plan" && t.plan.phases.length > 1 ? `<button class="link-btn" data-show-all="plan">${showAll.plan ? "Show one phase" : "Show all phases"}</button>` : ""}</div>
          <div class="progress-groups">${progressGroups(t)}</div>
        </div>
        <div class="tabs" role="tablist">${tabs}</div>
        ${tab === "spec" && sections.filter((x) => x.title).length > 1 ? specNav(t, sections) : ""}
      </div>
      <section id="tab-body">${body}</section>`;
  }

  function trackSummary(t) {
    const p = projectById(project);
    return p && p.tracks.find((x) => x.id === t.id);
  }
  function trackRequests(t) {
    const s = trackSummary(t);
    if (!s || !s.requests.length) return "";
    return `<div class="banner req-banner"><div>${requestChips(project, s)}</div></div>`;
  }
  function trackRequestButtons(t) {
    const s = trackSummary(t);
    return s ? requestButtons(project, s) : "";
  }

  // One group per phase, sized by its task count: a numbered phase bar on top,
  // a segment per task below. Everything jumps to that place in the plan.
  function progressGroups(t) {
    const clean = (s) => s.replace(/^Phase\s*\d+\s*:\s*/i, "").replace(/\(diagram:[^)]*\)/g, "").trim();
    return t.plan.phases.map((p, i) => `
      <div class="pg ${p.status}" style="flex-grow:${Math.max(p.tasks.length, 1)}">
        <button class="pg-phase" data-goto-phase="${i}" aria-current="${tab === "plan" && !showAll.plan && i === planFocus(t)}" title="Phase ${i + 1}: ${esc(clean(p.title))} — ${p.done}/${p.total}">
          <span class="pg-num">${p.status === "done" ? "✓" : i + 1}</span><span class="pg-name">${esc(clean(p.title))}</span></button>
        <div class="pg-tasks">${p.tasks.map((task, j) => `<button class="pg-task ${task.status}" data-goto-task="${i}/${j}" aria-label="Phase ${i + 1}, task ${j + 1}, ${esc(STATUS_LABEL[task.status] || task.status)}: ${esc(clean(task.text).replace(/`/g, ""))}" title="${esc(STATUS_LABEL[task.status] || task.status)}: ${esc(clean(task.text).replace(/`/g, ""))}"></button>`).join("")}</div>
      </div>`).join("");
  }

  // The phase to show: the one picked, else the first in progress, else the first not done.
  function planFocus(t) {
    const n = t.plan.phases.length;
    const picked = (ui.focus[`${project}/${t.id}`] || {}).plan;
    if (picked != null && picked < n) return picked;
    const at = (st) => t.plan.phases.findIndex((p) => p.status === st);
    return [at("in_progress"), at("pending")].find((i) => i >= 0) ?? Math.max(n - 1, 0);
  }
  function specFocus(t, sections) {
    const picked = (ui.focus[`${project}/${t.id}`] || {}).spec;
    return picked != null && picked < sections.length ? picked : 0;
  }
  function setFocus(kind, i) { const k = `${project}/${current}`; (ui.focus[k] = ui.focus[k] || {})[kind] = i; }

  function pager(kind, i, items, label) {
    const btn = (j, dir) => j < 0 || j >= items.length ? "<span></span>"
      : `<button class="btn pager-${dir}" data-focus="${kind}:${j}">${dir === "prev" ? "← " : ""}${esc(label(items[j], j))}${dir === "next" ? " →" : ""}</button>`;
    return `<nav class="pager" aria-label="${kind === "plan" ? "Phases" : "Sections"}">${btn(i - 1, "prev")}${btn(i + 1, "next")}</nav>`;
  }

  function renderPlan(t, ctx) {
    if (!t.plan.phases.length) return `<div class="empty"><strong>No plan yet</strong>The agent hasn't written <code>plan.md</code> for this track.</div>`;
    const focus = planFocus(t);
    const phaseName = (p, i) => `${i + 1} · ${p.title.replace(/^Phase\s*\d+\s*:\s*/i, "").replace(/\(diagram:[^)]*\)/g, "").trim()}`;
    const html = t.plan.phases.map((p, i) => {
      if (!showAll.plan && i !== focus) return "";
      const title = p.title.replace(/^Phase\s*\d+\s*:\s*/i, "");
      const pt = phaseTarget(p, i);
      const nfb = openFeedbackFor(t, pt);
      const tasksHtml = p.tasks.map((task, j) => {
        const tt = taskTarget(p, i, task);
        const n = openFeedbackFor(t, tt);
        return `<li class="task ${task.status}${task.is_checkpoint ? " checkpoint" : ""}" data-key="${i}/${j}">
          ${statusIcon(task.status)}
          <div class="task-line"><span class="task-text">${inline(task.text, ctx)}</span>
            ${n ? `<span class="has-fb" title="Open feedback">${commentIcon}${n}</span>` : ""}
            ${shaChips(task)}
            ${commentBtn(tt)}</div>
          ${task.subtasks.length ? `<ul class="subtasks">${task.subtasks.map((s) => `<li class="subtask">${statusIcon(s.status)}<span>${inline(s.text, ctx)}</span>${shaChips(s)}</li>`).join("")}</ul>` : ""}
          ${task.notes.length ? `<div class="notes md">${md(task.notes.join("\n"), ctx)}</div>` : ""}
        </li>`;
      }).join("");
      return `<article class="phase ${p.status}" id="phase-${i}">
        <div class="phase-head">
          <span class="phase-num">${p.status === "done" ? "✓" : i + 1}</span>
          <span class="phase-title">${inline(title, ctx)}</span>
          <span class="phase-meta">
            ${nfb ? `<span class="has-fb">${commentIcon}${nfb}</span>` : ""}
            ${p.checkpoint ? `<span class="sha" title="Phase checkpoint">⚑ ${esc(p.checkpoint.slice(0, 7))}</span>` : ""}
            ${commentBtn(pt)}
            <span class="mini-bar"><i style="width:${p.total ? (p.done / p.total) * 100 : 0}%"></i></span>
            <span class="muted small mono">${p.done}/${p.total}</span>
          </span>
        </div>
        ${p.notes.length ? `<div class="notes md" style="padding:8px 16px 0">${md(p.notes.join("\n"), ctx)}</div>` : ""}
        <ul class="tasks">${tasksHtml}</ul>
      </article>`;
    }).join("");
    return showAll.plan || t.plan.phases.length < 2 ? html : html + pager("plan", focus, t.plan.phases, phaseName);
  }

  function specSections(src) {
    const lines = String(src || "").split("\n");
    const sections = [];
    let cur = { title: null, lines: [] };
    for (const l of lines) {
      if (/^#\s+/.test(l)) continue;
      const m = l.match(/^##\s+(.*)$/);
      if (m) { if (cur.title || cur.lines.join("").trim()) sections.push(cur); cur = { title: m[1].trim(), lines: [] }; }
      else cur.lines.push(l);
    }
    if (cur.title || cur.lines.join("").trim()) sections.push(cur);
    return sections;
  }

  function specNav(t, sections) {
    const focus = specFocus(t, sections);
    const chips = sections.map((s, i) => `<button data-focus="spec:${i}" aria-current="${!showAll.spec && i === focus}">${esc(s.title || "Overview")}</button>`).join("");
    return `<div class="spec-toc">${chips}<button class="link-btn" data-show-all="spec">${showAll.spec ? "Show one section" : "Show whole spec"}</button></div>`;
  }

  function renderSpec(t, ctx, sections) {
    if (!t.spec.trim()) return `<div class="empty"><strong>No spec yet</strong></div>`;
    const focus = specFocus(t, sections);
    const single = !showAll.spec && sections.length > 1;
    const html = sections.map((s, i) => {
      if (single && i !== focus) return "";
      const target = `spec › ${s.title || "Intro"}`;
      const n = openFeedbackFor(t, target);
      return `<section class="spec-section${/question/i.test(s.title || "") ? " questions" : ""}" id="spec-${i}">
        ${commentBtn(target)}
        <div class="md">${s.title ? `<h2>${inline(s.title, ctx)} ${n ? `<span class="has-fb">${commentIcon}${n}</span>` : ""}</h2>` : ""}${md(s.lines.join("\n"), ctx)}</div>
      </section>`;
    }).join("");
    return single ? html + pager("spec", focus, sections, (s) => s.title || "Overview") : html;
  }

  function renderDiagrams(t) {
    if (!t.diagrams.length) return `<div class="empty"><strong>No diagrams yet</strong>Agents add them as <code>diagrams/&lt;slug&gt;.json</code> (world map) or <code>.svg</code> in the track folder.</div>`;
    return `<div class="diagram-grid">` + t.diagrams.map((d) => {
      if (d.type === "error") return `<div class="error-card">${esc(d.error)}</div>`;
      const data = d.data || {};
      const thumb = d.type === "svg" ? `<img alt="" style="max-width:92%;max-height:88%" src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(d.svg)}">` : window.WorldMap.thumbnail(data);
      return `<button class="diagram-card" data-diagram="${esc(d.slug)}">
        <div class="diagram-thumb">${thumb}</div>
        <div class="diagram-body"><h3>${esc(d.title)}</h3><p>${esc(data.summary || "")}</p>
          <div class="meta"><span class="chip mono">${esc(d.slug)}</span>
          ${d.type === "map" ? `<span class="chip">${(data.nodes || []).length} nodes</span>${(data.tour || []).length ? `<span class="chip">tour · ${data.tour.length}</span>` : ""}` : `<span class="chip">svg</span>`}</div></div>
      </button>`;
    }).join("") + `</div>`;
  }

  // Each item is a conversation: the user's comment, then the agent's and the user's replies in order.
  const FB_STATE = {
    waiting: ["warn", "Needs your answer", "The agent asked you something. Reply below."],
    open: ["wait", "With the agent", "The agent reads it the next time it replies. Say “check feedback” in chat to make that happen now."],
    resolved: ["ok", "Resolved", ""],
  };
  const FB_KIND = { comment: "commented", revise: "requested changes", approve: "approved", archive: "asked to archive", restore: "asked to restore", delete: "asked to delete" };
  function fbMessage(who, when, text, ctx, extra = "") {
    const name = { you: "You", agent: "Agent", note: "Note" }[who];
    return `<li class="fb-msg ${who}"><div class="fb-meta"><strong>${name}</strong>${extra}${when ? ` <span class="fb-when">${esc(when)}</span>` : ""}</div>
      <div class="md">${md(text, ctx)}</div></li>`;
  }
  function renderFeedback(t, ctx) {
    const count = (st) => t.feedback.filter((f) => f.status === st).length;
    // Newest first, but anything waiting on the user goes on top.
    const all = t.feedback.slice().reverse().sort((a, b) => (b.status === "waiting") - (a.status === "waiting"));
    const shown = ui.feedbackFilter === "all" ? all : all.filter((f) => f.status === ui.feedbackFilter);
    const filters = [["all", "All", all.length], ["waiting", "Needs you", count("waiting")], ["open", "With the agent", count("open")], ["resolved", "Resolved", count("resolved")]];
    const toolbar = `<div class="fb-toolbar" role="group" aria-label="Show feedback">
      ${filters.map(([k, l, n]) => `<button class="fchip" data-fbfilter="${k}" aria-pressed="${ui.feedbackFilter === k}">${l} <span class="count">${n}</span></button>`).join("")}
      <span class="muted small fb-file">conductor/tracks/${esc(t.id)}/feedback.md</span></div>`;
    if (!shown.length) return toolbar + `<div class="empty"><strong>${all.length ? "Nothing here" : "No feedback yet"}</strong>Hover any phase, task or spec section and hit <em>Comment</em>. Then tell your agent “check feedback”.</div>`;
    return toolbar + shown.map((f) => {
      const [cls, label, hint] = FB_STATE[f.status] || FB_STATE.open;
      const first = fbMessage("you", f.when, f.body === "_(no message)_" ? "" : f.body, ctx, ` <span class="muted small">${esc(FB_KIND[f.kind] || f.kind)}</span>`);
      const rest = (f.thread || []).map((e) => fbMessage(e.who, e.when, e.text.replace(/^\*\*Agent:\*\*\s*/, ""), ctx)).join("");
      const canReply = !readOnly && !SNAPSHOT;
      return `<article class="fb-item ${esc(f.status)}" id="fb-${esc(f.id)}">
        <div class="fb-head"><span class="fb-id">${esc(f.id)}</span><span class="chip ${cls}">${label}</span>
          <span class="fb-target">${esc(f.target)}</span></div>
        <ol class="fb-thread">${first}${rest}</ol>
        ${canReply || hint ? `<div class="fb-foot">${hint ? `<span class="muted small">${hint}</span>` : ""}
          ${canReply ? `<button class="btn${f.status === "waiting" ? " primary" : ""}" data-reply="${esc(f.id)}">${f.status === "resolved" ? "Reply (reopens it)" : "Reply"}</button>` : ""}</div>` : ""}
      </article>`;
    }).join("");
  }

  function highlightChanges(t) {
    const next = new Map();
    t.plan.phases.forEach((p, i) => p.tasks.forEach((task, j) => next.set(`${t.id}:${i}/${j}`, task.status)));
    if (prevStatuses.size) next.forEach((s, k) => {
      if (prevStatuses.has(k) && prevStatuses.get(k) !== s) {
        const el = document.querySelector(`.task[data-key="${k.split(":")[1]}"]`);
        if (el) el.classList.add("just-changed");
      }
    });
    prevStatuses = next;
  }

  /* ---------------- feedback composer ---------------- */

  let pending = null;
  function compose(kind, target, id) {
    pending = { kind, target, id };
    const titles = { comment: "Comment", revise: "Request changes", approve: "Approve", reply: `Reply to ${id}` };
    $("#composer-kind").textContent = titles[kind];
    $("#composer-target").textContent = target;
    $("#composer-file").textContent = LOCAL ? "your clipboard, to paste to your agent" : `${(projectById(project) || {}).name || ""}/conductor/tracks/${current}/feedback.md`;
    $("#composer-send").textContent = LOCAL ? "Copy" : "Send";
    $("#composer-text").value = "";
    $("#composer-text").placeholder = kind === "approve" ? "Optional note for the agent…" : kind === "reply" ? "Your answer, or what's still not right…" : "What should the agent change, clarify or consider?";
    $("#composer").showModal();
    $("#composer-text").focus();
  }

  async function send() {
    const text = $("#composer-text").value.trim();
    if (pending.kind !== "approve" && !text) { $("#composer-text").focus(); return; }
    if (LOCAL) return copyForChat(pending.kind === "reply" ? `Reply to ${pending.id} on track ${current}:\n\n${text}`
      : window.ConductorLocal.feedbackForChat(current, pending.kind, pending.target, text));
    try {
      if (pending.kind === "reply") {
        await postJSON("api/feedback/reply", { project, track: current, id: pending.id, text });
        $("#composer").close();
        toast(`Replied on ${pending.id}. Tell your agent “check feedback”.`);
        await loadProject(); render(true);
        return;
      }
      const j = await postJSON("api/feedback", { project, track: current, kind: pending.kind, target: pending.target, text });
      $("#composer").close();
      toast(`Saved ${j.id} to feedback.md — tell your agent “check feedback”.`);
      await loadProject(); render(true);
    } catch (e) { toast("Could not save feedback: " + e.message); }
  }

  async function copyForChat(block) {
    try {
      await navigator.clipboard.writeText(block);
      $("#composer").close();
      toast("Copied. Paste it to your agent; it will add it to feedback.md.");
    } catch {
      // No clipboard access (some browsers on file://): leave it selected for Ctrl+C.
      $("#composer-text").value = block;
      $("#composer-text").select();
      toast("Press Ctrl+C (⌘C on a Mac) to copy, then paste it to your agent.");
    }
  }

  function pickerScreen() {
    return `<div class="empty picker"><strong>Open a Conductor project</strong>
      <p>This page was opened from disk, so there's no server to read your files. Pick the project folder (or just its <code>conductor</code> folder) to view it read-only. Feedback is copied for you to paste to your agent.</p>
      <label class="btn primary"><input type="file" id="pick-folder" webkitdirectory multiple hidden>Open project folder</label>
      <p class="muted small">Your browser may ask to confirm reading the folder. Nothing leaves your computer. For live updates and saving feedback, run <code>python3 serve.py --open</code> instead.</p></div>`;
  }

  async function openPicked(fileList) {
    const { files, project: folder } = await window.ConductorLocal.readPicked(fileList);
    if (!Object.keys(files).some((p) => p.startsWith("conductor/"))) { toast("No conductor/ folder in what you picked."); return; }
    state = window.ConductorLocal.buildState(files, folder);
    state.project_id = project = "project";
    home = homeFromState();
    readHash();
    render();
    setLive("local");
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg; el.classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 3800);
  }

  /* ---------------- workflow settings ---------------- */

  const homeIcon = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M3.5 11.5 12 4l8.5 7.5M6 10v9.5h4.5V15h3v4.5H18V10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>';
  const searchIcon = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="m15 15 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const gearIcon = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5l1.8 1.8M16.7 16.7l1.8 1.8M5.5 18.5l1.8-1.8M16.7 7.3l1.8-1.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';

  function settingDef(key) {
    const schema = (state && state.settings && state.settings.schema) || (home && home.main_settings && home.main_settings.schema);
    if (!schema) return null;
    for (const g of schema.groups) for (const st of g.settings) if (st.key === key) return st;
    return null;
  }
  function optionOf(key, value) { const st = settingDef(key); return st && st.options.find((o) => o.value === value); }

  function workflowChips() {
    const eff = (state.settings && state.settings.effective) || {};
    const keys = Object.keys(eff);
    const chips = keys.map((k) => { const o = eff[k] && optionOf(k, eff[k].value); return o ? `<button class="chip wf" data-view="settings" title="${esc(settingDef(k).label)} — change in Workflow settings">${esc(o.label)}</button>` : ""; }).join("");
    return chips ? `<div class="wf-row"><span class="muted small">Workflow</span>${chips}</div>` : "";
  }

  const SOURCE_LABEL = { repo: "this repo's exception", main: "main rule", default: "built-in default", invalid: "invalid value in file" };
  const optLabel = (key, value) => (optionOf(key, value) || {}).label || value;

  function settingsGroups(S, scope) {
    const disabled = SNAPSHOT || LOCAL;
    return S.schema.groups.map((g) => `<section class="set-group">
      <h2>${esc(g.label)}</h2><p class="muted">${esc(g.summary || "")}</p>
      ${g.settings.map((st) => {
        const e = S.effective[st.key] || { value: st.default, source: "default" };
        const sel = st.options.find((o) => o.value === e.value);
        let chips = "";
        if (scope === "project") {
          const same = e.source === "repo" && e.value === e.main;
          chips = `<span class="chip src-${esc(e.source)}${e.source === "repo" && !same ? " warn" : ""}">${esc(same ? "same as main rule" : SOURCE_LABEL[e.source] || e.source)}</span>
            ${e.source === "repo" || e.source === "invalid" ? `<button class="link-btn" data-reset="${esc(st.key)}" data-scope="project">Use main rule (${esc(optLabel(st.key, e.main))})</button>` : ""}`;
        } else {
          chips = `<span class="chip">${esc(e.source === "main" ? "set in main rules" : e.source === "invalid" ? "invalid value in file — using built-in" : "built-in default")}</span>
            ${e.source === "main" && e.value !== st.default ? `<button class="link-btn" data-reset="${esc(st.key)}" data-scope="main">Reset to built-in (${esc(optLabel(st.key, st.default))})</button>` : ""}`;
        }
        return `<div class="setting">
          <div class="setting-head"><h3>${esc(st.label)}</h3>${chips}</div>
          <div class="opts" role="radiogroup" aria-label="${esc(st.label)}">
            ${st.options.map((o) => `<button class="opt" role="radio" aria-checked="${o.value === e.value}" data-setting="${esc(st.key)}" data-value="${esc(o.value)}" data-scope="${scope}"${disabled ? " disabled" : ""}>
              <span class="opt-label"><span class="radio"></span>${esc(o.label)}</span>
              <span class="opt-summary">${inline(o.summary || "", {})}</span></button>`).join("")}
          </div>
          ${sel && sel.detail ? `<div class="opt-detail md">${md(sel.detail, {})}</div>` : ""}
          ${st.key.startsWith("testing.") ? `<p class="muted small">Plans that already exist keep their structure. Ask the agent to re-plan a track to apply a change there.</p>` : ""}
        </div>`;
      }).join("")}
    </section>`).join("");
  }

  function exceptionList() {
    const rules = home.main_settings.effective;
    const projects = sortedProjects().filter((p) => !p.missing);
    const withExceptions = projects.filter((p) => p.exceptions && p.exceptions.length);
    const tidy = projects.filter((p) => p.same_as_main && p.same_as_main.length);
    const following = projects.length - withExceptions.length;
    const rows = withExceptions.map((p) => `<li class="exc">
        <a class="exc-name" href="#/${enc(p.id)}/settings">${esc(p.name)}</a>
        <ul>${p.exceptions.map((k) => `<li><span>${esc((settingDef(k) || {}).label || k)}: <strong>${esc(optLabel(k, p.settings[k]))}</strong>
            <span class="muted">(main rule: ${esc(optLabel(k, rules[k] && rules[k].value))})</span></span>
            <button class="link-btn" data-reset="${esc(k)}" data-scope="project" data-project="${esc(p.id)}">Use main rule</button></li>`).join("")}</ul></li>`).join("");
    return `<section class="set-group exceptions">
      <h2>Exceptions</h2>
      <p class="muted">${following} of ${projects.length} project${projects.length === 1 ? "" : "s"} follow${following === 1 ? "s" : ""} the main rules${withExceptions.length ? "; these don't, in the settings listed" : ""}. Exceptions live in each repo's <code>conductor/settings.json</code>, so everyone working on that repo shares them.</p>
      ${rows ? `<ul class="exc-list">${rows}</ul>` : ""}
      ${tidy.map((p) => `<div class="banner"><div><strong>${esc(p.name)}</strong> repeats the main rule in ${p.same_as_main.length} setting${p.same_as_main.length === 1 ? "" : "s"} (${esc(p.same_as_main.map((k) => (settingDef(k) || {}).label || k).join(", "))}). Tidy removes them from its <code>settings.json</code>, so only real exceptions remain.</div>
        <div class="banner-actions"><button class="btn" data-tidy="${esc(p.id)}">Tidy</button></div></div>`).join("")}
    </section>`;
  }

  function renderSettings() {
    const main = settingsScope === "main";
    const S = (main ? home && home.main_settings : state && state.settings) || {};
    const p = !main && projectById(project);
    const name = (p && p.name) || (state && state.project) || "this project";
    let head;
    if (main) {
      head = `<div class="eyebrow"><span class="chip type">All projects</span><span class="chip mono">${esc(S.file || "settings.json")}</span></div>
        <h1 class="track-title">Main workflow rules</h1>
        <p class="track-sub">Every project follows these unless it has an exception. They're yours: saved on this machine, never in a repo.</p>`;
    } else {
      const exc = (S.exceptions || []), same = (S.same_as_main || []);
      head = `<div class="eyebrow"><span class="chip type">Project</span><span class="chip mono">conductor/settings.json</span>
          ${S.exists ? "" : `<span class="chip">no settings.json: follows the main rules</span>`}</div>
        <h1 class="track-title">Workflow settings · ${esc(name)}</h1>
        <p class="track-sub">Changing a value here makes it an exception for this repo, saved in its <code>conductor/settings.json</code> and shared with everyone who works on it. <a href="#/settings">Edit the main rules</a></p>
        <div class="follow" role="group" aria-label="Main rules or exceptions">
          <button class="fchip" aria-pressed="${!exc.length}" data-follow="main"${SNAPSHOT || LOCAL ? " disabled" : ""}>Follows main rules</button>
          <button class="fchip" aria-pressed="${!!exc.length}" disabled>Has exceptions${exc.length ? ` <span class="count">${exc.length}</span>` : ""}</button>
          ${exc.length ? `<span class="muted small">${esc(exc.map((k) => (settingDef(k) || {}).label || k).join(", "))}</span>` : `<span class="muted small">Pick a different value below to add an exception.</span>`}
        </div>
        ${same.length && !SNAPSHOT && !LOCAL ? `<div class="banner"><div>${same.length} setting${same.length === 1 ? "" : "s"} in this repo's file repeat${same.length === 1 ? "s" : ""} the main rule. Tidy removes them, so only real exceptions remain.</div>
          <div class="banner-actions"><button class="btn" data-tidy="${esc(project)}">Tidy</button></div></div>` : ""}`;
    }
    if (S.error) return head + `<div class="error-card">${esc(S.error)}</div>`;
    if (!S.schema) return head + `<div class="empty"><strong>Settings schema not found</strong>Expected <code>conductor-setup/assets/settings.schema.json</code> next to this skill.<pre class="md">${esc(JSON.stringify(S.values, null, 2))}</pre></div>`;
    return head + (main ? exceptionList() : "") + settingsGroups(S, main ? "main" : "project") + (main ? portSection() : "");
  }

  const PORT_SOURCE = { "--port": "the --port flag", CONDUCTOR_VIEW_PORT: "the CONDUCTOR_VIEW_PORT environment variable", "config.json": "your saved port", default: "the default" };
  function portSection() {
    const P = home && home.port;
    if (!P) return "";
    const overridden = P.saved && (P.source === "--port" || P.source === "CONDUCTOR_VIEW_PORT");
    return `<section class="set-group" id="port">
      <h2>Viewer port</h2>
      <p class="muted">The viewer only listens on this computer (127.0.0.1). Pick another port if ${P.default} clashes with something else you run.</p>
      <div class="setting">
        <div class="setting-head"><h3>Port</h3><span class="chip mono">now: ${P.value}</span><span class="chip">from ${esc(PORT_SOURCE[P.source] || P.source)}</span></div>
        <form class="port-form" id="port-form" novalidate>
          <label class="dlg-label" for="port-input">Saved port</label>
          <input id="port-input" class="dlg-input port-input" type="number" min="1024" max="65535" inputmode="numeric" placeholder="${P.default}" value="${P.saved ?? ""}">
          <button type="submit" class="btn primary">Save</button>
          ${P.saved ? `<button type="button" class="btn ghost" data-port-clear>Use default (${P.default})</button>` : ""}
        </form>
        <p class="muted small">Takes effect the next time the viewer starts: stop it (Ctrl+C where it runs), then run <code>${esc(P.restart)}</code>. Priority: <code>--port</code>, then <code>CONDUCTOR_VIEW_PORT</code>, then the saved port, then ${P.default}.${overridden ? ` <strong>Right now ${esc(PORT_SOURCE[P.source])} overrides your saved port.</strong>` : ""}</p>
      </div></section>`;
  }

  async function savePort(value) {
    try {
      await postJSON("api/config", { key: "port", value });
      toast(value === null ? "Saved: the viewer will use the default port next time it starts." : `Saved port ${value}. It applies the next time the viewer starts.`);
      await loadHome(); render(true);
    } catch (e) { toast(e.message); }
  }

  async function saveSetting(key, value, scope, pid) {
    try {
      await postJSON("api/settings", { project: pid || project, key, value, scope });
      const what = value === null ? (scope === "main" ? "back to the built-in default" : "back to the main rule") : `→ ${optLabel(key, value)}`;
      toast(`Saved: ${(settingDef(key) || {}).label || key} ${what}${scope === "main" ? " (main rules)" : ""}. Agents use it from their next step.`);
      await loadHome(); if (state) await loadProject(); render(true);
    } catch (e) { toast("Could not save setting: " + e.message); }
  }

  async function tidy(pid) {
    try {
      const j = await postJSON("api/settings/tidy", { project: pid });
      toast(j.removed.length ? `Tidied: removed ${j.removed.length} setting${j.removed.length === 1 ? "" : "s"} that repeated the main rule.` : "Nothing to tidy.");
      await loadHome(); if (state) await loadProject(); render(true);
    } catch (e) { toast("Could not tidy: " + e.message); }
  }

  async function followMain() {
    const exc = (state && state.settings && state.settings.exceptions) || [];
    if (!exc.length) return;
    if (!confirm(`Remove ${exc.length} exception${exc.length === 1 ? "" : "s"} from this repo's settings.json? The project will follow the main rules.`)) return;
    for (const k of exc) await postJSON("api/settings", { project, key: k, value: null, scope: "project" }).catch((e) => toast(e.message));
    await tidy(project);
  }

  /* ---------------- routing & events ---------------- */

  // Routes: #/ (home, ?q=&status=), #/settings (main rules), #/<project> (home, that card),
  // #/<project>/settings, #/<project>/<track>/<tab>[/<phase-n|section-n|diagram>[/<node>]].
  // Old links without a project (#/<track>/...) still work when the track id is unique.
  function findTrackOwner(tid) {
    const owners = ((home && home.projects) || []).filter((p) => p.tracks.some((t) => t.id === tid));
    const active = owners.find((p) => p.active);
    return active ? active.id : owners.length === 1 ? owners[0].id : null;
  }

  function readHash() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [pathPart, query = ""] = raw.split("?");
    const q = new URLSearchParams(query);
    homeUi.q = q.get("q") || "";
    homeUi.filters = {};
    for (const k of FILTER_KEYS) if (q.has(k)) homeUi.filters[k] = new Set(q.get(k).split(",").filter(Boolean));
    let segs = pathPart.split("/").filter(Boolean).map((s) => { try { return decodeURIComponent(s); } catch { return s; } });
    homeUi.focus = null;
    if (!segs.length) { view = "home"; return null; }
    if (segs[0] === "settings") { view = "settings"; settingsScope = "main"; return null; }
    if (!projectById(segs[0])) {
      const owner = findTrackOwner(segs[0]);
      if (!owner) { view = "home"; return null; }
      segs = [owner, ...segs];
    }
    project = segs[0];
    const [, tid, tabName, extra, node] = segs;
    if (!tid) { view = "home"; homeUi.focus = project; return null; }
    if (tid === "settings") { view = "settings"; settingsScope = "project"; return null; }
    view = "track"; current = tid;
    if (["plan", "spec", "diagrams", "feedback"].includes(tabName)) tab = tabName;
    const f = extra && extra.match(/^(phase|section)-(\d+|all)$/);
    if (f) {
      const kind = f[1] === "phase" ? "plan" : "spec";
      showAll[kind] = f[2] === "all";
      if (f[2] !== "all") setFocus(kind, Math.max(+f[2] - 1, 0));
      return null;
    }
    return extra ? { slug: extra, node } : null;
  }
  function writeHash() {
    let h;
    if (view === "home") {
      const q = new URLSearchParams();
      if (homeUi.q) q.set("q", homeUi.q);
      for (const k of FILTER_KEYS) if (homeUi.filters[k]) q.set(k, [...homeUi.filters[k]].join(","));
      h = "#/" + (homeUi.focus ? enc(homeUi.focus) : "") + (q.toString() ? "?" + q : "");
    } else if (view === "settings") h = settingsScope === "main" || !project ? "#/settings" : `#/${enc(project)}/settings`;
    else {
      let extra = "";
      const t = state && state.tracks.find((x) => x.id === current);
      if (t && tab === "plan") extra = showAll.plan ? "/phase-all" : `/phase-${planFocus(t) + 1}`;
      if (t && tab === "spec") extra = showAll.spec ? "/section-all" : `/section-${specFocus(t, specSections(t.spec)) + 1}`;
      h = `#/${enc(project)}/${enc(current)}/${tab}${extra}`;
    }
    if (location.hash !== h) history.replaceState(null, "", h);
  }

  // Keep the frozen overview in view and land content just below it.
  function settle(target) {
    const ov = $("#overview"), anchor = $("#overview-anchor");
    if (!ov || !anchor) return;
    const top = $(".topbar").offsetHeight;
    document.documentElement.style.setProperty("--sticky-offset", `${top + ov.offsetHeight + 12}px`);
    const stuckAt = anchor.getBoundingClientRect().top + window.scrollY - top;
    if (target) {
      const r = target.getBoundingClientRect();
      if (r.top < top + ov.offsetHeight || r.bottom > window.innerHeight) target.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (window.scrollY > stuckAt) window.scrollTo(0, stuckAt);
  }
  function pulse(el) { el.classList.remove("pulse"); void el.offsetWidth; el.classList.add("pulse"); }

  function openDiagram(slug, node) {
    const t = state.tracks.find((x) => x.id === current);
    const d = t && t.diagrams.find((x) => x.slug === slug);
    if (!d || d.type === "error") return;
    history.replaceState(null, "", `#/${enc(project)}/${enc(current)}/${tab}/${enc(slug)}`);
    window.WorldMap.open(d, { md: (s) => md(s, { track: t }), onClose: writeHash, focus: node });
  }

  async function navigate() {
    if (window.WorldMap.isOpen()) window.WorldMap.close();
    const deep = readHash();
    try { await ensureProject(); } catch (e) { toast(e.message); view = "home"; }
    render();
    if (view === "track") settle(); else window.scrollTo(0, 0);
    if (view === "home" && homeUi.focus) { const card = document.getElementById("proj-" + homeUi.focus); if (card) card.scrollIntoView({ block: "start" }); }
    if (deep) openDiagram(deep.slug, deep.node);
    writeHash();
  }

  /* ---------------- find / add projects ---------------- */

  function openDialog(html, focus) {
    const d = $("#dlg");
    d.innerHTML = html;
    if (!d.open) d.showModal();
    const f = focus && d.querySelector(focus);
    if (f) f.focus();
  }
  const dialogFoot = (primary, label) => `<div class="composer-foot"><span class="dlg-status muted small" role="status"></span>
    <div class="composer-actions"><button type="button" class="btn ghost" data-close>Cancel</button>${primary ? `<button type="submit" class="btn primary">${label}</button>` : ""}</div></div>`;

  function addDialog() {
    openDialog(`<form id="add-form"><div class="composer-head"><span class="composer-kind" id="dlg-title">Add a project by path</span>
        <span class="composer-target">A folder that contains <code>conductor/index.md</code>. Only listed here; nothing in it changes.</span></div>
      <input type="text" id="add-path" class="dlg-input" placeholder="/home/you/code/my-project" aria-label="Project folder path" autocomplete="off" spellcheck="false">
      ${dialogFoot(true, "Add")}</form>`, "#add-path");
  }

  function findDialog(found) {
    const results = !found ? "" : !found.found.length
      ? `<p class="muted">No Conductor projects found${found.truncated ? " before the search stopped" : ""}. Try other folders or a deeper search.</p>`
      : `<ul class="found">${found.found.map((f, i) => `<li><label><input type="checkbox" name="pick" value="${i}"${f.registered ? " checked disabled" : " checked"}>
          <span><strong>${esc(f.name)}</strong> <span class="mono muted small">${esc(f.path)}</span>${f.registered ? ` <span class="chip ok">already added</span>` : ""}</span></label></li>`).join("")}</ul>
        ${found.truncated ? `<p class="muted small">The search stopped early (time or result limit). Search a narrower folder to see more.</p>` : ""}`;
    const fresh = found ? found.found.filter((f) => !f.registered).length : 0;
    openDialog(`<form id="find-form"><div class="composer-head"><span class="composer-kind" id="dlg-title">Find projects</span>
        <span class="composer-target">Looks for folders containing <code>conductor/index.md</code>. Skips hidden, dependency and build folders.</span></div>
      <label class="dlg-label" for="find-roots">Folders to search, one per line</label>
      <textarea id="find-roots" class="dlg-input" rows="2" placeholder="Leave empty to search your home folder">${esc(((found && found.query) || []).join("\n"))}</textarea>
      <label class="dlg-label" for="find-depth">How deep <select id="find-depth">${[2, 3, 4, 5, 6].map((n) => `<option${n === ((found && found.depth) || 4) ? " selected" : ""}>${n}</option>`).join("")}</select> folders</label>
      <div class="dlg-row"><button type="button" class="btn" data-find>${searchIcon}Search</button></div>
      <div class="dlg-results">${results}</div>
      ${dialogFoot(fresh > 0, `Add selected`)}</form>`, found ? null : "#find-roots");
    findDialog.last = found;
  }

  async function runFind() {
    const roots = $("#find-roots").value.split("\n").map((s) => s.trim()).filter(Boolean);
    const depth = +$("#find-depth").value;
    $(".dlg-status").textContent = "Searching…";
    try {
      const found = await postJSON("api/scan", { roots: roots.length ? roots : null, depth });
      findDialog({ ...found, query: roots });
    } catch (e) { $(".dlg-status").textContent = e.message; }
  }

  async function addPaths(paths) {
    const added = [];
    for (const path of paths) {
      try { added.push(await postJSON("api/projects", { action: "add", path })); }
      catch (e) { $(".dlg-status").textContent = e.message; return null; }
    }
    $("#dlg").close();
    await loadHome();
    render(true);
    return added;
  }

  document.addEventListener("submit", async (ev) => {
    if (ev.target.id === "req-form") { ev.preventDefault(); return sendRequest(ev.target); }
    if (ev.target.id === "port-form") {
      ev.preventDefault();
      const raw = $("#port-input").value.trim();
      savePort(raw ? Number(raw) : null);
    } else if (ev.target.id === "add-form") {
      ev.preventDefault();
      const path = $("#add-path").value.trim();
      if (!path) return $("#add-path").focus();
      const added = await addPaths([path]);
      if (added) { toast(added[0].added ? `Added ${added[0].id}.` : `${added[0].id} was already added.`); location.hash = projectHref(added[0].id); }
    } else if (ev.target.id === "find-form") {
      ev.preventDefault();
      const found = findDialog.last;
      if (!found) return runFind();
      const picks = [...document.querySelectorAll('#find-form input[name=pick]:checked:not(:disabled)')].map((c) => found.found[+c.value].path);
      if (!picks.length) { $(".dlg-status").textContent = "Tick at least one project."; return; }
      const added = await addPaths(picks);
      if (added) toast(`Added ${added.length} project${added.length === 1 ? "" : "s"}.`);
    }
  });

  /* ---------------- archive / restore / delete requests ---------------- */

  function gitReport(d, kind) {
    if (!d) return "";
    if (!d.git) return `<div class="banner warn gitcheck"><div><strong>Not a git repo.</strong> Nothing protects these files${kind === "delete" ? ": a delete can't be undone" : ""}.</div></div>`;
    const lost = kind === "delete";
    const items = [];
    if (d.uncommitted_files.length) items.push(`<li><strong>${d.uncommitted} uncommitted file${d.uncommitted === 1 ? "" : "s"}</strong>${lost ? " would be lost" : " (the agent commits them with the move)"}:<ul class="mono small">${d.uncommitted_files.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></li>`);
    if (d.unpushed_commits.length && d.remote) items.push(`<li><strong>${d.unpushed} commit${d.unpushed === 1 ? "" : "s"} only on this machine</strong>${d.branch ? ` (branch <code>${esc(d.branch)}</code>)` : ""}:<ul class="mono small">${d.unpushed_commits.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></li>`);
    if (!d.remote) items.push(`<li>The repo has <strong>no remote</strong>: committed history stays on this machine only.</li>`);
    const safe = !d.uncommitted && (!d.unpushed || !d.remote) && d.remote;
    const fetched = d.remote ? `<p class="muted small">“Pushed” is as of the last fetch${d.last_fetch ? ` (${esc(ago(d.last_fetch))})` : " (never fetched here)"}.</p>` : "";
    return `<div class="banner ${safe ? "" : "warn"} gitcheck"><div>${safe
      ? `<strong>Safe.</strong> Committed and pushed${d.landed ? `, and landed in <code>${esc(d.main)}</code>` : ""}. ${lost ? "Its history stays in git after the delete." : ""}`
      : `<strong>Before you ${kind}:</strong><ul>${items.join("")}</ul>`}${fetched}</div></div>`;
  }
  const unsafe = (d) => d && (!d.git || d.uncommitted > 0 || (d.remote && d.unpushed > 0));

  async function requestDialog(kind, pid, tid) {
    const p = projectById(pid), t = p && p.tracks.find((x) => x.id === tid);
    if (!t) return;
    const what = {
      archive: `The agent moves it to <code>conductor/archive/${esc(tid)}/</code>, takes it out of <code>tracks.md</code> and commits. You can restore it later.`,
      restore: `The agent moves it back to <code>conductor/tracks/${esc(tid)}/</code>, adds it to <code>tracks.md</code> again and commits.`,
      delete: `The agent removes its folder and its <code>tracks.md</code> entry and commits, after checking with you once more in chat.`,
    }[kind];
    openDialog(`<form id="req-form" data-kind="${kind}" data-project="${esc(pid)}" data-track="${esc(tid)}">
      <div class="composer-head"><span class="composer-kind" id="dlg-title">${REQ[kind].verb} “${esc(t.title)}”${kind === "delete" ? " for good" : ""}?</span>
        <span class="composer-target">${esc(p.name)} · <span class="mono">${esc(tid)}</span></span></div>
      <p class="dlg-text">${what} The viewer only files the request; nothing changes until your agent acts on it.</p>
      <div class="dlg-git">${LOCAL ? "" : `<p class="muted small">Checking git…</p>`}</div>
      ${kind === "delete" ? `<label class="dlg-label" for="req-confirm">Type <code>${esc(tid)}</code> to confirm</label>
        <input id="req-confirm" class="dlg-input" autocomplete="off" spellcheck="false" aria-label="Type the track id to confirm">` : ""}
      <textarea id="req-note" class="dlg-input" rows="2" placeholder="Optional note for the agent" aria-label="Note for the agent"></textarea>
      ${dialogFoot(true, LOCAL ? "Copy request" : REQ[kind].verb)}</form>`, kind === "delete" ? "#req-confirm" : "#req-note");
    const submit = $("#req-form [type=submit]");
    if (kind === "delete") { submit.classList.add("danger"); submit.disabled = true; }
    if (LOCAL) return;
    try {
      const d = await getJSON(`api/git?project=${enc(pid)}&track=${enc(tid)}`);
      if (!$("#req-form")) return;
      $(".dlg-git").innerHTML = gitReport(d, kind);
      if (kind === "delete" && unsafe(d)) submit.textContent = "Delete anyway";
    } catch (e) { $(".dlg-git").innerHTML = `<p class="muted small">Couldn't check git: ${esc(e.message)}</p>`; }
  }

  async function sendRequest(form) {
    const { kind, project: pid, track: tid } = form.dataset;
    const text = $("#req-note").value.trim();
    if (LOCAL) {
      const block = window.ConductorLocal.feedbackForChat(tid, kind, "track", `${REQ[kind].verb} this track. ${text}`.trim());
      try { await navigator.clipboard.writeText(block); $("#dlg").close(); toast("Copied. Paste it to your agent."); }
      catch { $("#req-note").value = block; $("#req-note").select(); toast("Press Ctrl+C (⌘C on a Mac) to copy, then paste it to your agent."); }
      return;
    }
    try {
      const j = await postJSON("api/feedback", { project: pid, track: tid, kind, text, confirm: kind === "delete" ? $("#req-confirm").value.trim() : undefined });
      $("#dlg").close();
      toast(j.existing ? `Already requested (${j.id}). Tell your agent “check feedback”.` : `${REQ[kind].done} (${j.id}). Tell your agent “check feedback”.`);
      await loadHome(); if (state && state.project_id === pid) await loadProject(); render(true);
    } catch (e) { $(".dlg-status").textContent = e.message; }
  }

  async function withdraw(pid, tid, id) {
    try {
      await postJSON("api/feedback/withdraw", { project: pid, track: tid, id });
      toast(`Withdrew ${id}.`);
      await loadHome(); if (state && state.project_id === pid) await loadProject(); render(true);
    } catch (e) { toast(e.message); }
  }

  document.addEventListener("input", (ev) => {
    if (ev.target.id !== "req-confirm") return;
    const form = $("#req-form");
    form.querySelector("[type=submit]").disabled = ev.target.value.trim() !== form.dataset.track;
  });

  async function homeAction(url, body, done) {
    try { const j = await postJSON(url, body); if (done) toast(done(j)); await loadHome(); render(true); }
    catch (e) { toast(e.message); }
  }

  function closeMenus() {
    homeUi.openMenu = null;
    document.querySelectorAll(".th-filter[open]").forEach((d) => d.removeAttribute("open"));
  }
  document.addEventListener("toggle", (ev) => {
    const d = ev.target;
    if (!(d instanceof HTMLElement) || !d.classList.contains("th-filter")) return;
    if (d.open) {
      homeUi.openMenu = d.dataset.menu;
      document.querySelectorAll(".th-filter[open]").forEach((o) => { if (o !== d) o.removeAttribute("open"); });
      placeMenus();
    } else if (homeUi.openMenu === d.dataset.menu) homeUi.openMenu = null;
  }, true);
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape" || !homeUi.openMenu) return;
    const summary = document.querySelector(`.th-filter[data-menu="${homeUi.openMenu}"] summary`);
    closeMenus(); if (summary) summary.focus();
  });
  window.addEventListener("scroll", placeMenus, true);
  window.addEventListener("resize", placeMenus);
  document.addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.dataset.filter) {
      const k = t.dataset.filter;
      setFilter(k, new Set([...document.querySelectorAll(`[data-filter="${k}"]:checked`)].map((i) => i.value)));
      const again = document.querySelector(`[data-filter="${k}"][value="${CSS.escape(t.value)}"]`);
      if (again) again.focus();
    } else if (t.id === "home-sort") {
      homeUi.sort = SORTS[t.value] ? t.value : "activity";
      try { localStorage.setItem("conductor-view-sort", homeUi.sort); } catch {}
      render(); $("#home-sort").focus();
    }
  });
  document.addEventListener("click", (ev) => {
    if (homeUi.openMenu && !ev.target.closest(".th-filter")) closeMenus();
    const el = ev.target.closest("[data-view],[data-setting],[data-tab],[data-diagram],[data-comment],[data-decide],[data-goto-phase],[data-goto-task],[data-focus],[data-show-all],[data-fbfilter],[data-status],[data-forget],[data-restore],[data-dismiss],[data-dialog],[data-find],[data-close],[data-reset],[data-tidy],[data-follow],[data-port-clear],[data-request],[data-withdraw],[data-reply],[data-filter-set],[data-clear-filters]");
    if (!el) return;
    if (el.dataset.dialog) return el.dataset.dialog === "find" ? findDialog(null) : addDialog();
    if ("find" in el.dataset) return runFind();
    if ("close" in el.dataset) return $("#dlg").close();
    if (el.dataset.request) return requestDialog(el.dataset.request, el.dataset.project, el.dataset.track);
    if (el.dataset.reply) {
      const t = state && state.tracks.find((x) => x.id === current), f = t && t.feedback.find((x) => x.id === el.dataset.reply);
      return compose("reply", f ? f.target : "", el.dataset.reply);
    }
    if (el.dataset.withdraw) return withdraw(el.dataset.project, el.dataset.track, el.dataset.withdraw);
    if (el.dataset.view) { view = el.dataset.view; settingsScope = project ? "project" : "main"; writeHash(); render(); window.scrollTo(0, 0); }
    else if (el.dataset.setting) { if (el.getAttribute("aria-checked") !== "true") saveSetting(el.dataset.setting, el.dataset.value, el.dataset.scope || "project"); }
    else if (el.dataset.reset) saveSetting(el.dataset.reset, null, el.dataset.scope, el.dataset.project);
    else if (el.dataset.tidy) tidy(el.dataset.tidy);
    else if (el.dataset.follow) followMain();
    else if ("portClear" in el.dataset) savePort(null);
    else if (el.dataset.tab) { tab = el.dataset.tab; writeHash(); render(); settle(); }
    else if (el.dataset.diagram) openDiagram(el.dataset.diagram);
    else if (el.dataset.comment) compose("comment", el.dataset.comment);
    else if (el.dataset.decide) { const [kind, what] = el.dataset.decide.split(":"); compose(kind, what || (tab === "spec" ? "spec" : "plan")); }
    else if (el.dataset.gotoPhase || el.dataset.gotoTask) {
      const key = el.dataset.gotoTask || el.dataset.gotoPhase;
      tab = "plan"; setFocus("plan", +key.split("/")[0]); writeHash(); render();
      const target = el.dataset.gotoTask ? $(`.task[data-key="${CSS.escape(key)}"]`) : showAll.plan ? $(`#phase-${key}`) : null;
      settle(target);
      if (el.dataset.gotoTask && target) pulse(target);
    }
    else if (el.dataset.focus) {
      const [kind, i] = el.dataset.focus.split(":");
      setFocus(kind, +i); writeHash(); render();
      settle(showAll[kind] ? $(kind === "plan" ? `#phase-${i}` : `#spec-${i}`) : null);
    }
    else if (el.dataset.showAll) { const k = el.dataset.showAll; showAll[k] = !showAll[k]; saveShowAll(); writeHash(); render(); settle(); }
    else if (el.dataset.fbfilter) { ui.feedbackFilter = el.dataset.fbfilter; render(); }
    else if (el.dataset.status) { toggleStatus(el.dataset.status); $(`[data-status="${el.dataset.status}"]`).focus(); }
    else if (el.dataset.filterSet) {
      const [k, what] = el.dataset.filterSet.split(":");
      const all = new Set([...document.querySelectorAll(`[data-filter="${k}"]`)].map((i) => i.value));
      setFilter(k, what === "all" ? all : new Set());
    }
    else if ("clearFilters" in el.dataset) { homeUi.filters = {}; homeUi.focus = null; homeUi.q = ""; writeHash(); render(); }
    else if (el.dataset.forget) {
      const p = projectById(el.dataset.forget);
      if (p && confirm(`Stop listing ${p.name}? Its files are not touched, and you can add it again any time.`))
        homeAction("api/projects", { action: "forget", id: p.id }, () => `Forgot ${p.name}.`);
    }
    else if (el.dataset.restore) homeAction("api/config/restore", { file: el.dataset.restore }, () => `Restored ${el.dataset.restore}.`);
    else if (el.dataset.dismiss) homeAction("api/config/dismiss", { file: el.dataset.dismiss });
  });
  document.addEventListener("input", (ev) => {
    if (ev.target.id !== "home-search") return;
    homeUi.q = ev.target.value;
    writeHash();
    const pos = ev.target.selectionStart;
    render();
    const box = $("#home-search");
    box.focus();
    box.setSelectionRange(pos, pos);
  });
  document.addEventListener("change", (ev) => {
    if (ev.target.id === "project-switch") location.hash = ev.target.value ? projectHref(ev.target.value) : "#/";
  });
  // Links clicked or pasted (writeHash uses replaceState, so it never fires this).
  window.addEventListener("hashchange", () => { if (home || state) navigate(); });
  $("#composer-form").addEventListener("submit", (ev) => { ev.preventDefault(); send(); });
  $("#composer-cancel").addEventListener("click", () => $("#composer").close());
  $("#composer-text").addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); send(); } });

  /* theme */
  function setTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem("conductor-view-theme", t); } catch {} }
  let saved = null;
  try { saved = localStorage.getItem("conductor-view-theme"); } catch {}
  setTheme(saved || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
  $("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light"));

  /* boot */
  (async function boot() {
    if (LOCAL) {
      $("#main").innerHTML = pickerScreen();
      document.addEventListener("change", (ev) => { if (ev.target.id === "pick-folder" && ev.target.files.length) openPicked(ev.target.files); });
      $("#live").addEventListener("click", () => { if (state) { $("#main").innerHTML = pickerScreen(); $("#pick-folder").click(); } });
      setLive("local");
      return;
    }
    if (SNAPSHOT) { state = SNAPSHOT; project = state.project_id; }
    try { await loadHome(); } catch (e) { setLive("off"); $("#main").innerHTML = `<div class="empty"><strong>Can't reach the viewer server</strong>${esc(e.message)}</div>`; return; }
    await navigate();
    if (SNAPSHOT) setLive("snap"); else setTimeout(poll, 1500);
  })();
})();
