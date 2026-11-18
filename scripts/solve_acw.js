// 解阿里云 WAF acw_sc__v2 挑战：在沙箱中运行挑战页 JS，捕获写入的 cookie 值
// 用法: node solve_acw.js <challenge.html>
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync(process.argv[2], "utf8");
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const rd = html.match(/<textarea id="renderData"[^>]*>([\s\S]*?)<\/textarea>/);
if (!rd) { console.error("renderData not found"); process.exit(1); }
const renderDataJSON = rd[1].trim();

let cookieValue = null;
const sandbox = {
  console,
  Date,
  JSON,
  setTimeout: (fn, d) => { try { fn(); } catch (e) {} },
  document: {
    referrer: "",
    getElementById: () => ({ innerHTML: renderDataJSON }),
    // cookie setter：捕获 acw_sc__v2=xxx
    get cookie() { return Object.entries(cookieStore).map(([k, v]) => k + "=" + v).join("; "); },
    set cookie(str) {
      const m = /acw_sc__v2=([^;]+)/.exec(str);
      if (m) cookieValue = m[1];
    },
    location: { href: "https://www.yingjiesheng.com/commend-fulltime-1.html", reload: () => {} },
  },
  location: { href: "https://www.yingjiesheng.com/commend-fulltime-1.html", reload: () => {} },
  navigator: { userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0", language: "zh-CN", languages: ["zh-CN","zh"], platform: "Win32", cookieEnabled: true, plugins: [], webdriver: false },
  screen: { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, pixelDepth: 24 },
  history: { length: 2, pushState: () => {}, replaceState: () => {}, back: () => {}, forward: () => {} },
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  setInterval: () => 0, clearInterval: () => {},
  requestAnimationFrame: () => 0,
  addEventListener: () => {}, removeEventListener: () => {},
  atob: (s) => Buffer.from(s, "base64").toString("binary"),
  btoa: (s) => Buffer.from(s, "binary").toString("base64"),
};
sandbox.window = sandbox;
sandbox.self = sandbox;
sandbox.globalThis = sandbox;
sandbox.top = sandbox;
sandbox.parent = sandbox;
sandbox.frames = sandbox;
const cookieStore = {};
// 让 document.cookie 读写 cookieStore（简化：只捕获 acw_sc__v2）
sandbox.document.cookie = "";
Object.defineProperty(sandbox.document, "cookie", {
  set(str) { const m = /acw_sc__v2=([^;]+)/.exec(str); if (m) cookieValue = m[1]; },
  get() { return ""; },
  configurable: true,
});

try {
  vm.createContext(sandbox);
  for (const s of scripts) {
    if (s.trim()) vm.runInContext(s, sandbox, { timeout: 30000 });
  }
} catch (e) {
  console.error("EXEC ERR:", e.message);
}
if (cookieValue) {
  console.log(cookieValue);
} else {
  console.error("NO COOKIE CAPTURED");
  process.exit(2);
}
