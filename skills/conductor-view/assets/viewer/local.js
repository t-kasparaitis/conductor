/* Conductor view without Python: when index.html is opened straight from disk,
 * the user picks the project (or its conductor/) folder and these parsers build
 * the same state serve.py would. They mirror serve.py's parse_* functions;
 * tests/test_local_parity.py checks both give identical results. Read-only:
 * feedback is copied for the chat instead of saved. */
(function () {
  "use strict";

  const STATUS = { " ": "pending", "~": "in_progress", x: "done", X: "done" };
  const TRACK_ID_RE = /^[A-Za-z0-9._-]+$/;
  const SHA_RE = /\s+`?\[?([0-9a-f]{7,40})\]?`?\s*$/;

  // Same breaks as Python's str.splitlines(), which also drops a final empty line.
  function lines(text) {
    const out = String(text || "").split(/\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/);
    if (out.length && out[out.length - 1] === "") out.pop();
    return out;
  }

  function parseRegistry(text) {
    const entries = [];
    let current = null;
    for (const line of lines(text)) {
      const m = line.match(/^\s*-\s*\[([ ~xX])\]\s*\*\*(?:Track:\s*)?(.+?)\*\*/) || line.match(/^##\s*\[([ ~xX])\]\s*Track:\s*(.+?)\s*$/);
      if (m) { current = { status: STATUS[m[1]], description: m[2].trim(), link: null }; entries.push(current); continue; }
      const link = line.match(/\[[^\]]*\]\(([^)]+)\)/);
      if (current && link && current.link === null) current.link = link[1].trim();
    }
    for (const e of entries) {
      if (!e.link) { e.track_id = null; continue; }
      const parts = e.link.replace(/\\/g, "/").split("/");
      parts.pop();
      // Python's Path("./x/index.md").parent.name: the last non-"." part.
      const name = parts.filter((p) => p !== "" && p !== ".").pop();
      e.track_id = name === undefined ? "" : name;
    }
    return entries;
  }

  function splitShas(body) {
    const shas = [];
    for (;;) {
      const m = body.match(SHA_RE);
      if (!m) return [body, shas.reverse()];
      shas.push(m[1]);
      body = body.slice(0, m.index).replace(/\s+$/, "");
    }
  }

  function isCheckpoint(text) {
    const low = text.toLowerCase();
    return low.includes("sign-off") || (low.includes("verification") && low.includes("checkpoint"));
  }

  function expandIndent(ws) {
    let n = 0;
    for (const ch of ws) n = ch === "\t" ? n + 4 - (n % 4) : n + 1;
    return n;
  }

  function parsePlan(text) {
    const plan = { title: null, preamble: [], phases: [] };
    let phase = null, task = null;
    for (const raw of lines(text)) {
      const line = raw.replace(/\s+$/, "");
      const h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        const level = h[1].length;
        let title = h[2].trim();
        if (level === 1 && plan.title === null && !plan.phases.length) { plan.title = title; continue; }
        const cp = title.match(/\[checkpoint:\s*([0-9a-f]{7,40})\]/);
        title = title.replace(/\s*\[checkpoint:[^\]]*\]/g, "").trim();
        phase = { title, checkpoint: cp ? cp[1] : null, tasks: [], notes: [] };
        plan.phases.push(phase);
        task = null;
        continue;
      }
      const m = line.match(/^(\s*)[-*]\s+\[([ ~xX])\]\s+(.*)$/);
      if (m && phase) {
        const indent = expandIndent(m[1]);
        const [body, shas] = splitShas(m[3]);
        const sha = shas.length ? shas[shas.length - 1] : null;
        if (indent === 0 || !task) {
          task = { text: body.replace(/^task:\s*/i, ""), status: STATUS[m[2]], sha, shas,
                   is_checkpoint: /^task:/i.test(body) && isCheckpoint(body), subtasks: [], notes: [] };
          phase.tasks.push(task);
        } else task.subtasks.push({ text: body, status: STATUS[m[2]], sha, shas });
        continue;
      }
      if (!line.trim()) continue;
      (task ? task.notes : phase ? phase.notes : plan.preamble).push(line.trim());
    }
    for (const p of plan.phases) {
      const items = p.tasks.map((t) => t.status);
      p.done = items.filter((s) => s === "done").length;
      p.total = items.length;
      p.status = items.length && p.done === items.length ? "done" : items.some((s) => s !== "pending") ? "in_progress" : "pending";
    }
    return plan;
  }

  const FB_HEAD = /^###\s+(FB-\d+)\s*·\s*(open|resolved)\s*·\s*([\w-]+)\s*$/i;

  function parseFeedback(text) {
    const items = [];
    let cur = null;
    for (const line of lines(text)) {
      const h = line.trim().match(FB_HEAD);
      if (h) {
        cur = { id: h[1], status: h[2].toLowerCase(), kind: h[3].toLowerCase(), target: "", when: "", body: [], reply: [] };
        items.push(cur);
        continue;
      }
      if (!cur) continue;
      const m = line.match(/^-\s+\*\*(Target|When):\*\*\s*(.*)$/);
      if (m && !cur.body.length) cur[m[1].toLowerCase()] = m[2].trim();
      else if (line.startsWith(">")) cur.reply.push(line.slice(1).trim());
      else cur.body.push(line);
    }
    for (const it of items) { it.body = it.body.join("\n").trim(); it.reply = it.reply.join("\n").trim(); }
    return items;
  }

  function diagramProblem(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) return "must be a JSON object";
    const nodes = data.nodes === undefined ? [] : data.nodes;
    if (!Array.isArray(nodes) || !nodes.every((n) => n && typeof n === "object" && !Array.isArray(n) && "id" in n))
      return "`nodes` must be a list of objects, each with an `id`";
    const ids = new Set(nodes.map((n) => String(n.id)));
    if (ids.size < nodes.length) return "node ids must be unique";
    for (const key of ["edges", "regions", "tour"]) if (data[key] !== undefined && !Array.isArray(data[key])) return `\`${key}\` must be a list`;
    for (const e of data.edges || []) {
      if (!e || typeof e !== "object" || !ids.has(String(e.from)) || !ids.has(String(e.to))) return `edge ${JSON.stringify(e)} must join two node ids`;
    }
    const missing = (data.tour || []).filter((t) => !ids.has(String(t)));
    return missing.length ? `tour stops ${JSON.stringify(missing)} are not node ids` : null;
  }

  function loadDiagrams(files, dir) {
    const out = [];
    const names = Object.keys(files).filter((p) => p.startsWith(dir) && !p.slice(dir.length).includes("/")).sort();
    for (const path of names) {
      const name = path.slice(dir.length), stem = name.replace(/\.[^.]*$/, "");
      if (name.endsWith(".json")) {
        let data = null, problem = null;
        try { data = JSON.parse(files[path]); problem = diagramProblem(data); } catch (e) { problem = e.message; }
        out.push(problem ? { slug: stem, type: "error", title: stem, error: `${name}: ${problem}` }
                         : { slug: stem, type: "map", data, title: data.title || stem });
      } else if (name.endsWith(".svg")) out.push({ slug: stem, type: "svg", title: stem, svg: files[path] });
    }
    return out;
  }

  /** files: { "conductor/tracks/x/plan.md": "text", ... } -> the state serve.py would return. */
  function buildState(files, project) {
    const has = (p) => Object.prototype.hasOwnProperty.call(files, p);
    const registry = parseRegistry(files["conductor/tracks.md"] || "")
      .filter((e) => e.track_id && TRACK_ID_RE.test(e.track_id) && e.track_id !== "." && e.track_id !== "..");
    const byId = new Map(registry.map((e) => [e.track_id, e]));
    const foldersIn = (dir) => new Set(Object.keys(files).map((p) => p.slice(0, dir.length) === dir ? p.slice(dir.length).split("/") : null)
      .filter((parts) => parts && parts.length > 1 && TRACK_ID_RE.test(parts[0])).map((parts) => parts[0]));
    const folders = foldersIn("conductor/tracks/");
    const order = registry.map((e) => e.track_id).concat([...folders].filter((f) => !byId.has(f)).sort());
    const loadTrack = (tid, base, archived) => {
      let meta = {}, metaError = null;
      if (files[base + "metadata.json"]) {
        try { meta = JSON.parse(files[base + "metadata.json"]); if (!meta || typeof meta !== "object" || Array.isArray(meta)) { meta = {}; metaError = "must be a JSON object"; } }
        catch (e) { metaError = e.message; }
      }
      return {
        id: tid, archived, registry: byId.get(tid) || null, metadata: meta, metadata_error: metaError,
        spec: files[base + "spec.md"] || "", plan: parsePlan(files[base + "plan.md"] || ""),
        feedback: parseFeedback(files[base + "feedback.md"] || ""), diagrams: loadDiagrams(files, base + "diagrams/"),
      };
    };
    const tracks = order.filter((tid) => folders.has(tid)).map((tid) => loadTrack(tid, `conductor/tracks/${tid}/`, false));
    const seen = new Set(tracks.map((t) => t.id));
    // Same as serve.py: sorted by code point, and a folder in both places keeps the live copy.
    [...foldersIn("conductor/archive/")].filter((tid) => !seen.has(tid)).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
      .forEach((tid) => tracks.push(loadTrack(tid, `conductor/archive/${tid}/`, true)));
    let values = {}, error = null;
    if (has("conductor/settings.json")) {
      try { values = JSON.parse(files["conductor/settings.json"]); } catch (e) { error = "settings.json: " + e.message; }
    }
    return {
      project, initialized: has("conductor/index.md"), tracks, version: "local",
      settings: { schema: null, exists: has("conductor/settings.json"), values, effective: {}, error },
    };
  }

  /** Read a picked folder (the project root or its conductor/) into buildState's input. */
  async function readPicked(fileList) {
    const files = {};
    let project = "";
    const wanted = /^conductor\/(index\.md|tracks\.md|settings\.json|(?:tracks|archive)\/[^/]+\/(spec\.md|plan\.md|feedback\.md|metadata\.json|diagrams\/[^/]+\.(json|svg)))$/;
    for (const f of fileList) {
      const parts = (f.webkitRelativePath || f.name).split("/");
      const top = parts.shift();
      const rel = top === "conductor" ? "conductor/" + parts.join("/") : parts.join("/");
      if (!project) project = top === "conductor" ? "" : top;
      if (wanted.test(rel)) files[rel] = await f.text();
    }
    return { files, project };
  }

  function feedbackForChat(track, kind, target, text) {
    return [
      `Please add this to conductor/tracks/${track}/feedback.md as the next FB item and address it:`,
      "",
      `### FB-NEW · open · ${kind}`,
      `- **Target:** ${target}`,
      `- **When:** ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
      "",
      text || "_(no message)_",
    ].join("\n");
  }

  window.ConductorLocal = { parseRegistry, parsePlan, parseFeedback, diagramProblem, buildState, readPicked, feedbackForChat };
})();
