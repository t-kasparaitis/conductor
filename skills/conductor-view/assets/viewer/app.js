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
  const ui = { feedbackFilter: "open", focus: {} };
  const homeUi = { q: "", status: "all", focus: null };
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
    return t.feedback.filter((f) => f.status === "open" && f.target === target).length;
  }
  // An open change request wins; once the agent resolves it, the last approval (if any) shows again.
  function decision(t, what) {
    const items = t.feedback.filter((f) => f.target === what);
    const last = (kind, open) => items.filter((f) => f.kind === kind && (!open || f.status === "open")).pop() || null;
    return last("revise", true) || last("approve", false);
  }
  // The browser can't message the agent; it only writes feedback.md. Say what unblocks it.
  function waiting(d) {
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
    if (view === "home") main.innerHTML = renderHome();
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

  function renderSidebar() {
    const sb = $("#sidebar");
    if (view === "home" || (view === "settings" && settingsScope === "main") || !project) {
      const projects = home ? sortedProjects() : [];
      sb.innerHTML = `<a class="track-link" href="#/" aria-current="${view === "home" && !homeUi.focus}">
          <span class="gear">${homeIcon}</span><span><div class="t-name">All projects</div><div class="t-id">${projects.length} project${projects.length === 1 ? "" : "s"}</div></span></a>
        ${SNAPSHOT || LOCAL ? "" : `<a class="track-link settings-link" href="#/settings" aria-current="${view === "settings"}">
          <span class="gear">${gearIcon}</span><span><div class="t-name">Main workflow rules</div><div class="t-id">for every project</div></span></a>`}
        <h2>Projects</h2>` + projects.map((p) => {
        const live = p.tracks.filter((t) => !t.archived);
        const done = live.reduce((n, t) => n + t.done, 0), total = live.reduce((n, t) => n + t.total, 0);
        const now = p.tracks.filter((t) => t.group === "now").length;
        return `<a class="track-link" href="${projectHref(p.id)}" aria-current="${view === "home" && homeUi.focus === p.id}">
          <span class="ring" style="--p:${pct(done, total)}" data-label="${pct(done, total)}%"></span>
          <span><div class="t-name">${esc(p.name)}</div><div class="t-id">${p.missing ? "not found" : `${live.length} track${live.length === 1 ? "" : "s"}${now ? ` · ${now} now` : ""}`}</div></span></a>`;
      }).join("");
      return;
    }
    const eff = (state && state.settings && state.settings.effective) || {};
    const label = (key) => optionOf(key, eff[key] && eff[key].value)?.label || "";
    const tracks = state ? state.tracks : [];
    const link = (t) => {
      const { done, total } = trackTotals(t);
      const name = (t.registry && t.registry.description) || trackTitle(t);
      return `<a class="track-link" href="${trackHref(project, t.id)}" data-track="${esc(t.id)}" aria-current="${view === "track" && t.id === current}">
        <span class="ring" style="--p:${pct(done, total)}" data-label="${pct(done, total)}%"></span>
        <span><div class="t-name">${esc(name)}</div><div class="t-id">${esc(t.id)}</div></span></a>`;
    };
    const live = tracks.filter((t) => !t.archived), archived = tracks.filter((t) => t.archived);
    const p = projectById(project);
    sb.innerHTML = `${SNAPSHOT || LOCAL ? "" : `<a class="back-link" href="#/">← All projects</a>`}
      <h2>${esc((p && p.name) || (state && state.project) || "Project")}</h2>
      <a class="track-link settings-link" href="#/${enc(project)}/settings" aria-current="${view === "settings"}">
        <span class="gear">${gearIcon}</span>
        <span><div class="t-name">Workflow settings</div><div class="t-id">${esc([label("git.strategy"), label("testing.verification")].filter(Boolean).join(" · "))}</div></span></a>
      <h2>Tracks</h2>${live.map(link).join("")}
      ${archived.length ? `<details class="side-archive"${archived.some((t) => t.id === current) ? " open" : ""}><summary><h2>Archived · ${archived.length}</h2></summary>${archived.map(link).join("")}</details>` : ""}`;
  }

  /* ---------------- home page ---------------- */

  const GROUPS = [["now", "Now"], ["open", "Open"], ["done", "Done"], ["archived", "Archived"]];
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
  function trackRow(p, t) {
    const g = t.git || null;
    return `<li class="trow g-${t.group}">
      <a class="trow-main" href="${trackHref(p.id, t.id)}">
        <span class="trow-title">${esc(t.title)}</span>
        <span class="trow-sub"><span class="mono">${esc(t.id)}</span>${t.current && t.group === "now" ? ` · <span class="trow-now">${t.current.next ? "next:" : "▶"} ${esc(t.current.text)}</span>` : ""}</span>
      </a>
      <div class="trow-progress">${phaseBar(t)}<span class="mono small muted">${t.done}/${t.total}</span></div>
      <div class="trow-chips">
        <span class="chip type">${esc(t.type)}</span>
        ${reviewChip(t.spec, "Spec")}${reviewChip(t.plan, "Plan")}
        ${t.open_feedback ? `<a class="chip warn" href="${trackHref(p.id, t.id, "feedback")}" title="Open feedback">${commentIcon}${t.open_feedback}</a>` : ""}
        ${safetyChip(g)}
        ${g && g.branch ? `<span class="chip mono" title="The track's branch">⎇ ${esc(g.branch)}</span>` : ""}
        ${g && g.last_activity ? `<span class="muted small" title="${esc(new Date(g.last_activity * 1000).toLocaleString())}">${esc(ago(g.last_activity))}</span>` : ""}
      </div>
    </li>`;
  }

  function matchesSearch(t) {
    const q = homeUi.q.trim().toLowerCase();
    return !q || [t.title, t.id, t.description].some((s) => String(s || "").toLowerCase().includes(q));
  }
  const groupShown = (g) => homeUi.status === "all" || homeUi.status === g;

  function projectCard(p) {
    const tracks = p.tracks.filter(matchesSearch);
    const filtering = homeUi.q.trim() || homeUi.status !== "all";
    if (filtering && !tracks.some((t) => groupShown(t.group))) return "";
    const counts = Object.fromEntries(GROUPS.map(([g]) => [g, p.tracks.filter((t) => t.group === g).length]));
    const settingsChip = !p.exceptions || !p.exceptions.length
      ? `<a class="chip" href="#/${enc(p.id)}/settings" title="This project uses the main workflow rules">follows main rules</a>`
      : `<a class="chip warn" href="#/${enc(p.id)}/settings" title="${esc(p.exceptions.join(", "))}">${p.exceptions.length} exception${p.exceptions.length === 1 ? "" : "s"}</a>`;
    const head = `<header class="proj-head">
        <div class="proj-titles">
          <h2 class="proj-name"><a href="${projectHref(p.id)}">${esc(p.name)}</a></h2>
          ${p.path ? `<div class="proj-path mono" title="${esc(p.path)}">${esc(p.path)}</div>` : ""}
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
      if (!groupShown(g)) return "";
      const rows = tracks.filter((t) => t.group === g);
      if (!rows.length) return "";
      const body = `<ul class="trows">${rows.map((t) => trackRow(p, t)).join("")}</ul>`;
      const title = `<h3>${label} <span class="count">${rows.length}</span></h3>`;
      if (g === "archived") return `<details class="tgroup g-archived"${homeUi.status === "archived" || homeUi.q.trim() ? " open" : ""}><summary>${title}</summary>${body}</details>`;
      return `<div class="tgroup g-${g}">${title}${body}</div>`;
    }).join("");
    const live = p.tracks.filter((t) => !t.archived);
    const summary = `<div class="proj-counts">${GROUPS.map(([g, label]) => counts[g] ? `<span><strong>${counts[g]}</strong> ${label.toLowerCase()}</span>` : "").join("")}
      <span class="muted">${live.reduce((n, t) => n + t.done, 0)}/${live.reduce((n, t) => n + t.total, 0)} tasks</span></div>`;
    return `<section class="proj-card${p.active ? " active" : ""}${homeUi.focus === p.id ? " focused" : ""}" id="proj-${esc(p.id)}">${head}${summary}
      ${groups || `<div class="empty small"><strong>No tracks yet</strong>Ask your agent in this project to start one.</div>`}</section>`;
  }

  function renderHome() {
    if (!home) return `<div class="empty"><strong>Loading…</strong></div>`;
    const problems = (home.problems || []).map((pr) => `<div class="banner warn" role="alert">
        <div><strong>Couldn't read ${esc(pr.name)}</strong> (${esc(pr.error)}). The viewer started fresh and kept your old file as <code>${esc(pr.saved_as)}</code>. Fix it, then Restore.</div>
        <div class="banner-actions"><button class="btn" data-restore="${esc(pr.name)}">Restore</button><button class="btn ghost" data-dismiss="${esc(pr.name)}">Dismiss</button></div></div>`).join("");
    const projects = sortedProjects();
    const all = projects.flatMap((p) => p.tracks.filter(matchesSearch));
    const n = (g) => all.filter((t) => t.group === g).length;
    const chips = [["all", "All", all.filter((t) => !t.archived).length], ...GROUPS.map(([g, l]) => [g, l, n(g)])]
      .map(([g, l, c]) => `<button class="fchip" data-status="${g}" aria-pressed="${homeUi.status === g}">${l} <span class="count">${c}</span></button>`).join("");
    const cards = projects.map(projectCard).join("");
    const filtering = homeUi.q.trim() || homeUi.status !== "all";
    return `${SNAPSHOT ? `<div class="snapshot-banner">Read-only snapshot. Run <code>serve.py</code> for the live view.</div>` : ""}${problems}
      <div class="home-head">
        <div><h1 class="track-title">${projects.length === 1 ? esc(projects[0].name) : "Projects"}</h1>
          <p class="track-sub">${projects.length} project${projects.length === 1 ? "" : "s"} · ${all.filter((t) => !t.archived).length} tracks${n("now") ? ` · ${n("now")} in progress now` : ""}</p></div>
      </div>
      <div class="home-tools">
        <input type="search" id="home-search" placeholder="Search tracks by name or id" aria-label="Search tracks" value="${esc(homeUi.q)}">
        <div class="fchips" role="group" aria-label="Filter by status">${chips}</div>
      </div>
      ${cards || (filtering ? `<div class="empty"><strong>No tracks match</strong>Try another search or status.</div>`
        : `<div class="empty"><strong>No projects yet</strong>Start the viewer inside a Conductor project, or add one.</div>`)}`;
  }

  function renderTrack(t) {
    const ctx = { track: t };
    readOnly = !!SNAPSHOT || !!t.archived;
    const { done, total, tasks } = trackTotals(t);
    const status = (t.registry && t.registry.status) || t.metadata.status || "new";
    const openFb = t.feedback.filter((f) => f.status === "open").length;
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
      ["feedback", "Feedback", openFb ? `${openFb} open` : t.feedback.length || ""],
    ].map(([id, label, count]) => `<button class="tab" role="tab" data-tab="${id}" aria-selected="${tab === id}">${label}${count !== "" ? `<span class="count${id === "feedback" && openFb ? " hot" : ""}">${count}</span>` : ""}</button>`).join("");

    let body = "";
    const sections = tab === "spec" ? specSections(t.spec) : [];
    if (tab === "plan") body = preamble + renderPlan(t, ctx);
    else if (tab === "spec") body = renderSpec(t, ctx, sections);
    else if (tab === "diagrams") body = renderDiagrams(t);
    else body = renderFeedback(t, ctx);

    return `
      ${SNAPSHOT ? `<div class="snapshot-banner">Read-only snapshot — feedback is disabled. Run <code>serve.py</code> for the live view.</div>` : ""}
      ${t.archived ? `<div class="banner archived-banner"><div><strong>Archived track</strong> · read-only. It lives in <code>conductor/archive/${esc(t.id)}/</code>.</div></div>` : ""}
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

  function renderFeedback(t, ctx) {
    const all = t.feedback.slice().reverse();
    const items = ui.feedbackFilter === "open" ? all.filter((f) => f.status === "open") : all;
    const toolbar = `<div class="fb-toolbar">
      <button class="btn${ui.feedbackFilter === "open" ? " primary" : ""}" data-fbfilter="open">Open · ${all.filter((f) => f.status === "open").length}</button>
      <button class="btn${ui.feedbackFilter === "all" ? " primary" : ""}" data-fbfilter="all">All · ${all.length}</button>
      <span class="muted small" style="margin-left:auto">conductor/tracks/${esc(t.id)}/feedback.md</span></div>`;
    if (!items.length) return toolbar + `<div class="empty"><strong>${all.length ? "Nothing open" : "No feedback yet"}</strong>Hover any phase, task or spec section and hit <em>Comment</em>. Then tell your agent “check feedback”.</div>`;
    return toolbar + items.map((f) => `<article class="fb-item ${f.status}">
      <div class="fb-head"><span class="fb-id">${esc(f.id)}</span>
        <span class="chip ${f.status === "open" ? "warn" : "ok"}">${esc(f.status)}</span>
        <span class="chip">${esc(f.kind)}</span>
        <span class="fb-target">${esc(f.target)}</span>
        <span class="fb-when">${esc(f.when)}</span></div>
      <div class="md">${md(f.body, ctx)}</div>
      ${f.reply ? `<div class="fb-reply"><div class="fb-reply-label">Agent</div><div class="md">${md(f.reply.replace(/^\*\*Agent:\*\*\s*/, ""), ctx)}</div></div>` : ""}
    </article>`).join("");
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
  function compose(kind, target) {
    pending = { kind, target };
    const titles = { comment: "Comment", revise: "Request changes", approve: "Approve" };
    $("#composer-kind").textContent = titles[kind];
    $("#composer-target").textContent = target;
    $("#composer-file").textContent = LOCAL ? "your clipboard, to paste to your agent" : `${(projectById(project) || {}).name || ""}/conductor/tracks/${current}/feedback.md`;
    $("#composer-send").textContent = LOCAL ? "Copy" : "Send";
    $("#composer-text").value = "";
    $("#composer-text").placeholder = kind === "approve" ? "Optional note for the agent…" : "What should the agent change, clarify or consider?";
    $("#composer").showModal();
    $("#composer-text").focus();
  }

  async function send() {
    const text = $("#composer-text").value.trim();
    if (pending.kind !== "approve" && !text) { $("#composer-text").focus(); return; }
    if (LOCAL) return copyForChat(window.ConductorLocal.feedbackForChat(current, pending.kind, pending.target, text));
    try {
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

  function renderSettings() {
    const S = (settingsScope === "main" ? home && home.main_settings : state && state.settings) || {};
    const head = `<div class="eyebrow"><span class="chip type">Project</span><span class="chip mono">${esc((S.schema && S.schema.file) || "conductor/settings.json")}</span>
      ${S.exists ? "" : `<span class="chip warn">no settings.json yet — showing defaults</span>`}</div>
      <h1 class="track-title">Workflow settings</h1>
      <p class="track-sub">Project defaults every agent reads before planning, committing, pushing and testing. Changes save straight to <code>conductor/settings.json</code>.</p>`;
    if (S.error) return head + `<div class="error-card">${esc(S.error)}</div>`;
    if (!S.schema) return head + `<div class="empty"><strong>Settings schema not found</strong>Expected <code>conductor-setup/assets/settings.schema.json</code> next to this skill.<pre class="md">${esc(JSON.stringify(S.values, null, 2))}</pre></div>`;
    return head + S.schema.groups.map((g) => `<section class="set-group">
      <h2>${esc(g.label)}</h2><p class="muted">${esc(g.summary || "")}</p>
      ${g.settings.map((st) => {
        const e = S.effective[st.key] || { value: st.default, source: "default" };
        const sel = st.options.find((o) => o.value === e.value);
        return `<div class="setting">
          <div class="setting-head"><h3>${esc(st.label)}</h3>
            ${e.source === "invalid" ? `<span class="chip warn">invalid value in file — using default</span>` : e.source === "default" ? `<span class="chip">default</span>` : ""}
            ${e.value !== st.default ? `<span class="chip mono">default: ${esc(optionOf(st.key, st.default)?.label || st.default)}</span>` : ""}</div>
          <div class="opts" role="radiogroup" aria-label="${esc(st.label)}">
            ${st.options.map((o) => `<button class="opt" role="radio" aria-checked="${o.value === e.value}" data-setting="${esc(st.key)}" data-value="${esc(o.value)}"${SNAPSHOT || LOCAL ? " disabled" : ""}>
              <span class="opt-label"><span class="radio"></span>${esc(o.label)}</span>
              <span class="opt-summary">${inline(o.summary || "", {})}</span></button>`).join("")}
          </div>
          ${sel && sel.detail ? `<div class="opt-detail md">${md(sel.detail, {})}</div>` : ""}
          ${st.key.startsWith("testing.") ? `<p class="muted small">Plans that already exist keep their structure. Ask the agent to re-plan a track to apply a change there.</p>` : ""}
        </div>`;
      }).join("")}
    </section>`).join("");
  }

  async function saveSetting(key, value) {
    try {
      await postJSON("api/settings", { project, key, value });
      toast(`Saved: ${settingDef(key).label} → ${optionOf(key, value).label}. Agents use it from their next step.`);
      await load(); render(true);
    } catch (e) { toast("Could not save setting: " + e.message); }
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
    homeUi.status = GROUPS.some(([g]) => g === q.get("status")) ? q.get("status") : "all";
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
      if (homeUi.status !== "all") q.set("status", homeUi.status);
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

  async function homeAction(url, body, done) {
    try { const j = await postJSON(url, body); if (done) toast(done(j)); await loadHome(); render(true); }
    catch (e) { toast(e.message); }
  }

  document.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-view],[data-setting],[data-tab],[data-diagram],[data-comment],[data-decide],[data-goto-phase],[data-goto-task],[data-focus],[data-show-all],[data-fbfilter],[data-status],[data-forget],[data-restore],[data-dismiss]");
    if (!el) return;
    if (el.dataset.view) { view = el.dataset.view; settingsScope = project ? "project" : "main"; writeHash(); render(); window.scrollTo(0, 0); }
    else if (el.dataset.setting) { if (el.getAttribute("aria-checked") !== "true") saveSetting(el.dataset.setting, el.dataset.value); }
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
    else if (el.dataset.status) { homeUi.status = el.dataset.status; writeHash(); render(); }
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
