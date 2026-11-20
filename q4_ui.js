const $ = (id) => document.getElementById(id);

const state = {
  tab: "closest_pair",
  files: [],
  loaded: null,
  result: null,
  kind: null,
  steps: [],
  index: 0,
  timer: null,
  view: { scale: 1, ox: 0, oy: 0 },
  points: [],
  bounds: null,
};

let requestId = 0;
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (c) =>
  ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

const canvas = $("canvas");
const ctx = canvas.getContext("2d");

const fmt = (n) => typeof n === "number"
  ? n.toLocaleString("en-US", { maximumFractionDigits: 3 })
  : (n ?? "—");

const ms = (v) => v == null ? "—" : v < 1 ? (v * 1000).toFixed(0) + " µs" : v.toFixed(2) + " ms";

function toast(text, isError) {
  const node = $("toast");
  node.textContent = text;
  node.className = "toast show" + (isError ? " err" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { node.className = "toast"; }, 3000);
}

function setStatus(text, kind) {
  $("status-text").textContent = text;
  $("status").dataset.state = kind || "idle";
}

async function getJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function loadFiles() {
  try {
    const data = await getJSON("/api/files");
    state.files = data.files;
    renderFiles();
  } catch (err) {
    $("files").innerHTML = '<div class="dz-sub">could not load the dataset list</div>';
  }
}

function renderFiles() {
  const query = $("filter").value.trim().toLowerCase();
  const host = $("files");
  const list = state.files.filter((f) => f.kind === state.tab);
  const shown = list.filter((f) => {
    const size = f.n ? f.n + " points" : f.a_digits + " x " + f.b_digits + " digits";
    return !query || (f.name + " " + size + " " + f.shape).toLowerCase().includes(query);
  });

  $("file-count").textContent = `${shown.length} of ${list.length}`;
  host.innerHTML = "";
  if (!shown.length) {
    host.innerHTML = '<div class="dz-sub">no file matches that filter</div>';
    return;
  }

  shown.forEach((f) => {
    const b = document.createElement("button");
    b.className = "file";
    if (state.loaded && state.loaded.name === f.name) b.classList.add("active");
    const size = f.n ? f.n + " points" : f.a_digits + "×" + f.b_digits;
    b.innerHTML = `<span class="fname">${escapeHTML(f.name.replace(/^q2_/, "").replace(/^(closest_pair|integer_multiplication)_/, ""))}</span>
      <span class="fmeta">${escapeHTML(f.shape)}</span>
      <span class="badge">${size}</span>`;
    b.title = f.name;
    b.onclick = () => selectFile(f.name);
    host.appendChild(b);
  });
}

function setTab(tab, silent) {
  if (!silent) { requestId++; $("run").disabled = false; }
  state.tab = tab;
  document.querySelectorAll(".tab, .segmented button").forEach((b) => {
    if (b.dataset.tab) b.setAttribute("aria-selected", String(b.dataset.tab === tab));
  });
  const isInt = tab === "integer_multiplication";
  $("tree").hidden = !isInt;
  canvas.hidden = isInt;
  $("product-section").hidden = !isInt;
  $("levels-section").hidden = !isInt;
  $("zoom-controls").style.display = isInt ? "none" : "flex";
  $("legend").innerHTML = isInt
    ? '<span>Split → subproducts → combine</span>'
    : '<span><i style="background:#93a9d4"></i>point</span><span><i style="background:rgba(91,140,255,.55)"></i>subproblem</span><span><i style="background:#ffbf5c"></i>split line</span><span><i style="background:#7fd8ff"></i>answer</span>';

  stop();
  renderFiles();
  if (state.loaded && state.loaded.kind !== tab) {
    resetLoaded();
    if (!silent) loadFirst();
  } else if (!state.loaded && !silent) {
    loadFirst();
  }
  resize();
}

function loadFirst() {
  const list = state.files.filter((f) => f.kind === state.tab);
  if (!list.length) return;
  const pick = state.tab === "closest_pair"
    ? list[Math.min(3, list.length - 1)]
    : list.reduce((best, f) => {
        const target = 4000;
        return Math.abs(f.a_digits - target) < Math.abs(best.a_digits - target) ? f : best;
      }, list[0]);
  selectFile(pick.name);
}

