const DATA = window.DASHBOARD_DATA;
const GEO = window.PROVINCE_FEATURES;
const SIGUNGU_GEO = window.SIGUNGU_FEATURES || { features: [] };

const regionSearch = document.querySelector("#regionSearch");
const regionOptions = document.querySelector("#regionOptions");
const industrySearch = document.querySelector("#industrySearch");
const industryOptions = document.querySelector("#industryOptions");
const openSelection = document.querySelector("#openSelection");
const mapSvg = document.querySelector("#mapSvg");
const dialog = document.querySelector("#regionDialog");
const closeDialog = document.querySelector("#closeDialog");
const industrySelect = document.querySelector("#industrySelect");
const searchStatus = document.querySelector("#searchStatus");
const zoomOutMap = document.querySelector("#zoomOutMap");
const zoomInMap = document.querySelector("#zoomInMap");

let selectedRegion = DATA.regions.find((r) => r.id === "sido:경기도") || DATA.regions[0];
let zoomedQuarterRegion = null;
const labelOffsets = {
  서울: [-10, -18],
  인천: [-30, 5],
  경기도: [34, -4],
  세종: [0, 22],
  대전: [18, 18],
  충남: [-24, 14],
  충북: [24, -10],
  대구: [22, 12],
  울산: [28, 6],
  부산: [30, 12],
};

function fmt(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "-";
  return Number(v).toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "-";
  return `${Number(v).toFixed(2)}%`;
}

function idSafe(value) {
  return String(value).replace(/[^a-zA-Z0-9가-힣_-]/g, "_");
}

function setupOptions() {
  regionOptions.innerHTML = DATA.regions
    .map((r) => `<option value="${r.name}"></option>`)
    .join("");
  industryOptions.innerHTML = DATA.industries.map((x) => `<option value="${x}"></option>`).join("");
  industrySelect.innerHTML = DATA.industries.map((x) => `<option value="${x}">${x}</option>`).join("");
}

function findRegion(query) {
  const q = String(query || "").trim();
  if (!q) return { region: selectedRegion };
  const exactName = DATA.regions.filter((r) => r.name === q);
  if (exactName.length === 1) return { region: exactName[0] };
  const exactShort = DATA.regions.filter((r) => r.shortName === q);
  if (exactShort.length === 1) return { region: exactShort[0] };
  if (exactShort.length > 1) {
    return { error: `"${q}" 후보가 여러 개입니다: ${exactShort.slice(0, 8).map((r) => r.name).join(", ")}${exactShort.length > 8 ? "…" : ""}` };
  }
  const partial = DATA.regions.filter((r) => r.name.includes(q) || r.shortName.includes(q));
  if (partial.length === 1) return { region: partial[0] };
  if (partial.length > 1) {
    return { error: `"${q}" 후보가 여러 개입니다. 광역명까지 입력하세요: ${partial.slice(0, 8).map((r) => r.name).join(", ")}${partial.length > 8 ? "…" : ""}` };
  }
  return { error: `"${q}" 검색 결과가 없습니다.` };
}

function findIndustry(query) {
  const q = String(query || "전체").trim();
  if (!q) return { industry: "전체" };
  if (DATA.industries.includes(q)) return { industry: q };
  const partial = DATA.industries.filter((x) => x.includes(q));
  if (partial.length === 1) return { industry: partial[0] };
  if (partial.length > 1) return { error: `"${q}" 업종 후보가 여러 개입니다: ${partial.join(", ")}` };
  return { error: `"${q}" 업종 검색 결과가 없습니다.` };
}

function geoBounds() {
  const coords = [];
  for (const f of GEO.features) {
    collectCoords(f.geometry.coordinates, coords);
  }
  const xs = coords.map((d) => d[0]);
  const ys = coords.map((d) => d[1]);
  return {
    minLon: Math.min(...xs),
    maxLon: Math.max(...xs),
    minLat: Math.min(...ys),
    maxLat: Math.max(...ys),
  };
}

function collectCoords(node, out) {
  if (typeof node[0] === "number") {
    out.push(node);
    return;
  }
  for (const child of node) collectCoords(child, out);
}

const bounds = geoBounds();
const W = 720;
const H = 900;
const P = 30;

