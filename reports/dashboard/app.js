const DATA_PATHS = {
  sidoAnnual: "../../data/processed/rolling_annual_prediction_comparisons.csv",
  sidoQuarter: "../../data/processed/rolling_quarterly_gva_predictions.csv",
  sigunguQuarter: "../../data/processed/sigungu_quarterly_gva_estimates.csv",
  sigunguAnnual: "../../data/processed/sigungu_denton_constraint_diagnostics.csv",
  emdInventory: "../../data/processed/eupmyeondong_source_inventory.csv",
};

const state = {
  data: {},
  rows: [],
};

const $ = (id) => document.getElementById(id);

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const header = rows.shift() || [];
  return rows
    .filter((items) => items.some((item) => item !== ""))
    .map((items) => Object.fromEntries(header.map((key, idx) => [key, items[idx] === undefined ? "" : items[idx]])));
}

async function loadCsv(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  const buffer = await response.arrayBuffer();
  const text = new TextDecoder("euc-kr").decode(buffer);
  return parseCsv(text);
}

function number(value) {
  if (value === undefined || value === null || value === "") return NaN;
  return Number(String(value).replaceAll(",", ""));
}

function fmt(value, digits = 0) {
  const n = number(value);
  if (!Number.isFinite(n)) return "-";
  return n.toLocaleString("ko-KR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function pct(value) {
  const n = number(value);
  if (!Number.isFinite(n)) return "-";
  return `${n.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}%`;
}

function unique(rows, getter) {
  return [...new Set(rows.map(getter).filter(Boolean))].sort((a, b) => a.localeCompare(b, "ko"));
}

function optionText(value, label) {
  return `<option value="${String(value).replaceAll('"', "&quot;")}">${label === undefined ? value : label}</option>`;
}

function setOptions(select, options, selected) {
  select.innerHTML = options.map(([value, label]) => optionText(value, label)).join("");
  if (selected && options.some(([value]) => value === selected)) select.value = selected;
}

function regionKey(row, level) {
  if (level === "sigungu") return row.sigungu_code;
  if (level === "emd") return row.table_id;
  return row.area_code;
}

function regionName(row, level) {
  if (level === "sigungu") return `${row.source_region} ${row.sigungu_name} (${row.sigungu_code})`;
  if (level === "emd") return `${row.source} ${row.table_id}`;
  return row.area_code;
}

function sectorKey(row, level) {
  if (level === "emd") return row.assessment || row.name;
  return row.sector_code;
}

function sectorName(row, level) {
  if (level === "emd") return row.assessment || row.name;
  return `${row.sector_name || row.sector_code} (${row.sector_code})`;
}

function periodKey(row, grain) {
  if (grain === "quarter") return row.period || `${row.target_year}Q${row.quarter}`;
  return String(row.target_year || row.year || row.period || "");
}

function periodNumber(period) {
  const text = String(period);
  const q = text.match(/^(\d{4})Q([1-4])$/);
  if (q) return Number(q[1]) * 10 + Number(q[2]);
  return Number(text.replace(/\D/g, ""));
}

function datasetFor(level, grain) {
  if (level === "emd") return state.data.emdInventory;
  if (level === "sigungu") return grain === "annual" ? state.data.sigunguAnnual : state.data.sigunguQuarter;
  return grain === "annual" ? state.data.sidoAnnual : state.data.sidoQuarter;
}

function valueFields(level, grain) {
  if (level === "sigungu" && grain === "annual") {
    return { predicted: "estimated_annual_sum", actual: "benchmark_annual_gva", error: "percent_constraint_error" };
  }
  if (level === "sigungu") {
    return { predicted: "estimated_gva", actual: "", error: "" };
  }
  if (grain === "annual") {
    return { predicted: "predicted_annual_gva", actual: "actual_annual_gva", error: "percent_error" };
  }
  return { predicted: "predicted_gva", actual: "", error: "" };
}

function refreshFilters(keep = {}) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const rows = datasetFor(level, grain) || [];
  const regions = unique(rows, (row) => regionKey(row, level)).map((key) => {
    const found = rows.find((row) => regionKey(row, level) === key);
    return [key, regionName(found, level)];
  });
  const sectors = unique(rows, (row) => sectorKey(row, level)).map((key) => {
    const found = rows.find((row) => sectorKey(row, level) === key);
    return [key, sectorName(found, level)];
  });
  setOptions($("regionSelect"), regions, keep.region);
  setOptions($("sectorSelect"), sectors, keep.sector);
  refreshPeriods(keep);
}

