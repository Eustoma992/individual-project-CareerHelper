/* ============================================================
   轻量 SVG 图表：不依赖任何第三方库，离线可用
   Charts.hBar / donut / radar / line
   ============================================================ */
(function (global) {
  "use strict";

  var PALETTE = ["#0F2C4C", "#1F4E79", "#2E75B6", "#4472C4", "#5B9BD5", "#8FAADC", "#9DC3E6", "#BDD7EE"];

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function cut(s, n) {
    s = String(s);
    return s.length > n ? s.slice(0, n) + "…" : s;
  }

  /* -------- 横向条形图：考点占比 / 高频题频次 -------- */
  function hBar(el, items, opt) {
    opt = opt || {};
    if (!items || !items.length) { el.innerHTML = '<p class="tiny">暂无数据</p>'; return; }
    var W = 720, rowH = opt.rowH || 38, padTop = 6, labelW = opt.labelW || 220;
    var H = padTop + items.length * rowH + 8;
    var max = opt.max || Math.max.apply(null, items.map(function (i) { return i.value; })) || 1;
    var valueW = 54, barMax = W - labelW - valueW - 10;
    var rows = items.map(function (it, i) {
      var y = padTop + i * rowH;
      var w = Math.max(2, (it.value / max) * barMax);
      var color = it.color || (opt.color || "#2E75B6");
      var val = opt.format ? opt.format(it.value, it) : it.value;
      return '' +
        '<g class="c-row">' +
        '<text x="0" y="' + (y + 18) + '" font-size="12.5" fill="#3F5B72">' + esc(cut(it.label, opt.labelChars || 17)) + '</text>' +
        '<rect x="' + labelW + '" y="' + (y + 6) + '" width="' + barMax + '" height="16" rx="8" fill="#F0F6FB"/>' +
        '<rect x="' + labelW + '" y="' + (y + 6) + '" width="' + w.toFixed(1) + '" height="16" rx="8" fill="' + color + '">' +
        '<title>' + esc(it.label) + '：' + esc(val) + '</title></rect>' +
        '<text x="' + (labelW + w + 8).toFixed(1) + '" y="' + (y + 18) + '" font-size="12" font-weight="700" fill="#1F4E79">' + esc(val) + '</text>' +
        '</g>';
    }).join("");
    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' + rows + '</svg>';
  }

  /* -------- 环形图：题型配比 -------- */
  function donut(el, items, opt) {
    opt = opt || {};
    if (!items || !items.length) { el.innerHTML = ""; return; }
    var S = 300, c = S / 2, r = 88, sw = 30, C = 2 * Math.PI * r;
    var total = items.reduce(function (s, i) { return s + i.value; }, 0) || 1;
    var offset = 0;
    var arcs = items.map(function (it, i) {
      var len = (it.value / total) * C;
      var seg = '<circle cx="' + c + '" cy="' + c + '" r="' + r + '" fill="none" stroke="' + (it.color || PALETTE[i % PALETTE.length]) +
        '" stroke-width="' + sw + '" stroke-dasharray="' + len.toFixed(2) + ' ' + (C - len).toFixed(2) +
        '" stroke-dashoffset="' + (-offset).toFixed(2) + '" transform="rotate(-90 ' + c + ' ' + c + ')">' +
        '<title>' + esc(it.label) + '：' + Math.round(it.value / total * 100) + '%</title></circle>';
      offset += len;
      return seg;
    }).join("");
    var center = '<text x="' + c + '" y="' + (c - 2) + '" text-anchor="middle" font-size="13" fill="#7E97AC">题型配比</text>' +
      '<text x="' + c + '" y="' + (c + 24) + '" text-anchor="middle" font-size="17" font-weight="800" fill="#1F4E79">' +
      (opt.centerText || (items.length + " 类")) + '</text>';
    el.innerHTML = '<svg viewBox="0 0 ' + S + ' ' + S + '" role="img">' + arcs + center + '</svg>';
  }

  /* -------- 雷达图：考点掌握度 -------- */
  function radar(el, items, opt) {
    opt = opt || {};
    if (!items || items.length < 3) {
      el.innerHTML = '<p class="tiny" style="text-align:center;padding:40px 0">至少完成 2 次、覆盖 3 个考点后显示雷达图</p>';
      return;
    }
    var S = 380, c = S / 2, R = 118, n = items.length;
    var rings = [25, 50, 75, 100].map(function (p) {
      var pts = [];
      for (var i = 0; i < n; i++) {
        var a = -Math.PI / 2 + i * 2 * Math.PI / n;
        pts.push((c + Math.cos(a) * R * p / 100).toFixed(1) + "," + (c + Math.sin(a) * R * p / 100).toFixed(1));
      }
      return '<polygon points="' + pts.join(" ") + '" fill="none" stroke="#E4EDF6" stroke-width="1"/>';
    }).join("");

    var axes = "", labels = "", dots = "", poly = [];
    items.forEach(function (it, i) {
      var a = -Math.PI / 2 + i * 2 * Math.PI / n;
      var x = c + Math.cos(a) * R, y = c + Math.sin(a) * R;
      axes += '<line x1="' + c + '" y1="' + c + '" x2="' + x.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="#E9F0F7"/>';
      var v = Math.max(2, Math.min(100, it.value)) / 100;
      var px = c + Math.cos(a) * R * v, py = c + Math.sin(a) * R * v;
      poly.push(px.toFixed(1) + "," + py.toFixed(1));
      dots += '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="3.5" fill="#1F4E79"/>';
      var lx = c + Math.cos(a) * (R + 24), ly = c + Math.sin(a) * (R + 24);
      var anchor = Math.abs(Math.cos(a)) < 0.25 ? "middle" : (Math.cos(a) > 0 ? "start" : "end");
      labels += '<text x="' + lx.toFixed(1) + '" y="' + (ly + 4).toFixed(1) + '" text-anchor="' + anchor +
        '" font-size="10.5" fill="#5A7184">' + esc(cut(it.label, 7)) + '</text>' +
        '<text x="' + lx.toFixed(1) + '" y="' + (ly + 17).toFixed(1) + '" text-anchor="' + anchor +
        '" font-size="10" font-weight="700" fill="#2E75B6">' + Math.round(it.value) + '%</text>';
    });

    el.innerHTML = '<svg viewBox="0 0 ' + S + ' ' + S + '" role="img">' + rings + axes +
      '<polygon points="' + poly.join(" ") + '" fill="rgba(46,117,182,.22)" stroke="#1F4E79" stroke-width="2"/>' +
      dots + labels + '</svg>';
  }

  /* -------- 折线图：正确率趋势 -------- */
  function line(el, points, opt) {
    opt = opt || {};
    if (!points || !points.length) { el.innerHTML = '<p class="tiny">暂无数据</p>'; return; }
    var W = 720, H = 250, L = 42, R = 18, T = 16, B = 34;
    var iw = W - L - R, ih = H - T - B;
    var xs = function (i) { return L + (points.length === 1 ? iw / 2 : i * iw / (points.length - 1)); };
    var ys = function (v) { return T + ih - (v / 100) * ih; };

    var grid = [0, 25, 50, 75, 100].map(function (v) {
      return '<line x1="' + L + '" y1="' + ys(v) + '" x2="' + (W - R) + '" y2="' + ys(v) + '" stroke="#EDF3F9"/>' +
        '<text x="' + (L - 8) + '" y="' + (ys(v) + 4) + '" text-anchor="end" font-size="10.5" fill="#8AA0B2">' + v + '</text>';
    }).join("");

    var pts = points.map(function (p, i) { return xs(i).toFixed(1) + "," + ys(p.value).toFixed(1); });
    var area = L + "," + ys(0) + " " + pts.join(" ") + " " + xs(points.length - 1).toFixed(1) + "," + ys(0);
    var dots = points.map(function (p, i) {
      return '<circle cx="' + xs(i).toFixed(1) + '" cy="' + ys(p.value).toFixed(1) + '" r="4" fill="#fff" stroke="#1F4E79" stroke-width="2">' +
        '<title>' + esc(p.label) + '：' + p.value + '%</title></circle>';
    }).join("");
    var labels = points.map(function (p, i) {
      var every = Math.ceil(points.length / 8);
      if (i % every !== 0 && i !== points.length - 1) return "";
      return '<text x="' + xs(i).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="10.5" fill="#8AA0B2">' +
        esc(cut(p.label, 8)) + '</text>';
    }).join("");

    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' + grid +
      '<polygon points="' + area + '" fill="rgba(46,117,182,.12)"/>' +
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="#1F4E79" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>' +
      dots + labels + '</svg>';
  }

  /* -------- 分组柱状图：同一批分类下的多组指标对比 -------- */
  function groupedBar(el, groups, series, opt) {
    opt = opt || {};
    if (!groups || !groups.length) { el.innerHTML = '<p class="tiny">暂无数据</p>'; return; }
    var W = 760, H = opt.height || 300, L = 46, R = 14, T = 24, B = 62;
    var iw = W - L - R, ih = H - T - B;
    var max = 0;
    series.forEach(function (s) { s.values.forEach(function (v) { if (v > max) max = v; }); });
    max = Math.max(max, 1) * 1.15;
    var band = iw / groups.length;
    var bw = Math.min(26, band / (series.length + 0.6));

    var grid = [0, 0.25, 0.5, 0.75, 1].map(function (f) {
      var v = max * f, y = T + ih - (v / max) * ih;
      return '<line x1="' + L + '" y1="' + y.toFixed(1) + '" x2="' + (W - R) + '" y2="' + y.toFixed(1) + '" stroke="#EDF3F9"/>' +
        '<text x="' + (L - 8) + '" y="' + (y + 4).toFixed(1) + '" text-anchor="end" font-size="10" fill="#8AA0B2">' +
        (opt.format ? opt.format(v) : Math.round(v)) + '</text>';
    }).join("");

    var bars = "", labels = "";
    groups.forEach(function (g, gi) {
      var cx = L + band * gi + band / 2;
      series.forEach(function (s, si) {
        var v = s.values[gi] || 0;
        var h = Math.max(1, (v / max) * ih);
        var x = cx - (series.length * bw) / 2 + si * bw;
        bars += '<rect x="' + x.toFixed(1) + '" y="' + (T + ih - h).toFixed(1) + '" width="' + (bw - 3).toFixed(1) +
          '" height="' + h.toFixed(1) + '" rx="3" fill="' + s.color + '"><title>' + esc(g) + " · " + esc(s.name) + "：" +
          (opt.format ? opt.format(v) : Math.round(v)) + '</title></rect>';
      });
      labels += '<text x="' + cx.toFixed(1) + '" y="' + (H - 38) + '" text-anchor="end" font-size="10.5" fill="#5A7184" ' +
        'transform="rotate(-28 ' + cx.toFixed(1) + ' ' + (H - 38) + ')">' + esc(cut(g, 10)) + '</text>';
    });

    var legend = series.map(function (s, i) {
      return '<g transform="translate(' + (L + i * 118) + ',10)">' +
        '<rect width="10" height="10" rx="2" fill="' + s.color + '"/>' +
        '<text x="15" y="9" font-size="11" fill="#5A7184">' + esc(s.name) + '</text></g>';
    }).join("");

    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' + grid + bars + labels + legend + '</svg>';
  }

  /* -------- 箱线图：看一组岗位/题型的分布与离群点 -------- */
  function boxPlot(el, items, opt) {
    opt = opt || {};
    if (!items || !items.length) { el.innerHTML = '<p class="tiny">暂无数据</p>'; return; }
    var W = 720, H = opt.height || 280, L = 44, R = 16, T = 18, B = 46;
    var iw = W - L - R, ih = H - T - B;
    var all = [];
    items.forEach(function (it) { all = all.concat(it.values); });
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.12 || 0.5;
    lo -= pad; hi += pad;
    var ys = function (v) { return T + ih - ((v - lo) / (hi - lo)) * ih; };

    var grid = [0, 0.25, 0.5, 0.75, 1].map(function (f) {
      var v = lo + (hi - lo) * f, y = ys(v);
      return '<line x1="' + L + '" y1="' + y.toFixed(1) + '" x2="' + (W - R) + '" y2="' + y.toFixed(1) + '" stroke="#EDF3F9"/>' +
        '<text x="' + (L - 8) + '" y="' + (y + 4).toFixed(1) + '" text-anchor="end" font-size="10" fill="#8AA0B2">' +
        v.toFixed(1) + '</text>';
    }).join("");

    var band = iw / items.length, boxes = "";
    items.forEach(function (it, i) {
      var v = it.values.slice().sort(function (a, b) { return a - b; });
      var q = function (p) {
        var pos = (v.length - 1) * p, base = Math.floor(pos), rest = pos - base;
        return v[base + 1] !== undefined ? v[base] + rest * (v[base + 1] - v[base]) : v[base];
      };
      var min = v[0], q1 = q(0.25), med = q(0.5), q3 = q(0.75), max = v[v.length - 1];
      var cx = L + band * i + band / 2, bw = Math.min(56, band * 0.52);
      var color = it.color || "#2E75B6";
      boxes += '<line x1="' + cx + '" y1="' + ys(min) + '" x2="' + cx + '" y2="' + ys(max) + '" stroke="' + color + '" stroke-width="1.4"/>' +
        '<line x1="' + (cx - bw / 3) + '" y1="' + ys(min) + '" x2="' + (cx + bw / 3) + '" y2="' + ys(min) + '" stroke="' + color + '" stroke-width="1.4"/>' +
        '<line x1="' + (cx - bw / 3) + '" y1="' + ys(max) + '" x2="' + (cx + bw / 3) + '" y2="' + ys(max) + '" stroke="' + color + '" stroke-width="1.4"/>' +
        '<rect x="' + (cx - bw / 2) + '" y="' + ys(q3) + '" width="' + bw + '" height="' + Math.max(1, ys(q1) - ys(q3)) +
        '" fill="' + color + '" fill-opacity="0.18" stroke="' + color + '" stroke-width="1.4" rx="3"><title>' +
        esc(it.label) + "：中位数 " + med.toFixed(2) + "，n=" + v.length + '</title></rect>' +
        '<line x1="' + (cx - bw / 2) + '" y1="' + ys(med) + '" x2="' + (cx + bw / 2) + '" y2="' + ys(med) + '" stroke="' + color + '" stroke-width="2.6"/>' +
        '<text x="' + cx + '" y="' + (H - 22) + '" text-anchor="middle" font-size="11" fill="#5A7184">' + esc(cut(it.label, 8)) + '</text>';
    });

    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' + grid + boxes + '</svg>';
  }

  global.Charts = { hBar: hBar, donut: donut, radar: radar, line: line, groupedBar: groupedBar, boxPlot: boxPlot, PALETTE: PALETTE };
})(window);
