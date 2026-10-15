// Capture the 15 "after" screenshots for the material-level / diagnostic-set
// feature. Headless Edge + CDP, width arg, DPR 1, full-page via
// captureBeyondViewport. Uses a FRESH Edge process per page so one crash cannot
// derail the rest, and every CDP call has a hard timeout. Writes -sesudah.png
// into docs/screenshots and appends progress to docs/screenshots/_after_run.log.
//
// Usage: node docs/tools/shot_after_1440.cjs [width]
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const WIDTH = parseInt(process.argv[2] || "1440", 10);
// Optional 1-based list of shot numbers to (re)capture, e.g. "12" or "1,2,12".
const ONLY = process.argv[3]
  ? new Set(process.argv[3].split(",").map((x) => parseInt(x.trim(), 10)))
  : null;
const BASE = "http://localhost:3000";
const OUTDIR = "D:\\Aldeann\\docs\\screenshots";
const LOG = path.join(OUTDIR, "_after_run.log");

function log(line) {
  const s = new Date().toISOString() + "  " + line + "\n";
  try { fs.appendFileSync(LOG, s); } catch (_) {}
  try { process.stdout.write(s); } catch (_) {}
}

const SHOTS = [
  { name: "dashboard-guru-sesudah.png", path: "/teacher", role: "teacher", marker: "Kode:" },
  { name: "daftar-materi-guru-sesudah.png", path: "/teacher/materials", role: "teacher", marker: null },
  { name: "form-materi-sesudah.png", path: "/teacher/materials/create", role: "teacher", marker: null },
  { name: "form-edit-materi-sesudah.png", path: "/teacher/materials/edit/107", role: "teacher", marker: null },
  { name: "analitik-materi-107-sesudah.png", path: "/teacher/materials/analytics/107", role: "teacher", marker: "Tingkat Materi" },
  { name: "latihan-per-bagian-guru-sesudah.png", path: "/teacher/practice", role: "teacher", marker: "diagnostik" },
  { name: "bank-soal-guru-sesudah.png", path: "/teacher/question-bank", role: "teacher", marker: "Menampilkan" },
  { name: "analitik-penguasaan-sesudah.png", path: "/teacher/analytics", role: "teacher", marker: "Distribusi Penguasaan" },
  { name: "ml-insights-sesudah.png", path: "/teacher/analytics/ml", role: "teacher", marker: "Siswa Dianalisis" },
  { name: "analitik-siswa-72-sesudah.png", path: "/teacher/analytics/students/72", role: "teacher", marker: "Progres per Materi" },
  { name: "daftar-materi-siswa-sesudah.png", path: "/student/materials", role: "student", marker: null },
  { name: "detail-materi-siswa-sesudah.png", path: "/student/materials/107", role: "student", marker: null },
  { name: "dashboard-siswa-sesudah.png", path: "/student/dashboard", role: "student", marker: "Progres Materi" },
  { name: "riwayat-belajar-siswa-sesudah.png", path: "/student/progress", role: "student", marker: "Total Materi" },
  { name: "progres-materi-siswa-107-sesudah.png", path: "/student/progress/107", role: "student", marker: "Bagian Materi" },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function withTimeout(promise, ms, label) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("timeout(" + ms + "ms): " + label)), ms);
    promise.then(
      (v) => { clearTimeout(t); resolve(v); },
      (e) => { clearTimeout(t); reject(e); }
    );
  });
}

async function login(email) {
  const r = await withTimeout(
    fetch("http://localhost:5000/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password: "123123123" }),
    }), 15000, "login");
  const body = await r.json();
  const token = body.access_token || (body.user && body.user.access_token);
  if (!token) throw new Error("no token for " + email);
  return token;
}

async function waitForTarget(port, deadline) {
  while (Date.now() < deadline) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch (_) {}
    await sleep(300);
  }
  throw new Error("debugger target never appeared on " + port);
}

