/* World-map diagrams: a pannable, zoomable canvas for ideas too big for a list.
 * Diagram JSON: { title, summary, regions[{id,label,tone}], nodes[{id,label,kind,detail,region,x,y}],
 *                 edges[{from,to,label,style}], tour[nodeId] }
 */
(function () {
  "use strict";

  const COL_W = 270, ROW_H = 110, REGION_GAP = 110, NODE_W = 190, NODE_H = 56;
  const PAD = 34, LABEL_PAD = 30;
  const TONES = ["teal", "amber", "violet", "rose", "blue", "green"];
  const KIND_TONE = { agent: "violet", person: "rose", file: "amber", doc: "amber", process: "teal",
    ui: "blue", store: "green", external: "blue", note: "amber" };
  const ICONS = {
    agent: '<path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z M18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9z" fill="currentColor"/>',
    person: '<circle cx="12" cy="8" r="3.6" fill="currentColor"/><path d="M4.5 20c.8-4 3.8-6 7.5-6s6.7 2 7.5 6z" fill="currentColor"/>',
    file: '<path d="M7 3h7l4 4v14H7z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M14 3v4h4M9.5 12h6M9.5 15.5h6" stroke="currentColor" stroke-width="1.6" fill="none"/>',
    doc: '<path d="M5 4h14v16H5z M8.5 8.5h7M8.5 12h7M8.5 15.5h4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
    process: '<circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    ui: '<rect x="3.5" y="5" width="17" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M3.5 9h17" stroke="currentColor" stroke-width="1.8"/><circle cx="6.5" cy="7" r=".9" fill="currentColor"/>',
    store: '<ellipse cx="12" cy="6" rx="7" ry="2.6" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M5 6v12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6M5 12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6" fill="none" stroke="currentColor" stroke-width="1.8"/>',
    external: '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M3.5 12h17M12 3.5c2.6 2.6 2.6 14.4 0 17M12 3.5c-2.6 2.6-2.6 14.4 0 17" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    note: '<path d="M5 4h14v11l-5 5H5z M14 20v-5h5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const toneVar = (t) => `var(--t-${TONES.includes(t) ? t : "blue"})`;

  /* ---------- layout ---------- */

  // Longest-path layering inside a node set; DFS back-edges are ignored so cycles still lay out.
  function rank(ids, edges) {
    const out = new Map(ids.map((id) => [id, []]));
    const indeg = new Map(ids.map((id) => [id, 0]));
    for (const e of edges) if (out.has(e.from) && out.has(e.to) && e.from !== e.to) { out.get(e.from).push(e.to); }
    const state = new Map(), dag = new Map(ids.map((id) => [id, []]));
    const visit = (u) => {
      state.set(u, 1);
      for (const v of out.get(u)) {
        if (state.get(v) === 1) continue; // back edge
        dag.get(u).push(v); indeg.set(v, indeg.get(v) + 1);
        if (!state.get(v)) visit(v);
      }
      state.set(u, 2);
    };
    for (const id of ids) if (!state.get(id)) visit(id);
    const r = new Map(ids.map((id) => [id, 0]));
    const queue = ids.filter((id) => indeg.get(id) === 0);
    while (queue.length) {
      const u = queue.shift();
      for (const v of dag.get(u)) {
        r.set(v, Math.max(r.get(v), r.get(u) + 1));
        indeg.set(v, indeg.get(v) - 1);
        if (indeg.get(v) === 0) queue.push(v);
      }
    }
    return r;
  }

  function layout(d) {
    const nodes = (d.nodes || []).map((n, i) => ({ ...n, id: String(n.id ?? i), w: NODE_W, h: NODE_H }));
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const edges = (d.edges || []).filter((e) => byId.has(String(e.from)) && byId.has(String(e.to)))
      .map((e) => ({ ...e, from: String(e.from), to: String(e.to) }));
    const regionDefs = (d.regions || []).map((r, i) => ({ ...r, id: String(r.id ?? i), tone: r.tone || TONES[i % TONES.length] }));
    const manual = nodes.length && nodes.every((n) => Number.isFinite(n.x) && Number.isFinite(n.y));

    if (!manual) {
      const groups = regionDefs.map((r) => ({ id: r.id, members: nodes.filter((n) => n.region === r.id) }));
      const loose = nodes.filter((n) => !regionDefs.some((r) => r.id === n.region));
      if (loose.length) groups.push({ id: null, members: loose });
      const neighbours = (n) => edges.flatMap((e) => (e.from === n.id ? [e.to] : e.to === n.id ? [e.from] : []));
      let cursorX = 0;
      const placed = new Set();
      const blocks = [];
      for (const g of groups) {
        if (!g.members.length) continue;
        const ids = g.members.map((n) => n.id);
        const r = rank(ids, edges);
        const cols = [];
        for (const n of g.members) (cols[r.get(n.id)] ||= []).push(n);
        const filled = cols.filter(Boolean);
        // Barycentre ordering against already-placed neighbours reduces crossings.
        filled.forEach((col, ci) => {
          col.forEach((n, i) => {
            const ys = neighbours(n).filter((id) => placed.has(id)).map((id) => byId.get(id).y);
            n._key = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : i * ROW_H;
          });
          col.sort((a, b) => a._key - b._key);
          col.forEach((n, i) => { n.x = cursorX + ci * COL_W; n.y = i * ROW_H; placed.add(n.id); });
        });
        const height = Math.max(...filled.map((c) => c.length)) * ROW_H;
        filled.forEach((col) => { const off = (height - col.length * ROW_H) / 2; col.forEach((n) => (n.y += off)); });
        blocks.push({ members: g.members, height });
        cursorX += filled.length * COL_W + REGION_GAP;
      }
      const maxH = Math.max(0, ...blocks.map((b) => b.height));
      blocks.forEach((b) => b.members.forEach((n) => (n.y += (maxH - b.height) / 2)));
    }
    return { nodes, byId, edges, regionDefs, manual };
  }

  function regionBoxes(L) {
    return L.regionDefs.map((r) => {
      const m = L.nodes.filter((n) => n.region === r.id);
      if (!m.length) return null;
      const x0 = Math.min(...m.map((n) => n.x)) - PAD, y0 = Math.min(...m.map((n) => n.y)) - PAD - LABEL_PAD;
      const x1 = Math.max(...m.map((n) => n.x + n.w)) + PAD, y1 = Math.max(...m.map((n) => n.y + n.h)) + PAD;
      return { ...r, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    }).filter(Boolean);
  }

  function bounds(L, boxes, extra) {
    const xs = [], ys = [];
    for (const n of L.nodes) { xs.push(n.x, n.x + n.w); ys.push(n.y, n.y + n.h); }
    for (const b of boxes) { xs.push(b.x, b.x + b.w); ys.push(b.y, b.y + b.h); }
    if (extra) { xs.push(extra.x, extra.x + extra.w); ys.push(extra.y, extra.y + extra.h); }
    if (!xs.length) return { x: 0, y: 0, w: 400, h: 300 };
    const x = Math.min(...xs), y = Math.min(...ys);
    return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
  }

  function edgePath(a, b, L) {
    const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 }, bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
    const dx = bc.x - ac.x, dy = bc.y - ac.y;
    let p0, p1, c0, c1;
    if (!L.manual && dx < -COL_W / 2 && Math.abs(dy) < ROW_H * 3) {
      // Back edge: loop underneath everything between the two nodes.
      const bottom = Math.max(...L.nodes.filter((n) => n.x + n.w >= Math.min(a.x, b.x) && n.x <= Math.max(a.x + a.w, b.x + b.w)).map((n) => n.y + n.h));
      const dip = bottom + 70 + Math.min(120, Math.abs(dx) * 0.06);
      p0 = { x: ac.x, y: a.y + a.h }; p1 = { x: bc.x, y: b.y + b.h };
      c0 = { x: ac.x, y: dip }; c1 = { x: bc.x, y: dip };
    } else if (Math.abs(dx) >= Math.abs(dy) * 0.8) {
      const s = Math.sign(dx) || 1;
      p0 = { x: s > 0 ? a.x + a.w : a.x, y: ac.y }; p1 = { x: s > 0 ? b.x : b.x + b.w, y: bc.y };
      const k = Math.max(40, Math.abs(p1.x - p0.x) * 0.45);
      c0 = { x: p0.x + s * k, y: p0.y }; c1 = { x: p1.x - s * k, y: p1.y };
    } else {
      const s = Math.sign(dy) || 1;
      p0 = { x: ac.x, y: s > 0 ? a.y + a.h : a.y }; p1 = { x: bc.x, y: s > 0 ? b.y : b.y + b.h };
      const k = Math.max(30, Math.abs(p1.y - p0.y) * 0.45);
      c0 = { x: p0.x, y: p0.y + s * k }; c1 = { x: p1.x, y: p1.y - s * k };
    }
    const t = 0.5, mt = 1 - t;
    const mid = {
      x: mt ** 3 * p0.x + 3 * mt * mt * t * c0.x + 3 * mt * t * t * c1.x + t ** 3 * p1.x,
      y: mt ** 3 * p0.y + 3 * mt * mt * t * c0.y + 3 * mt * t * t * c1.y + t ** 3 * p1.y,
    };
    return { d: `M${p0.x},${p0.y} C${c0.x},${c0.y} ${c1.x},${c1.y} ${p1.x},${p1.y}`, mid };
  }

  /* ---------- thumbnail (static SVG, estimated sizes) ---------- */

  function thumbnail(d) {
    const L = layout(d), boxes = regionBoxes(L), B = bounds(L, boxes);
    const pad = 20;
    let s = `<svg viewBox="${B.x - pad} ${B.y - pad} ${B.w + 2 * pad} ${B.h + 2 * pad}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">`;
    for (const b of boxes) s += `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="22" fill="${toneVar(b.tone)}" fill-opacity=".08" stroke="${toneVar(b.tone)}" stroke-opacity=".5" stroke-width="3" stroke-dasharray="10 8"/>`;
    for (const e of L.edges) { const p = edgePath(L.byId.get(e.from), L.byId.get(e.to), L); s += `<path d="${p.d}" fill="none" stroke="var(--edge)" stroke-width="4"${e.style === "dashed" ? ' stroke-dasharray="12 10"' : ""}/>`; }
    for (const n of L.nodes) { const t = toneVar(KIND_TONE[n.kind] || "blue"); s += `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" fill="var(--panel)" stroke="var(--line-2)" stroke-width="3"/><rect x="${n.x + 14}" y="${n.y + 15}" width="26" height="26" rx="7" fill="${t}" fill-opacity=".8"/><rect x="${n.x + 52}" y="${n.y + 22}" width="${Math.min(120, 12 + String(n.label).length * 6)}" height="11" rx="5" fill="var(--text-2)" fill-opacity=".55"/>`; }
    return s + "</svg>";
  }

  /* ---------- interactive modal ---------- */

  let active = null;

  function open(diagram, opts = {}) {
    close();
    const md = opts.md || ((t) => `<p>${esc(t)}</p>`);
    const isSvg = diagram.type === "svg";
    const d = isSvg ? { title: diagram.title, nodes: [], edges: [] } : diagram.data;
    const L = layout(d);
    const tour = (d.tour || []).map(String).filter((id) => L.byId.has(id));

    const root = document.createElement("div");
    root.className = "wm";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", d.title || diagram.slug);
    root.innerHTML = `
      <div class="wm-top">
        <div class="wm-titles"><div class="wm-title">${esc(d.title || diagram.slug)}</div>
          <div class="wm-summary">${esc(d.summary || "")}</div></div>
        <div class="wm-controls">
          ${tour.length ? `<div class="wm-tour"><button data-act="prev" title="Previous stop (P)" aria-label="Previous stop">‹</button><button data-act="tour" class="wm-step" title="Start tour (T)">Tour · ${tour.length} stops</button><button data-act="next" title="Next stop (N)" aria-label="Next stop">›</button></div>` : ""}
          <button class="icon-btn" data-act="out" title="Zoom out (−)" aria-label="Zoom out">−</button>
          <span class="wm-zoom" aria-live="polite">100%</span>
          <button class="icon-btn" data-act="in" title="Zoom in (+)" aria-label="Zoom in">+</button>
          <button class="btn" data-act="fit" title="Fit everything (F)">Fit</button>
          <button class="icon-btn" data-act="close" title="Close (Esc)" aria-label="Close">✕</button>
        </div>
      </div>
      <div class="wm-viewport" tabindex="0">
        <div class="wm-world"><svg class="wm-svg"><defs>
          <marker id="wm-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="wm-arrow"/></marker>
          <marker id="wm-arr-hot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="wm-arrow-hot"/></marker>
        </defs><g class="wm-regions"></g><g class="wm-edges"></g></svg></div>
        <aside class="wm-panel" aria-live="polite"></aside>
        <div class="wm-mini" title="Minimap — click or drag to travel"><svg></svg></div>
        <div class="wm-hint"><kbd>drag</kbd> pan · <kbd>scroll</kbd> zoom · <kbd>←↑↓→</kbd> move · <kbd>F</kbd> fit${tour.length ? " · <kbd>N</kbd>/<kbd>P</kbd> tour" : ""} · <kbd>Esc</kbd> close</div>
      </div>`;
    document.body.appendChild(root);
    document.body.style.overflow = "hidden";

    const vp = root.querySelector(".wm-viewport"), world = root.querySelector(".wm-world");
    const gRegions = root.querySelector(".wm-regions"), gEdges = root.querySelector(".wm-edges");
    const panel = root.querySelector(".wm-panel"), mini = root.querySelector(".wm-mini svg");
    const zoomLabel = root.querySelector(".wm-zoom"), stepBtn = root.querySelector(".wm-step");

    // Nodes as HTML (real text wrapping), measured, then edges/regions drawn in SVG.
    const els = new Map();
    let svgBox = null;
    if (isSvg) {
      const img = new Image();
      img.className = "wm-img";
      img.alt = d.title || "diagram";
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(diagram.svg);
      world.appendChild(img);
      svgBox = { x: 0, y: 0, w: 1200, h: 800 };
      img.onload = () => { svgBox.w = img.naturalWidth || 1200; svgBox.h = img.naturalHeight || 800; img.width = svgBox.w; img.height = svgBox.h; fit(false); drawMini(); };
    }
    const tourIndex = new Map();
    tour.forEach((id, i) => { if (!tourIndex.has(id)) tourIndex.set(id, i + 1); });
    for (const n of L.nodes) {
      const el = document.createElement("button");
      el.className = "wm-node";
      el.style.left = n.x + "px"; el.style.top = n.y + "px";
      el.style.setProperty("--tone", toneVar(KIND_TONE[n.kind] || "blue"));
      el.innerHTML = `<span class="k-icon"><svg viewBox="0 0 24 24" width="16" height="16">${ICONS[n.kind] || ICONS.note}</svg></span>
        <span><div class="n-label">${esc(n.label ?? n.id)}</div>${n.kind ? `<div class="n-kind">${esc(n.kind)}</div>` : ""}</span>
        ${tourIndex.has(n.id) ? `<span class="n-step">${tourIndex.get(n.id)}</span>` : ""}`;
      el.dataset.id = n.id;
      world.appendChild(el);
      els.set(n.id, el);
    }
    for (const n of L.nodes) { const el = els.get(n.id); n.w = el.offsetWidth; n.h = el.offsetHeight; }

    const boxes = regionBoxes(L);
    gRegions.innerHTML = boxes.map((b) => `<g class="wm-region"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="22" fill="${toneVar(b.tone)}" fill-opacity=".06" stroke="${toneVar(b.tone)}" stroke-opacity=".55"/>
      <text x="${b.x + 18}" y="${b.y + 24}" fill="${toneVar(b.tone)}">${esc(b.label || b.id)}</text></g>`).join("");
    gEdges.innerHTML = L.edges.map((e, i) => {
      const p = edgePath(L.byId.get(e.from), L.byId.get(e.to), L);
      return `<g class="wm-edge${e.style === "dashed" ? " dashed" : ""}" data-i="${i}"><path d="${p.d}" marker-end="url(#wm-arr)"/>${e.label ? `<text x="${p.mid.x}" y="${p.mid.y + 4}" text-anchor="middle">${esc(e.label)}</text>` : ""}</g>`;
    }).join("");
    const edgeEls = [...gEdges.children];
    const B = () => bounds(L, boxes, svgBox);

    /* camera */
    const cam = { x: 0, y: 0, k: 1 };
    let anim = null;
    const apply = () => {
      world.style.transform = `translate(${cam.x}px, ${cam.y}px) scale(${cam.k})`;
      vp.style.backgroundSize = `${26 * cam.k}px ${26 * cam.k}px`;
      vp.style.backgroundPosition = `${cam.x}px ${cam.y}px`;
      zoomLabel.textContent = Math.round(cam.k * 100) + "%";
      drawViewport();
    };
    const clampK = (k) => Math.min(2.5, Math.max(0.12, k));
    const zoomAt = (k, sx, sy) => { k = clampK(k); cam.x = sx - (sx - cam.x) * (k / cam.k); cam.y = sy - (sy - cam.y) * (k / cam.k); cam.k = k; apply(); };
    const target = (wx, wy, k) => ({ k, x: vp.clientWidth / 2 - wx * k - (panel.classList.contains("open") ? 180 : 0), y: vp.clientHeight / 2 - wy * k });
    function flyTo(to, ms = 650) {
      cancelAnimationFrame(anim);
      const from = { ...cam };
      const dist = Math.hypot(to.x - from.x, to.y - from.y) / Math.max(vp.clientWidth, 1);
      const dip = Math.min(0.45, dist * 0.25); // zoom out mid-flight, like travelling on a map
      const t0 = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - t0) / ms), e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
        const kLin = from.k + (to.k - from.k) * e;
        cam.k = kLin * (1 - dip * Math.sin(Math.PI * t));
        // keep the interpolated world-centre on screen-centre so the dip zooms around it
        const cx = (vp.clientWidth / 2 - (from.x + (to.x - from.x) * e)) / kLin;
        const cy = (vp.clientHeight / 2 - (from.y + (to.y - from.y) * e)) / kLin;
        cam.x = vp.clientWidth / 2 - cx * cam.k; cam.y = vp.clientHeight / 2 - cy * cam.k;
        apply();
        if (t < 1) anim = requestAnimationFrame(step);
      };
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) { Object.assign(cam, to); apply(); } else anim = requestAnimationFrame(step);
    }
    function fit(animate = true) {
      const b = B(), m = 60;
      const k = clampK(Math.min((vp.clientWidth - 2 * m) / b.w, (vp.clientHeight - 2 * m) / b.h, 1.15));
      const to = { k, x: (vp.clientWidth - b.w * k) / 2 - b.x * k, y: (vp.clientHeight - b.h * k) / 2 - b.y * k };
      if (animate) flyTo(to, 500); else { Object.assign(cam, to); apply(); }
    }

    /* minimap */
    let miniView = null;
    function drawMini() {
      const b = B(), pad = Math.max(b.w, b.h) * 0.06;
      miniView = { x: b.x - pad, y: b.y - pad, w: b.w + 2 * pad, h: b.h + 2 * pad };
      mini.setAttribute("viewBox", `${miniView.x} ${miniView.y} ${miniView.w} ${miniView.h}`);
      mini.innerHTML = boxes.map((r) => `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="20" fill="${toneVar(r.tone)}" fill-opacity=".14"/>`).join("")
        + (svgBox ? `<rect x="0" y="0" width="${svgBox.w}" height="${svgBox.h}" fill="var(--line-2)"/>` : "")
        + L.nodes.map((n) => `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="${toneVar(KIND_TONE[n.kind] || "blue")}" fill-opacity=".75"/>`).join("")
        + `<rect class="vp" rx="8"/>`;
      drawViewport();
    }
    function drawViewport() {
      const r = mini.querySelector(".vp");
      if (!r) return;
      r.setAttribute("x", -cam.x / cam.k); r.setAttribute("y", -cam.y / cam.k);
      r.setAttribute("width", vp.clientWidth / cam.k); r.setAttribute("height", vp.clientHeight / cam.k);
    }
    function miniTravel(ev, animate) {
      const rect = mini.getBoundingClientRect();
      const s = Math.max(miniView.w / rect.width, miniView.h / rect.height); // preserveAspectRatio meet
      const ox = (rect.width - miniView.w / s) / 2, oy = (rect.height - miniView.h / s) / 2;
      const wx = miniView.x + (ev.clientX - rect.left - ox) * s, wy = miniView.y + (ev.clientY - rect.top - oy) * s;
      const to = target(wx, wy, cam.k);
      if (animate) flyTo(to, 400); else { cancelAnimationFrame(anim); Object.assign(cam, to); apply(); }
    }
    let miniDrag = false;
    root.querySelector(".wm-mini").addEventListener("pointerdown", (ev) => { miniDrag = true; ev.currentTarget.setPointerCapture(ev.pointerId); miniTravel(ev, true); });
    root.querySelector(".wm-mini").addEventListener("pointermove", (ev) => { if (miniDrag) miniTravel(ev, false); });
    root.querySelector(".wm-mini").addEventListener("pointerup", () => { miniDrag = false; });

    /* selection & panel */
    let selected = null, tourAt = -1;
    function select(id, fly = true) {
      selected = id;
      root.classList.toggle("has-sel", !!id);
      const near = new Set();
      edgeEls.forEach((g, i) => {
        const e = L.edges[i], hot = id && (e.from === id || e.to === id);
        g.classList.toggle("hot", !!hot);
        g.querySelector("path").setAttribute("marker-end", hot ? "url(#wm-arr-hot)" : "url(#wm-arr)");
        if (hot) { near.add(e.from); near.add(e.to); }
      });
      els.forEach((el, nid) => { el.classList.toggle("sel", nid === id); el.classList.toggle("near", near.has(nid)); });
      if (!id) { panel.classList.remove("open"); return; }
      const n = L.byId.get(id);
      const outs = L.edges.filter((e) => e.from === id), ins = L.edges.filter((e) => e.to === id);
      const conn = (e, dir) => { const o = L.byId.get(dir === "→" ? e.to : e.from); return `<button class="wm-conn" data-go="${esc(o.id)}"><span class="dir">${dir}</span><span>${esc(o.label ?? o.id)}</span>${e.label ? `<span class="lbl">${esc(e.label)}</span>` : ""}</button>`; };
      const tone = toneVar(KIND_TONE[n.kind] || "blue");
      panel.innerHTML = `<button class="icon-btn close" data-act="unsel" aria-label="Close details">✕</button>
        <div class="p-kind" style="color:${tone}">${esc(n.kind || "node")}${tourAt >= 0 ? ` · stop ${tourAt + 1} of ${tour.length}` : ""}</div>
        <h2>${esc(n.label ?? n.id)}</h2>
        <div class="md">${n.detail ? md(String(n.detail)) : '<p class="muted">No detail.</p>'}</div>
        ${outs.length ? `<h4>Leads to</h4>${outs.map((e) => conn(e, "→")).join("")}` : ""}
        ${ins.length ? `<h4>Comes from</h4>${ins.map((e) => conn(e, "←")).join("")}` : ""}`;
      panel.classList.add("open");
      if (fly) flyTo(target(n.x + n.w / 2, n.y + n.h / 2, Math.max(cam.k, 1)));
    }
    function tourGo(i) {
      if (!tour.length) return;
      tourAt = (i + tour.length) % tour.length;
      stepBtn.textContent = `${tourAt + 1} / ${tour.length}`;
      select(tour[tourAt]);
    }

    /* input */
    let drag = null;
    vp.addEventListener("pointerdown", (ev) => {
      if (ev.target.closest(".wm-panel, .wm-mini")) return;
      cancelAnimationFrame(anim);
      drag = { x: ev.clientX, y: ev.clientY, cx: cam.x, cy: cam.y, moved: false, node: ev.target.closest(".wm-node") };
      vp.setPointerCapture(ev.pointerId);
    });
    vp.addEventListener("pointermove", (ev) => {
      if (!drag) return;
      const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) > 4) { drag.moved = true; vp.classList.add("dragging"); }
      if (drag.moved) { cam.x = drag.cx + dx; cam.y = drag.cy + dy; apply(); }
    });
    vp.addEventListener("pointerup", () => {
      if (drag && !drag.moved) { tourAt = -1; if (stepBtn) stepBtn.textContent = `Tour · ${tour.length} stops`; select(drag.node ? drag.node.dataset.id : null, !!drag.node); }
      drag = null; vp.classList.remove("dragging");
    });
    vp.addEventListener("wheel", (ev) => {
      if (ev.target.closest(".wm-panel")) return;
      ev.preventDefault();
      cancelAnimationFrame(anim);
      const r = vp.getBoundingClientRect();
      const trackpadPan = !ev.ctrlKey && ev.deltaMode === 0 && (Math.abs(ev.deltaX) > 0.5 || Math.abs(ev.deltaY) < 40);
      if (trackpadPan) { cam.x -= ev.deltaX; cam.y -= ev.deltaY; apply(); }
      else zoomAt(cam.k * Math.exp(-ev.deltaY * (ev.ctrlKey ? 0.01 : 0.0018) * (ev.deltaMode === 1 ? 30 : 1)), ev.clientX - r.left, ev.clientY - r.top);
    }, { passive: false });
    root.addEventListener("click", (ev) => {
      const go = ev.target.closest("[data-go]");
      if (go) { tourAt = -1; return select(go.dataset.go); }
      const act = ev.target.closest("[data-act]")?.dataset.act;
      const c = () => [vp.clientWidth / 2, vp.clientHeight / 2];
      if (act === "close") close();
      else if (act === "fit") fit();
      else if (act === "in") zoomAt(cam.k * 1.25, ...c());
      else if (act === "out") zoomAt(cam.k / 1.25, ...c());
      else if (act === "unsel") select(null);
      else if (act === "tour") tourGo(tourAt < 0 ? 0 : tourAt);
      else if (act === "next") tourGo(tourAt + 1);
      else if (act === "prev") tourGo(tourAt - 1);
    });
    const onKey = (ev) => {
      if (ev.target.closest && ev.target.closest("input, textarea")) return;
      const step = (ev.shiftKey ? 240 : 80), c = [vp.clientWidth / 2, vp.clientHeight / 2];
      const k = ev.key;
      if (k === "Escape") { if (selected) select(null); else close(); }
      else if (k === "ArrowLeft" || k === "a") { cam.x += step; apply(); }
      else if (k === "ArrowRight" || k === "d") { cam.x -= step; apply(); }
      else if (k === "ArrowUp" || k === "w") { cam.y += step; apply(); }
      else if (k === "ArrowDown" || k === "s") { cam.y -= step; apply(); }
      else if (k === "+" || k === "=") zoomAt(cam.k * 1.2, ...c);
      else if (k === "-" || k === "_") zoomAt(cam.k / 1.2, ...c);
      else if (k === "f" || k === "0") fit();
      else if (k === "n" || k === "]" || (k === " " && tour.length)) tourGo(tourAt + 1);
      else if (k === "p" || k === "[") tourGo(tourAt - 1);
      else if (k === "t") tourGo(0);
      else return;
      ev.preventDefault();
    };
    document.addEventListener("keydown", onKey);
    const onResize = () => drawViewport();
    window.addEventListener("resize", onResize);

    active = { root, cleanup: () => { document.removeEventListener("keydown", onKey); window.removeEventListener("resize", onResize); cancelAnimationFrame(anim); }, onClose: opts.onClose };
    drawMini();
    fit(false);
    vp.focus();
    if (opts.focus && L.byId.has(opts.focus)) select(opts.focus);
  }

  function close() {
    if (!active) return;
    active.cleanup();
    active.root.remove();
    document.body.style.overflow = "";
    const cb = active.onClose;
    active = null;
    if (cb) cb();
  }

  window.WorldMap = { open, close, thumbnail, layout, isOpen: () => !!active };
})();