function project([lon, lat]) {
  const x = P + ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * (W - P * 2);
  const y = H - P - ((lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * (H - P * 2);
  return [x, y];
}

function pathFromGeometry(geometry) {
  const polys = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  return polys
    .map((poly) =>
      poly
        .map((ring) =>
          ring
            .map((pt, idx) => {
              const [x, y] = project(pt);
              return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ") + " Z",
        )
        .join(" "),
    )
    .join(" ");
}

function projectedBounds(features) {
  const coords = [];
  for (const f of features) collectCoords(f.geometry.coordinates, coords);
  if (!coords.length) return { x0: 0, y0: 0, x1: W, y1: H };
  const projected = coords.map((pt) => project(pt));
  return {
    x0: Math.min(...projected.map((p) => p[0])),
    y0: Math.min(...projected.map((p) => p[1])),
    x1: Math.max(...projected.map((p) => p[0])),
    y1: Math.max(...projected.map((p) => p[1])),
  };
}

function setViewToFeatures(features) {
  if (!features || !features.length) {
    mapSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    return;
  }
  const b = projectedBounds(features);
  const pad = 34;
  const vx = Math.max(0, b.x0 - pad);
  const vy = Math.max(0, b.y0 - pad);
  const vw = Math.min(W - vx, b.x1 - b.x0 + pad * 2);
  const vh = Math.min(H - vy, b.y1 - b.y0 + pad * 2);
  mapSvg.setAttribute("viewBox", `${vx.toFixed(1)} ${vy.toFixed(1)} ${vw.toFixed(1)} ${vh.toFixed(1)}`);
}

function zoomToProvince(quarterRegion) {
  zoomedQuarterRegion = quarterRegion;
  const region = DATA.regions.find((r) => r.id === `sido:${quarterRegion}`);
  if (region) selectedRegion = region;
  regionSearch.value = region ? region.name : "";
  searchStatus.textContent = `${region ? region.name : quarterRegion} 시군구 경계를 표시했습니다. 경계 또는 마커를 선택하세요.`;
  drawMap();
}

function drawMap() {
  mapSvg.innerHTML = "";
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("id", "mapLayer");
  mapSvg.appendChild(g);
  const sigunguFeatures = zoomedQuarterRegion
    ? SIGUNGU_GEO.features.filter((f) => f.properties.quarter_region === zoomedQuarterRegion)
    : [];

  for (const f of GEO.features) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathFromGeometry(f.geometry));
    path.setAttribute("class", `province${zoomedQuarterRegion && f.properties.quarter_region !== zoomedQuarterRegion ? " dimmed" : ""}`);
    path.setAttribute("tabindex", "0");
    path.setAttribute("role", "button");
    path.setAttribute("aria-label", `${f.properties.name} 선택`);
    path.dataset.region = f.properties.quarter_region;
    path.insertAdjacentHTML("afterbegin", `<title>${f.properties.name}</title>`);
    path.addEventListener("click", () => {
      zoomToProvince(f.properties.quarter_region);
    });
    path.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        zoomToProvince(f.properties.quarter_region);
      }
    });
    g.appendChild(path);
  }
  for (const f of sigunguFeatures) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathFromGeometry(f.geometry));
    path.setAttribute("class", "sigungu-boundary");
    path.setAttribute("tabindex", "0");
    path.setAttribute("role", "button");
    path.setAttribute("aria-label", `${f.properties.name} 선택`);
    path.dataset.regionId = f.properties.id;
    path.insertAdjacentHTML("afterbegin", `<title>${f.properties.name}</title>`);
    path.addEventListener("click", () => {
      const region = DATA.regions.find((r) => r.id === f.properties.id);
      if (region) openRegion(region, "전체");
    });
    path.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        const region = DATA.regions.find((r) => r.id === f.properties.id);
        if (region) openRegion(region, "전체");
      }
    });
    g.appendChild(path);
  }
  for (const f of GEO.features) {
    const region = DATA.regions.find((r) => r.id === `sido:${f.properties.quarter_region}`);
    if (!region) continue;
    const [x0, y0] = project([region.lon, region.lat]);
    const [dx, dy] = labelOffsets[region.shortName] || [0, 0];
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("class", "province-label");
    label.setAttribute("x", x0 + dx);
    label.setAttribute("y", y0 + dy);
    label.textContent = region.shortName;
    mapSvg.appendChild(label);
  }
  drawMarker(selectedRegion, false);
  if (sigunguFeatures.length) setViewToFeatures(sigunguFeatures);
  else mapSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
}