function resetLoaded() {
  stop();
  state.loaded = null;
  state.result = null;
  state.steps = [];
  state.index = 0;
  state.points = [];
  state.bounds = null;
  $("filecard").innerHTML = '<div class="dz-sub">no file loaded yet</div>';
  $("answer").innerHTML = '<div class="dz-sub">run an algorithm to see the result</div>';
  $("verify").innerHTML = '<div class="dz-sub">nothing checked yet</div>';
  $("stats").innerHTML = "";
  $("levels").innerHTML = "";
  $("product").textContent = "";
  $("caption").style.opacity = "0";
  $("empty").classList.remove("hide");
  $("tree").innerHTML = "";
  $("step-detail").textContent = "Choose an input file, then press Run.";
  $("run").disabled = true;
  $("copy").disabled = true;
  setRange(0, 0);
  clearCanvas();
  setStatus("ready", "idle");
}

function showInput(data, content) {
  resetLoaded();
  state.kind = data.kind;
  state.loaded = { name: data.name, kind: data.kind, size: data.size, content };
  if (state.tab !== data.kind) setTab(data.kind, true);
  renderFileCard(data);
  renderFiles();
  if (data.kind === "closest_pair") {
    state.points = data.input.points;
    state.bounds = computeBounds(state.points);
    resize(); fitView(); draw();
  } else {
    $("tree").innerHTML = `<div class="step-work"><h2>Input numbers</h2><pre>a = ${escapeHTML(data.input.a)}\nb = ${escapeHTML(data.input.b)}</pre><p>Press Run to split these numbers and calculate their product.</p></div>`;
  }
  $("empty").classList.add("hide");
  $("step-detail").textContent = "Input loaded. Press Run to calculate and begin the walkthrough.";
  $("run").disabled = false;
  setStatus("input ready — press Run", "idle");
}

async function selectFile(name) {
  const id = ++requestId;
  stop();
  resetLoaded();
  $("run").disabled = true;
  setStatus("loading input", "busy");
  try {
    const data = await postJSON("/api/prepare", { name });
    if (id !== requestId) return;
    showInput(data);
  } catch (err) {
    if (id !== requestId) return;
    setStatus("error", "error");
    toast("Could not load: " + err.message, true);
  }
}

function renderFileCard(meta) {
  const entry = state.files.find((f) => f.name === meta.name);
  const rows = entry && entry.n
    ? `<dt>points</dt><dd>${fmt(entry.n)}</dd><dt>shape</dt><dd>${entry.shape}</dd>`
    : entry
      ? `<dt>digits a</dt><dd>${fmt(entry.a_digits)}</dd><dt>digits b</dt><dd>${fmt(entry.b_digits)}</dd>`
      : "";
  $("filecard").innerHTML =
    `<div class="cname">${escapeHTML(meta.name.replace(/^q2_/, ""))}</div>
     <dl class="kv">
       <dt>problem</dt><dd>${meta.kind.replace(/_/g, " ")}</dd>
       <dt>size</dt><dd>${(meta.size / 1024).toFixed(1)} KB</dd>
       ${rows}
     </dl>
     <pre class="preview">${escapeHTML(meta.preview)}</pre>`;
}

async function run(name) {
  if (!name) return;
  const id = ++requestId;
  setStatus("running", "busy");
  $("run").disabled = true;
  stop();
  state.steps = [];
  state.result = null;
  hideAnswer();
  $("tree").innerHTML = "";
  $("step-detail").textContent = "Calculating this input and recording its steps…";
  draw();
  try {
    const data = await postJSON("/api/run", state.loaded?.content != null
      ? { name, content: state.loaded.content } : { name });
    if (id !== requestId) return;
    if (!data.ok) throw new Error(data.error);
    state.result = data;
    state.kind = data.kind;
    if (data.kind === "closest_pair") {
      state.points = data.result.points;
      state.bounds = computeBounds(data.result.points);
      state.steps = data.result.steps;
      canvas.hidden = false;
      resize();
      fitView();
    } else {
      state.steps = data.result.steps;
    }
    state.steps.unshift({kind: "input", title: "Start with the input", depth: 0,
      boxes: [], splits: [], lines: ["The input is ready. Follow each split, calculation and combine step."]});
    renderStats(data.result);
    setRange(0, state.steps.length - 1);
    goto(0);
    play();
    $("empty").classList.add("hide");
  } catch (err) {
    if (id !== requestId) return;
    setStatus("error", "error");
    toast("Run failed: " + err.message, true);
  } finally {
    if (id === requestId) $("run").disabled = false;
  }
}

