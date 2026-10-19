/* Conductor view: renders conductor/ live and writes feedback.md items. */
(function () {
  "use strict";

  const SNAPSHOT = window.CONDUCTOR_SNAPSHOT || null;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let state = null, version = null, current = null, tab = "plan", view = "track";
  let prevStatuses = new Map();
  const ui = { feedbackFilter: "open" };

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

  async function load() {
    if (SNAPSHOT) { state = SNAPSHOT; return; }
    const r = await fetch("api/state", { cache: "no-store" });
    if (!r.ok) throw new Error("state " + r.status);
    state = await r.json();
    version = state.version;
  }

  async function poll() {
    try {
      const r = await fetch("api/version", { cache: "no-store" });
      const v = (await r.json()).version;
      setLive("on");
      if (v !== version) {
        await load();
        render(true);
        setLive("flash");
      }
    } catch { setLive("off"); }
    setTimeout(poll, 1500);
  }

  function setLive(mode) {
    const el = $("#live"), txt = $("#live-text");
    el.classList.remove("off", "flash", "snap");
    if (mode === "off") { el.classList.add("off"); txt.textContent = "disconnected"; }
    else if (mode === "snap") { el.classList.add("snap"); txt.textContent = "snapshot"; }
    else if (mode === "flash") { el.classList.add("flash"); txt.textContent = "updated"; clearTimeout(setLive.t); setLive.t = setTimeout(() => setLive("on"), 1800); }
    else if (!el.classList.contains("flash")) txt.textContent = "live";
  }

  /* ---------------- helpers ---------------- */

  const STATUS_LABEL = { pending: "Pending", in_progress: "In progress", done: "Done", new: "New" };
  const statusIcon = (s) => `<span class="st st-${s}" role="img" aria-label="${STATUS_LABEL[s] || s}"></span>`;
  const commentIcon = '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>';
  const commentBtn = (target, label = "Comment") => SNAPSHOT ? "" : `<button class="comment-btn" data-comment="${esc(target)}">${commentIcon}${label}</button>`;

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
    $("#project").textContent = state.project ? `~/${state.project}` : "";
    const tracks = state.tracks;
    if (!current || !tracks.some((t) => t.id === current)) current = tracks[0] && tracks[0].id;
    renderSidebar();
    const main = $("#main");
    const scroll = window.scrollY;
    if (!state.initialized && !tracks.length) {
      main.innerHTML = `<div class="empty"><strong>No Conductor project here yet</strong>Run the <code>conductor-setup</code> skill in this project, then create a track.</div>`;
      return;
    }
    if (view === "settings") { main.innerHTML = renderSettings(); if (fromPoll) window.scrollTo(0, scroll); return; }
    if (!tracks.length) { main.innerHTML = `<div class="empty"><strong>No tracks yet</strong>Ask your agent to start a new track — it will appear here live.</div>`; return; }
    const t = tracks.find((x) => x.id === current);
    main.innerHTML = renderTrack(t);
    if (fromPoll) window.scrollTo(0, scroll);
    highlightChanges(t);
  }

  function renderSidebar() {
    const eff = (state.settings && state.settings.effective) || {};
    const label = (key) => optionOf(key, eff[key] && eff[key].value)?.label || "";
    $("#sidebar").innerHTML = `<h2>Project</h2>
      <button class="track-link settings-link" data-view="settings" aria-current="${view === "settings"}">
        <span class="gear">${gearIcon}</span>
        <span><div class="t-name">Workflow settings</div><div class="t-id">${esc([label("git.strategy"), label("testing.verification")].filter(Boolean).join(" · "))}</div></span></button>
      <h2>Tracks</h2>` + state.tracks.map((t) => {
      const { done, total } = trackTotals(t);
      const pct = total ? Math.round((done / total) * 100) : 0;
      const name = (t.registry && t.registry.description) || trackTitle(t);
      return `<button class="track-link" data-track="${esc(t.id)}" aria-current="${view === "track" && t.id === current}">
        <span class="ring" style="--p:${pct}" data-label="${pct}%"></span>
        <span><div class="t-name">${esc(name)}</div><div class="t-id">${esc(t.id)}</div></span></button>`;
    }).join("");
  }

  function renderTrack(t) {
    const ctx = { track: t };
    const { done, total, tasks } = trackTotals(t);
    const status = (t.registry && t.registry.status) || t.metadata.status || "new";
    const openFb = t.feedback.filter((f) => f.status === "open").length;
    const dSpec = decision(t, "spec"), dPlan = decision(t, "plan");
    const badge = (d, what) => !d ? "" : d.kind === "approve"
      ? `<span class="chip ok">✓ ${what} approved</span>${waiting(d)}`
      : `<span class="chip warn">↺ ${what}: changes requested</span>${waiting(d)}`;
    const preamble = t.plan.preamble.length ? `<div class="preamble md">${md(t.plan.preamble.join("\n"), ctx)}</div>` : "";
    const created = (t.metadata.created_at || "").slice(0, 10);

    const rail = t.plan.phases.map((p, i) => `
      <button class="station ${p.status}" data-goto-phase="${i}" title="${esc(p.title)}">
        <span class="dot">${p.status === "done" ? "✓" : i + 1}</span>
        <span class="s-title">${esc(p.title.replace(/^Phase\s*\d+\s*:\s*/i, "").replace(/\(diagram:[^)]*\)/g, "").trim())}</span>
        <span class="s-count">${p.done}/${p.total}</span>
      </button>`).join("");

    const tabs = [
      ["plan", "Plan", `${done}/${total}`],
      ["spec", "Spec", ""],
      ["diagrams", "Diagrams", t.diagrams.length],
      ["feedback", "Feedback", openFb ? `${openFb} open` : t.feedback.length || ""],
    ].map(([id, label, count]) => `<button class="tab" role="tab" data-tab="${id}" aria-selected="${tab === id}">${label}${count !== "" ? `<span class="count${id === "feedback" && openFb ? " hot" : ""}">${count}</span>` : ""}</button>`).join("");

    let body = "";
    if (tab === "plan") body = preamble + renderPlan(t, ctx);
    else if (tab === "spec") body = renderSpec(t, ctx);
    else if (tab === "diagrams") body = renderDiagrams(t);
    else body = renderFeedback(t, ctx);

    return `
      ${SNAPSHOT ? `<div class="snapshot-banner">Read-only snapshot — feedback is disabled. Run <code>serve.py</code> for the live view.</div>` : ""}
      <div class="eyebrow">
        <span class="chip type">${esc(t.metadata.type || "track")}</span>
        <span class="chip st-${esc(status)}">${esc(STATUS_LABEL[status] || status)}</span>
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
        ${SNAPSHOT ? "" : `<div class="review-actions">
          <button class="btn" data-decide="revise">↺ Request changes</button>
          <button class="btn good" data-decide="approve:spec">✓ Approve spec</button>
          <button class="btn primary" data-decide="approve:plan">✓ Approve plan</button>
        </div>`}
      </div>
      <div class="progress">
        <div class="progress-meta"><span>${done} of ${total} tasks done</span><span>${total ? Math.round((done / total) * 100) : 0}%</span></div>
        <div class="progress-groups">${progressGroups(t)}</div>
      </div>
      ${workflowChips()}
      <div class="rail" role="list">${rail}</div>
      <div class="tabs" role="tablist">${tabs}</div>
      <section>${body}</section>`;
  }

  // One group per phase, sized by its task count: a numbered phase bar on top,
  // a segment per task below. Everything jumps to that place in the plan.
  function progressGroups(t) {
    const clean = (s) => s.replace(/^Phase\s*\d+\s*:\s*/i, "").replace(/\(diagram:[^)]*\)/g, "").trim();
    return t.plan.phases.map((p, i) => `
      <div class="pg ${p.status}" style="flex-grow:${Math.max(p.tasks.length, 1)}">
        <button class="pg-phase" data-goto-phase="${i}" title="Phase ${i + 1}: ${esc(clean(p.title))} — ${p.done}/${p.total}">
          <span class="pg-num">${p.status === "done" ? "✓" : i + 1}</span><span class="pg-name">${esc(clean(p.title))}</span></button>
        <div class="pg-tasks">${p.tasks.map((task, j) => `<button class="pg-task ${task.status}" data-goto-task="${i}/${j}" title="${esc(STATUS_LABEL[task.status] || task.status)}: ${esc(clean(task.text).replace(/`/g, ""))}"></button>`).join("")}</div>
      </div>`).join("");
  }

  function renderPlan(t, ctx) {
    if (!t.plan.phases.length) return `<div class="empty"><strong>No plan yet</strong>The agent hasn't written <code>plan.md</code> for this track.</div>`;
    return t.plan.phases.map((p, i) => {
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
            ${task.sha ? `<span class="sha">${esc(task.sha.slice(0, 7))}</span>` : ""}
            ${commentBtn(tt)}</div>
          ${task.subtasks.length ? `<ul class="subtasks">${task.subtasks.map((s) => `<li class="subtask">${statusIcon(s.status)}<span>${inline(s.text, ctx)}</span>${s.sha ? `<span class="sha">${esc(s.sha.slice(0, 7))}</span>` : ""}</li>`).join("")}</ul>` : ""}
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

  function renderSpec(t, ctx) {
    if (!t.spec.trim()) return `<div class="empty"><strong>No spec yet</strong></div>`;
    const sections = specSections(t.spec);
    const toc = sections.filter((s) => s.title).map((s, i) => `<button data-goto-section="${i}">${esc(s.title)}</button>`).join("");
    return `<div class="spec-toc">${toc}</div>` + sections.map((s, i) => {
      const target = `spec › ${s.title || "Intro"}`;
      const n = openFeedbackFor(t, target);
      return `<section class="spec-section${/question/i.test(s.title || "") ? " questions" : ""}" id="spec-${i}">
        ${commentBtn(target)}
        <div class="md">${s.title ? `<h2>${inline(s.title, ctx)} ${n ? `<span class="has-fb">${commentIcon}${n}</span>` : ""}</h2>` : ""}${md(s.lines.join("\n"), ctx)}</div>
      </section>`;
    }).join("");
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
    $("#composer-file").textContent = `conductor/tracks/${current}/feedback.md`;
    $("#composer-text").value = "";
    $("#composer-text").placeholder = kind === "approve" ? "Optional note for the agent…" : "What should the agent change, clarify or consider?";
    $("#composer").showModal();
    $("#composer-text").focus();
  }

  async function send() {
    const text = $("#composer-text").value.trim();
    if (pending.kind !== "approve" && !text) { $("#composer-text").focus(); return; }
    try {
      const r = await fetch("api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ track: current, kind: pending.kind, target: pending.target, text }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.status);
      $("#composer").close();
      toast(`Saved ${j.id} to feedback.md — tell your agent “check feedback”.`);
      await load(); render(true);
    } catch (e) { toast("Could not save feedback: " + e.message); }
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg; el.classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 3800);
  }

  /* ---------------- workflow settings ---------------- */

  const gearIcon = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5l1.8 1.8M16.7 16.7l1.8 1.8M5.5 18.5l1.8-1.8M16.7 7.3l1.8-1.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';

  function settingDef(key) {
    const schema = state.settings && state.settings.schema;
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
    const S = state.settings || {};
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
            ${st.options.map((o) => `<button class="opt" role="radio" aria-checked="${o.value === e.value}" data-setting="${esc(st.key)}" data-value="${esc(o.value)}"${SNAPSHOT ? " disabled" : ""}>
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
      const r = await fetch("api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key, value }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.status);
      toast(`Saved: ${settingDef(key).label} → ${optionOf(key, value).label}. Agents use it from their next step.`);
      await load(); render(true);
    } catch (e) { toast("Could not save setting: " + e.message); }
  }

  /* ---------------- routing & events ---------------- */

  function readHash() {
    if (/^#\/settings\b/.test(location.hash)) { view = "settings"; return null; }
    const m = location.hash.match(/^#\/([^/]+)(?:\/(\w+))?(?:\/([\w.-]+))?(?:\/([\w.-]+))?/);
    if (m) { current = decodeURIComponent(m[1]); tab = m[2] || tab; return m[3] ? { slug: m[3], node: m[4] } : null; }
    return null;
  }
  function writeHash() { history.replaceState(null, "", view === "settings" ? "#/settings" : `#/${encodeURIComponent(current)}/${tab}`); }

  function openDiagram(slug, node) {
    const t = state.tracks.find((x) => x.id === current);
    const d = t && t.diagrams.find((x) => x.slug === slug);
    if (!d || d.type === "error") return;
    history.replaceState(null, "", `#/${encodeURIComponent(current)}/${tab}/${slug}`);
    window.WorldMap.open(d, { md: (s) => md(s, { track: t }), onClose: writeHash, focus: node });
  }

  document.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-view],[data-setting],[data-track],[data-tab],[data-diagram],[data-comment],[data-decide],[data-goto-phase],[data-goto-task],[data-goto-section],[data-fbfilter]");
    if (!el) return;
    if (el.dataset.view) { view = el.dataset.view; writeHash(); render(); window.scrollTo(0, 0); }
    else if (el.dataset.setting) { if (el.getAttribute("aria-checked") !== "true") saveSetting(el.dataset.setting, el.dataset.value); }
    else if (el.dataset.track) { view = "track"; current = el.dataset.track; prevStatuses = new Map(); writeHash(); render(); window.scrollTo(0, 0); }
    else if (el.dataset.tab) { tab = el.dataset.tab; writeHash(); render(); }
    else if (el.dataset.diagram) openDiagram(el.dataset.diagram);
    else if (el.dataset.comment) compose("comment", el.dataset.comment);
    else if (el.dataset.decide) { const [kind, what] = el.dataset.decide.split(":"); compose(kind, what || (tab === "spec" ? "spec" : "plan")); }
    else if (el.dataset.gotoPhase) { if (tab !== "plan") { tab = "plan"; writeHash(); render(); } document.getElementById("phase-" + el.dataset.gotoPhase)?.scrollIntoView({ behavior: "smooth", block: "start" }); }
    else if (el.dataset.gotoTask) {
      if (tab !== "plan") { tab = "plan"; writeHash(); render(); }
      const li = document.querySelector(`.task[data-key="${CSS.escape(el.dataset.gotoTask)}"]`);
      if (li) { li.scrollIntoView({ behavior: "smooth", block: "center" }); li.classList.remove("pulse"); void li.offsetWidth; li.classList.add("pulse"); }
    }
    else if (el.dataset.gotoSection) document.getElementById("spec-" + el.dataset.gotoSection)?.scrollIntoView({ behavior: "smooth", block: "start" });
    else if (el.dataset.fbfilter) { ui.feedbackFilter = el.dataset.fbfilter; render(); }
  });
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
    const deepDiagram = readHash();
    try { await load(); } catch (e) { setLive("off"); $("#main").innerHTML = `<div class="empty"><strong>Can't reach the viewer server</strong>${esc(e.message)}</div>`; return; }
    render();
    if (deepDiagram) openDiagram(deepDiagram.slug, deepDiagram.node);
    if (SNAPSHOT) setLive("snap"); else setTimeout(poll, 1500);
  })();
})();