function drawMarker(region, zoom) {
  mapSvg.querySelectorAll(".region-marker").forEach((el) => el.remove());
  mapSvg.querySelectorAll(".province").forEach((el) => {
    el.classList.toggle("active", el.dataset.region === region.quarterRegion);
  });
  mapSvg.querySelectorAll(".sigungu-boundary").forEach((el) => {
    el.classList.toggle("active", el.dataset.regionId === region.id);
  });
  const [x, y] = project([region.lon, region.lat]);
  const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  marker.setAttribute("class", "region-marker");
  marker.setAttribute("cx", x);
  marker.setAttribute("cy", y);
  marker.setAttribute("r", region.type === "sido" ? 9 : 7);
  mapSvg.appendChild(marker);
  if (!zoom) {
    mapSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    return;
  }
  const viewW = region.type === "sido" ? 540 : 310;
  const viewH = region.type === "sido" ? 660 : 380;
  const vx = Math.max(0, Math.min(W - viewW, x - viewW / 2));
  const vy = Math.max(0, Math.min(H - viewH, y - viewH / 2));
  mapSvg.setAttribute("viewBox", `${vx} ${vy} ${viewW} ${viewH}`);
}

function openRegion(region, industry = "전체") {
  selectedRegion = region;
  zoomedQuarterRegion = region.quarterRegion;
  searchStatus.textContent = "";
  regionSearch.value = region.name;
  industrySearch.value = industry;
  industrySelect.value = industry;
  drawMap();
  renderDialog(region, industry);
  if (!dialog.open) dialog.showModal();
}

function selectedMetric(region) {
  return DATA.metrics[region.id];
}

function renderDialog(region, industry) {
  const metric = selectedMetric(region);
  document.querySelector("#dialogType").textContent = region.type === "sido" ? "시도 GRDP" : "시군구 GVA 추정 / GRDP형 참고값";
  document.querySelector("#dialogTitle").textContent = region.name;
  document.querySelector("#dialogSubtitle").textContent =
    region.type === "sido"
      ? "공식 시도 GRDP actual과 추정 GRDP 비교"
      : "시군구 공개 GVA actual과 추정 GVA, 순생산물세 배분형 GRDP 참고값 표시";
  document.querySelector("#actualCoverage").textContent =
    region.type === "sido"
      ? "시도 GRDP actual: 2021–2025 제공 범위"
      : "시군구 공개 GVA actual: 주로 2021–2023 · 2024–2025는 추정 구간";
  document.querySelector("#coordinateBasis").textContent = `지도 이동 기준: ${region.coordinateBasis || "행정구역 대표점"}`;
  const sources = (metric && metric.actualSources) || [];
  document.querySelector("#actualSource").innerHTML = sources.length
    ? sources
        .slice(0, 4)
        .map((s) => `<li><b>${s.title}</b><span>${s.role || ""}${s.latestChangeDate ? ` · 최신변경 ${s.latestChangeDate}` : ""}</span></li>`)
        .join("")
    : "<li>actual 출처 정보 없음</li>";

  const total = (metric && metric.total) || [];
  drawLineChart(
    "#totalChart",
    total,
    region.type === "sido" ? "estimated_grdp_eok" : "estimated_gva_total_eok",
    region.type === "sido" ? "actual_grdp_eok" : "actual_gva_total_eok",
    region.type === "sido" ? "추정 GRDP" : "추정 GVA",
    region.type === "sido" ? "공식 actual" : "공개 GVA actual",
  );
  document.querySelector("#totalChartTitle").textContent =
    region.type === "sido" ? "연도별 GRDP 추정·공식 actual" : "연도별 추정 GVA · 공개 GVA actual";

  const metricIndustries = (metric && metric.industries) || [];
  const industryRows = industry === "전체" ? [] : metricIndustries.filter((r) => r.activity === industry);
  if (industry === "전체") {
    drawEmptyChart("#industryChart", "업종 합산은 중복 가능성이 있어 표시하지 않습니다. 업종을 선택하세요.");
  } else {
    drawLineChart("#industryChart", industryRows, "estimated_gva_eok", "actual_gva_eok", "추정 GVA", "공개 actual");
  }
  document.querySelector("#industryChartTitle").textContent = industry === "전체" ? "업종별 GVA 비교" : `${industry} GVA 추정·공개 actual 비교`;
  renderOperatingCard(region, metric);
  renderTable(region, industry, total, industryRows);
  renderNotes(region, metric);
}

