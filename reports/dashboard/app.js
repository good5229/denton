const DATA_PATHS = {
  sidoAnnual: "../../data/processed/rolling_annual_prediction_comparisons.csv",
  sidoQuarter: "../../data/processed/rolling_quarterly_gva_predictions.csv",
  sidoActual: "../../data/processed/rolling_annual_grva_real.csv",
  nationalQuarterActual: "../../data/processed/rolling_national_quarterly_gdp_real.csv",
  sigunguQuarter: "../../data/processed/sigungu_quarterly_gva_estimates.csv",
  sigunguAnnual: "../../data/processed/sigungu_denton_constraint_diagnostics.csv",
  sigunguQuarterForecast: "../../data/processed/sigungu_quarterly_gva_forecasts.csv",
  sigunguAnnualForecast: "../../data/processed/sigungu_annual_gva_forecasts.csv",
  seoulDistrictAnnual: "../../data/processed/seoul_district_grdp_annual.csv",
  detailQuarter: "../../data/processed/detailed_industry_quarterly_estimates.csv",
  detailAnnual: "../../data/processed/detailed_industry_annual_estimates.csv",
  emdQuarter: "../../data/processed/emd_quarterly_gva_estimates.csv",
  emdAnnual: "../../data/processed/emd_annual_gva_estimates.csv",
  emdInventory: "../../data/processed/eupmyeondong_source_inventory.csv",
  confidenceScores: "../../data/processed/estimate_confidence_scores.csv",
};

const OPTIONAL_DATA_KEYS = new Set(["sigunguQuarterForecast", "sigunguAnnualForecast", "seoulDistrictAnnual", "detailQuarter", "detailAnnual", "emdQuarter", "emdAnnual", "confidenceScores"]);
const BASE_DATA_KEYS = ["sidoAnnual", "sidoQuarter", "sidoActual", "nationalQuarterActual", "sigunguQuarter", "sigunguAnnual", "seoulDistrictAnnual"];
const ALL_SECTOR = "__ALL__";
const REGION_SUM_PREFIX = "__REGION_SUM__|";
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
  filterOptions: {
    regions: [],
    sectors: [],
  },
  filters: {
    regions: [],
    sectors: [],
  },
  picker: {
    kind: "",
    draft: [],
  },
  lookup: {
    areaNames: {},
    sectorNames: {},
    nationalQuarterBySector: {},
    nationalQuarterByCode: {},
    seoulDistrictAnnual: {},
    confidenceByKey: {},
  },
  availableProcessedFiles: null,
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

