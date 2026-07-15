const DATA_PATHS = {
  sidoAnnual: "../../data/processed/rolling_annual_prediction_comparisons.csv",
  sidoQuarter: "../../data/processed/rolling_quarterly_gva_predictions.csv",
  sidoActual: "../../data/processed/rolling_annual_grva_real.csv",
  nationalQuarterActual: "../../data/processed/rolling_national_quarterly_gdp_real.csv",
  sigunguQuarter: "../../data/processed/sigungu_quarterly_gva_estimates.csv",
  sigunguAnnual: "../../data/processed/sigungu_denton_constraint_diagnostics.csv",
  seoulDistrictAnnual: "../../data/processed/seoul_district_grdp_annual.csv",
  detailQuarter: "../../data/processed/detailed_industry_quarterly_estimates.csv",
  detailAnnual: "../../data/processed/detailed_industry_annual_estimates.csv",
  emdQuarter: "../../data/processed/emd_quarterly_gva_estimates.csv",
  emdAnnual: "../../data/processed/emd_annual_gva_estimates.csv",
  emdInventory: "../../data/processed/eupmyeondong_source_inventory.csv",
};

const OPTIONAL_DATA_KEYS = new Set(["seoulDistrictAnnual", "detailQuarter", "detailAnnual", "emdQuarter", "emdAnnual"]);
const BASE_DATA_KEYS = ["sidoAnnual", "sidoQuarter", "sidoActual", "nationalQuarterActual", "sigunguQuarter", "sigunguAnnual", "seoulDistrictAnnual"];
const ALL_SECTOR = "__ALL__";
const TABLE_LIMIT = 500;

const DETAIL_LEVEL_LABELS = {
  middle: "중분류",
  small: "소분류",
  class: "세분류",
};

const REGION_CODE_NAMES = {
  "00": "전국",
  "11": "서울특별시",
  "21": "부산광역시",
  "22": "대구광역시",
  "23": "인천광역시",
  "24": "광주광역시",
  "25": "대전광역시",
  "26": "울산광역시",
  "29": "세종특별자치시",
  "31": "경기도",
  "32": "강원특별자치도",
  "33": "충청북도",
  "34": "충청남도",
  "35": "전북특별자치도",
  "36": "전라남도",
  "37": "경상북도",
  "38": "경상남도",
  "39": "제주특별자치도",
};

const SECTOR_TO_GDP_CODE = {
  A00: "13102136275ACC_ITEM.1101",
  B00: "13102136275ACC_ITEM.1102",
  C00: "13102136275ACC_ITEM.1103",
  D00: "13102136275ACC_ITEM.1104",
  F00: "13102136275ACC_ITEM.1105",
  G00: "13102136275ACC_ITEM.1106",
  H00: "13102136275ACC_ITEM.1107",
  I00: "13102136275ACC_ITEM.1106",
  J00: "13102136275ACC_ITEM.1114",
  K00: "13102136275ACC_ITEM.1108",
  L00: "13102136275ACC_ITEM.1109",
  MN0: "13102136275ACC_ITEM.1115",
  O00: "13102136275ACC_ITEM.1110",
  P00: "13102136275ACC_ITEM.1111",
  Q00: "13102136275ACC_ITEM.1112",
  ERS: "13102136275ACC_ITEM.1113",
};

const GDP_CODE_TO_SECTORS = Object.entries(SECTOR_TO_GDP_CODE).reduce((acc, [sector, code]) => {
  acc[code] = acc[code] || [];
  acc[code].push(sector);
  return acc;
}, {});
const UNIQUE_GDP_CODES = [...new Set(Object.values(SECTOR_TO_GDP_CODE))];