function summarizeIndustry(rows) {
  const byYear = new Map();
  for (const r of rows) {
    if (!byYear.has(r.year)) byYear.set(r.year, { year: r.year, estimated_gva_eok: 0, actual_gva_eok: 0, actual_count: 0 });
    const x = byYear.get(r.year);
    x.estimated_gva_eok += Number(r.estimated_gva_eok || 0);
    if (r.actual_gva_eok !== null && r.actual_gva_eok !== undefined) {
      x.actual_gva_eok += Number(r.actual_gva_eok || 0);
      x.actual_count += 1;
    }
  }
  return [...byYear.values()].map((r) => {
    if (!r.actual_count) return { ...r, actual_gva_eok: null, abs_error_eok: null, ape_pct: null };
    const err = Math.abs(r.estimated_gva_eok - r.actual_gva_eok);
    return { ...r, abs_error_eok: err, ape_pct: r.actual_gva_eok ? (err / Math.abs(r.actual_gva_eok)) * 100 : null };
  });
}

function chartExtent(rows, keys) {
  const vals = rows.flatMap((r) => keys.map((k) => Number(r[k])).filter((v) => Number.isFinite(v) && v > 0));
  if (!vals.length) return [0, 1];
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const pad = (max - min || max || 1) * 0.15;
  return [Math.max(0, min - pad), max + pad];
}

function drawEmptyChart(selector, message) {
  const svg = document.querySelector(selector);
  svg.innerHTML = "";
  const chunks = message.length > 34 ? [message.slice(0, 34), message.slice(34)] : [message];
  svg.insertAdjacentHTML(
    "beforeend",
    `<text x="380" y="150" text-anchor="middle" class="chart-label">${chunks
      .map((line, idx) => `<tspan x="380" dy="${idx ? 18 : 0}">${line}</tspan>`)
      .join("")}</text>`,
  );
}

function drawLineChart(selector, rows, estimateKey, actualKey, estimateLabel, actualLabel) {
  const svg = document.querySelector(selector);
  svg.innerHTML = "";
  const width = 760, height = 320, left = 70, right = 24, top = 24, bottom = 42;
  const data = rows.slice().sort((a, b) => Number(a.year) - Number(b.year));
  if (!data.length) {
    drawEmptyChart(selector, "표시할 데이터가 없습니다");
    return;
  }
  const years = data.map((r) => Number(r.year));
  const [minY, maxY] = chartExtent(data, [estimateKey, actualKey]);
  const x = (year) => left + ((year - Math.min(...years)) / Math.max(1, Math.max(...years) - Math.min(...years))) * (width - left - right);
  const y = (val) => height - bottom - ((Number(val) - minY) / Math.max(1, maxY - minY)) * (height - top - bottom);

  for (let i = 0; i < 4; i += 1) {
    const gy = top + (i / 3) * (height - top - bottom);
    const tickValue = maxY - (i / 3) * (maxY - minY);
    svg.insertAdjacentHTML("beforeend", `<line class="grid-line" x1="${left}" y1="${gy}" x2="${width - right}" y2="${gy}"/>`);
    svg.insertAdjacentHTML("beforeend", `<text class="chart-label" x="${left - 8}" y="${gy + 4}" text-anchor="end">${fmt(tickValue, 0)}</text>`);
  }
  svg.insertAdjacentHTML("beforeend", `<line class="axis" x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}"/>`);
  svg.insertAdjacentHTML("beforeend", `<line class="axis" x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}"/>`);

  for (const r of data) {
    svg.insertAdjacentHTML("beforeend", `<text class="chart-label" x="${x(Number(r.year))}" y="${height - 14}" text-anchor="middle">${r.year}</text>`);
  }
  svg.insertAdjacentHTML("beforeend", `<text class="legend" x="${left}" y="16" fill="#1769aa">● ${estimateLabel || "추정"}</text><text class="legend" x="${left + 190}" y="16" fill="#d95757">● ${actualLabel || "actual"}</text>`);

  const line = (key) =>
    data
      .filter((r) => r[key] !== null && r[key] !== undefined)
      .map((r, i) => `${i === 0 ? "M" : "L"}${x(Number(r.year)).toFixed(1)},${y(r[key]).toFixed(1)}`)
      .join(" ");
  svg.insertAdjacentHTML("beforeend", `<path class="line-est" d="${line(estimateKey)}"/>`);
  svg.insertAdjacentHTML("beforeend", `<path class="line-act" d="${line(actualKey)}"/>`);
  for (const r of data) {
    if (r[estimateKey] !== null && r[estimateKey] !== undefined) svg.insertAdjacentHTML("beforeend", `<circle class="dot-est" cx="${x(Number(r.year))}" cy="${y(r[estimateKey])}" r="4"/>`);
    if (r[actualKey] !== null && r[actualKey] !== undefined) svg.insertAdjacentHTML("beforeend", `<circle class="dot-act" cx="${x(Number(r.year))}" cy="${y(r[actualKey])}" r="4"/>`);
  }
}