async function optionalDataExists(path) {
  if (!path.startsWith("../../data/processed/")) return true;
  if (!state.availableProcessedFiles) {
    try {
      const response = await fetch("../../data/processed/");
      const html = response.ok ? await response.text() : "";
      state.availableProcessedFiles = new Set([...html.matchAll(/href="([^"]+\.csv)"/g)].map((match) => decodeURIComponent(match[1])));
    } catch (error) {
      state.availableProcessedFiles = new Set();
    }
  }
  return state.availableProcessedFiles.has(path.split("/").pop());
}

async function loadDataKey(key) {
  if (state.data[key]) return state.data[key];
  if (state.loading[key]) return state.loading[key];
  $("loadStatus").textContent = `${key} CSV 로딩 중`;
  if (OPTIONAL_DATA_KEYS.has(key) && !(await optionalDataExists(DATA_PATHS[key]))) {
    state.data[key] = [];
    $("loadStatus").textContent = "CSV 로딩 완료";
    return [];
  }
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
  if (level === "sigungu") {
    await loadDataKey(grain === "annual" ? "sigunguAnnualForecast" : "sigunguQuarterForecast");
    normalizeSigunguAnnualRows();
    normalizeSigunguQuarterRows();
  }
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

function syncHiddenSelect(id, options, selectedValues) {
  const select = $(id);
  setOptions(select, options, selectedValues[0]);
  select.value = selectedValues[0] || "";
}

function selectedLabels(kind) {
  const key = kind === "region" ? "regions" : "sectors";
  const lookup = new Map(state.filterOptions[key]);
  return state.filters[key].map((value) => [value, lookup.get(value) || value]);
}

function selectionSummary(kind) {
  const labels = selectedLabels(kind).map(([, label]) => label);
  if (!labels.length) return kind === "region" ? "지역 선택" : "산업군 선택";
  if (labels.length === 1) return labels[0];
  return `${labels[0]} 외 ${labels.length - 1}개`;
}

function renderSelectedChips() {
  const render = (kind, targetId) => {
    const rows = selectedLabels(kind);
    $(targetId).innerHTML = rows.length
      ? rows
          .map(
            ([value, label]) =>
              `<span class="chip">${escapeHtml(label)}<button type="button" data-kind="${kind}" data-value="${escapeHtml(value)}" aria-label="삭제">×</button></span>`
          )
          .join("")
      : `<span class="chip">선택 없음</span>`;
  };
  render("region", "selectedRegions");
  render("sector", "selectedSectors");
  $("regionPickerButton").textContent = selectionSummary("region");
  $("sectorPickerButton").textContent = selectionSummary("sector");
}

function ensureSelection(currentValues, options, fallbackIndex = 0) {
  const valid = new Set(options.map(([value]) => value));
  const kept = currentValues.filter((value) => valid.has(value));
  if (kept.length) return kept;
  return options[fallbackIndex] ? [options[fallbackIndex][0]] : [];
}

function ensureFilterSelection(key, values) {
  if (key === "sectors") {
    const valid = new Set(state.filterOptions.sectors.map(([value]) => value));
    const kept = values.filter((value) => valid.has(value));
    return kept.length ? kept : [ALL_SECTOR];
  }
  return ensureSelection(values, state.filterOptions.regions);
}

function pickerOptionsFor(kind) {
  const options = kind === "region" ? state.filterOptions.regions : state.filterOptions.sectors;
  return options.filter(([value]) => value !== ALL_SECTOR);
}

function pickerScopeText(kind) {
  const levelOption = $("levelSelect").selectedOptions[0];
  const grainOption = $("grainSelect").selectedOptions[0];
  const levelText = levelOption ? levelOption.textContent : "";
  const grainText = grainOption ? grainOption.textContent : "";
  if (kind === "region") {
    return `현재 지역 수준: ${levelText}. 검색어와 일치하는 지역을 복수로 선택할 수 있습니다.`;
  }
  return `현재 지역 수준: ${levelText}, 시점 단위: ${grainText}. 대분류·중분류·소분류·세분류 라벨과 업종명을 검색할 수 있습니다.`;
}

function filteredPickerOptions() {
  const kind = state.picker.kind;
  const query = compactName($("pickerSearch").value).toLowerCase();
  return pickerOptionsFor(kind).filter(([, label]) => !query || compactName(label).toLowerCase().includes(query));
}

function openPicker(kind) {
  state.picker.kind = kind;
  const selected = state.filters[kind === "region" ? "regions" : "sectors"];
  state.picker.draft = selected.includes(ALL_SECTOR) ? pickerOptionsFor(kind).map(([value]) => value) : [...selected];
  $("pickerTitle").textContent = kind === "region" ? "지역 검색 및 선택" : "산업군 검색 및 선택";
  $("pickerScope").textContent = pickerScopeText(kind);
  $("pickerSearch").value = "";
  $("pickerModal").hidden = false;
  renderPickerOptions();
  $("pickerSearch").focus();
}

function closePicker() {
  $("pickerModal").hidden = true;
  state.picker.kind = "";
  state.picker.draft = [];
}

function renderPickerOptions() {
  const draft = new Set(state.picker.draft);
  const options = filteredPickerOptions();
  const visibleValues = options.map(([value]) => value);
  const selectedVisibleCount = visibleValues.filter((value) => draft.has(value)).length;
  $("pickerCount").textContent = `${draft.size.toLocaleString("ko-KR")}개 선택 · ${options.length.toLocaleString("ko-KR")}개 표시`;
  $("pickerToggleVisible").hidden = options.length === 0;
  $("pickerToggleVisible").textContent =
    options.length > 0 && selectedVisibleCount === options.length ? "검색 결과 전체 선택 해제" : "검색 결과 전체 선택";
  $("pickerOptions").innerHTML = options
    .map(([value, label]) => {
      const selected = draft.has(value);
      return `<button type="button" class="picker-option${selected ? " selected" : ""}" data-value="${escapeHtml(value)}">
        <span class="picker-check">${selected ? "✓" : ""}</span>
        <span>${escapeHtml(label)}</span>
      </button>`;
    })
    .join("");
}

async function applyPicker() {
  const kind = state.picker.kind;
  const key = kind === "region" ? "regions" : "sectors";
  const allOptions = pickerOptionsFor(kind);
  const baseOptions = kind === "region" ? state.filterOptions.regions : state.filterOptions.sectors;
  const allVisibleSelected = allOptions.length > 0 && state.picker.draft.length === allOptions.length;
  state.filters[key] = kind === "sector" && allVisibleSelected ? [ALL_SECTOR] : ensureFilterSelection(key, state.picker.draft);
  syncHiddenSelect(kind === "region" ? "regionSelect" : "sectorSelect", baseOptions, state.filters[key]);
  renderSelectedChips();
  closePicker();
  refreshPeriods();
  render();
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

function compactName(value) {
  return String(value || "").replaceAll(" ", "").replaceAll(",", "").replaceAll("·", "").replaceAll("ㆍ", "");
}

function isSigunguTotalRow(row) {
  const source = compactName(row.source_region);
  const name = compactName(row.sigungu_name);
  if (!source || !name) return false;
  return name === source || name === source.replace("특별", "") || name === source.replace("광역", "");
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
  const confidenceByKey = {};
  (state.data.confidenceScores || []).forEach((row) => {
    const key = [row.level, row.grain, row.area_code || "__ALL__", row.sector_code || "__ALL__"].join("|");
    confidenceByKey[key] = row;
  });
  state.lookup = { areaNames, sectorNames, nationalQuarterBySector, nationalQuarterByCode, seoulDistrictAnnual, confidenceByKey };
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
  ["sigunguAnnual", "sigunguAnnualForecast"].forEach((key) => {
    state.data[key] = (state.data[key] || []).map((row) => ({
      ...row,
      predicted_annual_gva: row.predicted_annual_gva || row.estimated_annual_sum || row.estimated_annual_gva || "",
      actual_annual_gva: row.actual_annual_gva || row.benchmark_annual_gva || "",
      percent_error: row.percent_error || row.percent_constraint_error || "",
    }));
  });
}

function normalizeSigunguQuarterRows() {
  ["sigunguQuarter", "sigunguQuarterForecast"].forEach((key) => {
    state.data[key] = (state.data[key] || []).map((row) => ({
      ...row,
      predicted_gva: row.predicted_gva || row.estimated_gva || "",
      actual_quarterly_gva: row.actual_quarterly_gva || "",
    }));
  });
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
  if (level === "sigungu") {
    return grain === "annual"
      ? [...(state.data.sigunguAnnual || []), ...(state.data.sigunguAnnualForecast || [])]
      : [...(state.data.sigunguQuarter || []), ...(state.data.sigunguQuarterForecast || [])];
  }
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
    return { predicted: "predicted_gva", actual: "actual_quarterly_gva", error: "" };
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
      grade: "A/B",
      gradeClass: "grade-b",
      status: "벤치마크 구간 + 예측 구간",
      method: "2019-2023은 공식 연간 GRVA 제약, 2024-2025는 부모 시도 rolling 예측과 2023년 시군구 비중으로 외삽",
      caution: "actual이 있는 연도는 공식 벤치마크 제약 구간이고, actual이 비어 있는 연도만 out-of-sample 예측입니다.",
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
    caution: "전국은 분기 GDP actual과 비교 가능하나 시도별 산업별 분기 GRDP/GVA 공식 actual은 현재 원천 CSV에 없습니다. 시도별 분기·월간 생산/서비스 지표는 추정 indicator로 사용합니다.",
  };
}

function gradeClass(grade) {
  const normalized = String(grade || "").toLowerCase().slice(0, 1);
  return ["a", "b", "c", "d"].includes(normalized) ? `grade-${normalized}` : "grade-muted";
}

function dynamicConfidenceInfo(level, grain) {
  const base = confidenceInfo(level, grain);
  const lookup = state.lookup.confidenceByKey || {};
  if (grain === "month") return base;
  const regions = state.filters.regions || [];
  const sectors = state.filters.sectors || [];
  const sector = sectors.includes(ALL_SECTOR) || sectors.length !== 1 ? "__ALL__" : sectors[0];
  const area = regions.length === 1 && !regions[0].startsWith(REGION_SUM_PREFIX) ? regions[0] : "__ALL__";
  const candidates = [
    [level, grain, area, sector],
    [level, grain, area, "__ALL__"],
    [level, grain, "__ALL__", sector],
    [level, grain, "__ALL__", "__ALL__"],
  ];
  const found = candidates.map((parts) => lookup[parts.join("|")]).find(Boolean);
  if (!found) return base;
  const metrics = [];
  if (found.comparison_count) metrics.push(`비교 ${Number(found.comparison_count).toLocaleString("ko-KR")}건`);
  if (found.mape) metrics.push(`MAPE ${pct(found.mape)}`);
  if (found.wmape) metrics.push(`WMAPE ${pct(found.wmape)}`);
  return {
    ...base,
    grade: found.confidence_grade || base.grade,
    gradeClass: gradeClass(found.confidence_grade || base.grade),
    status: `${found.value_role || base.status}${metrics.length ? ` · ${metrics.join(" · ")}` : ""}`,
    method: found.confidence_reason || base.method,
    caution: `${base.caution || ""} ${found.as_of_policy ? `적용 기준: ${found.as_of_policy}.` : ""}`.trim(),
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
  if (level === "sigungu") {
    const sources = uniqueOptions(
      rows.filter((row) => row.source_region),
      (row) => `${REGION_SUM_PREFIX}${row.source_region}`,
      (row) => `${row.source_region} 전체 시군구 합계`
    );
    regions.unshift(...sources);
  }
  const sectors = uniqueOptions(rows, (row) => sectorKey(row, level), (row) => sectorName(row, level));
  sectors.unshift([ALL_SECTOR, "전체"]);
  state.filterOptions.regions = regions;
  if (level === "detail") {
    const groups = [{ label: "집계", options: [[ALL_SECTOR, "전체 제조업 세부산업"]] }, ...detailSectorGroups(rows)];
    state.filterOptions.sectors = groups.flatMap((group) => group.options.map(([value, label]) => [value, `${group.label} · ${label}`]));
  } else {
    state.filterOptions.sectors = sectors;
  }
  const keepRegions = Array.isArray(keep.regions) ? keep.regions : keep.region ? [keep.region] : state.filters.regions;
  const keepSectors = Array.isArray(keep.sectors) ? keep.sectors : keep.sector ? [keep.sector] : state.filters.sectors;
  state.filters.regions = ensureSelection(keepRegions, state.filterOptions.regions);
  state.filters.sectors = ensureSelection(keepSectors, state.filterOptions.sectors);
  syncHiddenSelect("regionSelect", state.filterOptions.regions, state.filters.regions);
  syncHiddenSelect("sectorSelect", state.filterOptions.sectors, state.filters.sectors);
  renderSelectedChips();
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
  const regions = state.filters.regions;
  const sectors = state.filters.sectors;
  const start = $("startSelect").value;
  const end = $("endSelect").value;
  let rows = [...(datasetFor(level, grain) || [])];
  if (regions.length) {
    rows = rows.filter((row) =>
      regions.some((region) => {
        if (level === "sigungu" && region.startsWith(REGION_SUM_PREFIX)) {
          const sourceRegion = region.slice(REGION_SUM_PREFIX.length);
          return row.source_region === sourceRegion && !isSigunguTotalRow(row);
        }
        return regionKey(row, level) === region;
      })
    );
  }
  if (sectors.length && !sectors.includes(ALL_SECTOR)) {
    rows = rows.filter((row) => sectors.includes(sectorKey(row, level)));
  }
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
  const sectors = state.filters.sectors;
  const regions = state.filters.regions;
  const hasAllSector = sectors.includes(ALL_SECTOR);
  const aggregateRegion = level === "sigungu" && regions.some((region) => region.startsWith(REGION_SUM_PREFIX));
  const aggregateSelection = aggregateRegion || hasAllSector || regions.length !== 1 || sectors.length !== 1;
  if (!aggregateSelection) return rows;
  const fields = valueFields(level, grain);
  const groups = new Map();
  const regionLabel = selectedLabels("region").map(([, label]) => label).join(", ");
  const sectorLabel = hasAllSector ? "전체" : selectedLabels("sector").map(([, label]) => label).join(", ");
  rows.forEach((row) => {
    const key = periodKey(row, grain);
    if (!groups.has(key)) {
      groups.set(key, {
        ...row,
        sigungu_code: aggregateSelection ? "__SELECTED_REGIONS__" : row.sigungu_code,
        sigungu_name: aggregateSelection ? regionLabel : row.sigungu_name,
        area_code: aggregateSelection ? "__SELECTED_REGIONS__" : row.area_code,
        area_name: aggregateSelection ? regionLabel : row.area_name,
        emd_name: aggregateSelection ? regionLabel : row.emd_name,
        sector_code: aggregateSelection ? "__SELECTED_SECTORS__" : row.sector_code,
        sector_name: aggregateSelection ? sectorLabel : row.sector_name,
        detail_name: aggregateSelection ? sectorLabel : row.detail_name,
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
      if (aggregateSelection) {
        row.method = "sum of selected region and sector rows";
      }
      delete row.actualCount;
      return row;
    })
    .sort((a, b) => periodNumber(periodKey(a, grain)) - periodNumber(periodKey(b, grain)));
}

function updateMessage(level, grain, rows) {
  const box = $("message");
  const messages = [];
  const info = dynamicConfidenceInfo(level, grain);
  if (info.caution) messages.push(info.caution);
  if (level === "sigungu" && grain === "annual") {
    messages.push("2019-2023 시군구 연도값은 공식 연간 GRVA를 벤치마크로 사용한 제약 구간입니다. 2024-2025는 공식 시군구 GRVA가 아직 없어 부모 시도 rolling 예측과 2023년 시군구 비중으로 외삽한 예측값입니다.");
  }
  if (grain === "month") messages.push("현재 원천 데이터는 월간 예측값을 포함하지 않습니다. 연도 또는 분기를 선택해 주세요.");
  if (level === "emd") messages.push("읍면동은 2015 경제총조사 프록시로 시군구 분기 GVA를 하향 배분한 추정값입니다.");
  if (level === "detail" && grain === "quarter") messages.push("세부산업 분기값은 시군구 제조업 분기 총량을 KSIC 연간 프록시 비중으로 배분한 추정값입니다.");
  if (level === "detail" && grain === "annual") messages.push("세부산업 연도 actual은 제조업조사 부가가치 프록시가 있는 경우에만 비교합니다.");
  if (level === "sigungu" && grain === "quarter") messages.push("시군구 분기 실제값은 공개되지 않아 예측값만 표시합니다. 연간 실제 벤치마크 비교는 시점 단위 '연도'에서 볼 수 있습니다.");
  if (level === "sido" && grain === "quarter") messages.push("전국은 GDP 분기 실측치와 비교합니다. 강원특별자치도 같은 시도에는 분기·월간 산업활동 지표가 있지만, 이는 GRDP/GVA actual이 아니라 Denton 추정에 쓰는 indicator입니다.");
  if (!rows.length) messages.push("선택한 조건에 해당하는 행이 없습니다.");
  box.hidden = messages.length === 0;
  box.textContent = messages.join(" ");
}

function updateConfidence(level, grain) {
  const info = dynamicConfidenceInfo(level, grain);
  $("metricConfidence").textContent = info.grade;
  $("confidencePanel").innerHTML = `
    <div><span class="grade-badge ${info.gradeClass}">${escapeHtml(info.grade)}</span></div>
    <div class="confidence-item"><span>방법론 상태</span><strong>${escapeHtml(info.status)}</strong></div>
    <div class="confidence-item"><span>산출 방식</span><strong>${escapeHtml(info.method)}</strong></div>
  `;
}

const CHART_COLORS = ["#2f72c8", "#c8564a", "#3e8f50", "#7b5bbd", "#b87a18", "#238b8b", "#d05d9f", "#596579", "#8a6f35", "#2d8fc7", "#b14f3b", "#4f8f45"];

function selectedSectorIsAll() {
  return state.filters.sectors.includes(ALL_SECTOR);
}

function chartGroupInfo(row, level) {
  const region = regionName(row, level);
  const sector = selectedSectorIsAll() ? "전체" : sectorName(row, level);
  const key = `${regionKey(row, level)}|${selectedSectorIsAll() ? ALL_SECTOR : sectorKey(row, level)}`;
  const label = selectedSectorIsAll() ? region : `${region} · ${sector}`;
  return { key, label, region, sector };
}

function buildChartSeries(rows, level, grain, fields) {
  const groups = new Map();
  rows.forEach((row) => {
    const predicted = number(row[fields.predicted]);
    const actual = fields.actual ? number(row[fields.actual]) : NaN;
    if (!Number.isFinite(predicted) && !Number.isFinite(actual)) return;
    const period = periodKey(row, grain);
    if (!period) return;
    const info = chartGroupInfo(row, level);
    if (!groups.has(info.key)) {
      groups.set(info.key, { ...info, periods: new Map() });
    }
    const series = groups.get(info.key);
    if (!series.periods.has(period)) {
      series.periods.set(period, { period, predicted: 0, actual: 0, predictedCount: 0, actualCount: 0 });
    }
    const point = series.periods.get(period);
    if (Number.isFinite(predicted)) {
      point.predicted += predicted;
      point.predictedCount += 1;
    }
    if (Number.isFinite(actual)) {
      point.actual += actual;
      point.actualCount += 1;
    }
  });
  return [...groups.values()]
    .map((series, idx) => ({
      ...series,
      color: CHART_COLORS[idx % CHART_COLORS.length],
      points: [...series.periods.values()]
        .map((point) => ({
          ...point,
          predicted: point.predictedCount ? point.predicted : NaN,
          actual: point.actualCount ? point.actual : NaN,
        }))
        .sort((a, b) => periodNumber(a.period) - periodNumber(b.period)),
    }))
    .sort((a, b) => a.label.localeCompare(b.label, "ko"));
}

function drawChart(rows) {
  const chart = $("chart");
  chart.innerHTML = "";
  const level = $("levelSelect").value;
  const grain = $("grainSelect").value;
  if (!rows.length || grain === "month") {
    chart.innerHTML = `<div class="empty-chart">표시할 시계열이 없습니다.</div>`;
    return;
  }
  if (!window.Plotly) {
    chart.innerHTML = `<div class="empty-chart">Plotly를 불러오지 못했습니다. 인터넷 연결 또는 CDN 접근을 확인해 주세요.</div>`;
    return;
  }
  const fields = valueFields(level, grain);
  const series = buildChartSeries(rows, level, grain, fields);
  if (!series.length) {
    chart.innerHTML = `<div class="empty-chart">표시할 시계열이 없습니다.</div>`;
    return;
  }
  const traces = [];
  series.forEach((item) => {
    const predictedPoints = item.points.filter((point) => Number.isFinite(point.predicted));
    const actualPoints = item.points.filter((point) => Number.isFinite(point.actual));
    const common = {
      mode: "lines+markers",
      legendgroup: item.key,
      marker: { size: 7, color: item.color, line: { color: "#ffffff", width: 1.5 } },
      hovertemplate: "%{customdata[0]}<br>%{x}<br>%{customdata[1]}: %{y:,.3f}<extra></extra>",
    };
    if (actualPoints.length) {
      traces.push({
        ...common,
        name: `${item.label} 실제`,
        x: actualPoints.map((point) => point.period),
        y: actualPoints.map((point) => point.actual),
        customdata: actualPoints.map(() => [item.label, "실제값"]),
        line: { color: item.color, width: 3, dash: "solid" },
      });
    }
    if (predictedPoints.length) {
      traces.push({
        ...common,
        name: `${item.label} 예측`,
        x: predictedPoints.map((point) => point.period),
        y: predictedPoints.map((point) => point.predicted),
        customdata: predictedPoints.map(() => [item.label, "예측값"]),
        line: { color: item.color, width: 3, dash: "dot" },
      });
    }
  });

  const layout = {
    margin: { l: 76, r: 24, t: 12, b: 56 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    hovermode: "closest",
    legend: { orientation: "h", y: -0.22, x: 0, font: { size: 12 } },
    xaxis: {
      type: "category",
      tickfont: { size: 12, color: "#5e6b7a" },
      gridcolor: "#eef2f7",
      zeroline: false,
    },
    yaxis: {
      tickfont: { size: 12, color: "#5e6b7a" },
      gridcolor: "#e7ecf3",
      zeroline: false,
      separatethousands: true,
    },
    font: {
      family: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif',
      color: "#17202a",
    },
  };
  const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] };
  window.Plotly.react(chart, traces, layout, config);
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
      confidence: dynamicConfidenceInfo(level, grain).grade,
      method: row.method || (level === "sigungu" && grain === "annual" ? "annual benchmark constraint check" : ""),
    }));
  const cols = ["period", "region", "sector", "predicted", "actual", "error", "confidence", "method"];
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
  $("chartSubtitle").textContent = `${selectionSummary("region")} · ${selectionSummary("sector")}`;
  drawChart(baseRows);
  renderTable(rows);
}

async function init() {
  try {
    await Promise.all(BASE_DATA_KEYS.map((key) => loadDataKey(key)));
    await loadDataKey("confidenceScores");
    buildLookups();
    enrichSidoRows();
    normalizeSigunguAnnualRows();
    normalizeSigunguQuarterRows();
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
  $("regionPickerButton").addEventListener("click", () => openPicker("region"));
  $("sectorPickerButton").addEventListener("click", () => openPicker("sector"));
  $("pickerClose").addEventListener("click", closePicker);
  $("pickerApply").addEventListener("click", applyPicker);
  $("pickerClear").addEventListener("click", () => {
    state.picker.draft = [];
    renderPickerOptions();
  });
  $("pickerToggleVisible").addEventListener("click", () => {
    const visible = filteredPickerOptions().map(([value]) => value);
    if (!visible.length) return;
    const visibleSet = new Set(visible);
    const allVisibleSelected = visible.every((value) => state.picker.draft.includes(value));
    state.picker.draft = allVisibleSelected
      ? state.picker.draft.filter((value) => !visibleSet.has(value))
      : [...new Set([...state.picker.draft, ...visible])];
    renderPickerOptions();
  });
  $("pickerSearch").addEventListener("input", renderPickerOptions);
  $("pickerOptions").addEventListener("click", (event) => {
    const button = event.target.closest(".picker-option");
    if (!button) return;
    const value = button.dataset.value;
    if (state.picker.draft.includes(value)) {
      state.picker.draft = state.picker.draft.filter((item) => item !== value);
    } else {
      state.picker.draft.push(value);
    }
    renderPickerOptions();
  });
  $("pickerModal").addEventListener("click", (event) => {
    if (event.target.id === "pickerModal") closePicker();
  });
  ["selectedRegions", "selectedSectors"].forEach((id) => {
    $(id).addEventListener("click", (event) => {
      const button = event.target.closest("button[data-kind]");
      if (!button) return;
      const key = button.dataset.kind === "region" ? "regions" : "sectors";
      state.filters[key] = ensureFilterSelection(key, state.filters[key].filter((value) => value !== button.dataset.value));
      syncHiddenSelect(key === "regions" ? "regionSelect" : "sectorSelect", state.filterOptions[key], state.filters[key]);
      renderSelectedChips();
      refreshPeriods();
      render();
    });
  });
  ["startSelect", "endSelect"].forEach((id) => $(id).addEventListener("change", render));
  await refreshFilters();
  render();
}

init();
