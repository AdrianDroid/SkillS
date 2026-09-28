(function () {
  const app = document.getElementById("app");

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function cell(v, n) {
    if (v === null || v === undefined || v === "") return "N/A";
    if (typeof v === "number") return v.toFixed(n);
    return esc(v);
  }

  function byCode(universe) {
    const m = {};
    (universe || []).forEach((r) => {
      m[r.code] = r;
    });
    return m;
  }

  function pickTable(items, u) {
    return items
      .map((p) => {
        const r = u[p.code] || {};
        return `<tr>
          <td>${esc(p.code)}</td><td>${esc(r.name || "")}</td>
          <td>${cell(r.ret_1y, 1)}</td><td>${cell(r.ret_3y, 1)}</td>
          <td>${cell(r.ret_5y, 1)}</td><td>${cell(r.ter, 2)}</td>
          <td class="reason">${esc(p.reason)}</td></tr>`;
      })
      .join("");
  }

  function ageTable(items, u) {
    return items
      .map((p) => {
        const r = u[p.code] || {};
        return `<tr>
          <td>${esc(p.code)}</td><td>${esc(r.name || "")}</td>
          <td>${esc(r.house || "")}</td>
          <td>${esc(p.weight)}%</td>
          <td>${cell(r.ret_1y, 1)}</td><td>${cell(r.ret_3y, 1)}</td>
          <td>${cell(r.ret_5y, 1)}</td>
          <td class="reason">${esc(p.reason)}</td></tr>`;
      })
      .join("");
  }

  function renderUniverse(list) {
    return (list || [])
      .map(
        (r) => `<tr>
      <td>${esc(r.code)}</td><td>${esc(r.name)}</td><td>${esc(r.house)}</td>
      <td>${esc(r.type)}</td>
      <td>${cell(r.nav, 4)}</td><td>${cell(r.ret_1y, 1)}</td>
      <td>${cell(r.ret_3y, 1)}</td><td>${cell(r.ret_5y, 1)}</td>
      <td>${cell(r.ter, 2)}</td></tr>`
      )
      .join("");
  }

  function bindSort(universe) {
    let sortKey = "code",
      sortDir = 1;
    const keys = ["code", "name", "house", "type", "nav", "ret_1y", "ret_3y", "ret_5y", "ter"];
    document.querySelectorAll("#all-funds th").forEach((th) => {
      th.addEventListener("click", () => {
        const idx = [...th.parentNode.children].indexOf(th);
        const key = keys[idx];
        const num = th.dataset.sort === "num";
        if (sortKey === key) sortDir *= -1;
        else {
          sortKey = key;
          sortDir = 1;
        }
        const copy = universe.slice().sort((a, b) => {
          const av = a[key],
            bv = b[key];
          const aN = av === null || av === undefined || av === "";
          const bN = bv === null || bv === undefined || bv === "";
          if (aN && bN) return 0;
          if (aN) return 1;
          if (bN) return -1;
          if (num) return (av - bv) * sortDir;
          return String(av).localeCompare(String(bv), "zh-Hant") * sortDir;
        });
        document.querySelector("#all-funds tbody").innerHTML = renderUniverse(copy);
      });
    });
  }

  function bindTabs() {
    document.querySelectorAll(".tabs button").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const el = document.getElementById(btn.dataset.tab);
        if (el) el.classList.add("active");
      });
    });
  }

  function paint(d) {
    const u = byCode(d.universe);
    const m = d.meta;
    document.title = (m.plan || "ILAS") + " 報告";
    const macroRows = (d.macro.rows || [])
      .map(
        (r) =>
          `<tr><td>${esc(r.indicator)}</td><td>${esc(r.value)}</td><td>${esc(r.date)}</td><td>${esc(r.source)}</td></tr>`
      )
      .join("");
    const feeP = (d.fees.paragraphs || []).map((p) => `<p>${esc(p)}</p>`).join("");
    const groups = (d.appendix.groups || [])
      .map((g) => {
        const lis = (g.links || [])
          .map((l) => `<li><a href="${esc(l.href)}">${esc(l.label)}</a></li>`)
          .join("");
        return `<h3>${esc(g.title)}</h3><ul>${lis}</ul>`;
      })
      .join("");

    app.innerHTML = `
<p><span class="pill">${esc(m.as_of)}</span> ${esc(m.nav_date || "")} · ${esc(String(m.fund_count))} 隻投資選擇${m.risk ? " · 風險 " + esc(m.risk) : ""}</p>
<h1>${esc(m.plan)}</h1>
<p class="sub">${esc(m.subtitle || "")}</p>
<div class="card disclaimer"><strong>免責：</strong>${esc(m.disclaimer)}</div>

<section id="macro">
<h2>1. 宏觀分析</h2>
<div class="card">
<table>
<thead><tr><th>指標</th><th>數值</th><th>日期</th><th>來源</th></tr></thead>
<tbody>${macroRows}</tbody>
</table>
<p><strong>主題判斷：</strong>${esc(d.macro.thesis)}</p>
<p><strong>對本計劃的含義：</strong>${esc(d.macro.ilas)}</p>
</div>
</section>

<section id="fees">
<h2>1b. 收費層</h2>
<div class="card">${feeP}</div>
</section>

<section id="universe">
<h2>2. 全部基金 1／3／5 年回報</h2>
<details class="universe" open>
<summary>展開／收合全部 ${esc(String(m.fund_count))} 隻（點欄位排序）</summary>
<p class="muted">N/A＝成立未滿或來源無數字。</p>
<div style="overflow:auto">
<table id="all-funds">
<thead><tr>
<th data-sort="str">代碼</th><th data-sort="str">名稱</th><th data-sort="str">公司</th><th data-sort="str">類型</th>
<th data-sort="num">NAV</th><th data-sort="num">1年%</th><th data-sort="num">3年年化%</th>
<th data-sort="num">5年年化%</th><th data-sort="num">OCF%</th>
</tr></thead>
<tbody>${renderUniverse(d.universe)}</tbody>
</table>
</div>
</details>
</section>

<section id="picks">
<h2>3. 短名單與挑選理由</h2>
<h3>增長型 10</h3>
<table>
<thead><tr><th>代碼</th><th>名稱</th><th>1年%</th><th>3年%</th><th>5年%</th><th>OCF%</th><th>理由</th></tr></thead>
<tbody>${pickTable(d.picks.growth, u)}</tbody>
</table>
<h3>收益／防禦 10</h3>
<table>
<thead><tr><th>代碼</th><th>名稱</th><th>1年%</th><th>3年%</th><th>5年%</th><th>OCF%</th><th>理由</th></tr></thead>
<tbody>${pickTable(d.picks.income, u)}</tbody>
</table>
</section>

<section id="ages">
<h2>4. 年齡組合</h2>
<p class="muted">${esc(d.ages.why_count)}</p>
<div class="tabs">
<button type="button" class="active" data-tab="age-60">60+</button>
<button type="button" data-tab="age-40">40s</button>
<button type="button" data-tab="age-20">20–30s</button>
</div>
<div id="age-60" class="panel active">
<h3>60 歲以上</h3>
<table>
<thead><tr><th>代碼</th><th>名稱</th><th>公司</th><th>權重</th><th>1年%</th><th>3年%</th><th>5年%</th><th>理由</th></tr></thead>
<tbody>${ageTable(d.ages.tabs["60+"], u)}</tbody>
</table>
</div>
<div id="age-40" class="panel">
<h3>40 歲</h3>
<table>
<thead><tr><th>代碼</th><th>名稱</th><th>公司</th><th>權重</th><th>1年%</th><th>3年%</th><th>5年%</th><th>理由</th></tr></thead>
<tbody>${ageTable(d.ages.tabs["40s"], u)}</tbody>
</table>
</div>
<div id="age-20" class="panel">
<h3>20–30 歲</h3>
<table>
<thead><tr><th>代碼</th><th>名稱</th><th>公司</th><th>權重</th><th>1年%</th><th>3年%</th><th>5年%</th><th>理由</th></tr></thead>
<tbody>${ageTable(d.ages.tabs["20-30s"], u)}</tbody>
</table>
</div>
</section>

<section id="appendix">
<details class="appendix">
<summary>5. 附錄／來源</summary>
<p>${esc(d.appendix.coverage)}</p>
${groups}
</details>
</section>`;
    bindSort(d.universe || []);
    bindTabs();
  }

  fetch("report.json", { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(paint)
    .catch((e) => {
      app.innerHTML = `<div class="err"><strong>無法載入 report.json</strong><p>${esc(e.message)}</p><p>請用 http.server 開此目錄（不可 file://），並確保同目錄有 report.json。</p></div>`;
    });
})();