const state = {
  data: {},
  loading: {},
  rows: [],
  lookup: {
    areaNames: {},
    sectorNames: {},
    nationalQuarterBySector: {},
    nationalQuarterByCode: {},
    seoulDistrictAnnual: {},
  },
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

async function loadDataKey(key) {
  if (state.data[key]) return state.data[key];
  if (state.loading[key]) return state.loading[key];
  $("loadStatus").textContent = `${key} CSV 로딩 중`;
  state.loading[key] = loadCsv(DATA_PATHS[key])
    .then((rows) => {
      state.data[key] = rows;
      $("loadStatus").textContent = "CSV 로딩 완료";
      return rows;
    })
    .catch((error) => {
      if (OPTIONAL_DATA_KEYS.has(key)) {
        state.data[key] = [];
        $("loadStatus").textContent = "CSV 로딩 완료";
        return [];
      }
      throw error;
    })
    .finally(() => {
      delete state.loading[key];
    });
  return state.loading[key];
}

function dataKeyFor(level, grain) {
  if (level === "emd") return grain === "annual" ? "emdAnnual" : "emdQuarter";
  if (level === "detail") return grain === "annual" ? "detailAnnual" : "detailQuarter";
  if (level === "sigungu") return grain === "annual" ? "sigunguAnnual" : "sigunguQuarter";
  return grain === "annual" ? "sidoAnnual" : "sidoQuarter";
}

async function ensureLevelData(level, grain) {
  await loadDataKey(dataKeyFor(level, grain));
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

function escapeHtml(value) {
  return String(value === undefined || value === null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function optionText(value, label) {
  return `<option value="${escapeHtml(value)}">${escapeHtml(label === undefined ? value : label)}</option>`;
}

function setOptions(select, options, selected) {
  select.innerHTML = options.map(([value, label]) => optionText(value, label)).join("");
  if (selected && options.some(([value]) => value === selected)) select.value = selected;
}

function setGroupedOptions(select, groups, selected) {
  select.innerHTML = groups
    .map(({ label, options }) => `<optgroup label="${escapeHtml(label)}">${options.map(([value, text]) => optionText(value, text)).join("")}</optgroup>`)
    .join("");
  const flat = groups.flatMap((group) => group.options);
  if (selected && flat.some(([value]) => value === selected)) select.value = selected;
}

function uniqueOptions(rows, keyGetter, labelGetter) {
  const seen = new Map();
  rows.forEach((row) => {
    const key = keyGetter(row);
    if (!key || seen.has(key)) return;
    seen.set(key, labelGetter(row));
  });
  return [...seen.entries()].sort((a, b) => String(a[1]).localeCompare(String(b[1]), "ko"));
}

function buildLookups() {
  const areaNames = { ...REGION_CODE_NAMES };
  const sectorNames = {};
  (state.data.sidoActual || []).forEach((row) => {
    if (row.c1_id && row.c1_nm) areaNames[row.c1_id] = row.c1_nm;
    if (row.c2_id && row.c2_nm) sectorNames[row.c2_id] = row.c2_nm;
  });
  const nationalQuarterBySector = {};
  const nationalQuarterByCode = {};
  (state.data.nationalQuarterActual || []).forEach((row) => {
    const period = quarterPeriod(row.prd_de);
    const value = number(row.value);
    if (!period || !Number.isFinite(value) || !row.c1_id) return;
    const scaled = value * 1000;
    nationalQuarterByCode[`${row.c1_id}|${period}`] = scaled;
    (GDP_CODE_TO_SECTORS[row.c1_id] || []).forEach((sector) => {
      nationalQuarterBySector[`${sector}|${period}`] = scaled;
    });
  });
  const seoulDashboardCodesByName = {};
  [...(state.data.sigunguAnnual || []), ...(state.data.sigunguQuarter || [])].forEach((row) => {
    if (row.source_region === "서울특별시" && row.sigungu_name && row.sigungu_code) {
      seoulDashboardCodesByName[row.sigungu_name] = row.sigungu_code;
    }
  });
  const seoulDistrictAnnual = {};
  (state.data.seoulDistrictAnnual || []).forEach((row) => {
    const year = String(row.year || row.prd_de || "");
    const code = row.sigungu_code || row.c1_id || row.region_code || "";
    const value = number(row.value || row.actual_annual_gva || row.grdp);
    if (year && code && Number.isFinite(value)) {
      seoulDistrictAnnual[`${code}|${year}`] = value;
      const dashboardCode = seoulDashboardCodesByName[row.sigungu_name || row.c1_nm || row.region_name || ""];
      if (dashboardCode) seoulDistrictAnnual[`${dashboardCode}|${year}`] = value;
    }
  });
  state.lookup = { areaNames, sectorNames, nationalQuarterBySector, nationalQuarterByCode, seoulDistrictAnnual };
}

function enrichSidoRows() {
  ["sidoAnnual", "sidoQuarter"].forEach((key) => {
    state.data[key] = (state.data[key] || []).map((row) => {
      const out = {
        ...row,
        area_name: row.area_name || state.lookup.areaNames[row.area_code] || row.area_code,
        sector_name: row.sector_name || state.lookup.sectorNames[row.sector_code] || row.sector_code,
      };
      if (key === "sidoQuarter" && out.area_code === "00") {
        const actual = state.lookup.nationalQuarterBySector[`${out.sector_code}|${out.period}`];
        if (Number.isFinite(actual)) {
          out.actual_quarterly_gva = String(actual);
          const predicted = number(out.predicted_gva);
          out.quarter_percent_error = Number.isFinite(predicted) && actual !== 0 ? String(((predicted - actual) / actual) * 100) : "";
        }
      }
      return out;
    });
  });
}

function normalizeSigunguAnnualRows() {
  state.data.sigunguAnnual = (state.data.sigunguAnnual || []).map((row) => ({
    ...row,
    predicted_annual_gva: row.predicted_annual_gva || row.estimated_annual_sum || row.estimated_annual_gva || "",
    actual_annual_gva: row.actual_annual_gva || row.benchmark_annual_gva || "",
    percent_error: row.percent_error || row.percent_constraint_error || "",
  }));
}

function quarterPeriod(prdDe) {
  const text = String(prdDe || "");
  if (!/^\d{6}$/.test(text)) return "";
  const quarter = Number(text.slice(4));
  if (quarter < 1 || quarter > 4) return "";
  return `${text.slice(0, 4)}Q${quarter}`;
}

function regionKey(row, level) {
  if (level === "detail") return row.sigungu_code;
  if (level === "sigungu") return row.sigungu_code;
  if (level === "emd") return row.emd_code || row.table_id;
  return row.area_code;
}

function regionName(row, level) {
  if (level === "detail") return `${row.source_region} ${row.sigungu_name} (${row.sigungu_code})`;
  if (level === "sigungu") return `${row.source_region} ${row.sigungu_name} (${row.sigungu_code})`;
  if (level === "emd") return row.emd_code ? `${row.source_region} ${row.sigungu_name} ${row.emd_name} (${row.emd_code})` : `${row.source} ${row.table_id}`;
  return row.area_name || state.lookup.areaNames[row.area_code] || row.area_code;
}

function sectorKey(row, level) {
  if (level === "detail") return row.detail_code;
  if (level === "emd") return row.sector_code || row.assessment || row.name;
  return row.sector_code;
}

function sectorName(row, level) {
  if (level === "detail") return `${row.detail_name || row.detail_code} (${row.detail_code}, ${row.detail_level || ""})`;
  if (level === "emd") return row.sector_code ? `${row.sector_name || row.sector_code} (${row.sector_code})` : row.assessment || row.name;
  return `${row.sector_name || state.lookup.sectorNames[row.sector_code] || row.sector_code} (${row.sector_code})`;
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
  if (level === "emd") return grain === "annual" ? state.data.emdAnnual : state.data.emdQuarter;
  if (level === "detail") return grain === "annual" ? state.data.detailAnnual : state.data.detailQuarter;
  if (level === "sigungu") return grain === "annual" ? state.data.sigunguAnnual : state.data.sigunguQuarter;
  return grain === "annual" ? state.data.sidoAnnual : state.data.sidoQuarter;
}

function valueFields(level, grain) {
  if (level === "emd" && grain === "annual") {
    return { predicted: "estimated_annual_gva", actual: "", error: "" };
  }
  if (level === "emd") {
    return { predicted: "estimated_gva", actual: "", error: "" };
  }
  if (level === "detail" && grain === "annual") {
    return { predicted: "estimated_annual_gva", actual: "actual_proxy_value", error: "percent_proxy_error" };
  }
  if (level === "detail") {
    return { predicted: "estimated_gva", actual: "", error: "" };
  }
  if (level === "sigungu" && grain === "annual") {
    return { predicted: "predicted_annual_gva", actual: "actual_annual_gva", error: "percent_error" };
  }
  if (level === "sigungu") {
    return { predicted: "estimated_gva", actual: "", error: "" };
  }
  if (grain === "annual") {
    return { predicted: "predicted_annual_gva", actual: "actual_annual_gva", error: "percent_error" };
  }
  return { predicted: "predicted_gva", actual: "actual_quarterly_gva", error: "quarter_percent_error" };
}

function confidenceInfo(level, grain) {
  if (grain === "month") {
    return {
      grade: "-",
      gradeClass: "grade-muted",
      status: "미지원",
      method: "월간 예측 산출물이 없습니다.",
      caution: "연도 또는 분기를 선택해야 합니다.",
    };
  }
  if (level === "emd") {
    return {
      grade: "D",
      gradeClass: "grade-d",
      status: "탐색용 프록시 배분",
      method: "시군구 분기 GVA를 읍면동 사업체·종사자·매출 프록시 비중으로 하향 배분",
      caution: "공식 읍면동 GVA가 아니며 지역 미시분석 후보값으로 사용해야 합니다.",
    };
  }
  if (level === "detail") {
    return {
      grade: "C",
      gradeClass: "grade-c",
      status: "세부산업 프록시 배분",
      method: "시군구 부모 산업 총량을 KSIC 세부 프록시 비중으로 배분",
      caution: "중분류·소분류·세분류는 서로 다른 배분 레벨이므로 동시에 합산하지 않습니다.",
    };
  }
  if (level === "sigungu" && grain === "annual") {
    return {
      grade: "A",
      gradeClass: "grade-a",
      status: "공식 연간 벤치마크 정합",
      method: "시군구 연간 GRVA 벤치마크와 비교 가능한 연간 합산값",
      caution: "연간 합계 검증용이며 분기 내 배분 경로의 직접 관측값은 아닙니다.",
    };
  }
  if (level === "sigungu") {
    return {
      grade: "B",
      gradeClass: "grade-b",
      status: "벤치마크 제약 추정",
      method: "시군구 연간 GRVA를 시도 분기 GVA 경로로 비례형 Denton 배분",
      caution: "분기 실제값은 공개되지 않아 연간 합계 제약으로 정합성을 확인합니다.",
    };
  }
  if (level === "sido" && grain === "annual") {
    return {
      grade: "B",
      gradeClass: "grade-b",
      status: "rolling 예측 검증 가능",
      method: "과거 연간 GRVA와 분기 지표로 목표연도 연간 합계를 예측하고 실제값과 비교",
      caution: "실제 연간 GRVA가 존재하는 기간만 오차가 계산됩니다.",
    };
  }
  return {
    grade: "B",
    gradeClass: "grade-b",
    status: "분기 경로 추정",
    method: "연간 GRVA와 산업별 분기 지표를 이용한 비례형 Denton 및 외삽",
    caution: "전국은 분기 GDP actual과 비교 가능하나 시도별 분기 GRVA actual은 공개되지 않습니다.",
  };
}

function detailSectorGroups(rows) {
  const buckets = { middle: new Map(), small: new Map(), class: new Map(), other: new Map() };
  rows.forEach((row) => {
    const key = sectorKey(row, "detail");
    if (!key) return;
    const level = row.detail_level || "other";
    const bucket = buckets[level] || buckets.other;
    if (!bucket.has(key)) {
      const prefix = DETAIL_LEVEL_LABELS[level] || "기타";
      bucket.set(key, `[${prefix}] ${row.detail_name || key} (${key})`);
    }
  });
  return ["middle", "small", "class", "other"]
    .filter((level) => buckets[level].size)
    .map((level) => ({
      label: DETAIL_LEVEL_LABELS[level] || "기타",
      options: [...buckets[level].entries()].sort((a, b) => String(a[1]).localeCompare(String(b[1]), "ko")),
    }));
}

async function refreshFilters(keep = {}) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  await ensureLevelData(level, grain);
  const rows = datasetFor(level, grain) || [];
  const regions = uniqueOptions(rows, (row) => regionKey(row, level), (row) => regionName(row, level));
  const sectors = uniqueOptions(rows, (row) => sectorKey(row, level), (row) => sectorName(row, level));
  sectors.unshift([ALL_SECTOR, "전체"]);
  setOptions($("regionSelect"), regions, keep.region);
  if (level === "detail") {
    const groups = [{ label: "집계", options: [[ALL_SECTOR, "전체 제조업 세부산업"]] }, ...detailSectorGroups(rows)];
    setGroupedOptions($("sectorSelect"), groups, keep.sector);
  } else {
    setOptions($("sectorSelect"), sectors, keep.sector);
  }
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
  if (sector && sector !== ALL_SECTOR) rows = rows.filter((row) => sectorKey(row, level) === sector);
  if (applyPeriod && start && end) {
    const lo = Math.min(periodNumber(start), periodNumber(end));
    const hi = Math.max(periodNumber(start), periodNumber(end));
    rows = rows.filter((row) => {
      const p = periodNumber(periodKey(row, grain));
      return p >= lo && p <= hi;
    });
  }
  return rows;
}

function aggregateIfNeeded(rows) {
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  const sector = $("sectorSelect").value;
  if (sector !== ALL_SECTOR) return rows;
  const fields = valueFields(level, grain);
  const groups = new Map();
  rows.forEach((row) => {
    const key = `${regionKey(row, level)}|${periodKey(row, grain)}`;
    if (!groups.has(key)) {
      groups.set(key, {
        ...row,
        sector_code: ALL_SECTOR,
        sector_name: "전체",
        [fields.predicted]: 0,
        [fields.actual]: "",
        [fields.error]: "",
        actualCount: 0,
      });
    }
    const item = groups.get(key);
    const predicted = number(row[fields.predicted]);
    if (Number.isFinite(predicted)) item[fields.predicted] += predicted;
    const actual = number(row[fields.actual]);
    if (Number.isFinite(actual)) {
      item[fields.actual] = number(item[fields.actual]) || 0;
      item[fields.actual] += actual;
      item.actualCount += 1;
    }
  });
  return [...groups.values()]
    .map((row) => {
      if (level === "sido" && grain === "quarter" && row.area_code === "00") {
        const period = periodKey(row, grain);
        const totalActual = UNIQUE_GDP_CODES.reduce((sum, code) => {
          const actual = number(state.lookup.nationalQuarterByCode[`${code}|${period}`]);
          return Number.isFinite(actual) ? sum + actual : sum;
        }, 0);
        row[fields.actual] = totalActual > 0 ? totalActual : "";
      }
      if (level === "sigungu" && grain === "annual") {
        const seoulActual = number(state.lookup.seoulDistrictAnnual[`${row.sigungu_code}|${periodKey(row, grain)}`]);
        if (Number.isFinite(seoulActual)) row[fields.actual] = seoulActual;
      }
      if (row.actualCount === 0 && !Number.isFinite(number(row[fields.actual]))) row[fields.actual] = "";
      const predicted = number(row[fields.predicted]);
      const actual = number(row[fields.actual]);
      row[fields.error] = Number.isFinite(predicted) && Number.isFinite(actual) && actual !== 0 ? String(((predicted - actual) / actual) * 100) : "";
      delete row.actualCount;
      return row;
    })
    .sort((a, b) => periodNumber(periodKey(a, grain)) - periodNumber(periodKey(b, grain)));
}

function updateMessage(level, grain, rows) {
  const box = $("message");
  const messages = [];
  const info = confidenceInfo(level, grain);
  if (info.caution) messages.push(info.caution);
  if (grain === "month") messages.push("현재 원천 데이터는 월간 예측값을 포함하지 않습니다. 연도 또는 분기를 선택해 주세요.");
  if (level === "emd") messages.push("읍면동은 2015 경제총조사 프록시로 시군구 분기 GVA를 하향 배분한 추정값입니다.");
  if (level === "detail" && grain === "quarter") messages.push("세부산업 분기값은 시군구 제조업 분기 총량을 KSIC 연간 프록시 비중으로 배분한 추정값입니다.");
  if (level === "detail" && grain === "annual") messages.push("세부산업 연도 actual은 제조업조사 부가가치 프록시가 있는 경우에만 비교합니다.");
  if (level === "sigungu" && grain === "quarter") messages.push("시군구 분기 실제값은 공개되지 않아 예측값만 표시합니다. 연간 실제 벤치마크 비교는 시점 단위 '연도'에서 볼 수 있습니다.");
  if (level === "sido" && grain === "quarter") messages.push("전국은 GDP 분기 실측치와 비교하고, 시도별 분기 GRVA는 공개 actual이 없어 예측값만 표시합니다.");
  if (!rows.length) messages.push("선택한 조건에 해당하는 행이 없습니다.");
  box.hidden = messages.length === 0;
  box.textContent = messages.join(" ");
}

function updateConfidence(level, grain) {
  const info = confidenceInfo(level, grain);
  $("metricConfidence").textContent = info.grade;
  $("confidencePanel").innerHTML = `
    <div><span class="grade-badge ${info.gradeClass}">${escapeHtml(info.grade)}</span></div>
    <div class="confidence-item"><span>방법론 상태</span><strong>${escapeHtml(info.status)}</strong></div>
    <div class="confidence-item"><span>산출 방식</span><strong>${escapeHtml(info.method)}</strong></div>
  `;
}

function drawChart(rows) {
  const svg = $("chart");
  svg.innerHTML = "";
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  if (!rows.length || grain === "month") {
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
  if (level === "emd" && rows.length && !("estimated_gva" in rows[0]) && !("estimated_annual_gva" in rows[0])) {
    const cols = ["source", "table_id", "name", "period", "dimensions", "assessment"];
    table.innerHTML = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${cols.map((c) => `<td>${row[c] || ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
    return;
  }
  const limitedRows = rows.slice(0, TABLE_LIMIT);
  $("tableNote").textContent =
    rows.length > TABLE_LIMIT
      ? `원천 CSV: data/processed/*.csv (CP949) · ${rows.length.toLocaleString("ko-KR")}행 중 ${TABLE_LIMIT.toLocaleString("ko-KR")}행 표시`
      : "원천 CSV: data/processed/*.csv (CP949)";
  const mapped = limitedRows
    .sort((a, b) => periodNumber(periodKey(a, grain)) - periodNumber(periodKey(b, grain)))
    .map((row) => ({
      period: periodKey(row, grain),
      region: level === "sigungu" || level === "detail" ? row.sigungu_name : level === "emd" ? row.emd_name : regionName(row, level),
      sector: row.sector_name || row.detail_name || (sectorKey(row, level) === ALL_SECTOR ? "전체" : ""),
      predicted: fmt(row[fields.predicted], 3),
      actual: fields.actual ? fmt(row[fields.actual], 3) : "-",
      error: fields.error ? pct(row[fields.error]) : "-",
      method: row.method || "",
    }));
  const cols = ["period", "region", "sector", "predicted", "actual", "error", "method"];
  table.innerHTML = `<thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${mapped.map((row) => `<tr>${cols.map((c) => `<td>${row[c] || ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

function render() {
  const baseRows = filteredBaseRows(true);
  const rows = aggregateIfNeeded(baseRows);
  state.rows = rows;
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  updateConfidence(level, grain);
  updateMessage(level, grain, rows);
  updateMetrics(rows);
  $("chartTitle").textContent = level === "emd" ? "읍면동 예측값" : "예측값과 실제값";
  const regionOption = $("regionSelect").selectedOptions[0];
  const sectorOption = $("sectorSelect").selectedOptions[0];
  $("chartSubtitle").textContent = `${regionOption ? regionOption.textContent : ""} · ${sectorOption ? sectorOption.textContent : ""}`;
  drawChart(rows);
  renderTable(rows);
}

async function init() {
  try {
    await Promise.all(BASE_DATA_KEYS.map((key) => loadDataKey(key)));
    buildLookups();
    enrichSidoRows();
    normalizeSigunguAnnualRows();
    $("loadStatus").textContent = "CSV 로딩 완료";
  } catch (error) {
    $("loadStatus").textContent = "CSV 로딩 실패";
    $("message").hidden = false;
    $("message").textContent = `CSV를 불러오지 못했습니다. repo root에서 'python -m http.server'로 실행한 뒤 http://localhost:8000/reports/dashboard/ 로 접속해 주세요. (${error.message})`;
    return;
  }
  ["levelSelect", "grainSelect"].forEach((id) => {
    $(id).addEventListener("change", async () => {
      await refreshFilters();
      render();
    });
  });
  ["regionSelect", "sectorSelect"].forEach((id) => {
    $(id).addEventListener("change", () => {
      refreshPeriods({ region: $("regionSelect").value, sector: $("sectorSelect").value });
      render();
    });
  });
  ["startSelect", "endSelect"].forEach((id) => $(id).addEventListener("change", render));
  await refreshFilters();
  render();
}

init();