function renderTable(region, industry, total, industryRows) {
  const table = document.querySelector("#valueTable");
  const rows = industry === "전체" ? total : industryRows;
  const isSido = region.type === "sido";
  const headers =
    industry === "전체"
      ? isSido
        ? [
            ["연도", ""],
            ["추정 GRDP", "억원"],
            ["실제 GRDP", "억원"],
            ["오차", "억원"],
            ["오차율", "%"],
          ]
        : [
            ["연도", ""],
            ["GRDP형 추정", "억원"],
            ["추정 GVA", "억원"],
            ["실제 GVA", "억원"],
            ["GVA 오차율", "%"],
          ]
      : [
          ["연도", ""],
          ["추정 GVA", "억원"],
          ["실제 GVA", "억원"],
          ["오차", "억원"],
          ["오차율", "%"],
        ];
  const body = rows
    .slice()
    .sort((a, b) => Number(a.year) - Number(b.year))
    .map((r) => {
      if (industry === "전체" && isSido) {
        return `<tr><td>${r.year}</td><td>${fmt(r.estimated_grdp_eok)}</td><td>${fmt(r.actual_grdp_eok)}</td><td>${fmt(r.abs_error_eok)}</td><td>${fmtPct(r.ape_pct)}</td></tr>`;
      }
      if (industry === "전체") {
        return `<tr><td>${r.year}</td><td>${fmt(r.estimated_grdp_like_eok)}</td><td>${fmt(r.estimated_gva_total_eok)}</td><td>${fmt(r.actual_gva_total_eok)}</td><td>${fmtPct(r.gva_ape_pct)}</td></tr>`;
      }
      return `<tr><td>${r.year}</td><td>${fmt(r.estimated_gva_eok)}</td><td>${fmt(r.actual_gva_eok)}</td><td>${fmt(r.abs_error_eok)}</td><td>${fmtPct(r.ape_pct)}</td></tr>`;
    })
    .join("");
  table.innerHTML = `<table><thead><tr>${headers.map(([h, unit]) => `<th>${h}${unit ? `<br><small>${unit}</small>` : ""}</th>`).join("")}</tr></thead><tbody>${body || `<tr><td colspan="${headers.length}">표시할 데이터가 없습니다</td></tr>`}</tbody></table>`;
}

function renderNotes(region, metric) {
  const notes = [...DATA.notes];
  if (region.coordinateStatus === "admin_office_coordinate_not_yet_sourced") {
    notes.push("현재 지도 마커는 도청·시청·군청·구청 청사 좌표가 아니라 행정구역 도형 내부 대표점이다.");
  }
  if (region.type === "sido" && ["인천", "울산", "세종", "대구", "충북"].includes(region.quarterRegion)) {
    notes.push("이 지역은 5개년 검증에서 상대적으로 어려운 지역으로 분류되어 Q1·Q1~Q2 조기점검 보조 추정값도 함께 보유한다.");
  }
  if (region.type === "sigungu") {
    notes.push("시군구 공개 GVA actual 비교는 현재 2021~2023년 중심이며, 2024~2025년 시군구 actual은 미공표/미확보로 검증오차를 산출하지 않는다.");
    notes.push("GRDP형 참고값은 추정 GVA에 시도 순생산물세·기타항목을 배분한 값이며, 공개 GVA actual과 직접 오차 비교하지 않는다.");
  }
  document.querySelector("#regionNotes").innerHTML = notes.map((n) => `<li>${n}</li>`).join("");
}