function refreshPeriods(keep = {}) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const rows = filteredBaseRows(false);
  const periods = unique(rows, (row) => periodKey(row, grain)).sort((a, b) => periodNumber(a) - periodNumber(b));
  const options = periods.map((period) => [period, period]);
  setOptions($("startSelect"), options, keep.start || periods[0]);
  setOptions($("endSelect"), options, keep.end || periods[periods.length - 1]);
}

function filteredBaseRows(applyPeriod = true) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const region = $("regionSelect").value;
  const sector = $("sectorSelect").value;
  const start = $("startSelect").value;
  const end = $("endSelect").value;
  let rows = [...(datasetFor(level, grain) || [])];
  if (region) rows = rows.filter((row) => regionKey(row, level) === region);
  if (sector) rows = rows.filter((row) => sectorKey(row, level) === sector);
  if (applyPeriod && start && end && level !== "emd") {
    const lo = Math.min(periodNumber(start), periodNumber(end));
    const hi = Math.max(periodNumber(start), periodNumber(end));
    rows = rows.filter((row) => {
      const p = periodNumber(periodKey(row, grain));
      return p >= lo && p <= hi;
    });
  }
  return rows;
}

function updateMessage(level, grain, rows) {
  const box = $("message");
  const messages = [];
  if (grain === "month") messages.push("현재 원천 데이터는 월간 예측값을 포함하지 않습니다. 연도 또는 분기를 선택해 주세요.");
  if (level === "emd") messages.push("읍면동은 아직 예측값이 아니라 자료 후보 인벤토리만 표시합니다.");
  if (level === "sigungu" && grain === "quarter") messages.push("시군구 분기 실제값은 공개되지 않아 예측값만 표시합니다. 연간 실제 벤치마크 비교는 시점 단위 '연도'에서 볼 수 있습니다.");
  if (!rows.length) messages.push("선택한 조건에 해당하는 행이 없습니다.");
  box.hidden = messages.length === 0;
  box.textContent = messages.join(" ");
}

function drawChart(rows) {
  const svg = $("chart");
  svg.innerHTML = "";
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  if (!rows.length || level === "emd" || grain === "month") {
    svg.innerHTML = `<text x="560" y="210" text-anchor="middle" class="tick">표시할 시계열이 없습니다.</text>`;
    return;
  }
  const fields = valueFields(level, grain);
  const points = rows
    .map((row) => ({
      period: periodKey(row, grain),
      predicted: number(row[fields.predicted]),
      actual: fields.actual ? number(row[fields.actual]) : NaN,
    }))
    .filter((row) => Number.isFinite(row.predicted))
    .sort((a, b) => periodNumber(a.period) - periodNumber(b.period));
  if (!points.length) return;

  const width = 1120;
  const height = 420;
  const margin = { left: 78, right: 26, top: 28, bottom: 58 };
  const xs = points.map((_, idx) => margin.left + (idx * (width - margin.left - margin.right)) / Math.max(1, points.length - 1));
  const values = points.flatMap((p) => [p.predicted, p.actual]).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min || max || 1) * 0.08;
  const lo = min - pad;
  const hi = max + pad;
  const y = (v) => margin.top + ((hi - v) / (hi - lo)) * (height - margin.top - margin.bottom);
  const x = (idx) => xs[idx];
  const path = (field) => points.map((p, idx) => `${idx ? "L" : "M"}${x(idx).toFixed(1)},${y(p[field]).toFixed(1)}`).join(" ");
  const actualPoints = points.filter((p) => Number.isFinite(p.actual));

  for (let i = 0; i <= 4; i += 1) {
    const gy = margin.top + (i * (height - margin.top - margin.bottom)) / 4;
    const val = hi - (i * (hi - lo)) / 4;
    svg.insertAdjacentHTML("beforeend", `<line x1="${margin.left}" x2="${width - margin.right}" y1="${gy}" y2="${gy}" class="grid"/>`);
    svg.insertAdjacentHTML("beforeend", `<text x="${margin.left - 10}" y="${gy + 4}" text-anchor="end" class="tick">${fmt(val)}</text>`);
  }
  svg.insertAdjacentHTML("beforeend", `<line x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}" class="axis"/>`);
  svg.insertAdjacentHTML("beforeend", `<line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" class="axis"/>`);
  svg.insertAdjacentHTML("beforeend", `<path d="${path("predicted")}" class="pred"/>`);
  if (actualPoints.length) svg.insertAdjacentHTML("beforeend", `<path d="${path("actual")}" class="actual"/>`);
  points.forEach((p, idx) => {
    svg.insertAdjacentHTML("beforeend", `<circle cx="${x(idx)}" cy="${y(p.predicted)}" r="4" class="dot-pred"/>`);
    if (Number.isFinite(p.actual)) svg.insertAdjacentHTML("beforeend", `<circle cx="${x(idx)}" cy="${y(p.actual)}" r="4" class="dot-actual"/>`);
    if (idx % Math.ceil(points.length / 10) === 0 || idx === points.length - 1) {
      svg.insertAdjacentHTML("beforeend", `<text x="${x(idx)}" y="${height - margin.bottom + 24}" text-anchor="middle" class="tick">${p.period}</text>`);
    }
  });
  svg.insertAdjacentHTML("beforeend", `<circle cx="860" cy="24" r="5" class="dot-pred"/><text x="872" y="29" class="legend">예측값</text>`);
  svg.insertAdjacentHTML("beforeend", `<circle cx="940" cy="24" r="5" class="dot-actual"/><text x="952" y="29" class="legend">실제값</text>`);
}