function cdp(ws) {
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    }
  });
  ws.addEventListener("close", () => {
    for (const { reject } of pending.values()) reject(new Error("socket closed"));
    pending.clear();
  });
  return (method, params = {}) =>
    withTimeout(new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
    }), 30000, method);
}

async function waitReady(send, marker, deadline) {
  while (Date.now() < deadline) {
    try {
      const expr = marker
        ? `document.body.innerText.indexOf(${JSON.stringify(marker)}) >= 0`
        : `document.body.innerText.length > 250 && !/Memuat|Loading/.test(document.body.innerText)`;
      const chk = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
      if (chk.result.value === true) return true;
    } catch (_) {}
    await sleep(600);
  }
  return false;
}

async function captureOne(s, tokens, port) {
  const profile = path.join(os.tmpdir(), "edge-shot-" + Date.now() + "-" + Math.floor(Math.random() * 1e6));
  const proc = spawn(EDGE, [
    "--headless=new",
    "--disable-gpu",
    "--remote-debugging-port=" + port,
    "--user-data-dir=" + profile,
    "--window-size=" + WIDTH + ",900",
    "--hide-scrollbars",
    "about:blank",
  ]);
  try {
    const wsUrl = await waitForTarget(port, Date.now() + 25000);
    const ws = new WebSocket(wsUrl);
    await withTimeout(new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; }), 15000, "ws-open");
    const send = cdp(ws);
    await send("Page.enable");
    await send("Network.enable");
    for (const c of [
      ["access_token", tokens[s.role]],
      ["role", s.role],
      ["username", s.role === "teacher" ? "Guru 1" : "Murid 1"],
    ]) {
      await send("Network.setCookie", { name: c[0], value: c[1], url: BASE, path: "/" });
    }
    await send("Page.navigate", { url: BASE + s.path });
    const loaded = await waitReady(send, s.marker, Date.now() + 70000);
    await sleep(1500);

    const dim = await send("Runtime.evaluate", {
      expression:
        "JSON.stringify({h: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, window.innerHeight), w: document.documentElement.scrollWidth, path: location.pathname})",
      returnByValue: true,
    });
    const d = JSON.parse(dim.result.value);
    const clip = { x: 0, y: 0, width: Math.min(d.w || WIDTH, WIDTH), height: d.h, scale: 1, captureBeyondViewport: true };
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip });
    if (!shot || !shot.data) throw new Error("no screenshot data");
    const out = path.join(OUTDIR, s.name);
    fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
    ws.close();
    return { name: s.name, w: clip.width, h: Math.round(clip.height), kb: Math.round(fs.statSync(out).size / 1024), loaded, landed: d.path };
  } finally {
    try { proc.kill(); } catch (_) {}
  }
}

(async () => {
  log(`=== RUN only=${ONLY ? [...ONLY].join(",") : "all"} width=${WIDTH} ===`);
  const tokens = {
    teacher: await login("guru1@ebiox.com"),
    student: await login("murid1@ebiox.com"),
  };
  fs.mkdirSync(OUTDIR, { recursive: true });
  let ok = 0, fail = 0;
  const portBase = Math.floor(Math.random() * 30000) + 10000;
  for (let i = 0; i < SHOTS.length; i++) {
    if (ONLY && !ONLY.has(i + 1)) continue;
    const s = SHOTS[i];
    const port = portBase + i * 2;
    try {
      const r = await captureOne(s, tokens, port);
      ok++;
      log(`[${i + 1}/${SHOTS.length}] OK   ${r.name}  ${r.w}x${r.h}  (${r.kb} KB)  data=${r.loaded}  [landed ${r.landed}]`);
    } catch (e) {
      fail++;
      log(`[${i + 1}/${SHOTS.length}] FAIL ${s.name}  -> ${e.message}`);
    }
  }
  log(`DONE ok=${ok} fail=${fail}`);
})().catch((e) => { log("FATAL: " + (e && e.stack || e)); });