function renderClosestAnswer(r) {
  $("answer").innerHTML = `
    <div class="stat-label">minimum distance</div>
    <div class="big-value">${r.distance.toFixed(6)}</div>
    <div class="pair"><b>P1</b> (${r.pair[0][0].toFixed(4)}, ${r.pair[0][1].toFixed(4)})<br />
      <b>P2</b> (${r.pair[1][0].toFixed(4)}, ${r.pair[1][1].toFixed(4)})</div>
    <div class="chips"><span class="chip info">n = ${fmt(r.n)}</span>
      <span class="chip info">O(n log n)</span>
      <span class="chip">${ms(r.ms)}</span></div>`;

  const v = $("verify");
  if (!r.brute) {
    v.innerHTML = `<div class="row"><span class="k">brute force</span><span class="v">skipped, n above 3000</span></div>
      <div class="row"><span class="k">reported pair</span><span class="v">not independently checked</span></div>`;
    return;
  }
  v.innerHTML = `
    <div class="row"><span class="k">divide and conquer</span><span class="v">${r.distance.toFixed(6)}</span></div>
    <div class="row"><span class="k">brute force</span><span class="v">${r.brute.distance.toFixed(6)}</span></div>
    <div class="row"><span class="k">brute force time</span><span class="v">${ms(r.brute.ms)}</span></div>
    <div class="chips"><span class="chip ${r.brute.match ? "ok" : "no"}">${r.brute.match ? "answers agree" : "mismatch"}</span></div>`;
}

function renderIntegerAnswer(r) {
  $("answer").innerHTML = `
    <div class="stat-label">product</div>
    <div class="big-value">${fmt(r.product_digits)} digits</div>
    <div class="pair"><b>a</b> ${fmt(r.a_digits)} digits<br /><b>b</b> ${fmt(r.b_digits)} digits</div>
    <div class="chips"><span class="chip info">O(n^1.585)</span><span class="chip">${ms(r.ms)}</span></div>`;

  $("product").textContent = r.product;
  $("verify").innerHTML = `
    <div class="row"><span class="k">karatsuba</span><span class="v">${ms(r.ms)}</span></div>
    <div class="row"><span class="k">schoolbook</span><span class="v">${ms(r.schoolbook_ms)}</span></div>
    <div class="chips"><span class="chip ${r.match ? "ok" : "no"}">${r.match ? "identical to schoolbook" : "mismatch"}</span></div>`;
}

function renderStats(r) {
  $("stats").innerHTML = `<div class="row"><span class="k">calculation time</span><span class="v">${ms(r.ms)}</span></div>
    <div class="row"><span class="k">playback steps</span><span class="v">${r.steps.length}</span></div>
    <div class="row"><span class="k">grouped operations</span><span class="v">${r.omitted}</span></div>`;
  $("levels").textContent = "Follow the current operation in the workspace. Deeper calls may be grouped for large inputs.";
}

function hideAnswer() {
  $("answer").innerHTML = '<div class="dz-sub">Final answer appears after the last step.</div>';
  $("verify").textContent = "Verification appears with the final answer.";
  $("product").textContent = "";
  $("copy").disabled = true;
}

function computeBounds(points) {
  let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
  for (const [x, y] of points) {
    if (x < xmin) xmin = x;
    if (x > xmax) xmax = x;
    if (y < ymin) ymin = y;
    if (y > ymax) ymax = y;
  }
  return { xmin, xmax, ymin, ymax };
}

function fitView() {
  if (!state.bounds) return;
  const w = canvas.clientWidth || 640;
  const h = canvas.clientHeight || 420;
  const pad = 42;
  const { xmin, xmax, ymin, ymax } = state.bounds;
  const dx = Math.max(xmax - xmin, 1e-9);
  const dy = Math.max(ymax - ymin, 1e-9);
  const s = Math.min((w - 2 * pad) / dx, (h - 2 * pad) / dy);
  state.view.scale = s;
  state.view.ox = pad + (w - 2 * pad - dx * s) / 2 - xmin * s;
  state.view.oy = h - pad - (h - 2 * pad - dy * s) / 2 + ymin * s;
}

const sx = (x) => x * state.view.scale + state.view.ox;
const sy = (y) => -y * state.view.scale + state.view.oy;

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
}