function renderOperatingCard(region, metric) {
  const card = document.querySelector("#operatingCard");
  const box = document.querySelector("#operatingSummary");
  const hard = ["인천", "울산", "세종", "대구", "충북"].includes(region.quarterRegion);
  if (!hard || !metric || !metric.operating) {
    card.hidden = true;
    return;
  }
  const q1 = metric.operating.filter((r) => r.available_quarters === 1 && r.rolling_routed_annualized_predicted_grdp_eok !== null);
  const q2 = metric.operating.filter((r) => r.available_quarters === 2 && r.rolling_routed_annualized_predicted_grdp_eok !== null);
  if (!q1.length && !q2.length) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const latestQ1 = q1[q1.length - 1] || {};
  const latestQ2 = q2[q2.length - 1] || {};
  const diagnostics = ((DATA.hardRegionDiagnostics || {})[region.quarterRegion] || []).slice(0, 5);
  const diagnosticRows = diagnostics
    .map(
      (r) => `<tr>
        <td>${r.activity}</td>
        <td>${fmtPct(r.annualized_wape_pct)}</td>
        <td>${fmtPct(r.max_annualized_ape_pct)}</td>
        <td>${fmt(r.years_over_10pct, 0)}</td>
        <td>${r.cause_class || "-"}</td>
        <td>${r.needed_direct_data || "-"}</td>
        <td>${r.candidate_action || "-"}</td>
      </tr>`,
    )
    .join("");
  box.innerHTML = `
    <div class="stat-grid compact">
      <div><strong>${fmtPct(latestQ1.annualized_ape_pct)}</strong><span>Q1 기본 최신연도 오차율</span></div>
      <div><strong>${fmtPct(latestQ1.rolling_routed_ape_pct)}</strong><span>Q1 보조 최신연도 오차율</span></div>
      <div><strong>${fmtPct(latestQ2.annualized_ape_pct)}</strong><span>Q1~Q2 기본 최신연도 오차율</span></div>
      <div><strong>${fmtPct(latestQ2.rolling_routed_ape_pct)}</strong><span>Q1~Q2 보조 최신연도 오차율</span></div>
      <div><strong>3.417% → 2.948%</strong><span>5개 어려운 시도 Q1 WAPE</span></div>
      <div><strong>2.863% → 2.503%</strong><span>5개 어려운 시도 Q1~Q2 WAPE</span></div>
    </div>
    <div class="warning-tile"><strong>자동채택 금지</strong><span>1~3분기·정밀화에서는 악화 확인. 보조지표는 Q1·Q1~Q2 조기점검 참고값으로 제한한다.</span></div>
    <div class="diagnostic-panel">
      <h4>1분기+1개월 기준 취약 업종 TOP 5</h4>
      <p>2021–2025년 Q1(1분기+1개월) 속보 운영시점 기준 진단이다. Q1~Q2 보조 성과와는 별도이며, 보조지표 적용이 업종별로 항상 개선된다는 뜻은 아니다.</p>
      <p class="scroll-hint">좌우로 스크롤해 필요 직접자료와 개선/보강 방향까지 확인</p>
      <table>
        <thead>
          <tr><th>업종</th><th>5개년 WAPE(%)</th><th>최대 연도 오차율(%)</th><th>10% 초과 연도</th><th>주요 원인</th><th>필요 직접자료</th><th>개선/보강 방향</th></tr>
        </thead>
        <tbody>${diagnosticRows || `<tr><td colspan="7">취약 업종 진단 데이터가 없습니다</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function handleOpen() {
  const resolved = findRegion(regionSearch.value);
  if (resolved.error) {
    searchStatus.textContent = resolved.error;
    return;
  }
  const industry = findIndustry(industrySearch.value);
  if (industry.error) {
    searchStatus.textContent = industry.error;
    return;
  }
  openRegion(resolved.region, industry.industry);
}

openSelection.addEventListener("click", handleOpen);
regionSearch.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleOpen();
});
industrySearch.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleOpen();
});
industrySelect.addEventListener("change", () => {
  industrySearch.value = industrySelect.value;
  renderDialog(selectedRegion, industrySelect.value);
});
closeDialog.addEventListener("click", () => dialog.close());
zoomOutMap.addEventListener("click", () => {
  zoomedQuarterRegion = null;
  searchStatus.textContent = "전국 지도로 돌아왔습니다.";
  drawMap();
});
zoomInMap.addEventListener("click", () => {
  zoomToProvince(selectedRegion.quarterRegion);
});

setupOptions();
drawMap();
