/* ============================================================
   校招笔面试辅导工具 · 纯前端应用逻辑
   数据：window.JOB_DATA（岗位画像 + 内置题库）
   存储：localStorage（设置、练习记录），不上传任何服务器
   ============================================================ */
(function () {
  "use strict";

  var DATA = window.JOB_DATA || { positions: {}, questions: {}, groups: {}, meta: {} };
  var POS = DATA.positions;
  var QBANK = DATA.questions;
  var GROUPS = DATA.groups || {};

  var LS_SETTINGS = "jobprep.settings.v1";
  var LS_RECORDS = "jobprep.records.v1";

  /* ---------------- 基础工具 ---------------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function nowStr() {
    var d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function readJSON(key, def) {
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  }
  function writeJSON(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); return true; }
    catch (e) { toast("浏览器存储不可用，记录无法保存"); return false; }
  }
  function qText(item) {
    if (typeof item === "string") return item;
    if (item && typeof item === "object") return item.text || item.question || "";
    return "";
  }
  function isFollowupItem(item) { return !!(item && typeof item === "object" && item.isFollowup); }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  var toastTimer = null;
  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    requestAnimationFrame(function () { t.classList.add("is-show"); });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      t.classList.remove("is-show");
      setTimeout(function () { t.hidden = true; }, 280);
    }, 2400);
  }

  /* ---------------- 设置 ---------------- */
  var Settings = {
    data: readJSON(LS_SETTINGS, { key: "", model: "deepseek-chat" }),
    get: function () { return this.data; },
    hasKey: function () { return !!(this.data.key && this.data.key.indexOf("sk-") === 0); },
    save: function (key, model) {
      this.data = { key: (key || "").trim(), model: model || "deepseek-chat" };
      writeJSON(LS_SETTINGS, this.data);
    }
  };

  function refreshAIStrip() {
    var strip = $("#ai-strip"), txt = $("#ai-strip-text"), btn = $("#ai-strip-btn");
    if (Settings.hasKey()) {
      strip.classList.add("is-ok");
      txt.textContent = "AI 已接入（" + Settings.get().model + "）：可现场出题、深度点评与智能追问。";
      btn.textContent = "修改";
    } else {
      strip.classList.remove("is-ok");
      txt.textContent = "未配置 AI Key：内置 " + (DATA.meta.questionCount || 192) + " 道题 + 本地评估，全部功能可直接使用。";
      btn.textContent = "接入 AI";
    }
  }

  /* ---------------- AI 调用（可选） ---------------- */
  function aiChat(messages, temperature) {
    var s = Settings.get();
    if (!Settings.hasKey()) return Promise.reject(new Error("NO_KEY"));
    return fetch("https://api.deepseek.com/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + s.key },
      body: JSON.stringify({
        model: s.model || "deepseek-chat",
        messages: messages,
        temperature: temperature == null ? 0.7 : temperature
      })
    }).then(function (r) {
      if (!r.ok) return r.text().then(function (t) { throw new Error("接口返回 " + r.status + "：" + t.slice(0, 120)); });
      return r.json();
    }).then(function (j) {
      return j.choices[0].message.content;
    });
  }

  function parseJSON(text) {
    var t = String(text).trim();
    var m = t.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (m) t = m[1].trim();
    var s1 = t.indexOf("["), s2 = t.indexOf("{");
    var start = Math.min.apply(null, [s1, s2].filter(function (i) { return i >= 0; }));
    var end = Math.max(t.lastIndexOf("]"), t.lastIndexOf("}"));
    return JSON.parse(t.slice(start, end + 1));
  }

  /* ---------------- 路由 ---------------- */
  var VIEWS = ["home", "board", "written", "interview", "review"];
  var current = "home";
  function go(name) {
    if (VIEWS.indexOf(name) < 0) name = "home";
    current = name;
    VIEWS.forEach(function (v) {
      var el = $("#view-" + v);
      if (el) el.hidden = v !== name;
    });
    $$(".nav__menu a").forEach(function (a) {
      a.classList.toggle("is-active", a.getAttribute("data-nav") === name);
    });
    $("#nav-menu").classList.remove("is-open");
    if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (name === "board") renderBoard();
    if (name === "review") renderReview();
  }

  /* ---------------- 岗位下拉 ---------------- */
  function fillPositionSelects() {
    var names = Object.keys(POS);
    var html = "";
    Object.keys(GROUPS).forEach(function (g) {
      var items = GROUPS[g].filter(function (p) { return POS[p]; });
      if (!items.length) return;
      html += '<optgroup label="' + esc(g) + '">';
      items.forEach(function (p) { html += '<option value="' + esc(p) + '">' + esc(p) + '</option>'; });
      html += "</optgroup>";
    });
    var rest = names.filter(function (p) {
      return !Object.keys(GROUPS).some(function (g) { return GROUPS[g].indexOf(p) >= 0; });
    });
    if (rest.length) {
      html += '<optgroup label="其他">';
      rest.forEach(function (p) { html += '<option value="' + esc(p) + '">' + esc(p) + "</option>"; });
      html += "</optgroup>";
    }
    ["board-position", "written-position", "iv-position"].forEach(function (id) {
      var sel = $("#" + id);
      if (sel) { sel.innerHTML = html; }
    });
  }

  /* ---------------- 岗位看板 ---------------- */
  function renderBoard() {
    var p = $("#board-position").value || Object.keys(POS)[0];
    var body = POS[p];
    if (!body) return;
    var w = body.written, iv = body.interview;
    var pro = iv["专业面高频题"], beh = iv["行为面高频题"];

    $("#board-kpis").innerHTML = [
      kpi("考点数", w["考点分布"].length + " 个", ""),
      kpi("高频面试题", (pro.length + beh.length) + " 道", ""),
      kpi("最高频考点", w["考点分布"][0]["考点"], "", true),
      kpi("内置练习题", (QBANK[p] || []).length + " 道", "")
    ].join("");

    Charts.hBar($("#chart-topics"), w["考点分布"].map(function (t) {
      return { label: t["考点"], value: t["占比"] * 100 };
    }), { format: function (v) { return v.toFixed(0) + "%"; } });

    var typeItems = Object.keys(w["题型分布"]).map(function (k, i) {
      return { label: k, value: w["题型分布"][k] * 100, color: Charts.PALETTE[i % Charts.PALETTE.length] };
    });
    Charts.donut($("#chart-types"), typeItems, { centerText: typeItems.length + " 类" });
    $("#legend-types").innerHTML = typeItems.map(function (t) {
      return '<li><i style="background:' + t.color + '"></i>' + esc(t.label) + " " + Math.round(t.value) + "%</li>";
    }).join("");

    Charts.hBar($("#chart-pro"), pro.map(function (q) {
      return { label: q["问题"], value: q["频次"] };
    }), { labelW: 300, labelChars: 24, color: "#2E75B6", format: function (v) { return v + " 次"; } });

    Charts.hBar($("#chart-behavior"), beh.map(function (q) {
      return { label: q["问题"], value: q["频次"] };
    }), { labelW: 300, labelChars: 24, color: "#4472C4", format: function (v) { return v + " 次"; } });

    var kws = w["面经关键词"];
    $("#board-keywords").innerHTML = kws.map(function (k, i) {
      var size = 15 + ((k.length * 7 + i * 3) % 12);
      return '<span style="font-size:' + size + 'px" title="面经高频关键词">' + esc(k) + "</span>";
    }).join("");

    var rounds = iv["轮次重点"], order = ["初面", "复面", "终面"];
    $("#board-rounds").innerHTML = order.map(function (r, i) {
      return '<article class="round"><h4><span class="round__badge">' + r + "</span>" +
        (i === 0 ? "基础与动机" : i === 1 ? "专业深挖" : "素质与稳定性") + "</h4><p>" + esc(rounds[r]) + "</p></article>";
    }).join("");
  }

  function kpi(label, value, sub, accent) {
    var long = String(value).length > 8 ? " kpi--long" : "";
    return '<div class="kpi' + (accent ? " kpi--accent" : "") + long + '"><b>' + esc(value) + "</b><span>" + esc(label) +
      (sub ? " · " + esc(sub) : "") + "</span></div>";
  }

  /* ---------------- 笔试 ---------------- */
  var paper = null;

  function pickByType(questions, n) {
    var byType = {};
    questions.forEach(function (q) {
      (byType[q.type] = byType[q.type] || []).push(q);
    });
    var types = Object.keys(byType);
    var picked = [];
    // 每个题型先保证 1 题，再按比例补足
    var counts = {}, remain = n;
    types.forEach(function (t, i) {
      if (i === types.length - 1) { counts[t] = remain; }
      else {
        var c = Math.max(1, Math.round(n * byType[t].length / questions.length));
        counts[t] = Math.min(c, byType[t].length);
        remain -= counts[t];
      }
    });
    types.forEach(function (t) {
      picked = picked.concat(shuffle(byType[t]).slice(0, Math.max(0, counts[t])));
    });
    if (picked.length < n) {
      var rest = shuffle(questions.filter(function (q) { return picked.indexOf(q) < 0; }));
      picked = picked.concat(rest.slice(0, n - picked.length));
    }
    return shuffle(picked).slice(0, n);
  }

  function genPaper() {
    var p = $("#written-position").value;
    var n = parseInt($("#written-count").value, 10);
    var src = $("#written-source").value;
    var bank = QBANK[p] || [];

    if (src === "ai") {
      if (!Settings.hasKey()) { toast("AI 出题需要先在右上角设置里填入 DeepSeek Key"); openModal(); return; }
      var w = POS[p].written;
      var topicDesc = w["考点分布"].map(function (t) { return t["考点"] + "（占比" + Math.round(t["占比"] * 100) + "%）"; }).join("；");
      toast("AI 正在出题，约 10-30 秒…");
      aiChat([
        { role: "system", content: "你是资深校园招聘笔试命题专家，只输出 JSON 数组，不要任何多余文字。" },
        {
          role: "user", content: "岗位：" + p + "\n高频考点及占比：" + topicDesc +
            "\n题型配比：" + Object.keys(w["题型分布"]).map(function (k) { return k + Math.round(w["题型分布"][k] * 100) + "%"; }).join("、") +
            "\n请生成 " + n + " 道题，考点贴合占比。单选/多选给 4 个选项（answer 为字母），简答/计算/案例不给选项（options 为 []）。" +
            '输出 JSON 数组，每项 {"type":"单选|多选|简答|计算题|案例题","topic":"考点","question":"题干","options":[],"answer":"答案","explanation":"解析","difficulty":"易|中|难"}'
        }
      ], 0.8).then(function (text) {
        var qs = parseJSON(text);
        qs = qs.map(function (q) {
          return {
            type: q.type || "简答", topic: q.topic || "综合", question: q.question || "",
            options: q.options || [], answer: String(q.answer || ""),
            explanation: q.explanation || "", difficulty: q.difficulty || "中"
          };
        }).filter(function (q) { return q.question; });
        if (!qs.length) throw new Error("AI 返回内容无法解析");
        startPaper(p, qs.slice(0, n), "ai");
      }).catch(function (e) {
        toast("AI 出题失败：" + (e.message === "NO_KEY" ? "未配置 Key" : e.message));
      });
      return;
    }

    if (!bank.length) { toast("该岗位暂无内置题目"); return; }
    startPaper(p, pickByType(bank, n), "bank");
  }

  function startPaper(p, questions, source) {
    paper = { position: p, questions: questions, answers: questions.map(function () { return null; }), submitted: false, source: source };
    $("#written-empty").hidden = true;
    var old = $(".result-card");
    if (old) old.remove();
    var form = $("#paper");
    form.hidden = false;
    form.innerHTML = questions.map(function (q, i) {
      var typeTag = '<span class="tag">' + esc(q.type) + "</span>";
      var diffCls = q.difficulty === "易" ? "tag--easy" : q.difficulty === "难" ? "tag--hard" : "tag--mid";
      var body;
      if (q.type === "单选" || q.type === "多选") {
        body = '<div class="opts" data-i="' + i + '">' + q.options.map(function (o, oi) {
          var letter = String.fromCharCode(65 + oi);
          return '<label class="opt"><input type="' + (q.type === "单选" ? "radio" : "checkbox") +
            '" name="q' + i + '" value="' + letter + '" data-i="' + i + '" data-letter="' + letter + '"><span>' + esc(o) + "</span></label>";
        }).join("") + "</div>";
      } else {
        body = '<textarea class="q__text" data-i="' + i + '" placeholder="写下你的思路与要点；计算题请写出关键步骤和结果。"></textarea>';
      }
      return '<article class="q" data-i="' + i + '">' +
        '<div class="q__head"><span class="q__no">第 ' + (i + 1) + " 题</span>" + typeTag +
        '<span class="tag tag--soft">' + esc(q.topic) + '</span><span class="tag ' + diffCls + '">' + esc(q.difficulty) + "</span></div>" +
        '<div class="q__title">' + esc(q.question) + "</div>" + body +
        '<div class="q__result" hidden></div></article>';
    }).join("") +
      '<div class="paper-bar"><span class="paper-bar__meta">共 ' + questions.length + " 题 · 作答后点击右侧交卷</span>" +
      '<button type="button" class="btn btn--primary" id="btn-submit-paper">交卷并评分</button></div>';

    form.onsubmit = function (e) { e.preventDefault(); };
    form.addEventListener("change", function (e) {
      var t = e.target;
      if (t.matches("input[type=radio],input[type=checkbox]")) {
        var idx = +t.getAttribute("data-i");
        var box = t.closest(".opts");
        if (t.type === "radio") {
          $$("label.opt", box).forEach(function (l) { l.classList.remove("is-picked"); });
          t.closest(".opt").classList.add("is-picked");
          paper.answers[idx] = [t.value];
        } else {
          t.closest(".opt").classList.toggle("is-picked", t.checked);
          paper.answers[idx] = $$("input:checked", box).map(function (x) { return x.value; });
        }
      }
      if (t.matches("textarea.q__text")) {
        paper.answers[+t.getAttribute("data-i")] = t.value;
      }
    });
    form.addEventListener("input", function (e) {
      if (e.target.matches("textarea.q__text")) paper.answers[+e.target.getAttribute("data-i")] = e.target.value;
    });
    $("#btn-submit-paper").addEventListener("click", function () {
      if (paper.submitted) return;
      submitPaper();
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
    toast("试卷已生成：" + questions.length + " 题");
  }

  function letters(s) {
    return String(s || "").toUpperCase().replace(/[^A-D]/g, "").split("").sort().join("");
  }

  /* 主观题本地估分：要点关键词覆盖 + 长度 + 结构 */
  function localScore(reference, answer) {
    var a = String(answer || "").replace(/\s+/g, "");
    if (a.length < 8) return 0;
    var tokens = String(reference || "").split(/[，。；、：:,.!?（）()【】\s\/]+/).filter(function (s) { return s.length >= 2; });
    var hit = 0;
    tokens.forEach(function (t) {
      var key = t.length > 6 ? t.slice(0, 6) : t;
      if (a.indexOf(key) >= 0) hit++;
    });
    var cover = tokens.length ? hit / tokens.length : 0;
    var lenScore = Math.min(1, a.length / 120);
    var score = 25 + cover * 55 + lenScore * 20;
    return Math.max(0, Math.min(98, Math.round(score)));
  }

  function submitPaper() {
    var qs = paper.questions, topicStats = {}, results = [];
    var correct = 0;

    qs.forEach(function (q, i) {
      var ans = paper.answers[i];
      var userText = Array.isArray(ans) ? ans.join("") : (ans || "");
      var ok, score, rightText = q.answer, verdict;
      if (q.type === "单选" || q.type === "多选") {
        ok = letters(userText) === letters(q.answer) && letters(userText) !== "";
        score = ok ? 100 : 0;
        rightText = q.answer;
        verdict = ok ? "回答正确" : "回答错误";
      } else {
        score = localScore(q.answer, userText);
        ok = score >= 60;
        verdict = "本地估分 " + score + " 分（按参考答案要点覆盖估算，仅供参考）";
      }

      var a = topicStats[q.topic] || [0, 0];
      a[0] += ok ? 1 : 0; a[1] += 1;
      topicStats[q.topic] = a;
      if (ok) correct++;

      results.push({ type: q.type, topic: q.topic, ok: ok, score: score });

      var card = $('.q[data-i="' + i + '"]');
      $$("input,textarea", card).forEach(function (x) { x.disabled = true; });
      var res = $(".q__result", card);
      res.hidden = false;
      var cls = ok ? "verdict--ok" : "verdict--bad";
      res.innerHTML = '<p><span class="verdict ' + cls + '">' + (ok ? "✅ " : "❌ ") + esc(verdict) + "</span></p>" +
        "<p><b>参考答案：</b>" + esc(rightText || "—") + "</p>" +
        "<p><b>解析：</b>" + esc(q.explanation || "—") + "</p>";

      if (q.type === "单选" || q.type === "多选") {
        $$("label.opt", card).forEach(function (l) {
          var input = $("input", l);
          var letter = input.value;
          var inAnswer = letters(q.answer).indexOf(letter) >= 0;
          var picked = input.checked;
          if (inAnswer) l.classList.add("is-right");
          if (picked && !inAnswer) l.classList.add("is-wrong");
        });
      }
    });

    paper.submitted = true;
    var acc = Math.round(correct / qs.length * 100);
    var weak = Object.keys(topicStats).filter(function (t) { return topicStats[t][0] < topicStats[t][1]; });

    var summary = document.createElement("div");
    summary.className = "result-card";
    summary.innerHTML = '<div style="font-size:15px;font-weight:800">📊 本卷成绩</div>' +
      '<div class="result-card__grid">' +
      "<div><b>" + acc + '%</b><span>正确率</span></div>' +
      "<div><b>" + correct + " / " + qs.length + "</b><span>答对题数</span></div>" +
      "<div><b>" + weak.length + "</b><span>薄弱考点</span></div>" +
      "<div><b>" + esc(paper.position) + "</b><span>目标岗位</span></div></div>" +
      (weak.length ? '<div class="weak-list"><span>建议加练：' + weak.map(esc).join("、") + "</span></div>" : '<div class="weak-list"><span>本卷全部答对，保持手感！</span></div>') +
      '<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">' +
      '<button class="btn btn--white btn--sm" id="btn-again">再练一套</button>' +
      '<button class="btn btn--ghost btn--sm" data-nav="review">去复盘看趋势</button></div>';

    var form = $("#paper");
    form.parentNode.insertBefore(summary, form);
    $("#btn-again").addEventListener("click", function () { genPaper(); summary.remove(); });
    $$("[data-nav]", summary).forEach(function (b) {
      b.addEventListener("click", function () { go(b.getAttribute("data-nav")); });
    });

    addRecord({
      kind: "written", position: paper.position, time: nowStr(),
      total: qs.length, correct: correct, accuracy: acc,
      topicStats: topicStats, source: paper.source
    });
    $("#btn-submit-paper").disabled = true;
    $("#btn-submit-paper").textContent = "已交卷";
    summary.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  /* ---------------- 记录存储 ---------------- */
  function addRecord(r) {
    var list = readJSON(LS_RECORDS, []);
    r.id = "r" + Date.now() + Math.random().toString(36).slice(2, 6);
    list.push(r);
    writeJSON(LS_RECORDS, list);
    return r;
  }
  function records() { return readJSON(LS_RECORDS, []); }

  /* ---------------- 面试 ---------------- */
  var iv = null;
  var recog = null, recognizing = false;

  function buildQueue(p, round) {
    var bank = POS[p].interview;
    var prof = bank["专业面高频题"].map(function (q) { return q["问题"]; });
    var beh = bank["行为面高频题"].map(function (q) { return q["问题"]; });
    var queue;
    if (round === "初面") queue = beh.slice(0, 1).concat(prof.slice(0, 3));
    else if (round === "复面") queue = prof.slice(0, 3).concat(beh.slice(0, 1));
    else queue = beh.slice(0, 3).concat(prof.slice(0, 1));
    while (queue.length < 4 && prof.length > queue.length) queue.push(prof[queue.length]);
    return queue.slice(0, 5);
  }

  function startInterview() {
    var p = $("#iv-position").value;
    var round = $("#iv-round").value;
    var engine = $("#iv-engine").value;
    if (engine === "ai" && !Settings.hasKey()) { toast("AI 评估需要先配置 Key"); openModal(); return; }
    iv = { position: p, round: round, engine: engine, queue: buildQueue(p, round), idx: 0, transcript: [], followups: 0 };
    $("#iv-setup").hidden = true;
    $("#iv-empty").hidden = true;
    $("#iv-summary").hidden = true;
    $("#iv-room").hidden = false;
    renderQuestion();
  }

  function renderQuestion() {
    var item = iv.queue[iv.idx];
    var q = qText(item);
    $("#iv-question").textContent = q;
    $("#iv-round-tag").textContent = iv.round + (isFollowupItem(item) ? " · 追问" : "");
    $("#iv-progress-text").textContent = "第 " + (iv.idx + 1) + " / " + iv.queue.length + " 题";
    $("#iv-progress-fill").style.width = ((iv.idx) / iv.queue.length * 100) + "%";
    $("#iv-answer").value = "";
    updateCounter();
    $("#iv-feedback").hidden = true;
    $("#iv-feedback").innerHTML = "";
    $("#btn-iv-submit").disabled = false;
    $("#btn-iv-submit").textContent = "提交回答，查看评估";
    $("#btn-iv-follow").disabled = false;
  }

  function updateCounter() {
    $("#iv-count").textContent = ($("#iv-answer").value || "").replace(/\s/g, "").length;
  }

  /* 本地评估：长度 + 结构词 + 岗位关键词 + 量化数据 */
  function localEval(question, answer) {
    var a = String(answer || "").replace(/\s+/g, "");
    var len = a.length;
    var structWords = ["首先", "其次", "然后", "最后", "因为", "所以", "例如", "比如", "当时", "结果", "总结", "复盘", "目标", "负责"];
    var structHits = structWords.filter(function (w) { return a.indexOf(w) >= 0; });
    var kws = (POS[iv.position].written["面经关键词"] || []);
    var kwHits = kws.filter(function (k) { return a.indexOf(k) >= 0 || (k.length >= 4 && a.indexOf(k.slice(0, 2)) >= 0); });
    var hasNum = /\d/.test(a);

    var score = 0;
    score += Math.min(36, len / 200 * 36);
    score += Math.min(24, structHits.length * 6);
    score += Math.min(28, kwHits.length * 9);
    score += hasNum ? 12 : 0;
    score = Math.round(Math.max(0, Math.min(96, score)));

    var logic = len < 40
      ? "回答偏短，缺少展开。建议用 STAR 结构：先说情境与任务，再说你具体做了什么，最后给结果。"
      : (structHits.length >= 2
        ? "回答有基本的层次（出现「" + structHits.slice(0, 3).join("、") + "」等衔接词），逻辑可读。"
        : "内容较完整，但层次不明显。建议分三段：背景 → 你的动作 → 结果与复盘。");

    var coverage = kwHits.length
      ? "覆盖了该岗位的关键点：" + kwHits.slice(0, 4).join("、") + "。"
      : "没有出现该岗位的高频关键词（如 " + kws.slice(0, 3).join("、") + "），面试官可能认为专业度不足。";
    coverage += hasNum ? "回答中包含量化信息，是加分项。" : "缺少具体数字或结果，建议补一句量化结果（提升多少 / 覆盖多少人 / 节省多少时间）。";

    var sug = [];
    if (len < 80) sug.push("把回答扩展到 150-250 字，补一个具体例子");
    if (!hasNum) sug.push("加入一个可量化的结果");
    if (kwHits.length < 3) sug.push("结合岗位术语（" + kws.slice(0, 2).join("、") + "）说明你的做法");
    sug.push("结尾用一句话总结你的收获或判断");

    return {
      score: score,
      logic: logic,
      coverage: coverage,
      suggestions: sug.join("；") + "。",
      key_points: kws.slice(0, 4),
      engine: "local"
    };
  }

  function evaluate(question, answer) {
    var engine = iv.engine;
    var useAI = engine === "ai" || (engine === "auto" && Settings.hasKey());
    if (!useAI) {
      return new Promise(function (resolve) { setTimeout(function () { resolve(localEval(question, answer)); }, 260); });
    }
    var prompt = "你是" + iv.position + "岗位的资深面试官，正在进行" + iv.round + "模拟面试。\n" +
      "面试问题：" + question + "\n候选人回答：" + answer + "\n" +
      "请结合该岗位考察特征评估回答，只输出 JSON：\n" +
      '{"score":整数0-100,"logic":"对逻辑框架的评价，2-3句","coverage":"关键信息覆盖情况：覆盖了什么、遗漏了什么，2-3句","suggestions":"具体可落地的优化建议，3句以内","key_points":["高分回答必须覆盖的3-5个要点"]}';
    return aiChat([{ role: "user", content: prompt }], 0.4).then(function (text) {
      var r = parseJSON(text);
      return {
        score: Math.max(0, Math.min(100, parseInt(r.score, 10) || 0)),
        logic: r.logic || "", coverage: r.coverage || "", suggestions: r.suggestions || "",
        key_points: r.key_points || [], engine: "ai"
      };
    }).catch(function (e) {
      toast("AI 评估失败，已改用本地评估：" + e.message);
      var r = localEval(question, answer);
      r.engine = "local";
      return r;
    });
  }

  function showFeedback(ev, answer) {
    var box = $("#iv-feedback");
    box.hidden = false;
    var cls = ev.score >= 80 ? "verdict--ok" : ev.score >= 60 ? "" : "verdict--bad";
    box.innerHTML = '<div class="feedback">' +
      '<div class="score-row"><div class="score-ring" style="--p:' + ev.score + '"><div><b>' + ev.score + "</b><span>得分</span></div></div>" +
      '<div style="flex:1;min-width:220px"><h3 style="margin-bottom:2px">' + (ev.score >= 80 ? "表现不错" : ev.score >= 60 ? "基本达标，可再打磨" : "需要重点改进") + "</h3>" +
      '<p class="engine-tag">评估引擎：' + (ev.engine === "ai" ? "AI 深度评估（" + Settings.get().model + "）" : "本地规则评估（离线）") + "</p></div></div>" +
      '<div class="fb-block"><h4>逻辑框架</h4><p>' + esc(ev.logic) + "</p></div>" +
      '<div class="fb-block"><h4>关键信息覆盖</h4><p>' + esc(ev.coverage) + "</p></div>" +
      '<div class="fb-block"><h4>优化建议</h4><p>' + esc(ev.suggestions) + "</p></div>" +
      (Array.isArray(ev.key_points) && ev.key_points.length ? '<div class="fb-block"><h4>高分要点</h4><div class="kp">' +
        ev.key_points.map(function (k) { return "<span>" + esc(k) + "</span>"; }).join("") + "</div></div>" : "") +
      '<div class="iv__actions"><button class="btn btn--primary" id="btn-iv-next">' +
      (iv.idx + 1 >= iv.queue.length ? "查看本轮总结" : "下一题") + "</button>" +
      '<button class="btn btn--ghost-blue" id="btn-iv-follow2">🔁 让面试官就这题追问</button></div></div>';

    $("#btn-iv-next").addEventListener("click", function () {
      iv.idx++;
      if (iv.idx >= iv.queue.length) finishInterview();
      else renderQuestion();
    });
    $("#btn-iv-follow2").addEventListener("click", askFollowup);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function submitAnswer(skip) {
    var answer = skip ? "（跳过）" : $("#iv-answer").value.trim();
    if (!skip && answer.length < 2) { toast("先写点内容，或点「跳过这题」"); return; }
    var q = qText(iv.queue[iv.idx]);
    $("#btn-iv-submit").disabled = true;
    $("#btn-iv-submit").textContent = "评估中…";
    $("#btn-iv-follow").disabled = true;

    evaluate(q, answer).then(function (ev) {
      iv.transcript.push({ question: q, answer: answer, evaluation: ev });
      addRecord({
        kind: "interview", position: iv.position, round: iv.round, time: nowStr(),
        question: q, answer: answer, score: ev.score, engine: ev.engine
      });
      showFeedback(ev, answer);
    });
  }

  function askFollowup() {
    var q = qText(iv.queue[iv.idx]);
    var answer = $("#iv-answer").value.trim();
    if (!answer) { toast("先作答，再让面试官追问"); return; }
    if (!Settings.hasKey()) {
      // 无 Key：用规则化追问，仍然是针对回答的真实追问
      var hasNum = /\d/.test(answer);
      var follow = hasNum
        ? "你提到的结果不错。如果当时时间或资源减少一半，你会优先保留哪一步，为什么？"
        : "能举一个更具体的例子吗？当时你的角色是什么，最后的结果用什么指标衡量？";
      insertFollowup(follow);
      return;
    }
    toast("面试官正在想追问…");
    aiChat([{
      role: "user",
      content: "你是" + iv.position + "岗位面试官。候选人刚回答了：「" + q + "」，回答：「" + answer +
        "」。请针对回答中最值得深挖的点提一个追问，只输出问题本身。"
    }], 0.8).then(function (text) {
      insertFollowup(text.trim().replace(/^["「]|["」]$/g, ""));
    }).catch(function (e) { toast("追问失败：" + e.message); });
  }

  function insertFollowup(text) {
    if (!text) return;
    iv.queue.splice(iv.idx + 1, 0, { text: text, isFollowup: true });
    // 先把当前题记为已回答（未评估分数）
    var cur = qText(iv.queue[iv.idx]);
    var last = iv.transcript[iv.transcript.length - 1];
    if (!last || last.question !== cur) {
      iv.transcript.push({ question: cur, answer: $("#iv-answer").value.trim(), evaluation: { score: null, engine: "followup" } });
    }
    iv.followups++;
    iv.idx++;
    renderQuestion();
    toast("已加入追问");
  }

  function finishInterview() {
    $("#iv-room").hidden = true;
    var scored = iv.transcript.filter(function (t) { return t.evaluation && typeof t.evaluation.score === "number"; });
    var avg = scored.length ? Math.round(scored.reduce(function (s, t) { return s + t.evaluation.score; }, 0) / scored.length) : 0;
    var weak = iv.transcript.filter(function (t) { return t.evaluation.score != null && t.evaluation.score < 60; });

    var html = '<div class="summary-head"><h3>🎉 本轮模拟面试完成</h3><p>' + esc(iv.position) + " · " + esc(iv.round) +
      " · 共 " + iv.transcript.length + " 题</p>" +
      '<div class="summary-grid"><div><b>' + avg + '</b><span>平均得分</span></div>' +
      "<div><b>" + scored.length + '</b><span>已评估题数</span></div>' +
      "<div><b>" + weak.length + "</b><span>失分点</span></div></div></div>";

    html += '<div class="panel"><div class="panel__head"><h3>失分点复盘</h3><span class="hint">低于 60 分的题目</span></div>' +
      (weak.length ? weak.map(function (t) {
        var ev = t.evaluation;
        return '<div class="review-item" style="margin-bottom:10px"><h4>❓ ' + esc(t.question) + "</h4>" +
          '<div class="ans">' + esc(t.answer || "（未作答）") + "</div>" +
          "<p style='margin-top:8px'><b>逻辑：</b>" + esc(ev.logic || "—") + "</p>" +
          "<p><b>覆盖：</b>" + esc(ev.coverage || "—") + "</p>" +
          "<p><b>建议：</b>" + esc(ev.suggestions || "—") + "</p></div>";
      }).join("") : '<p class="tiny">没有低于 60 分的题目，继续保持。</p>') + "</div>";

    html += '<div class="panel"><div class="panel__head"><h3>完整回放</h3><span class="hint">逐题查看问答与点评</span></div>' +
      iv.transcript.map(function (t, i) {
        return '<div class="review-item" style="margin-bottom:10px"><h4>第 ' + (i + 1) + " 题 · " +
          (t.evaluation.score == null ? "未评分" : t.evaluation.score + " 分") + "</h4>" +
          "<p><b>面试官：</b>" + esc(t.question) + "</p>" +
          '<div class="ans"><b>你：</b> ' + esc(t.answer || "（跳过）") + "</div>" +
          (t.evaluation.suggestions ? "<p style='margin-top:6px' class='tiny'>" + esc(t.evaluation.suggestions) + "</p>" : "") +
          "</div>";
      }).join("") + "</div>";

    html += '<div class="iv__actions"><button class="btn btn--primary" id="btn-iv-again">再来一轮</button>' +
      '<button class="btn btn--ghost-blue" data-nav="review">去复盘看记录</button>' +
      '<button class="btn btn--ghost-blue" id="btn-iv-export">导出本轮报告</button></div>';

    var box = $("#iv-summary");
    box.hidden = false;
    box.innerHTML = html;
    $("#btn-iv-again").addEventListener("click", function () {
      box.hidden = true;
      $("#iv-setup").hidden = false;
      $("#iv-room").hidden = true;
      $("#iv-empty").hidden = false;
    });
    $$("[data-nav]", box).forEach(function (b) {
      b.addEventListener("click", function () { go(b.getAttribute("data-nav")); });
    });
    $("#btn-iv-export").addEventListener("click", exportInterview);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------------- 语音 ---------------- */
  function speak(text) {
    if (!("speechSynthesis" in window)) { toast("当前浏览器不支持朗读，建议用 Chrome / Edge"); return; }
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-CN";
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }

  function initRecognition() {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      $("#iv-mic-hint").textContent = "当前浏览器不支持语音识别，请直接打字（Chrome / Edge 可用）";
      return null;
    }
    var r = new SR();
    r.lang = "zh-CN";
    r.continuous = true;
    r.interimResults = true;
    r.onresult = function (e) {
      var finalText = "", interim = "";
      for (var i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      if (finalText) {
        var ta = $("#iv-answer");
        ta.value = (ta.value ? ta.value.replace(/\s*$/, "") : "") + finalText;
        updateCounter();
      }
      $("#iv-mic-hint").textContent = interim ? "识别中：" + interim : "正在聆听…说完再点一次停止";
    };
    r.onerror = function (e) {
      recognizing = false;
      $("#btn-iv-mic").classList.remove("is-rec");
      $("#iv-mic-label").textContent = "按下说话";
      var map = { "not-allowed": "麦克风权限被拒绝，请在浏览器地址栏允许麦克风", "no-speech": "没有听到声音，请靠近麦克风", "network": "语音识别需要联网" };
      toast(map[e.error] || ("语音识别出错：" + e.error));
    };
    r.onend = function () {
      recognizing = false;
      $("#btn-iv-mic").classList.remove("is-rec");
      $("#iv-mic-label").textContent = "按下说话";
      $("#iv-mic-hint").textContent = "浏览器语音识别，音频不上传（Chrome / Edge 最佳）";
    };
    return r;
  }

  function toggleMic() {
    if (!recog) { recog = initRecognition(); if (!recog) return; }
    if (recognizing) { recog.stop(); return; }
    try {
      recog.start();
      recognizing = true;
      $("#btn-iv-mic").classList.add("is-rec");
      $("#iv-mic-label").textContent = "正在聆听…点击结束";
    } catch (e) { toast("无法启动麦克风：" + e.message); }
  }

  /* ---------------- 复盘 ---------------- */
  function renderReview() {
    var list = records();
    var hasAny = list.length > 0;
    $("#review-empty").hidden = hasAny;
    $("#review-content").hidden = !hasAny;
    if (!hasAny) return;

    var written = list.filter(function (r) { return r.kind === "written"; });
    var interviews = list.filter(function (r) { return r.kind === "interview"; });
    var avgAcc = written.length ? Math.round(written.reduce(function (s, r) { return s + r.accuracy; }, 0) / written.length) : 0;
    var scores = interviews.filter(function (r) { return typeof r.score === "number"; });
    var avgIv = scores.length ? Math.round(scores.reduce(function (s, r) { return s + r.score; }, 0) / scores.length) : 0;

    $("#review-kpis").innerHTML = [
      kpi("笔试模拟", written.length + " 次", ""),
      kpi("平均正确率", avgAcc + "%", "", true),
      kpi("面试练习", interviews.length + " 题", ""),
      kpi("面试平均分", scores.length ? avgIv + " 分" : "—", "")
    ].join("");

    Charts.line($("#chart-trend"), written.map(function (r, i) {
      return { label: "第" + (i + 1) + "次", value: r.accuracy };
    }));

    var agg = {};
    written.forEach(function (r) {
      Object.keys(r.topicStats || {}).forEach(function (t) {
        var a = agg[t] || [0, 0];
        a[0] += r.topicStats[t][0]; a[1] += r.topicStats[t][1];
        agg[t] = a;
      });
    });
    var mastery = Object.keys(agg).map(function (t) {
      return { label: t, value: Math.round(agg[t][0] / agg[t][1] * 100) };
    }).sort(function (a, b) { return b.value - a.value; }).slice(0, 7);
    Charts.radar($("#chart-mastery"), mastery);

    var rows = list.slice().reverse().slice(0, 30);
    $("#history-table").innerHTML = "<thead><tr>" +
      ["时间", "类型", "岗位", "结果"].map(function (h) { return "<th>" + h + "</th>"; }).join("") +
      "</tr></thead><tbody>" + rows.map(function (r) {
        var kind = r.kind === "written" ? "笔试" : "面试·" + r.round;
        var detail = r.kind === "written"
          ? r.accuracy + "%（" + r.correct + "/" + r.total + "）"
          : (r.score == null ? "未评分" : r.score + " 分");
        return "<tr><td>" + esc(r.time) + "</td><td>" + esc(kind) + "</td><td>" + esc(r.position) +
          "</td><td class='num'>" + esc(detail) + "</td></tr>";
      }).join("") + "</tbody>";
  }

  function exportMarkdown() {
    var list = records();
    var written = list.filter(function (r) { return r.kind === "written"; });
    var interviews = list.filter(function (r) { return r.kind === "interview"; });
    var md = "# 备考复盘报告\n\n生成时间：" + nowStr() + "\n\n## 概览\n\n";
    md += "- 笔试模拟：" + written.length + " 次\n";
    md += "- 面试练习：" + interviews.length + " 题\n";
    if (written.length) {
      md += "- 平均正确率：" + Math.round(written.reduce(function (s, r) { return s + r.accuracy; }, 0) / written.length) + "%\n";
    }
    md += "\n## 笔试记录\n\n| 时间 | 岗位 | 正确率 | 得分 |\n|---|---|---|---|\n";
    written.forEach(function (r) {
      md += "| " + r.time + " | " + r.position + " | " + r.accuracy + "% | " + r.correct + "/" + r.total + " |\n";
    });
    md += "\n## 面试记录\n\n| 时间 | 岗位 | 轮次 | 得分 | 问题 |\n|---|---|---|---|---|\n";
    interviews.forEach(function (r) {
      md += "| " + r.time + " | " + r.position + " | " + r.round + " | " + (r.score == null ? "—" : r.score) +
        " | " + String(r.question || "").replace(/\|/g, "／").slice(0, 40) + " |\n";
    });
    md += "\n> 由「大学生实习&校招笔面试数据分析辅导工具」生成，数据仅存于本机浏览器。\n";
    download("备考复盘-" + nowStr().replace(/[: ]/g, "-") + ".md", md, "text/markdown");
    toast("报告已导出");
  }

  function exportInterview() {
    if (!iv) return;
    var scored = iv.transcript.filter(function (t) { return t.evaluation && typeof t.evaluation.score === "number"; });
    var avg = scored.length ? Math.round(scored.reduce(function (s, t) { return s + t.evaluation.score; }, 0) / scored.length) : 0;
    var md = "# 模拟面试报告\n\n- 岗位：" + iv.position + "\n- 轮次：" + iv.round + "\n- 时间：" + nowStr() +
      "\n- 平均得分：" + avg + " 分\n\n";
    iv.transcript.forEach(function (t, i) {
      md += "## 第 " + (i + 1) + " 题（" + (t.evaluation.score == null ? "未评分" : t.evaluation.score + " 分") + "）\n\n";
      md += "**面试官：** " + t.question + "\n\n**我的回答：** " + (t.answer || "（跳过）") + "\n\n";
      if (t.evaluation.logic) md += "- 逻辑： " + t.evaluation.logic + "\n";
      if (t.evaluation.coverage) md += "- 覆盖： " + t.evaluation.coverage + "\n";
      if (t.evaluation.suggestions) md += "- 建议： " + t.evaluation.suggestions + "\n";
      md += "\n";
    });
    download("模拟面试-" + nowStr().replace(/[: ]/g, "-") + ".md", md, "text/markdown");
    toast("本轮报告已导出");
  }

  function download(filename, text, mime) {
    var blob = new Blob([text], { type: (mime || "text/plain") + ";charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }

  /* ---------------- 弹层 ---------------- */
  function openModal() {
    var s = Settings.get();
    $("#set-key").value = s.key || "";
    $("#set-model").value = s.model || "deepseek-chat";
    $("#key-status").textContent = Settings.hasKey()
      ? "当前已保存 Key（仅本机）。如需更换，直接覆盖后保存。"
      : "未保存 Key。不填也不影响题库练习与本地评估。";
    $("#modal").hidden = false;
  }
  function closeModal() { $("#modal").hidden = true; }

  /* ---------------- 事件绑定 ---------------- */
  function bind() {
    document.addEventListener("click", function (e) {
      var nav = e.target.closest("[data-nav]");
      if (nav) { e.preventDefault(); go(nav.getAttribute("data-nav")); return; }
      if (e.target.closest("[data-close]")) closeModal();
    });

    $("#btn-settings").addEventListener("click", openModal);
    $("#ai-strip-btn").addEventListener("click", openModal);
    $("#btn-save-key").addEventListener("click", function () {
      var k = $("#set-key").value.trim();
      if (k && k.indexOf("sk-") !== 0) { toast("Key 一般以 sk- 开头，请检查"); }
      Settings.save(k, $("#set-model").value);
      refreshAIStrip();
      closeModal();
      toast(k ? "已保存 Key，AI 功能已解锁" : "已清除 Key");
    });
    $("#btn-clear-key").addEventListener("click", function () {
      Settings.save("", $("#set-model").value);
      $("#set-key").value = "";
      refreshAIStrip();
      $("#key-status").textContent = "已清除 Key。";
    });

    $("#nav-toggle").addEventListener("click", function () {
      var m = $("#nav-menu");
      m.classList.toggle("is-open");
      this.setAttribute("aria-expanded", m.classList.contains("is-open") ? "true" : "false");
    });

    $("#board-position").addEventListener("change", renderBoard);
    $("#btn-paper").addEventListener("click", genPaper);

    $("#btn-iv-start").addEventListener("click", startInterview);
    $("#btn-iv-submit").addEventListener("click", function () { submitAnswer(false); });
    $("#btn-iv-skip").addEventListener("click", function () { submitAnswer(true); });
    $("#btn-iv-follow").addEventListener("click", askFollowup);
    $("#btn-iv-quit").addEventListener("click", finishInterview);
    $("#btn-iv-speak").addEventListener("click", function () { speak($("#iv-question").textContent); });
    $("#btn-iv-stop").addEventListener("click", function () { window.speechSynthesis.cancel(); });
    $("#btn-iv-mic").addEventListener("click", toggleMic);
    $("#iv-answer").addEventListener("input", updateCounter);

    $("#btn-export").addEventListener("click", exportMarkdown);
    $("#btn-clear").addEventListener("click", function () {
      if (!confirm("确定清空全部练习记录？该操作不可恢复。")) return;
      localStorage.removeItem(LS_RECORDS);
      renderReview();
      toast("记录已清空");
    });

    window.addEventListener("hashchange", function () {
      go((location.hash || "#home").slice(1));
    });
  }

  /* ---------------- 初始化 ---------------- */
  function init() {
    fillPositionSelects();
    refreshAIStrip();
    bind();
    if (DATA.meta && DATA.meta.questionCount) {
      $("#home-q-count").textContent = DATA.meta.questionCount;
      $("#stat-q").textContent = DATA.meta.questionCount;
    }
    // 默认岗位：优先上次选择
    var last = readJSON("jobprep.lastPos", null);
    if (last && POS[last]) {
      ["board-position", "written-position", "iv-position"].forEach(function (id) {
        $("#" + id).value = last;
      });
    }
    ["board-position", "written-position", "iv-position"].forEach(function (id) {
      $("#" + id).addEventListener("change", function () {
        writeJSON("jobprep.lastPos", this.value);
      });
    });
    go((location.hash || "#home").slice(1));
    renderBoard();

    // PWA：仅在 https / localhost 下注册（file:// 打开会失败）
    if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol)) {
      navigator.serviceWorker.register("./service-worker.js").catch(function () { /* 离线能力可选 */ });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