function draw() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  if (!state.points.length || state.kind !== "closest_pair") return;

  const step = state.steps[state.index];
  const dense = state.points.length > 1500;

  if (step) {
    for (const b of step.boxes) {
      const x = sx(b[0]);
      const y = sy(b[3]);
      const bw = sx(b[2]) - x;
      const bh = sy(b[1]) - y;
      const g = ctx.createLinearGradient(x, y, x + bw, y + bh);
      g.addColorStop(0, "rgba(91,140,255,0.10)");
      g.addColorStop(1, "rgba(169,123,255,0.10)");
      ctx.fillStyle = g;
      ctx.fillRect(x, y, bw, bh);
      ctx.strokeStyle = "rgba(120,165,255,0.5)";
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, bw, bh);
    }
    ctx.strokeStyle = "rgba(255,191,92,0.65)";
    ctx.setLineDash([5, 5]);
    for (const mx of step.splits) {
      ctx.beginPath();
      ctx.moveTo(sx(mx), 0);
      ctx.lineTo(sx(mx), h);
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  for (const [x, y] of state.points) {
    const px = sx(x);
    const py = sy(y);
    if (px < -4 || py < -4 || px > w + 4 || py > h + 4) continue;
    if (dense) {
      ctx.fillStyle = "rgba(150,175,225,0.65)";
      ctx.fillRect(px - 0.9, py - 0.9, 1.8, 1.8);
    } else {
      ctx.beginPath();
      ctx.fillStyle = "rgba(168,193,240,0.9)";
      ctx.arc(px, py, 1.9, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const isAnswer = step && step.kind === "answer";
  const pair = isAnswer ? state.result.result.pair : step?.pair;
  if (!pair || (step.kind === "combine" && step.depth === 0)) return;
  const a = [sx(pair[0][0]), sy(pair[0][1])];
  const b = [sx(pair[1][0]), sy(pair[1][1])];
  ctx.globalAlpha = isAnswer ? 1 : 0.22;
  ctx.strokeStyle = "#7fd8ff";
  ctx.lineWidth = isAnswer ? 2.2 : 1.4;
  ctx.shadowColor = "rgba(127,216,255,0.8)";
  ctx.shadowBlur = isAnswer ? 14 : 0;
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
  ctx.stroke();
  ctx.shadowBlur = 0;
  ctx.fillStyle = "#bdefff";
  ctx.strokeStyle = "rgba(127,216,255,0.55)";
  for (const p of [a, b]) {
    ctx.beginPath();
    ctx.arc(p[0], p[1], isAnswer ? 4.4 : 3, 0, Math.PI * 2);
    ctx.fill();
    if (isAnswer) {
      ctx.beginPath();
      ctx.arc(p[0], p[1], 9, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;
}

function buildTree(step) {
  $("tree").innerHTML = `<div class="step-work"><div class="eyebrow">Recursion depth ${step.depth}</div>
    <h2>${escapeHTML(step.title)}</h2>${step.lines.map(line => `<p>${escapeHTML(line)}</p>`).join("")}</div>`;
}

function setRange(index, total) {
  const scrub = $("scrub");
  scrub.max = total;
  scrub.value = index;
  $("counter").textContent = state.steps.length ? `${index + 1} / ${total + 1}` : "0 / 0";
  const pct = total > 0 ? (index / total) * 100 : 0;
  scrub.style.setProperty("--fill", pct + "%");
}

function goto(index) {
  if (!state.steps.length) return;
  state.index = Math.max(0, Math.min(index, state.steps.length - 1));
  setRange(state.index, state.steps.length - 1);
  const step = state.steps[state.index];

  $("caption-tag").textContent = step.title;
  $("caption-text").textContent = `Step ${state.index + 1} of ${state.steps.length} · recursion depth ${step.depth}`;
  $("caption").style.opacity = "1";
  $("step-detail").replaceChildren(...step.lines.map(line => {
    const p = document.createElement("p"); p.textContent = line; return p;
  }));
  if (step.kind === "answer") {
    if (state.kind === "closest_pair") renderClosestAnswer(state.result.result);
    else renderIntegerAnswer(state.result.result);
    $("copy").disabled = state.kind !== "integer_multiplication";
    setStatus("complete", "ok");
    stop();
  } else {
    hideAnswer();
    setStatus(`step ${state.index + 1} of ${state.steps.length}`, "busy");
  }
  if (state.kind === "closest_pair") draw();
  else buildTree(step);
}

function stop() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
  $("play-icon").innerHTML = '<path d="M8 5l11 7-11 7z" fill="currentColor" />';
}

function play() {
  if (state.timer) { stop(); return; }
  if (!state.steps.length) return;
  if (state.index >= state.steps.length - 1) goto(0);
  $("play-icon").innerHTML = '<path d="M7 5h4v14H7zM13 5h4v14h-4z" fill="currentColor" />';
  const delay = Number($("speed").value);
  state.timer = setInterval(() => {
    if (state.index >= state.steps.length - 1) { stop(); return; }
    goto(state.index + 1);
  }, delay);
}

function resize() {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(w * dpr));
  canvas.height = Math.max(1, Math.floor(h * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

$("run").onclick = () => run(state.loaded ? state.loaded.name : null);
$("play").onclick = play;
$("next").onclick = () => {
  stop();
  const last = state.steps.length - 1;
  goto(Math.min(last, state.index + 1));
};

$("back").onclick = () => {
  stop();
  const last = state.steps.length - 1;
  goto(Math.max(0, state.index - 1));
};
$("scrub").oninput = (e) => { stop(); goto(Number(e.target.value)); };
$("speed").onchange = () => { if (state.timer) { stop(); play(); } };
$("filter").oninput = renderFiles;

document.querySelectorAll(".segmented button").forEach((b) => {
  b.onclick = () => setTab(b.dataset.tab);
});

$("copy").onclick = () => {
  const text = $("product").textContent;
  Promise.resolve().then(() => navigator.clipboard.writeText(text)).then(
    () => toast("Product copied"),
    () => {
      const range = document.createRange();
      range.selectNodeContents($("product"));
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      toast("Selected, press Ctrl+C");
    });
};

$("zoom-in").onclick = () => { state.view.scale *= 1.25; draw(); };
$("zoom-out").onclick = () => { state.view.scale /= 1.25; draw(); };
$("zoom-fit").onclick = () => { fitView(); draw(); };

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const k = Math.exp(-e.deltaY * 0.0015);
  state.view.ox = mx - (mx - state.view.ox) * k;
  state.view.oy = my - (my - state.view.oy) * k;
  state.view.scale *= k;
  draw();
}, { passive: false });

let drag = null;
canvas.addEventListener("mousedown", (e) => { drag = { x: e.clientX, y: e.clientY }; canvas.style.cursor = "grabbing"; });
window.addEventListener("mouseup", () => { drag = null; canvas.style.cursor = "crosshair"; });
window.addEventListener("mousemove", (e) => {
  if (!drag) return;
  state.view.ox += e.clientX - drag.x;
  state.view.oy += e.clientY - drag.y;
  drag = { x: e.clientX, y: e.clientY };
  draw();
});

const dropzone = $("dropzone");
const fileinput = $("fileinput");
dropzone.onclick = () => fileinput.click();
dropzone.onkeydown = (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileinput.click(); }
};
dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add("over"); };
dropzone.ondragleave = () => dropzone.classList.remove("over");
dropzone.ondrop = (e) => {
  e.preventDefault();
  dropzone.classList.remove("over");
  if (e.dataTransfer.files.length) upload(e.dataTransfer.files[0]);
};
fileinput.onchange = () => {
  if (fileinput.files.length) upload(fileinput.files[0]);
  fileinput.value = "";
};

async function upload(file) {
  if (file.size > 20 * 1024 * 1024) { toast("That file is too large", true); return; }
  const id = ++requestId;
  resetLoaded();
  setStatus("reading input", "busy");
  try {
    const content = await file.text();
    if (id !== requestId) return;
    const data = await postJSON("/api/prepare", { content, name: file.name });
    if (id !== requestId) return;
    showInput(data, content);
  } catch (err) {
    if (id !== requestId) return;
    setStatus("error", "error"); toast("Upload failed: " + err.message, true);
  }
}

$("demo-points").onclick = () => upload(new File(["6\n1 1\n2 2\n3 8\n5 5\n6 5\n9 9"], "example_points.txt"));
$("demo-numbers").onclick = () => upload(new File(["123456789123456789\n987654321987654321"], "example_numbers.txt"));

window.addEventListener("keydown", (e) => {
  if (e.target.matches("input, select, textarea")) return;
  if (e.code === "Space") { e.preventDefault(); play(); }
  else if (e.key === "ArrowRight") { e.preventDefault(); $("next").onclick(); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); $("back").onclick(); }
  else if (e.key === "f" || e.key === "F") { fitView(); draw(); }
});

new ResizeObserver(() => resize()).observe($("canvas").parentElement);
window.addEventListener("resize", resize);

setTab("closest_pair", true);
loadFiles().then(() => {
  resize();
  loadFirst();
});
