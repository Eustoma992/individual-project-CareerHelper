/* E2E 冒烟：岗位看板 / 笔试全流程 / 面试流程 / 复盘，逐页截图 */
const puppeteer = require("puppeteer-core");

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const BASE = "http://127.0.0.1:8099/";
const OUT = "C:/Users/starain/WorkBuddy/2026-10-30-07-39-19/job-prep/.e2e";

(async () => {
  const fs = require("fs");
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: "new",
    args: ["--no-first-run", "--disable-gpu", "--window-size=1280,1400"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1400 });
  const errors = [];
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });

  await page.goto(BASE, { waitUntil: "networkidle0" });
  await sleep(500);

  // 1. 看板
  await page.evaluate(() => { location.hash = "#board"; });
  await sleep(600);
  await page.select("#board-position", "风险管理岗（银行）");
  await sleep(500);
  await shot("01-board");
  const kpi = await page.$eval("#board-kpis", (el) => el.textContent.slice(0, 80));

  // 2. 笔试：内置题库 8 题
  await page.evaluate(() => { location.hash = "#written"; });
  await sleep(400);
  await page.select("#written-position", "投资银行岗（券商）");
  await page.click("#btn-paper");
  await sleep(600);
  await shot("02-paper");
  // 填客观题：选第一个选项；主观题随便写字
  const info = await page.evaluate(() => {
    const qs = [...document.querySelectorAll("#paper .q")];
    qs.forEach((q, i) => {
      const radios = [...q.querySelectorAll("input[type=radio]")];
      const boxes = [...q.querySelectorAll("input[type=checkbox]")];
      if (radios.length) radios[Math.floor(Math.random() * radios.length)].click();
      else if (boxes.length) { boxes[0].click(); boxes[1] && boxes[1].click(); }
      else {
        const ta = q.querySelector("textarea");
        ta.value = "首先分析背景，其次我负责了数据核对工作，例如核对了应收账款明细，最后结果为核对差异率降到1%以内。";
        ta.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    return qs.length;
  });
  await page.click("#btn-submit-paper");
  await sleep(800);
  await shot("03-paper-result");
  const result = await page.$eval(".result-card", (el) => el.textContent.slice(0, 60)).catch(() => "NO RESULT CARD");

  // 3. 面试：本地评估
  await page.evaluate(() => { location.hash = "#interview"; });
  await sleep(400);
  await page.select("#iv-position", "银行管培生（中后台）");
  await page.select("#iv-engine", "local");
  await page.click("#btn-iv-start");
  await sleep(500);
  await shot("04-interview");
  await page.type("#iv-answer", "我选择银行是因为认同其稳健经营的文化。首先在校期间我系统学习了货币银行学，其次在实习中参与了对公业务辅助工作，例如整理授信材料，最后我希望能从中后台岗位开始，长期深耕风险管理。");
  await sleep(300);
  await page.click("#btn-iv-submit");
  await sleep(900);
  await shot("05-feedback");
  const feedback = await page.$eval("#iv-feedback", (el) => el.textContent.slice(0, 80)).catch(() => "NO FEEDBACK");
  // 追问（无 key → 规则追问）
  await page.click("#btn-iv-follow2");
  await sleep(600);
  const followup = await page.$eval("#iv-question", (el) => el.textContent.slice(0, 50));
  // 快进：跳过剩余题目
  for (let i = 0; i < 6; i++) {
    const done = await page.evaluate(() => document.querySelector("#btn-iv-next") === null);
    if (done) break;
    await page.click("#btn-iv-next").catch(() => {});
    await sleep(250);
    await page.click("#btn-iv-skip").catch(() => {});
    await sleep(500);
  }
  await sleep(500);
  await shot("06-summary");
  const summary = await page.$eval("#iv-summary", (el) => el.textContent.slice(0, 60)).catch(() => "NO SUMMARY");

  // 4. 复盘
  await page.evaluate(() => { location.hash = "#review"; });
  await sleep(700);
  await shot("07-review");
  const review = await page.$eval("#review-kpis", (el) => el.textContent.slice(0, 80)).catch(() => "NO REVIEW");

  console.log(JSON.stringify({
    boardKpi: kpi, questionCount: info, paperResult: result,
    feedback, followup, summary, review, errors
  }, null, 2));
  await browser.close();
})().catch((e) => { console.error("E2E FAILED:", e); process.exit(1); });
