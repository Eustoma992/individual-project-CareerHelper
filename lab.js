/* ============================================================
   模型实验室：梯度下降 / 闭式解 / 过拟合诊断
   纯前端实现，零依赖——所有计算（含矩阵求解）都在浏览器里跑
   ============================================================ */
(function (global) {
  "use strict";

  /* ---------------- 基础工具 ---------------- */
  function $(s) { return document.querySelector(s); }

  // 固定种子随机数，保证每次刷新数据一致（教学演示需要可复现）
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6d2b79f5) >>> 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  // 正态噪声（Box-Muller）
  function gauss(r) {
    var u = Math.max(r(), 1e-9), v = r();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  // 高斯消元解 Ax=b（带部分主元），用于最小二乘的法方程
  function solve(A, b) {
    var n = A.length, i, j, k;
    var M = A.map(function (row, idx) { return row.slice().concat([b[idx]]); });
    for (i = 0; i < n; i++) {
      var p = i;
      for (k = i + 1; k < n; k++) if (Math.abs(M[k][i]) > Math.abs(M[p][i])) p = k;
      var tmp = M[i]; M[i] = M[p]; M[p] = tmp;
      var pivot = M[i][i];
      if (Math.abs(pivot) < 1e-12) continue;
      for (k = i; k <= n; k++) M[i][k] /= pivot;
      for (k = 0; k < n; k++) {
        if (k === i) continue;
        var f = M[k][i];
        if (!f) continue;
        for (j = i; j <= n; j++) M[k][j] -= f * M[i][j];
      }
    }
    return M.map(function (row) { return row[n]; });
  }

  // 多项式最小二乘：返回系数（从低次到高次）
  function polyfit(xs, ys, deg) {
    var d = deg + 1, i, j, k;
    var A = [], b = [];
    for (i = 0; i < d; i++) {
      A.push(new Array(d).fill(0));
      b.push(0);
    }
    for (k = 0; k < xs.length; k++) {
      var pow = [1];
      for (j = 1; j < 2 * d; j++) pow.push(pow[j - 1] * xs[k]);
      for (i = 0; i < d; i++) {
        b[i] += pow[i] * ys[k];
        for (j = 0; j < d; j++) A[i][j] += pow[i + j];
      }
    }
    // 极小岭项，避免高阶时法方程病态导致求解失败
    for (i = 0; i < d; i++) A[i][i] += 1e-10;
    return solve(A, b);
  }

  function evalPoly(c, x) {
    var y = 0;
    for (var i = c.length - 1; i >= 0; i--) y = y * x + c[i];
    return y;
  }

  function mse(xs, ys, fn) {
    var s = 0;
    for (var i = 0; i < xs.length; i++) {
      var e = fn(xs[i]) - ys[i];
      s += e * e;
    }
    return s / xs.length;
  }

  /* ---------------- SVG 绘图工具 ---------------- */
  function svgWrap(W, H, body) {
    return '<svg viewBox="0 0 ' + W + " " + H + '" role="img" preserveAspectRatio="xMidYMid meet">' + body + "</svg>";
  }

  // 坐标映射
  function scale(d0, d1, r0, r1) {
    return function (v) { return r0 + ((v - d0) / (d1 - d0)) * (r1 - r0); };
  }

  function axes(W, H, pad, xr, yr, xLabel, yLabel, ticks) {
    var xs = scale(xr[0], xr[1], pad.l, W - pad.r);
    var ys = scale(yr[0], yr[1], H - pad.b, pad.t);
    var g = "";
    (ticks || 4).toString();
    var n = ticks || 4;
    for (var i = 0; i <= n; i++) {
      var vx = xr[0] + ((xr[1] - xr[0]) * i) / n;
      var vy = yr[0] + ((yr[1] - yr[0]) * i) / n;
      g += '<line x1="' + xs(vx).toFixed(1) + '" y1="' + pad.t + '" x2="' + xs(vx).toFixed(1) + '" y2="' + (H - pad.b) + '" stroke="#F1F6FB"/>';
      g += '<line x1="' + pad.l + '" y1="' + ys(vy).toFixed(1) + '" x2="' + (W - pad.r) + '" y2="' + ys(vy).toFixed(1) + '" stroke="#EDF3F9"/>';
      g += '<text x="' + xs(vx).toFixed(1) + '" y="' + (H - pad.b + 16) + '" text-anchor="middle" font-size="10.5" fill="#8AA0B2">' + fmt(vx) + "</text>";
      g += '<text x="' + (pad.l - 8) + '" y="' + (ys(vy) + 4).toFixed(1) + '" text-anchor="end" font-size="10.5" fill="#8AA0B2">' + fmt(vy) + "</text>";
    }
    g += '<text x="' + (pad.l + (W - pad.l - pad.r) / 2) + '" y="' + (H - 6) + '" text-anchor="middle" font-size="11" fill="#5A7184">' + xLabel + "</text>";
    g += '<text x="12" y="' + (pad.t + 14) + '" font-size="11" fill="#5A7184">' + yLabel + "</text>";
    return { g: g, xs: xs, ys: ys };
  }

  function fmt(v) {
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    if (Math.abs(v) >= 1) return v.toFixed(2);
    return v.toFixed(3);
  }

  /* ============ 模块一：一维梯度下降 ============ */
  function renderGD1D() {
    var eta = +$("#gd1d-eta").value;
    var iter = +$("#gd1d-iter").value;
    $("#gd1d-eta-val").textContent = eta.toFixed(2);
    $("#gd1d-iter-val").textContent = iter;

    // f(x)=x^2，梯度 2x，更新 x <- x - η·2x = (1-2η)x
    var x = 10, traj = [{ t: 0, x: x, f: x * x }];
    for (var i = 1; i <= iter; i++) {
      x = x - eta * 2 * x;
      traj.push({ t: i, x: x, f: x * x });
      if (Math.abs(x) > 1e6) break;
    }

    var W = 560, H = 300, pad = { l: 52, r: 20, t: 18, b: 42 };
    var ax = axes(W, H, pad, [-12, 12], [0, 130], "x", "f(x)=x²", 4);
    // 抛物线
    var curve = [];
    for (var k = -12; k <= 12; k += 0.2) {
      curve.push(ax.xs(k).toFixed(1) + "," + ax.ys(Math.min(k * k, 130)).toFixed(1));
    }
    var dots = traj.filter(function (p) { return Math.abs(p.x) <= 12 && p.f <= 130; }).map(function (p, i) {
      var r = i === 0 ? 5 : 3.6;
      var color = i === 0 ? "#C0392B" : "#2E75B6";
      return '<circle cx="' + ax.xs(p.x).toFixed(1) + '" cy="' + ax.ys(Math.min(p.f, 130)).toFixed(1) +
        '" r="' + r + '" fill="' + color + '" fill-opacity="' + (i === 0 ? 1 : 0.75) + '"><title>第 ' + p.t +
        " 步：x=" + p.x.toFixed(4) + "，f(x)=" + (p.x * p.x).toFixed(4) + "</title></circle>";
    }).join("");
    $("#gd1d-chart").innerHTML = svgWrap(W, H, ax.g +
      '<polyline points="' + curve.join(" ") + '" fill="none" stroke="#9DC3E6" stroke-width="2"/>' + dots);

    // 轨迹表（前 8 步）
    var rows = traj.slice(0, 9).map(function (p) {
      return "<tr><td>" + p.t + "</td><td>" + p.x.toFixed(4) + "</td><td>" + (p.x * p.x).toFixed(4) + "</td></tr>";
    }).join("");
    $("#gd1d-table").innerHTML = '<table class="lab-table"><thead><tr><th>步</th><th>x</th><th>f(x)</th></tr></thead><tbody>' +
      rows + "</tbody></table>";

    var factor = Math.abs(1 - 2 * eta);
    var status, cls;
    if (factor < 0.999) { status = "收敛：每步误差按 " + factor.toFixed(2) + " 倍缩小，" + iter + " 步后 |x|≈" + Math.abs(traj[traj.length - 1].x).toExponential(2); cls = "ok"; }
    else if (factor < 1.001) { status = "临界：η=0.5 时 x 每步正负跳变、幅度不变，永远在 ±10 之间振荡，不会收敛"; cls = "warn"; }
    else { status = "发散：误差每步被放大 " + factor.toFixed(2) + " 倍，η 超过 2/L（本例 L=2，即 η>1）后彻底失控"; cls = "bad"; }
    $("#gd1d-note").className = "lab-note lab-note--" + cls;
    $("#gd1d-note").textContent = status + "。判据：x 的衰减因子是 |1−2η|，η<0.5 收敛，η=0.5 振荡，η>0.5 发散。";
  }

  /* ============ 共享数据集：y = 3x + 2 + 噪声 ============ */
  var DATA = (function () {
    var r = rng(20261118), pts = [];
    for (var i = 0; i < 40; i++) {
      var x = 0.2 + (i / 39) * 9.6;
      pts.push({ x: x, y: 3 * x + 2 + gauss(r) * 1.4 });
    }
    return pts;
  })();

  // 标准化后再训练，避免量纲差异导致学习率难调
  var STD = (function () {
    var mx = mean(DATA.map(function (p) { return p.x; }));
    var my = mean(DATA.map(function (p) { return p.y; }));
    var sx = std(DATA.map(function (p) { return p.x; }), mx);
    var sy = std(DATA.map(function (p) { return p.y; }), my);
    return { mx: mx, my: my, sx: sx, sy: sy };
  })();

  function mean(a) { return a.reduce(function (s, v) { return s + v; }, 0) / a.length; }
  function std(a, m) {
    m = m === undefined ? mean(a) : m;
    return Math.sqrt(a.reduce(function (s, v) { return s + (v - m) * (v - m); }, 0) / a.length) || 1;
  }

  function toNorm(p) {
    return { x: (p.x - STD.mx) / STD.sx, y: (p.y - STD.my) / STD.sy };
  }
  // 标准化空间的参数还原成原始单位
  function unscale(w, b) {
    return { w: (w * STD.sy) / STD.sx, b: STD.my + b * STD.sy - (w * STD.sy * STD.mx) / STD.sx };
  }

  /* ============ 模块二：BGD / SGD / 小批量 ============ */
  function trainLinear(mode, eta, epochs, batchSize) {
    var pts = DATA.map(toNorm);
    var w = 0, b = 0, losses = [], n = pts.length;

    function grad(list) {
      var gw = 0, gb = 0;
      list.forEach(function (p) {
        var e = w * p.x + b - p.y;
        gw += 2 * e * p.x;
        gb += 2 * e;
      });
      return { gw: gw / list.length, gb: gb / list.length };
    }

    function lossOf(list) {
      var s = 0;
      list.forEach(function (p) { var e = w * p.x + b - p.y; s += e * e; });
      return s / list.length;
    }

    for (var ep = 0; ep < epochs; ep++) {
      if (mode === "bgd") {
        var g = grad(pts);
        w -= eta * g.gw;
        b -= eta * g.gb;
      } else if (mode === "sgd") {
        for (var i = 0; i < n; i++) {
          var p = pts[i];
          var e = w * p.x + b - p.y;
          w -= eta * 2 * e * p.x;
          b -= eta * 2 * e;
        }
      } else {
        var order = pts.slice();
        for (var k = order.length - 1; k > 0; k--) {
          var j = Math.floor(Math.random() * (k + 1));
          var t = order[k]; order[k] = order[j]; order[j] = t;
        }
        for (var s = 0; s < n; s += batchSize) {
          var g2 = grad(order.slice(s, s + batchSize));
          w -= eta * g2.gw;
          b -= eta * g2.gb;
        }
      }
      losses.push(lossOf(pts));
    }
    return { w: w, b: b, losses: losses, real: unscale(w, b) };
  }

  function renderBatch() {
    var eta = +$("#bgd-eta").value;
    var epochs = +$("#bgd-epochs").value;
    var batch = +$("#bgd-batch").value;
    $("#bgd-eta-val").textContent = eta.toFixed(3);
    $("#bgd-epochs-val").textContent = epochs;
    $("#bgd-batch-val").textContent = batch;

    var rB = trainLinear("bgd", eta, epochs, batch);
    var rS = trainLinear("sgd", eta, epochs, batch);
    var rM = trainLinear("mini", eta, epochs, batch);

    // 左图：散点 + 三条拟合线
    var W = 560, H = 300, pad = { l: 52, r: 16, t: 18, b: 42 };
    var ax = axes(W, H, pad, [0, 10], [0, 35], "x（刷题量 / 百题）", "y（笔试得分）", 4);
    var dots = DATA.map(function (p) {
      return '<circle cx="' + ax.xs(p.x).toFixed(1) + '" cy="' + ax.ys(p.y).toFixed(1) + '" r="3" fill="#9DC3E6" fill-opacity="0.85"><title>x=' + p.x.toFixed(2) + "，y=" + p.y.toFixed(2) + "</title></circle>";
    }).join("");
    function lineOf(r, color, width) {
      var y0 = r.real.w * 0 + r.real.b, y1 = r.real.w * 10 + r.real.b;
      return '<line x1="' + ax.xs(0) + '" y1="' + ax.ys(y0) + '" x2="' + ax.xs(10) + '" y2="' + ax.ys(y1) +
        '" stroke="' + color + '" stroke-width="' + width + '" stroke-linecap="round"><title>w=' + r.real.w.toFixed(3) + "，b=" + r.real.b.toFixed(3) + "</title></line>";
    }
    $("#bgd-chart").innerHTML = svgWrap(W, H, ax.g + dots +
      lineOf(rB, "#1F4E79", 2.4) + lineOf(rS, "#2E75B6", 1.6) + lineOf(rM, "#4472C4", 1.6));

    // 右图：三条损失曲线（对数纵轴）
    var W2 = 460, H2 = 300, pad2 = { l: 56, r: 14, t: 18, b: 42 };
    var all = rB.losses.concat(rS.losses, rM.losses).filter(function (v) { return v > 0; });
    var lo = Math.log10(Math.min.apply(null, all)), hi = Math.log10(Math.max.apply(null, all));
    if (hi - lo < 0.5) { hi = lo + 0.5; }
    var ax2 = axes(W2, H2, pad2, [0, epochs], [lo, hi], "epoch", "log10(MSE)", 4);
    function lossLine(r, color) {
      var pts = r.losses.map(function (v, i) { return ax2.xs(i + 1).toFixed(1) + "," + ax2.ys(Math.log10(Math.max(v, 1e-9))).toFixed(1); });
      return '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + color + '" stroke-width="2"/>';
    }
    $("#bgd-loss").innerHTML = svgWrap(W2, H2, ax2.g +
      lossLine(rB, "#1F4E79") + lossLine(rS, "#2E75B6") + lossLine(rM, "#4472C4"));

    $("#bgd-result").innerHTML =
      '<table class="lab-table"><thead><tr><th>算法</th><th>斜率 w</th><th>截距 b</th><th>最终 MSE</th></tr></thead><tbody>' +
      [["全批量 BGD", rB], ["SGD（逐样本）", rS], ["小批量 b=" + batch, rM]].map(function (row) {
        var r = row[1];
        return "<tr><td>" + row[0] + "</td><td>" + r.real.w.toFixed(3) + "</td><td>" + r.real.b.toFixed(3) +
          "</td><td>" + r.losses[r.losses.length - 1].toFixed(4) + "</td></tr>";
      }).join("") + "</tbody></table>";
  }

  /* ============ 模块三：闭式解 vs 手写 SGD ============ */
  function renderClosed() {
    var eta = +$("#cl-eta").value;
    var epochs = +$("#cl-epochs").value;
    $("#cl-eta-val").textContent = eta.toFixed(3);
    $("#cl-epochs-val").textContent = epochs;

    var pts = DATA.map(toNorm);
    var n = pts.length;
    // 法方程 (XᵀX)⁻¹Xᵀy，二维闭式解
    var sx = 0, sy = 0, sxx = 0, sxy = 0;
    pts.forEach(function (p) { sx += p.x; sy += p.y; sxx += p.x * p.x; sxy += p.x * p.y; });
    var den = n * sxx - sx * sx || 1e-12;
    var w = (n * sxy - sx * sy) / den;
    var b = (sy - w * sx) / n;

    // 同一个解，用 SGD 迭代到同一位置
    var w2 = 0, b2 = 0, losses = [];
    for (var ep = 0; ep < epochs; ep++) {
      for (var i = 0; i < n; i++) {
        var p = pts[i], e = w2 * p.x + b2 - p.y;
        w2 -= eta * 2 * e * p.x;
        b2 -= eta * 2 * e;
      }
      var s = 0;
      pts.forEach(function (q) { var e2 = w2 * q.x + b2 - q.y; s += e2 * e2; });
      losses.push(s / n);
    }
    var closed = unscale(w, b), sgd = unscale(w2, b2);

    var W = 560, H = 300, pad = { l: 52, r: 16, t: 18, b: 42 };
    var ax = axes(W, H, pad, [0, 10], [0, 35], "x（刷题量 / 百题）", "y（笔试得分）", 4);
    var dots = DATA.map(function (p) {
      return '<circle cx="' + ax.xs(p.x).toFixed(1) + '" cy="' + ax.ys(p.y).toFixed(1) + '" r="3" fill="#9DC3E6" fill-opacity="0.85"></circle>';
    }).join("");
    function lineOf(r, color, dash) {
      var y0 = r.b, y1 = r.w * 10 + r.b;
      return '<line x1="' + ax.xs(0) + '" y1="' + ax.ys(y0) + '" x2="' + ax.xs(10) + '" y2="' + ax.ys(y1) +
        '" stroke="' + color + '" stroke-width="2.4" ' + (dash ? 'stroke-dasharray="6 4"' : "") + "/>";
    }
    $("#cl-chart").innerHTML = svgWrap(W, H, ax.g + dots + lineOf(closed, "#1F4E79", false) + lineOf(sgd, "#E67E22", true));

    var W2 = 460, H2 = 300, pad2 = { l: 56, r: 14, t: 18, b: 42 };
    var lo = Math.log10(Math.max(Math.min.apply(null, losses), 1e-6)), hi = Math.log10(Math.max.apply(null, losses));
    var ax2 = axes(W2, H2, pad2, [0, epochs], [lo, hi + 0.1], "epoch", "log10(MSE)", 4);
    var pts2 = losses.map(function (v, i) { return ax2.xs(i + 1).toFixed(1) + "," + ax2.ys(Math.log10(Math.max(v, 1e-9))).toFixed(1); });
    $("#cl-loss").innerHTML = svgWrap(W2, H2, ax2.g + '<polyline points="' + pts2.join(" ") + '" fill="none" stroke="#E67E22" stroke-width="2"/>');

    var diffW = Math.abs(closed.w - sgd.w), diffB = Math.abs(closed.b - sgd.b);
    $("#cl-table").innerHTML = '<table class="lab-table"><thead><tr><th>方法</th><th>斜率 w</th><th>截距 b</th><th>与闭式解差值</th></tr></thead><tbody>' +
      "<tr><td>闭式解 (XᵀX)⁻¹Xᵀy</td><td>" + closed.w.toFixed(4) + "</td><td>" + closed.b.toFixed(4) + "</td><td>—</td></tr>" +
      "<tr><td>手写 SGD（" + epochs + " epoch）</td><td>" + sgd.w.toFixed(4) + "</td><td>" + sgd.b.toFixed(4) +
      "</td><td>Δw=" + diffW.toExponential(1) + "，Δb=" + diffB.toExponential(1) + "</td></tr>" +
      "</tbody></table>";
  }

  /* ============ 模块四：过拟合诊断 ============ */
  var OVERFIT = (function () {
    var r = rng(99991), pts = [];
    for (var i = 0; i < 30; i++) {
      var x = i / 29;
      pts.push({ x: x, y: 0.8 * Math.sin(2 * Math.PI * x) + gauss(r) * 0.16 });
    }
    var train = pts.filter(function (p, i) { return i % 10 < 7; });
    var test = pts.filter(function (p, i) { return i % 10 >= 7; });
    return { train: train, test: test };
  })();

  function renderOverfit() {
    var deg = +$("#of-deg").value;
    $("#of-deg-val").textContent = deg;

    var tr = OVERFIT.train, te = OVERFIT.test;
    var xsTr = tr.map(function (p) { return p.x; }), ysTr = tr.map(function (p) { return p.y; });
    var xsTe = te.map(function (p) { return p.x; }), ysTe = te.map(function (p) { return p.y; });
    var coef = polyfit(xsTr, ysTr, deg);
    var fn = function (x) { return evalPoly(coef, x); };
    var trainMse = mse(xsTr, ysTr, fn), testMse = mse(xsTe, ysTe, fn);

    var W = 560, H = 300, pad = { l: 52, r: 16, t: 18, b: 42 };
    var ax = axes(W, H, pad, [0, 1], [-1.4, 1.4], "x", "y", 4);
    var curve = [];
    for (var k = 0; k <= 200; k++) {
      var x = k / 200;
      var y = Math.max(-1.4, Math.min(1.4, fn(x)));
      curve.push(ax.xs(x).toFixed(1) + "," + ax.ys(y).toFixed(1));
    }
    var trainDots = tr.map(function (p) {
      return '<circle cx="' + ax.xs(p.x).toFixed(1) + '" cy="' + ax.ys(p.y).toFixed(1) + '" r="3.4" fill="#1F4E79"></circle>';
    }).join("");
    var testDots = te.map(function (p) {
      return '<circle cx="' + ax.xs(p.x).toFixed(1) + '" cy="' + ax.ys(p.y).toFixed(1) + '" r="3.4" fill="#fff" stroke="#C0392B" stroke-width="1.8"></circle>';
    }).join("");
    $("#of-chart").innerHTML = svgWrap(W, H, ax.g + '<polyline points="' + curve.join(" ") +
      '" fill="none" stroke="#2E75B6" stroke-width="2.2"/>' + trainDots + testDots);

    // MSE vs 阶数曲线
    var degs = [], trM = [], teM = [];
    for (var d = 1; d <= 12; d++) {
      var c = polyfit(xsTr, ysTr, d);
      degs.push(d);
      trM.push(mse(xsTr, ysTr, function (x) { return evalPoly(c, x); }));
      teM.push(mse(xsTe, ysTe, function (x) { return evalPoly(c, x); }));
    }
    var W2 = 460, H2 = 300, pad2 = { l: 58, r: 16, t: 18, b: 42 };
    var allM = trM.concat(teM).map(function (v) { return Math.log10(Math.max(v, 1e-6)); });
    var lo = Math.min.apply(null, allM), hi = Math.max.apply(null, allM);
    var ax2 = axes(W2, H2, pad2, [1, 12], [lo, hi + 0.2], "多项式阶数", "log10(MSE)", 4);
    function curveOf(arr, color) {
      return '<polyline points="' + arr.map(function (v, i) {
        return ax2.xs(degs[i]).toFixed(1) + "," + ax2.ys(Math.log10(Math.max(v, 1e-6))).toFixed(1);
      }).join(" ") + '" fill="none" stroke="' + color + '" stroke-width="2.2"/>' +
        arr.map(function (v, i) {
          return '<circle cx="' + ax2.xs(degs[i]).toFixed(1) + '" cy="' + ax2.ys(Math.log10(Math.max(v, 1e-6))).toFixed(1) +
            '" r="' + (degs[i] === deg ? 4.2 : 2.4) + '" fill="' + (degs[i] === deg ? "#C0392B" : color) + '"/>';
        }).join("");
    }
    $("#of-loss").innerHTML = svgWrap(W2, H2, ax2.g +
      '<line x1="' + ax2.xs(deg) + '" y1="' + pad2.t + '" x2="' + ax2.xs(deg) + '" y2="' + (H2 - pad2.b) +
      '" stroke="#C0392B" stroke-dasharray="4 4" stroke-width="1"/>' +
      curveOf(trM, "#1F4E79") + curveOf(teM, "#E67E22"));

    var gap = testMse / (trainMse || 1e-9);
    var verdict, cls;
    if (deg <= 2) { verdict = "欠拟合：模型太简单，训练误差和测试误差都高，曲线抓不到正弦的整体形状"; cls = "warn"; }
    else if (deg <= 4) { verdict = "合适：训练误差与测试误差都低，曲线平滑贴合趋势"; cls = "ok"; }
    else if (gap > 6 || testMse > 0.25) { verdict = "过拟合：训练误差继续下降（" + trainMse.toFixed(4) + "），测试误差反弹到 " + testMse.toFixed(4) + "，曲线开始穿过每个噪声点"; cls = "bad"; }
    else { verdict = "偏复杂：测试误差已高于最优阶数，继续加阶数只会拟合噪声"; cls = "warn"; }
    $("#of-note").className = "lab-note lab-note--" + cls;
    $("#of-note").textContent = verdict + "。当前 " + deg + " 阶：训练 MSE=" + trainMse.toFixed(4) + "，测试 MSE=" + testMse.toFixed(4) + "。";
  }

  /* ---------------- 初始化 ---------------- */
  var bound = false;
  function init() {
    if (bound) { renderAll(); return; }
    bound = true;
    ["gd1d-eta", "gd1d-iter"].forEach(function (id) { $("#" + id).addEventListener("input", renderGD1D); });
    ["bgd-eta", "bgd-epochs", "bgd-batch"].forEach(function (id) { $("#" + id).addEventListener("input", renderBatch); });
    ["cl-eta", "cl-epochs"].forEach(function (id) { $("#" + id).addEventListener("input", renderClosed); });
    $("#of-deg").addEventListener("input", renderOverfit);
    renderAll();
  }
  function renderAll() {
    renderGD1D(); renderBatch(); renderClosed(); renderOverfit();
  }

  global.Lab = { init: init };
})(window);