function updateMetrics(rows) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const fields = valueFields(level, grain);
  const comparable = rows.filter((row) => fields.actual && row[fields.actual] !== "" && Number.isFinite(number(row[fields.actual])));
  const errors = rows
    .map((row) => number(fields.error ? row[fields.error] : ""))
    .filter(Number.isFinite)
    .map(Math.abs);
  const latestItem = rows
    .map((row) => ({ row, p: periodNumber(periodKey(row, grain)) }))
    .sort((a, b) => b.p - a.p)[0];
  const latest = latestItem ? latestItem.row : null;
  $("metricRows").textContent = rows.length.toLocaleString("ko-KR");
  $("metricComparable").textContent = comparable.length.toLocaleString("ko-KR");
  $("metricMape").textContent = errors.length ? pct(errors.reduce((a, b) => a + b, 0) / errors.length) : "-";
  $("metricLatest").textContent = latest ? fmt(latest[fields.predicted], 0) : "-";
}

function renderTable(rows) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const fields = valueFields(level, grain);
  const table = $("resultTable");
  if (level === "emd") {
    const cols = ["source", "table_id", "name", "period", "dimensions", "assessment"];
    table.innerHTML = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${cols.map((c) => `<td>${row[c] || ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
    return;
  }
  const mapped = rows
    .sort((a, b) => periodNumber(periodKey(a, grain)) - periodNumber(periodKey(b, grain)))
    .map((row) => ({
      period: periodKey(row, grain),
      region: level === "sigungu" ? row.sigungu_name : row.area_code,
      sector: row.sector_name,
      predicted: fmt(row[fields.predicted], 3),
      actual: fields.actual ? fmt(row[fields.actual], 3) : "-",
      error: fields.error ? pct(row[fields.error]) : "-",
      method: row.method || "",
    }));
  const cols = ["period", "region", "sector", "predicted", "actual", "error", "method"];
  table.innerHTML = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${mapped.map((row) => `<tr>${cols.map((c) => `<td>${row[c] || ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

function render() {
  const rows = filteredBaseRows(true);
  state.rows = rows;
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  updateMessage(level, grain, rows);
  updateMetrics(rows);
  $("chartTitle").textContent = level === "emd" ? "읍면동 자료 후보" : "예측값과 실제값";
  const regionOption = $("regionSelect").selectedOptions[0];
  const sectorOption = $("sectorSelect").selectedOptions[0];
  $("chartSubtitle").textContent = `${regionOption ? regionOption.textContent : ""} · ${sectorOption ? sectorOption.textContent : ""}`;
  drawChart(rows);
  renderTable(rows);
}

async function init() {
  try {
    const entries = await Promise.all(Object.entries(DATA_PATHS).map(async ([key, path]) => [key, await loadCsv(path)]));
    state.data = Object.fromEntries(entries);
    $("loadStatus").textContent = "CSV 로딩 완료";
  } catch (error) {
    $("loadStatus").textContent = "CSV 로딩 실패";
    $("message").hidden = false;
    $("message").textContent = `CSV를 불러오지 못했습니다. repo root에서 'python -m http.server'로 실행한 뒤 http://localhost:8000/reports/dashboard/ 로 접속해 주세요. (${error.message})`;
    return;
  }
  ["levelSelect", "grainSelect"].forEach((id) => {
    $(id).addEventListener("change", () => refreshFilters());
  });
  ["regionSelect", "sectorSelect"].forEach((id) => {
    $(id).addEventListener("change", () => {
      refreshPeriods({ region: $("regionSelect").value, sector: $("sectorSelect").value });
      render();
    });
  });
  ["startSelect", "endSelect"].forEach((id) => $(id).addEventListener("change", render));
  refreshFilters();
  render();
}

init();
