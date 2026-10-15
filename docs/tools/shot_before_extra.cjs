// Capture the two MISSING "before" screenshots for the material-level /
// diagnostic-set feature: /teacher/practice and /teacher/question-bank.
// Same method as shot_all_1440.cjs: headless Edge + CDP, width arg, DPR 1,
// full-page via captureBeyondViewport. Non-destructive: only writes new files.
// Usage: node shot_before_extra.cjs [width]
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9337;
const WIDTH = parseInt(process.argv[2] || "1440", 10);
const BASE = "http://localhost:3000";
const OUTDIR = "D:\\Aldeann\\docs\\screenshots";

const SHOTS = [
  { name: "latihan-per-bagian-guru-sebelum.png", path: "/teacher/practice", marker: "soal disetujui" },
  { name: "bank-soal-guru-sebelum.png", path: "/teacher/question-bank", marker: "Menampilkan" },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function login(email) {
  const r = await fetch("http://localhost:5000/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: "123123123" }),
  });
  const body = await r.json();
  const token = body.access_token || (body.user && body.user.access_token);
  if (!token) throw new Error("no token for " + email);
  return token;
}

async function waitForTarget(deadline) {
  while (Date.now() < deadline) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch (_) {}
    await sleep(400);
  }
  throw new Error("debugger target never appeared");
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
  return (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
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
    await sleep(700);
  }
  return false;
}

(async () => {
  const tokens = { teacher: await login("guru1@ebiox.com") };
  fs.mkdirSync(OUTDIR, { recursive: true });
  const profile = path.join(os.tmpdir(), "edge-shot-extra-" + Date.now());
  const proc = spawn(EDGE, [
    "--headless=new",
    "--remote-debugging-port=" + PORT,
    "--user-data-dir=" + profile,
    "--window-size=" + WIDTH + ",900",
    "--hide-scrollbars",
    "about:blank",
  ]);
  try {
    const wsUrl = await waitForTarget(Date.now() + 20000);
    const ws = new WebSocket(wsUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const send = cdp(ws);
    await send("Page.enable");
    await send("Network.enable");

    for (const s of SHOTS) {
      for (const c of [
        ["access_token", tokens.teacher],
        ["role", "teacher"],
        ["username", "Guru 1"],
      ]) {
        await send("Network.setCookie", { name: c[0], value: c[1], url: BASE, path: "/" });
      }
      await send("Page.navigate", { url: BASE + s.path });
      const loaded = await waitReady(send, s.marker, Date.now() + 45000);
      await sleep(1500);

      const dim = await send("Runtime.evaluate", {
        expression:
          "JSON.stringify({h: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, window.innerHeight), w: document.documentElement.scrollWidth, iw: window.innerWidth, path: location.pathname})",
        returnByValue: true,
      });
      const d = JSON.parse(dim.result.value);
      const clip = { x: 0, y: 0, width: Math.min(d.w || WIDTH, WIDTH), height: d.h, scale: 1, captureBeyondViewport: true };
      const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip });
      const out = path.join(OUTDIR, s.name);
      fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
      console.log(
        `${s.name}  ->  ${clip.width}x${Math.round(clip.height)}  (${Math.round(fs.statSync(out).size / 1024)} KB)  data=${loaded}  [landed ${d.path}]`
      );
    }
    ws.close();
  } finally {
    try { proc.kill(); } catch (_) {}
  }
  console.log("DONE");
})().catch((e) => { console.error("FAILED:", e.message); process.exit(1); });
