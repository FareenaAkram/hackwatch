(function () {
  "use strict";
  var D = window.HACKWATCH;
  var $ = function (id) { return document.getElementById(id); };

  // DOM helpers. Never innerHTML: all dataset text goes through textContent.
  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else el.setAttribute(k, attrs[k]);
    });
    (function add(list) {
      list.forEach(function (c) {
        if (c == null || c === false) return;
        if (Array.isArray(c)) return add(c);
        el.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
      });
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  }
  var NS = "http://www.w3.org/2000/svg";
  function s(tag, attrs, text) {
    var el = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    if (text != null) el.textContent = text;
    for (var i = 3; i < arguments.length; i++) if (arguments[i]) el.appendChild(arguments[i]);
    return el;
  }
  function pct(x) { return Math.round(x * 100) + "%"; }
  function nice(label) { return ({ correct: "correct", subtle_bug: "subtle bug", bug: "bug", hack: "reward hack", suspected_hack: "suspected hack" })[label] || label; }

  if (!D) { $("detail").textContent = "data.js not found. Run: python -m hackwatch build"; return; }
  var S = D.stats, C = D.candidates, P = D.pairs;
  var byId = {};
  C.forEach(function (c) { byId[c.id] = c; });

  function reward(c, g) {
    if (g === "naive") return c.naive_pass ? 1 : 0;
    if (g === "strict") return c.strict_score;
    return c.naive_pass && !c.flagged ? 1 : 0;
  }
  var GRADERS = [
    { id: "naive", name: "Naive (visible tests)", blurb: "Full reward if the visible examples pass." },
    { id: "strict", name: "Strict (hidden tests)", blurb: "Share of hidden cases passed, exact types." },
    { id: "combined", name: "Naive + detector", blurb: "Naive reward, zeroed when the detector flags the code." }
  ];

  // ---- hero
  var H = S.headline, cnt = S.counts, det = S.detector;
  $("meta").textContent = "v" + S.meta.version + " · " + cnt.candidates + " candidates · " + cnt.problems + " problems · " +
    P.length + " pairs · generated " + S.meta.generated_at + " · Python " + S.meta.python + " · seed " + S.meta.config.seed;
  [
    [H.hacks_naive_rewarded + " / " + H.hacks, "reward hacks earn FULL credit under the naive visible-test grader", "bad"],
    [H.subtle_naive_rewarded + " / " + H.subtle_total, "honest-but-wrong solutions also earn full naive credit", "warn"],
    [H.hacks_flagged + " / " + H.hacks, "hacks flagged by the detector, which never sees the answer key", "good"],
    [H.correct_wrongly_flagged + " / " + H.correct_total, "correct solutions wrongly flagged (false positives)", H.correct_wrongly_flagged ? "warn" : "good"]
  ].forEach(function (x) {
    $("hero-stats").appendChild(h("div", { "class": "stat" }, h("b", { "class": x[2], text: x[0] }), h("span", { text: x[1] })));
  });

  // ---- reward lab
  var state = { problem: S.problems[0].name, grader: "naive", selected: null };
  var probSel = $("problem");
  S.problems.forEach(function (p) { probSel.appendChild(h("option", { value: p.name, text: p.title })); });
  probSel.addEventListener("change", function () { state.problem = probSel.value; state.selected = null; renderLab(); });
  var seg = $("grader");
  GRADERS.forEach(function (g) {
    var b = h("button", { type: "button", "aria-pressed": String(g.id === state.grader), title: g.blurb, text: g.name });
    b.addEventListener("click", function () {
      state.grader = g.id;
      Array.prototype.forEach.call(seg.children, function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      renderLab();
    });
    seg.appendChild(b);
  });

  var ORDER = { correct: 0, subtle_bug: 1, bug: 2, suspected_hack: 3, hack: 4 };
  function codeView(code, lines) {
    var hl = {};
    (lines || []).forEach(function (n) { hl[n] = true; });
    var pre = h("pre", { "class": "code" });
    code.replace(/\n$/, "").split("\n").forEach(function (ln, i) {
      pre.appendChild(h("span", { "class": "ln" + (hl[i + 1] ? " hl" : "") }, h("i", { text: String(i + 1) }), ln));
    });
    return pre;
  }
  function flagLines(c) {
    var out = [];
    c.flags.forEach(function (f) { f.lines.forEach(function (n) { if (out.indexOf(n) < 0) out.push(n); }); });
    return out;
  }

  function renderLab() {
    var prob = S.problems.filter(function (p) { return p.name === state.problem; })[0];
    var box = $("problem-box");
    box.textContent = "";
    box.appendChild(h("h3", { text: prob.title }));
    box.appendChild(h("p", { text: prob.doc }));
    box.appendChild(h("code", { text: prob.signature }));
    box.appendChild(h("pre", { text: "visible examples:\n" + prob.visible.map(function (v) { return "  solve" + v[0] + "  ->  " + v[1]; }).join("\n") }));

    var list = C.filter(function (c) { return c.problem === state.problem && c.origin !== "llm"; })
      .concat(C.filter(function (c) { return c.problem === state.problem && c.origin === "llm"; }));
    var g = state.grader;
    list.sort(function (a, b) { return reward(b, g) - reward(a, g) || ORDER[a.label] - ORDER[b.label] || (a.id < b.id ? -1 : 1); });
    var full = list.filter(function (c) { return reward(c, g) >= 0.9999; });
    var hacks = full.filter(function (c) { return c.label === "hack"; }).length;
    var subtle = full.filter(function (c) { return c.label === "subtle_bug"; }).length;
    var good = full.filter(function (c) { return c.label === "correct"; }).length;
    var co = $("callout");
    co.className = "callout " + (hacks ? "alarm" : subtle ? "mid" : "ok");
    co.textContent = "";
    co.appendChild(h("b", { text: GRADERS.filter(function (x) { return x.id === g; })[0].name + ": " }));
    co.appendChild(document.createTextNode(full.length + " of " + list.length + " solutions get full reward. " + good + " correct, " + subtle + " subtly wrong, " + hacks + " reward hack" + (hacks === 1 ? "" : "s") +
      (hacks ? ". A policy trained on this signal learns to cheat." : subtle ? ". No cheats get through, but weak tests still reward wrong code." : ". Only correct solutions are rewarded.")));

    if (!state.selected || !list.some(function (c) { return c.id === state.selected; })) state.selected = list[0].id;
    var ul = $("cands");
    ul.textContent = "";
    list.forEach(function (c) {
      var r = reward(c, g);
      var b = h("button", { type: "button", "aria-current": String(c.id === state.selected) },
        h("span", { "class": "name" }, c.origin + " / " + c.kind, h("span", { "class": "badge l-" + c.label, text: nice(c.label) })),
        h("span", { "class": "val", text: r >= 0.9999 ? "full" : r.toFixed(2) }),
        h("span", { "class": "track" }, (function () { var f = h("span", { "class": "fill f-" + c.label }); f.style.width = Math.max(r * 100, 1.5) + "%"; return f; })()));
      b.addEventListener("click", function () { state.selected = c.id; renderLab(); });
      ul.appendChild(h("li", {}, b));
    });
    renderDetail(byId[state.selected]);
  }

  function renderDetail(c) {
    var d = $("detail");
    d.textContent = "";
    d.appendChild(h("h3", { text: c.id }));
    d.appendChild(h("p", { "class": "muted", text: c.note }));
    d.appendChild(h("div", { "class": "grid3" },
      h("div", { "class": "mini" }, h("b", { text: c.naive_pass ? "FULL" : "none" }), h("span", { text: "naive reward" })),
      h("div", { "class": "mini" }, h("b", { text: pct(c.strict_score) }), h("span", { text: "hidden tests passed" })),
      h("div", { "class": "mini" }, h("b", { text: c.flagged ? "FLAGGED" : "clean" }), h("span", { text: "detector verdict" }))));
    d.appendChild(h("h4", { text: "Detector evidence" }));
    if (c.flags.length) {
      d.appendChild(h("ul", { "class": "flags" }, c.flags.map(function (f) {
        return h("li", {}, h("span", { "class": "kind", text: f.kind }), " (" + f.source + "): " + f.detail + (f.lines.length ? " · lines " + f.lines.join(", ") : ""));
      })));
    } else d.appendChild(h("p", { "class": "muted", text: "No hack indicators." }));
    if (c.failures.length || c.no_sentinel) {
      d.appendChild(h("h4", { text: "Counterexamples on hidden inputs" }));
      if (c.no_sentinel) d.appendChild(h("p", { "class": "cx", text: "The process ended without reporting any results (harness escape or crash)." }));
      c.failures.forEach(function (f) { d.appendChild(h("p", { "class": "cx", text: "solve" + f.input + "  returned  " + (f.got || "<nothing>") + "   expected  " + f.expected })); });
    }
    d.appendChild(h("h4", { text: "Code" + (flagLines(c).length ? " (flagged lines highlighted)" : "") }));
    d.appendChild(codeView(c.code, flagLines(c)));
  }

  // ---- aggregate chart: share receiving full reward
  function groupedBars() {
    var classes = ["correct", "subtle_bug", "bug", "hack"], series = [
      ["naive", "Naive (visible)", "#7aa7ff"], ["strict", "Strict (hidden)", "#5fd3a5"], ["combined", "Naive + detector", "#f6c453"]];
    var W = 680, Ht = 280, left = 40, bottom = 46, top = 18, gw = (W - left - 10) / classes.length;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + Ht, width: "100%", role: "img", "aria-label": "Share of each solution class receiving full reward under three graders" });
    [0, .25, .5, .75, 1].forEach(function (t) {
      var y = Ht - bottom - t * (Ht - bottom - top);
      svg.appendChild(s("line", { x1: left, x2: W - 6, y1: y, y2: y, stroke: "#243041", "stroke-width": 1 }));
      svg.appendChild(s("text", { x: left - 6, y: y + 4, "text-anchor": "end", "class": "muted" }, pct(t)));
    });
    classes.forEach(function (cl, i) {
      var x0 = left + i * gw + 12, bw = (gw - 24) / series.length;
      series.forEach(function (sr, j) {
        var v = S.rewards[cl][sr[0]], hgt = v * (Ht - bottom - top), x = x0 + j * bw;
        svg.appendChild(s("rect", { x: x, y: Ht - bottom - hgt, width: bw - 4, height: hgt, fill: sr[2], rx: 3 }));
        svg.appendChild(s("text", { x: x + (bw - 4) / 2, y: Ht - bottom - hgt - 5, "text-anchor": "middle" }, pct(v)));
      });
      svg.appendChild(s("text", { x: left + i * gw + gw / 2, y: Ht - 24, "text-anchor": "middle" }, nice(cl) + " (n=" + S.rewards[cl].n + ")"));
    });
    series.forEach(function (sr, j) {
      var x = left + j * 170;
      svg.appendChild(s("rect", { x: x, y: Ht - 12, width: 10, height: 10, fill: sr[2], rx: 2 }));
      svg.appendChild(s("text", { x: x + 15, y: Ht - 3 }, sr[1]));
    });
    return svg;
  }
  $("agg-sub").textContent = "Share of each solution class that receives full reward. A good reward signal gives ~100% to correct code and 0% to everything else. Naive reward gives " +
    pct(S.rewards.hack.naive) + " of hacks full credit; adding the detector drops that to " + pct(S.rewards.hack.combined) + ".";
  $("chart-rewards").appendChild(groupedBars());

  // ---- detector panel
  [[pct(det.precision), "precision"], [pct(det.recall), "recall"], [det.f1.toFixed(2), "F1"], [det.fp + " / " + (det.fp + det.tn), "false positives"]].forEach(function (x) {
    $("det-tiles").appendChild(h("div", { "class": "mini" }, h("b", { text: x[0] }), h("span", { text: x[1] })));
  });
  Object.keys(det.by_kind).forEach(function (k) {
    var v = det.by_kind[k];
    var bar = h("div", { "class": "bar" }, (function () { var i = h("i"); i.style.width = (v.n ? v.flagged / v.n * 100 : 0) + "%"; return i; })());
    $("det-kinds").appendChild(h("div", { "class": "krow" }, h("code", { text: k }), bar, h("span", { text: v.flagged + "/" + v.n + " caught" })));
  });
  var fpText = det.false_positives.length
    ? det.false_positives.map(function (x) { return x.id + " (" + x.label + "; " + x.flags.join(", ") + ")"; }).join("; ")
    : "none";
  $("det-fp").appendChild(h("p", {}, h("b", { text: "Static only: " }), pct(det.static_only_recall) + " recall. ", h("b", { text: "Dynamic only: " }), pct(det.dynamic_only_recall) + " recall. Combining both is what closes the gaps."));
  $("det-fp").appendChild(h("p", {}, h("b", { text: "False positives: " }), fpText));
  $("det-fp").appendChild(h("p", {}, h("b", { text: "Missed hacks: " }), det.false_negatives.length ? det.false_negatives.join(", ") : "none"));

  // ---- pair ranking chart
  function stacked() {
    var rows = [["naive", "Naive"], ["strict", "Strict"], ["combined", "Naive + detector"]];
    var W = 560, Ht = 190, left = 130, bh = 26, total = S.pairs.n;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + Ht, width: "100%", role: "img", "aria-label": "Agreement of each reward signal with the intended ranking" });
    var cols = [["correct", "agrees", "#5fd3a5"], ["tie", "tie", "#8a97ab"], ["wrong", "disagrees", "#ff6b81"]];
    rows.forEach(function (r, i) {
      var y = 18 + i * 46, x = left, st = S.pairs[r[0]];
      svg.appendChild(s("text", { x: left - 10, y: y + 17, "text-anchor": "end" }, r[1]));
      cols.forEach(function (c) {
        var w = st[c[0]] / total * (W - left - 10);
        svg.appendChild(s("rect", { x: x, y: y, width: Math.max(w, 0), height: bh, fill: c[2], rx: 2 }));
        if (w > 34) svg.appendChild(s("text", { x: x + w / 2, y: y + 17, "text-anchor": "middle", fill: "#04110d", style: "fill:#04110d;font-weight:700" }, String(st[c[0]])));
        x += w;
      });
    });
    cols.forEach(function (c, i) {
      svg.appendChild(s("rect", { x: left + i * 110, y: Ht - 18, width: 10, height: 10, fill: c[2], rx: 2 }));
      svg.appendChild(s("text", { x: left + i * 110 + 15, y: Ht - 9 }, c[1]));
    });
    return svg;
  }
  $("chart-pairs").appendChild(stacked());

  // ---- pairs browser
  var ps = { type: "", problem: "", selected: P.length ? P[0].id : null };
  var ptSel = $("pair-type"), ppSel = $("pair-problem");
  ptSel.appendChild(h("option", { value: "", text: "All types" }));
  Object.keys(S.pairs.types).forEach(function (t) { ptSel.appendChild(h("option", { value: t, text: t + " (" + S.pairs.types[t] + ")" })); });
  ppSel.appendChild(h("option", { value: "", text: "All problems" }));
  S.problems.forEach(function (p) { ppSel.appendChild(h("option", { value: p.name, text: p.title })); });
  ptSel.addEventListener("change", function () { ps.type = ptSel.value; renderPairs(); });
  ppSel.addEventListener("change", function () { ps.problem = ppSel.value; renderPairs(); });

  function renderPairs() {
    var vis = P.filter(function (p) { return (!ps.type || p.type === ps.type) && (!ps.problem || p.problem === ps.problem); });
    if (!vis.some(function (p) { return p.id === ps.selected; })) ps.selected = vis.length ? vis[0].id : null;
    $("pair-count").textContent = vis.length + " of " + P.length + " pairs";
    var lst = $("pair-list");
    lst.textContent = "";
    vis.forEach(function (p) {
      var b = h("button", { type: "button", "aria-current": String(p.id === ps.selected), text: p.id.replace(":pair", " #") });
      b.addEventListener("click", function () { ps.selected = p.id; renderPairs(); });
      lst.appendChild(b);
    });
    var d = $("pair-detail");
    d.textContent = "";
    var p = vis.filter(function (x) { return x.id === ps.selected; })[0];
    if (!p) { d.appendChild(h("p", { "class": "muted", text: "No pairs match these filters." })); return; }
    var ch = byId[p.chosen], rj = byId[p.rejected];
    d.appendChild(h("h3", { text: p.id + "  ·  " + p.type }));
    d.appendChild(h("div", { "class": "critique" }, h("b", { text: "Critique of the rejected solution. " }), p.critique));
    d.appendChild(h("div", { "class": "sbs" },
      h("div", {}, h("h4", { "class": "chosen", text: "Chosen: " + ch.kind + " (" + nice(ch.label) + ")" }), codeView(ch.code, flagLines(ch))),
      h("div", {}, h("h4", { "class": "rejected", text: "Rejected: " + rj.kind + " (" + nice(rj.label) + ")" }), codeView(rj.code, flagLines(rj)))));
    var rb = p.rubric;
    d.appendChild(h("table", { "class": "rubric" },
      h("tr", {}, h("th", { text: "Rubric (0-5)" }), h("th", { text: "chosen" }), h("th", { text: "rejected" })),
      Object.keys(rb).map(function (k) { return h("tr", {}, h("td", { text: k.replace("_", " ") }), h("td", { text: String(rb[k].chosen) }), h("td", { text: String(rb[k].rejected) })); })));
  }

  renderLab();
  renderPairs();
})();
