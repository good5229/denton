from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pohang"
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase42_pohang"
HIERARCHICAL_VALIDATION = DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv"
FINAL_ACCURACY_REGISTRY = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"
NO_WORSE_REFINEMENT = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
PHASE114_REFINEMENT = DATA / "phase114_block_routed_refinement_audit" / "phase114_refined_registry.csv"
PHASE127_STRICT_REFINEMENT = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"
PHASE128_FLASH = DATA / "phase128_vintage_flash_redesign" / "phase128_vintage_middle_flash_detail.csv"
PHASE217_REPORTING = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"

W, H = 3508, 4967
M, GAP = 72, 20
BODY_W = W - 2 * M
COL_W = (BODY_W - 2 * GAP) / 3

NAVY = "#073B67"
BLUE = "#2B6F9F"
SKY = "#DCECF5"
PAGE = "#EEF4F7"
INK = "#14242E"
MUTED = "#50636F"
GRID = "#C7D4DC"
WHITE = "#FFFFFF"
TEAL = "#147D78"
ORANGE = "#E06A3B"
RED = "#B33B32"
GOLD = "#B98724"
PALE = "#F5F8FA"
GREEN = "#2D8B72"

FONT_BODY = "/Library/Fonts/NanumBarunGothic.ttf"
FONT_BOLD = "/Library/Fonts/NanumBarunGothicBold.ttf"
FONT_TITLE = "/Library/Fonts/NanumSquareExtraBold.ttf"


def display_size(size: int) -> int:
    if size <= 15:
        return size + 10
    if size <= 18:
        return size + 8
    if size <= 23:
        return size + 5
    if size <= 34:
        return size + 2
    return size


def parent_letters(parent_section: str) -> list[str]:
    parent_section = str(parent_section)
    if parent_section == "ERS":
        return ["E", "R", "S"]
    if parent_section == "MN0":
        return ["M", "N"]
    return [parent_section[0]]


def apply_phase128_flash(hv: pd.DataFrame, city: str) -> pd.DataFrame:
    """Replace rejected initial split with Q4+1M historical middle-industry flash."""
    if not PHASE128_FLASH.exists():
        hv["flash_eok"] = hv.initial_predicted_gva_eok
        hv["flash_error_eok"] = hv.initial_error_gva_eok
        hv["flash_error_rate_pct"] = hv.initial_error_rate_pct
        return hv
    flash = pd.read_csv(PHASE128_FLASH, dtype={"middle_code": str})
    flash["middle_code"] = flash.middle_code.str.zfill(2)
    flash = flash[
        flash.city.eq(city)
        & flash.vintage_id.eq("Q4_plus_1m")
        & flash.share_model_id.eq("historical_middle_split")
        & flash.allowed_track.eq("flash_candidate")
    ][["parent_code", "middle_code", "flash_predicted_gva_eok", "flash_error_gva_eok", "flash_error_rate_pct"]]
    hv["middle_code"] = hv.middle_code.astype(str).str.zfill(2)
    hv = hv.merge(flash, on=["parent_code", "middle_code"], how="left")
    hv["flash_eok"] = hv.flash_predicted_gva_eok.fillna(hv.initial_predicted_gva_eok)
    hv["flash_error_eok"] = hv.flash_error_gva_eok.fillna(hv.initial_error_gva_eok)
    hv["flash_error_rate_pct"] = hv.flash_error_rate_pct.fillna(hv.initial_error_rate_pct)
    return hv.drop(columns=["flash_predicted_gva_eok", "flash_error_gva_eok"], errors="ignore")


def load_reporting_hv(city: str) -> pd.DataFrame:
    """Load middle-industry GVA validation rows with the latest reporting columns."""
    if PHASE217_REPORTING.exists():
        hv = pd.read_csv(PHASE217_REPORTING, dtype={"middle_code": str})
        hv = hv[hv.city.eq(city)].copy()
        hv["middle_code"] = hv.middle_code.astype(str).str.zfill(2)
        hv["middle_label"] = hv.middle_label.fillna(hv.middle_code.astype(str))
        hv["actual_eok"] = hv.actual_gva_eok
        hv["flash_eok"] = hv.flash_predicted_gva_eok
        hv["flash_error_eok"] = hv.flash_error_gva_eok
        hv["flash_error_rate_pct"] = hv.flash_error_rate_pct
        hv["refined_eok"] = hv.phase217_guarded_predicted_gva_eok
        hv["refined_error_eok"] = hv.phase217_guarded_error_gva_eok
        hv["refined_error_rate_pct"] = hv.phase217_guarded_error_rate_pct
        return hv

    hv_source = PHASE127_STRICT_REFINEMENT if PHASE127_STRICT_REFINEMENT.exists() else PHASE114_REFINEMENT if PHASE114_REFINEMENT.exists() else NO_WORSE_REFINEMENT if NO_WORSE_REFINEMENT.exists() else FINAL_ACCURACY_REGISTRY
    hv = pd.read_csv(hv_source, dtype={"middle_code": str})
    hv = hv[hv.city.eq(city)].copy()
    hv["middle_label"] = hv.middle_label.fillna(hv.middle_code.astype(str))
    hv["actual_eok"] = hv.actual_gva_eok
    hv["refined_eok"] = hv["phase127_strict_predicted_gva_eok"] if "phase127_strict_predicted_gva_eok" in hv.columns else hv["phase114_predicted_gva_eok"] if "phase114_predicted_gva_eok" in hv.columns else hv["no_worse_refined_predicted_gva_eok"] if "no_worse_refined_predicted_gva_eok" in hv.columns else hv.protected_predicted_gva_eok
    hv = apply_phase128_flash(hv, city)
    hv["refined_error_eok"] = hv["phase127_strict_error_gva_eok"] if "phase127_strict_error_gva_eok" in hv.columns else hv["phase114_error_gva_eok"] if "phase114_error_gva_eok" in hv.columns else hv["no_worse_refined_error_gva_eok"] if "no_worse_refined_error_gva_eok" in hv.columns else hv.protected_error_gva_eok
    hv["refined_error_rate_pct"] = hv["phase127_strict_error_rate_pct"] if "phase127_strict_error_rate_pct" in hv.columns else hv["phase114_error_rate_pct"] if "phase114_error_rate_pct" in hv.columns else hv["no_worse_refined_error_rate_pct"] if "no_worse_refined_error_rate_pct" in hv.columns else hv.protected_error_rate_pct
    return hv


def font(size: int, bold: bool = False, title: bool = False):
    return ImageFont.truetype(FONT_TITLE if title else FONT_BOLD if bold else FONT_BODY, display_size(size))


def wrapped(draw: ImageDraw.ImageDraw, value: str, size: int, width: int, bold: bool = False):
    lines: list[str] = []
    for paragraph in str(value).split("\n"):
        line = ""
        for ch in paragraph:
            if draw.textlength(line + ch, font=font(size, bold)) <= width:
                line += ch
            else:
                if line:
                    lines.append(line)
                line = ch
        lines.append(line)
    return lines


def box_text(draw, box, value, size, color=INK, bold=False, title=False, align="left", pad=0):
    x0, y0, x1, y1 = box
    fnt = font(size, bold, title)
    bbox = draw.textbbox((0, 0), str(value), font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if align == "center":
        xx = x0 + (x1 - x0 - tw) / 2 - bbox[0]
    elif align == "right":
        xx = x1 - pad - tw - bbox[0]
    else:
        xx = x0 + pad - bbox[0]
    yy = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.text((xx, yy), str(value), font=fnt, fill=color)


def paragraph(draw, x, y, value, size, width, color=INK, bold=False, leading=7):
    fnt = font(size, bold)
    step = display_size(size) + leading
    for i, line in enumerate(wrapped(draw, value, size, width, bold)):
        draw.text((x, y + i * step), line, font=fnt, fill=color)
    return y + len(wrapped(draw, value, size, width, bold)) * step


def box_paragraph(draw, box, value, size, color=INK, bold=False, leading=7, pad=0, align="left"):
    x0, y0, x1, y1 = box
    lines = wrapped(draw, value, size, int(x1 - x0 - 2 * pad), bold)
    rendered = "\n".join(lines)
    fnt = font(size, bold)
    bbox = draw.multiline_textbbox((0, 0), rendered, font=fnt, spacing=leading)
    th = bbox[3] - bbox[1]
    yy = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.multiline_text((x0 + pad, yy), rendered, font=fnt, fill=color, spacing=leading, align=align)


def text(draw, xy, value, size, color=INK, bold=False, title=False, anchor=None):
    draw.text(xy, str(value), font=font(size, bold, title), fill=color, anchor=anchor)


def panel(draw, x, y, width, height, number, title):
    draw.rectangle((x, y, x + width, y + height), fill=WHITE, outline=GRID, width=2)
    draw.rectangle((x, y, x + width, y + 62), fill=NAVY)
    box_text(draw, (x + 10, y, x + 60, y + 62), number, 23, SKY, bold=True, align="center")
    box_text(draw, (x + 70, y, x + width - 16, y + 62), title, 28, WHITE, bold=True)
    return x + 16, y + 78, width - 32, height - 94


def subhead(draw, x, y, title, width):
    box_text(draw, (x, y, x + width, y + 34), title, 21, NAVY, bold=True)
    draw.line((x, y + 39, x + width, y + 39), fill=GRID, width=2)
    return y + 51


def bullet(draw, x, y, value, width, size=17, color=INK):
    fnt = font(size)
    bbox = draw.textbbox((0, 0), "가", font=fnt)
    cy = y + bbox[1] + (bbox[3] - bbox[1]) / 2
    draw.ellipse((x, cy - 5, x + 10, cy + 5), fill=ORANGE)
    return paragraph(draw, x + 22, y, value, size, width - 22, color, False, 6)


def rect(draw, box, fill=WHITE, outline=GRID, width=1):
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def table(draw, x, y, width, headers, rows, ratios, row_h=50, sizes=None):
    sizes = sizes or [16] * len(headers)
    draw.rectangle((x, y, x + width, y + row_h), fill=SKY)
    cur = x
    for header, ratio in zip(headers, ratios):
        box_text(draw, (cur, y, cur + width * ratio, y + row_h), header, 17, NAVY, bold=True, pad=8)
        cur += width * ratio
    for i, row in enumerate(rows):
        yy = y + row_h * (i + 1)
        draw.rectangle((x, yy, x + width, yy + row_h), fill=PALE if i % 2 else WHITE, outline=GRID, width=1)
        cur = x
        for j, (value, ratio) in enumerate(zip(row, ratios)):
            box_paragraph(
                draw,
                (cur + 7, yy + 2, cur + width * ratio - 7, yy + row_h - 2),
                str(value),
                sizes[j],
                INK,
                bold=(j == 0),
                leading=3,
                align="center" if j > 0 else "left",
            )
            cur += width * ratio
    draw.line((x, y + row_h * (len(rows) + 1), x + width, y + row_h * (len(rows) + 1)), fill=NAVY, width=2)
    return y + row_h * (len(rows) + 1)


def table_label(value: str, max_chars: int = 12) -> str:
    value = str(value)
    if "\n" in value or len(value) <= max_chars:
        return value
    pivots = [" 및 ", "·", " ", ";"]
    for pivot in pivots:
        positions = [i + len(pivot) for i in range(len(value)) if value.startswith(pivot, i)]
        if not positions:
            continue
        cut = min(positions, key=lambda p: abs(p - len(value) / 2))
        if 4 <= cut <= len(value) - 4:
            return value[:cut].strip() + "\n" + value[cut:].strip()
    return value[:max_chars].rstrip() + "\n" + value[max_chars:].lstrip()


def hbars(draw, x, y, width, labels, values, colors, maximum, row_h=62, suffix="%p"):
    label_w, value_w = 250, 105
    bar_w = width - label_w - value_w
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        yy = y + i * row_h
        box_text(draw, (x, yy, x + label_w - 12, yy + 46), label, 17, INK, bold=True)
        draw.rectangle((x + label_w, yy + 8, x + label_w + bar_w, yy + 36), fill="#E6EDF1")
        fill_w = max(4, bar_w * float(value) / maximum)
        draw.rectangle((x + label_w, yy + 8, x + label_w + fill_w, yy + 36), fill=color)
        box_text(draw, (x + label_w + bar_w + 8, yy, x + width, yy + 46), f"{value:.2f}{suffix}", 17, color, bold=True, align="right")


def rings(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [polygon[0] for polygon in geometry["coordinates"]]
    return []


def seq_color(value, minimum, maximum):
    t = .5 if maximum == minimum else min(1, max(0, (value - minimum) / (maximum - minimum)))
    lo, hi = (225, 239, 241), (4, 92, 98)
    return "#%02x%02x%02x" % tuple(round(lo[i] + t * (hi[i] - lo[i])) for i in range(3))


def map_plot(draw, geo, values, box):
    x0, y0, x1, y1 = box
    points = [point for feature in geo["features"] for ring in rings(feature["geometry"]) for point in ring]
    minx, maxx = min(p[0] for p in points), max(p[0] for p in points)
    miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
    scale = min((x1 - x0 - 8) / (maxx - minx), (y1 - y0 - 8) / (maxy - miny))
    ox = x0 + (x1 - x0 - (maxx - minx) * scale) / 2
    oy = y0 + (y1 - y0 - (maxy - miny) * scale) / 2
    lo, hi = min(values.values()), max(values.values())
    for feature in geo["features"]:
        code = str(feature["properties"]["adm_cd"])
        color = seq_color(values.get(code, lo), lo, hi)
        for ring in rings(feature["geometry"]):
            pts = [(ox + (p[0] - minx) * scale, oy + (maxy - p[1]) * scale) for p in ring]
            draw.polygon(pts, fill=color, outline=WHITE)
            draw.line(pts + [pts[0]], fill="#758993", width=2)
    return lo, hi


def line_chart(draw, x, y, width, height, series, periods):
    ymin, ymax = 70, 170
    for tick in (80, 100, 120, 140, 160):
        yy = y + height - (tick - ymin) / (ymax - ymin) * height
        draw.line((x, yy, x + width, yy), fill=GRID, width=1)
        text(draw, (x - 10, yy), str(tick), 14, MUTED, anchor="rm")
    for boundary in (12, 24):
        xx = x + boundary / 35 * width
        draw.line((xx, y, xx, y + height), fill="#AEBCC5", width=2)
    for label, center in (("2021", 5.5), ("2022", 17.5), ("2023", 29.5)):
        text(draw, (x + center / 35 * width, y + height + 14), label, 14, MUTED, anchor="ma")
    palette = [TEAL, ORANGE, BLUE, GOLD]
    for i, (name, values) in enumerate(series):
        pts = [(x + j / 35 * width, y + height - (float(v) - ymin) / (ymax - ymin) * height) for j, v in enumerate(values)]
        draw.line(pts, fill=palette[i], width=4)
        lx = x + i * width / 4
        draw.line((lx, y - 32, lx + 32, y - 32), fill=palette[i], width=5)
        box_text(draw, (lx + 40, y - 50, lx + width / 4 - 8, y - 18), name, 14, palette[i], bold=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status42 = json.loads((DATA / "partial_stats_phase42_pohang_status.json").read_text())
    status43 = json.loads((DATA / "partial_stats_phase43_pohang_status.json").read_text())
    status45 = json.loads((DATA / "partial_stats_phase45_pohang_status.json").read_text())
    diagnostics = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv", encoding="utf-8-sig", dtype={"industry_code": str})
    hierarchical = pd.read_csv(HIERARCHICAL_VALIDATION)
    complete = diagnostics.dropna(subset=["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"])
    good = complete.nsmallest(6, "combined_cv_score_pp")
    bad = complete.nlargest(6, "combined_cv_score_pp")
    cube = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")
    monthly = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("대분류"))].copy()
    annual_large = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("연")) & (cube.industry_level.eq("대분류")) & (cube.period.astype(str).eq("2023"))].copy()
    large_gva_by_code = annual_large.groupby("industry_code").estimated_gva.sum().to_dict()
    totals = monthly[monthly.period.str.startswith("2023")].groupby(["industry_code", "industry_name"], as_index=False).estimated_gva.sum().nlargest(3, "estimated_gva")
    periods = sorted(monthly.period.unique())
    trends = []
    for row in totals.itertuples():
        z = monthly[monthly.industry_code.eq(row.industry_code)].set_index("period").reindex(periods)
        base_mean = z[z.index.str.startswith("2021")].estimated_gva.mean()
        trends.append((str(row.industry_name).replace(" 서비스업", "").replace("업", ""), (z.estimated_gva / base_mean * 100).tolist()))
    base = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet")
    emd_gva = base[base.year.eq(2023)].groupby(["emd_code", "emd_name"], as_index=False).estimated_emd_group_monthly_gva.sum()
    population = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_population.csv", dtype={"emd_code": str})
    emd_gva = emd_gva.merge(population[["emd_code", "population"]], on="emd_code")
    emd_gva["gva_per_capita"] = emd_gva.estimated_emd_group_monthly_gva / emd_gva.population
    map_values = dict(zip(emd_gva.emd_code, emd_gva.gva_per_capita))
    geo = json.loads((RAW / "administrative_dong_20260401.geojson").read_text())
    geo["features"] = [feature for feature in geo["features"] if feature["properties"].get("sggnm") in {"포항시남구", "포항시북구"}]

    img = Image.new("RGB", (W, H), PAGE)
    draw = ImageDraw.Draw(img)

    text(draw, (M, 42), "포항시 읍면동·업종별 월간 산업활력 정책지도", 68, NAVY, title=True)
    text(draw, (M, 142), "29개 읍면동×전 산업 월별 총부가가치(GVA) 추정과 상위 공식통계 집계검증", 34, INK, bold=True)
    text(draw, (M, 204), "산단·항만·상권·고용지원 후보를 읍면동×업종×월 단위로 조기 도출", 22, MUTED)
    draw.line((M, 248, W - M, 248), fill=NAVY, width=7)
    rect(draw, (M, 270, W - M, 410), WHITE, GRID, 2)
    metrics = [("정책 산출물", "29개 읍면동×업종×월 후보목록"), ("19·74·228", "전 산업 대·중·소분류"), ("상위 공식통계 검증", "하위 추정합을 공식값과 대조"), ("분기 조기점검", "Q+1개월 자료로 연간 전망"), ("산단·항만·상권", "읍면동별 GVA 변화 확인"), ("활용 부서", "기업지원·물류·소상공인·고용 연결")]
    each = BODY_W / 6
    for i, (value, label) in enumerate(metrics):
        xx = M + i * each
        if i:
            draw.line((xx, 290, xx, 392), fill=GRID, width=2)
        box_text(draw, (xx + 10, 282, xx + each - 10, 340), value, 24, TEAL if i >= 4 else NAVY, bold=True, align="center")
        box_text(draw, (xx + 10, 340, xx + each - 10, 392), label, 16, MUTED, align="center")

    y1, h1 = 435, 650
    x, y, cw, ch = panel(draw, M, y1, COL_W, h1, "01", "문제 정의와 분석 목표")
    yy = subhead(draw, x, y, "정책 문제", cw)
    yy = paragraph(draw, x, yy, "포항 과제: 산단·항만·상권 변화의 시차 관리\n정책 공백: 읍면동·월·세부업종 변화 지연\n필요 기능: 조기 감지·현장확인 후보 산출", 21, cw, INK, True, 8) + 18
    yy = subhead(draw, x, yy, "분석 목표", cw)
    yy = bullet(draw, x, yy, "미공표 하위 GVA를 상위 총량에서 배분·외삽", cw, 18)
    yy = bullet(draw, x, yy + 5, "소분류→중분류, 월→분기·연, 읍면동→구·시 재집계 검증", cw, 18)
    yy = bullet(draw, x, yy + 5, "속보성 지표와 공표 후 정밀화 지표를 분리", cw, 18)
    table(draw, x, y + 350, cw, ["축", "분석 범위"], [("시간", "연·분기·월"), ("공간", "시·구·29개 읍면동"), ("산업", "산업 대·중·소분류")], [.25, .75], 26, [12, 12])
    rect(draw, (x, y + ch - 92, x + cw, y + ch - 8), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 12, y + ch - 92, x + 132, y + ch - 8), "핵심 질문", 18, ORANGE, bold=True)
    box_text(draw, (x + 140, y + ch - 92, x + cw - 12, y + ch - 8), "어느 동·산업을 먼저 확인하고 지원할 것인가?", 20, INK, bold=True)

    x2 = M + COL_W + GAP
    x, y, cw, ch = panel(draw, x2, y1, 2 * COL_W + GAP, h1, "02", "활용 데이터와 산출·검증 절차")
    table_w = cw * .48
    rows = [("KOSIS 지역계정", "시·산업 상위 GVA 공식값"), ("KOSIS 경제총조사", "소분류 매출·사업체·종사자"), ("KOSIS 광공업 월지수", "시도×상세산업 생산·출하·재고"), ("포항시 사업체조사", "읍면동·구 산업 구조"), ("포항시 공장등록 1,465건", "제조업 공간분포"), ("LOCALDATA 19종", "월 인허가·폐업 변화"), ("읍면동 인구·경계", "규모·공간 결합")]
    table(draw, x, y, table_w, ["무료 공식자료", "모형 역할"], rows, [.50, .50], 46, [16, 16])
    flow_x = x + table_w + 28
    flow_w = cw - table_w - 28
    text(draw, (flow_x, y), "추정·검증 흐름", 21, NAVY, bold=True)
    steps = [("1", "상위 공식값", "시×산업×연·분기"), ("2", "하위 산출", "대→중→소"), ("3", "공간 나눔", "시→구→읍면동"), ("4", "월 흐름", "분기→월"), ("5", "재집계", "하위합→상위 단위"), ("6", "공식값 대조", "오차·활용단계")]
    step_w = (flow_w - 30) / 3
    for i, (n, title, desc) in enumerate(steps):
        col, row = i % 3, i // 3
        xx = flow_x + col * (step_w + 15)
        yy2 = y + 50 + row * 152
        rect(draw, (xx, yy2, xx + step_w, yy2 + 132), PALE, GRID, 1)
        rect(draw, (xx + 8, yy2 + 8, xx + 46, yy2 + 46), TEAL, TEAL, 1)
        box_text(draw, (xx + 8, yy2 + 8, xx + 46, yy2 + 46), n, 18, WHITE, bold=True, align="center")
        box_text(draw, (xx + 54, yy2 + 5, xx + step_w - 8, yy2 + 52), title, 18, NAVY, bold=True)
        box_paragraph(draw, (xx + 12, yy2 + 55, xx + step_w - 12, yy2 + 120), desc, 16, INK, False, 5, align="center")
    matrix_y = y + ch - 122
    rect(draw, (x, matrix_y, x + table_w, matrix_y + 112), "#E8F2F5", GRID, 1)
    box_text(draw, (x + 12, matrix_y + 10, x + table_w - 12, matrix_y + 38), "생성 해상도 범위", 19, NAVY, bold=True, align="center")
    for i, (a, b) in enumerate([("시간", "연·분기·월"), ("공간", "시·구·읍면동"), ("산업", "대·중·소분류")]):
        xx = x + 18 + i * (table_w - 36) / 3
        box_text(draw, (xx, matrix_y + 50, xx + (table_w - 46) / 3, matrix_y + 74), a, 16, MUTED, bold=True, align="center")
        box_text(draw, (xx, matrix_y + 74, xx + (table_w - 46) / 3, matrix_y + 104), b, 17, TEAL, bold=True, align="center")
    rect(draw, (flow_x, matrix_y, flow_x + flow_w, matrix_y + 112), "#FFF2E8", GRID, 1)
    box_text(draw, (flow_x + 12, matrix_y + 10, flow_x + flow_w - 12, matrix_y + 38), "검증 원칙", 19, ORANGE, bold=True, align="center")
    box_paragraph(draw, (flow_x + 20, matrix_y + 44, flow_x + flow_w - 20, matrix_y + 102), "미공표 하위 GVA 자체가 아니라, 재집계한 상위 공식값 오차로 판단", 17, INK, True, 5, align="center")

    y2, h2 = 1110, 670
    titles = [("03", "독립 검증 설계"), ("04", "GVA 정책 활용 기준"), ("05", "상위 공식통계 검증")]
    for col, (number, title_) in enumerate(titles):
        xx = M + col * (COL_W + GAP)
        x, y, cw, ch = panel(draw, xx, y2, COL_W, h2, number, title_)
        if col == 0:
            cards = [("산업축", "소분류 추정합→\n중·대분류 공식값"), ("공간축", "읍면동 추정합→\n구·시 공식값"), ("시간축", "월 추정합→\n분기·연 공식값"), ("공표축", "속보 자료와\n정밀화 자료 분리")]
            for i, (a, b) in enumerate(cards):
                yy = y + i * 113
                rect(draw, (x, yy, x + cw, yy + 96), PALE, GRID, 1)
                box_text(draw, (x + 12, yy, x + 127, yy + 96), a, 18, NAVY, bold=True)
                box_paragraph(draw, (x + 138, yy, x + cw - 12, yy + 96), b, 17, INK, False, 5)
            table(draw, x, y + 452, cw, ["순서", "엄격 검증 원칙"], [("1", "공식값은 사후검증 기준"), ("2", "하위합을 상위값으로 재집계"), ("3", "공표시점별 입력자료 분리")], [.20, .80], 34, [14, 14])
        elif col == 1:
            text(draw, (x, y), "예측 대상과 검증축 분리", 19, NAVY, bold=True)
            rows = [
                ("시간", "월→분기·연", "월 추정합이 분기·연 공식값과 일치"),
                ("산업", "소→중→대", "소분류 추정합을 중·대분류 공식값과 비교"),
                ("공간", "읍면동→구→시", "읍면동 추정합이 구·시 공식값과 일치"),
                ("운영", "속보/정밀화", "공표 가능자료와 사후 전체자료 분리"),
            ]
            table(draw, x, y + 42, cw, ["검증축", "해상도", "검증근거"], rows, [.16, .32, .52], 56, [15, 14, 13])
            rect(draw, (x, y + 318, x + cw, y + 450), "#FFF2E8", "#FFF2E8", 1)
            box_text(draw, (x + 12, y + 318, x + 135, y + 450), "집계검증", 18, ORANGE, bold=True)
            box_paragraph(draw, (x + 145, y + 318, x + cw - 12, y + 450), "절차: 하위 추정 → 상위 단위 재집계 → 공식값 대조\n원칙: 공식값은 입력값 아님 · 사후 검증 기준", 18, INK, True, 5)
            rect(draw, (x, y + 470, x + cw, y + 590), "#E9F5F3", "#E9F5F3", 1)
            box_text(draw, (x + 12, y + 470, x + 135, y + 590), "출력", 19, TEAL, bold=True)
            box_paragraph(draw, (x + 145, y + 470, x + cw - 12, y + 590), "산출: 읍면동·월·소분류 GVA 추정\n분리: 활용 가능 / 검토 필요 / 추가자료 결합\n출력: 담당부서 확인 목록", 18, INK, True, 5)
        else:
            checks = [("합계보존", "상위 총량 유지", GREEN), ("소→중 검증", "중분류 공식값 대조", GOLD), ("GRDP 외부검증", "경기도 평균오차 0.974%", TEAL), ("월간 점검지표", "산업별 변화", BLUE)]
            for i, (a, b, color) in enumerate(checks):
                yy = y + i * 102
                rect(draw, (x, yy, x + cw, yy + 86), PALE, GRID, 1)
                draw.ellipse((x + 12, yy + 30, x + 36, yy + 54), fill=color)
                box_text(draw, (x + 50, yy, x + 205, yy + 86), a, 18, NAVY, bold=True)
                box_text(draw, (x + 212, yy, x + cw - 12, yy + 86), b, 17, color, bold=True)
            rect(draw, (x, y + 424, x + cw, y + 528), "#FFF2E8", "#FFF2E8", 1)
            box_paragraph(draw, (x + 12, y + 424, x + cw - 12, y + 528), "판정: 중분류 공식 GVA로 산업별 격차 확인\nGRDP 검증은 상위 경제총량 신뢰도 확인", 18, INK, True, 5, align="center")

    y3, h3 = 1810, 880
    x, y, cw, ch = panel(draw, M, y3, COL_W, h3, "06", "2023년 읍면동 산업활력 분포")
    map_plot(draw, geo, map_values, (x + 8, y + 8, x + cw - 8, y + 455))
    box_text(draw, (x, y + 462, x + cw, y + 494), "3초 판독: 제조업 관련 지표 후보", 19, NAVY, bold=True, align="center")
    top_dongs = sorted(map_values.items(), key=lambda kv: kv[1], reverse=True)[:3]
    emd_name_map = dict(zip(emd_gva.emd_code.astype(str), emd_gva.emd_name.astype(str)))
    top_rows = [(emd_name_map.get(str(code), str(code)), "산단·항만 배후", "공장·인허가") for code, _ in top_dongs]
    table(draw, x, y + 505, cw, ["후보 읍면동", "공간맥락", "확인자료"], top_rows, [.34, .34, .32], 34, [12, 12, 12])
    criteria_rows = [
        ("값", "읍면동 추정 GVA ÷ 주민등록인구"),
        ("선정", "상위 3개 동 · 제조업 관련 지표 후보"),
        ("해석", "확정 순위가 아닌 현장확인 우선목록"),
    ]
    table(draw, x, y + 652, cw, ["구분", "내용"], criteria_rows, [.20, .80], 30, [12, 12])

    x, y, cw, ch = panel(draw, x2, y3, 2 * COL_W + GAP, h3, "07", "월별 산업활력 지수와 운영시점")
    chart_w = cw * .60
    text(draw, (x, y), "월별 GVA 지수: 산단·항만·상권의 급변 시점 포착", 19, NAVY, bold=True)
    line_chart(draw, x + 52, y + 92, chart_w - 86, 405, trends, periods)
    rect(draw, (x, y + 535, x + chart_w - 12, y + 617), "#E9F5F3", GRID, 1)
    box_text(draw, (x + 14, y + 535, x + 118, y + 617), "판독", 17, TEAL, bold=True, align="center")
    box_paragraph(draw, (x + 128, y + 535, x + chart_w - 24, y + 617), "상위 산업 변화폭 확인\n급변 산업 → 읍면동 후보표 연결", 16, INK, True, 4)
    card_y = y + 642
    card_w = (chart_w - 28) / 2
    for i, (a, b) in enumerate([("회복 신호", "전년동월 대비 증가"), ("점검 신호", "기준선 하회·급락")]):
        xx = x + i * (card_w + 16)
        rect(draw, (xx, card_y, xx + card_w, card_y + 74), "#F8FBFC", GRID, 1)
        box_text(draw, (xx + 10, card_y + 4, xx + card_w - 10, card_y + 34), a, 15, TEAL if i == 0 else ORANGE, bold=True, align="center")
        box_text(draw, (xx + 10, card_y + 34, xx + card_w - 10, card_y + 72), b, 14, INK, bold=True, align="center")
    rx = x + chart_w + 24
    draw.line((rx - 12, y, rx - 12, y + ch), fill=GRID, width=2)
    box_text(draw, (rx, y, x + cw, y + 38), "분기누적 운영판", 21, NAVY, bold=True, align="center")
    timing_rows = [
        ("1분기+1개월", "1~3월 공개자료", "연간 1차 전망"),
        ("1~2분기+1개월", "1~6월 공개자료", "상반기 재전망"),
        ("1~3분기+1개월", "1~9월 공개자료", "연말 전 점검"),
        ("공표 후", "연간 공식통계·전체자료", "정밀 재산출"),
    ]
    table(draw, rx, y + 50, x + cw - rx, ["운영시점", "사용자료", "산출물"], timing_rows, [.31, .38, .31], 56, [10, 10, 10])
    output_y = y + 335
    card_w2 = (x + cw - rx - 14) / 2
    for i, (a, b) in enumerate([("후보지도", "읍면동×업종"), ("월 지수", "산업별 변화"), ("오차표", "공식값 대조"), ("확인목록", "부서별 점검")]):
        col, row = i % 2, i // 2
        xx = rx + col * (card_w2 + 14)
        yy2 = output_y + row * 88
        rect(draw, (xx, yy2, xx + card_w2, yy2 + 72), PALE, GRID, 1)
        box_text(draw, (xx + 8, yy2 + 2, xx + card_w2 - 8, yy2 + 30), a, 14, NAVY, bold=True, align="center")
        box_text(draw, (xx + 8, yy2 + 31, xx + card_w2 - 8, yy2 + 67), b, 13, INK, bold=True, align="center")
    rect(draw, (rx, y + ch - 62, x + cw, y + ch - 12), "#FFF2E8", GRID, 1)
    box_text(draw, (rx + 12, y + ch - 62, x + cw - 12, y + ch - 12), "산출물: 시점별 전망과 현장확인 후보를 한 화면에서 연결", 15, ORANGE, bold=True, align="center")

    y4, h4 = 2720, 900
    hv = load_reporting_hv("포항시")
    precise_frame = hv[hv.refined_error_rate_pct.le(10)].nsmallest(4, ["refined_error_rate_pct", "refined_error_eok"])
    gap_frame = hv.nlargest(4, "refined_error_eok")
    sections = [(M, "08", "공표 후 정밀화: 격차 작은 중분류", precise_frame, TEAL, "속보: 월 변화 감지 · 정밀화: 공표 후 재산출"), (x2, "09", "공표 후 정밀화: 금액격차 큰 중분류", gap_frame, RED, "10% 초과 산업: 검토·추가자료 결합")]
    for xx0, num, title_, rows_df, color, footer in sections:
        x, y, cw, ch = panel(draw, xx0, y4, COL_W, h4, num, title_)
        box_text(draw, (x, y + 406, x + cw, y + 432), "기준: 2023년 연간 · 단위: 억원", 12, NAVY, bold=True, align="right")
        rows = [(table_label(r.middle_label), f"{r.actual_eok:,.0f}", f"{r.flash_eok:,.0f}", f"{r.refined_eok:,.0f}", f"{r.flash_error_eok:,.0f}\n({r.flash_error_rate_pct:.1f}%)", f"{r.refined_error_eok:,.0f}\n({r.refined_error_rate_pct:.1f}%)") for r in rows_df.itertuples()]
        table(draw, x, y, cw, ["중분류", "실제", "Q+1M\n속보", "정밀화", "속보오차", "정밀오차"], rows, [.30, .13, .13, .13, .155, .155], 68, [13, 13, 13, 13, 12, 12])
        if color == TEAL:
            cards = [("속보", "월 변화 감지"), ("정밀화", "최종 표기 기준 적용")]
        else:
            cards = [("원인", "산업별 직접 활동자료 부족"), ("조치", "공장·항만·고용자료 결합")]
        card_y = y + 430
        card_w = (cw - 18) / 2
        for i, (a, b) in enumerate(cards):
            xx = x + i * (card_w + 18)
            rect(draw, (xx, card_y, xx + card_w, card_y + 124), "#E9F5F3" if color == TEAL else "#FFF2E8", GRID, 1)
            box_text(draw, (xx + 12, card_y + 8, xx + card_w - 12, card_y + 42), a, 17, color, bold=True, align="center")
            box_text(draw, (xx + 12, card_y + 45, xx + card_w - 12, card_y + 112), b, 16, INK, bold=True, align="center")
        checks = [("금액", "실제·속보·정밀화·오차 모두 억원"), ("기준", "2023년 연간 중분류 공식 GVA와 재집계 추정값 비교"), ("표기", "속보보다 나쁜 정밀화 후보는 공개 성능값에서 제외"), ("활용", "오차 크기에 따라 모니터링·부서확인·현장자료 결합")]
        table(draw, x, y + 585, cw, ["항목", "포스터 해석"], checks, [.28, .72], 40, [13, 13])
        footer_fill = "#E9F5F3" if color == TEAL else "#FFF2E8"
        footer_color = color if color == TEAL else ORANGE
        rect(draw, (x, y + ch - 95, x + cw, y + ch - 13), footer_fill, footer_fill, 1)
        box_text(draw, (x + 12, y + ch - 95, x + cw - 12, y + ch - 13), footer, 18, footer_color, bold=True, align="center")
    x3 = M + 2 * (COL_W + GAP)
    x, y, cw, ch = panel(draw, x3, y4, COL_W, h4, "10", "산단·항만·상권 우선 점검 후보")
    decision_rows = [
        ("산단 배후 제조업", "제조 후보 동", "기업지원·산단관리"),
        ("항만 물류", "운수·창고 변화", "항만·교통부서"),
        ("읍면동 상권", "도소매·음식점", "소상공인 지원"),
        ("고용지원", "격차 큰 산업", "일자리·기업상담"),
        ("예산 배분", "오차 포함 검증표", "사업 우선순위"),
    ]
    table(draw, x, y, cw, ["정책용도", "산출물", "연결부서"], decision_rows, [.32, .33, .35], 56, [12, 12, 12])
    output_rows = [("지도", "29개 읍면동×산업"), ("목록", "현장확인 후보"), ("대시보드", "월 변화·공간집중"), ("보고서", "실제·추정·오차")]
    table(draw, x, y + 390, cw, ["운영 산출물", "내용"], output_rows, [.34, .66], 38, [12, 12])
    verdict_cards = [("낮은 오차", "운영 모니터링", TEAL), ("중간 오차", "부서 확인", GOLD), ("큰 오차", "현장자료 결합", RED)]
    card_w = (cw - 20) / 3
    card_y = y + 590
    for i, (title_, detail, color) in enumerate(verdict_cards):
        xx = x + i * (card_w + 10)
        rect(draw, (xx, card_y, xx + card_w, card_y + 84), "#F8FBFC", GRID, 1)
        rect(draw, (xx, card_y, xx + card_w, card_y + 30), "#E8F2F5", "#E8F2F5", 1)
        box_text(draw, (xx + 8, card_y, xx + card_w - 8, card_y + 30), title_, 13, color, bold=True, align="center")
        box_text(draw, (xx + 8, card_y + 30, xx + card_w - 8, card_y + 84), detail, 15, INK, bold=True, align="center")
    rect(draw, (x, y + ch - 82, x + cw, y + ch - 13), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 12, y + ch - 82, x + cw - 12, y + ch - 13), "결정 지원: 산업지원 우선순위 · 현장점검 대상 · 예산 배분 보조", 17, ORANGE, bold=True, align="center")

    y5, h5 = 3650, 1200
    x, y, cw, ch = panel(draw, M, y5, COL_W, h5, "11", "자료 확보성과 운영 가능성")
    source_rows = [("속보 자료", "분기 종료 후\n1개월 내 지표"), ("정밀화 자료", "공식 GVA·사업체조사\n공표 후 전체자료"), ("누수 차단", "공식값은 입력이 아닌\n사후 비교 기준"), ("경계·인구", "29개 행정 읍면동\n현행 경계 기준")]
    card_w = (cw - 18) / 2
    for i, (a, b) in enumerate(source_rows):
        col, row = i % 2, i // 2
        xx = x + col * (card_w + 18)
        yy2 = y + row * 134
        rect(draw, (xx, yy2, xx + card_w, yy2 + 116), PALE, GRID, 1)
        box_text(draw, (xx + 10, yy2 + 8, xx + card_w - 10, yy2 + 42), a, 16, NAVY, bold=True, align="center")
        box_text(draw, (xx + 10, yy2 + 45, xx + card_w - 10, yy2 + 106), b, 15, INK, bold=True, align="center")
    yy = subhead(draw, x, y + 290, "언제 산출 가능한가", cw)
    input_rows = [("1분기+1개월", "1~3월 자료", "1차 전망"), ("상반기+1개월", "1~6월 자료", "재전망"), ("3분기+1개월", "1~9월 자료", "연말 전 점검"), ("공표 후", "연간 공식·전체자료", "정밀화")]
    table(draw, x, yy, cw, ["시점", "사용자료", "산출"], input_rows, [.32, .35, .33], 48, [12, 12, 12])
    yy2 = subhead(draw, x, yy + 260, "운영 판정", cw)
    verdicts = [("낮은 오차", "월별 모니터링", TEAL), ("중간 오차", "담당부서 확인", GOLD), ("큰 오차", "현장자료 결합", RED)]
    small_w = (cw - 24) / 3
    for i, (a, b, color) in enumerate(verdicts):
        xx = x + i * (small_w + 12)
        rect(draw, (xx, yy2, xx + small_w, yy2 + 88), "#F8FBFC", GRID, 1)
        box_text(draw, (xx + 8, yy2 + 6, xx + small_w - 8, yy2 + 36), a, 14, color, bold=True, align="center")
        box_text(draw, (xx + 8, yy2 + 40, xx + small_w - 8, yy2 + 80), b, 13, INK, bold=True, align="center")
    output_rows = [("후보지도", "읍면동×업종×월"), ("오차표", "공식값·재집계 추정값·격차"), ("확인목록", "산업별 담당부서 연결")]
    table(draw, x, y + 805, cw, ["산출물", "내용"], output_rows, [.32, .68], 44, [13, 13])

    x, y, cw, ch = panel(draw, x2, y5, 2 * COL_W + GAP, h5, "12", "핵심 기여 및 기대효과")
    card_w = (cw - 36) / 3
    for i, (title_, items) in enumerate([("방법론 기여", ["미공표 읍면동·월·소분류 GVA 추정", "전 산업 19대·74중·228소분류 산출", "속보성·정밀화 지표 분리", "하위 추정합을 상위 공식값과 재대조", "무료 공공자료 기반 반복 갱신"]), ("검증 기여", ["소→중, 월→분기·연 재집계", "GRDP 시장가격 평균오차 0.974%", "제조업 월별 생산지수 반영", "억원·상대오차 동시 표기", "오차 큰 산업은 별도 활용단계 부여"]), ("정책 기여", ["산단 배후 제조업 후보", "항만 물류 변화 후보", "읍면동 상권 점검", "고용지원 우선순위", "예산·현장점검 후보 목록화"])]):
        xx = x + i * (card_w + 18)
        rect(draw, (xx, y, xx + card_w, y + 420), PALE, GRID, 1)
        rect(draw, (xx, y, xx + card_w, y + 52), SKY, SKY, 1)
        box_text(draw, (xx + 12, y, xx + card_w - 12, y + 52), title_, 20, NAVY, bold=True)
        yy = y + 70
        for item in items:
            yy = bullet(draw, xx + 12, yy, item, card_w - 24, 19) + 15
    rect(draw, (x, y + 445, x + cw, y + 635), "#E9F5F3", GRID, 1)
    box_text(draw, (x + 18, y + 445, x + 168, y + 635), "최종 제안", 22, TEAL, bold=True, align="center")
    box_paragraph(draw, (x + 185, y + 445, x + cw - 18, y + 635), "포항시가 매월 확인할 읍면동·업종 후보를 먼저 좁히는 산업지원 의사결정표\n공식통계가 늦게 보여주는 산업 변화를 산단관리·항만물류·상권회복·고용지원으로 연결", 23, INK, True, 7, align="center")
    policy_cards = [("산단", "제조업 후보 동", "기업지원·산단관리"), ("항만", "운수·창고 변화", "항만물류 점검"), ("상권", "도소매·음식점 위축", "소상공인 지원"), ("고용", "활력 하락 산업", "고용지원 연계")]
    card_w = (cw - 42) / 4
    for i, (a, b, c) in enumerate(policy_cards):
        xx = x + i * (card_w + 14)
        yy2 = y + 670
        rect(draw, (xx, yy2, xx + card_w, yy2 + 150), "#F8FBFC", GRID, 1)
        rect(draw, (xx, yy2, xx + card_w, yy2 + 38), SKY, SKY, 1)
        box_text(draw, (xx + 8, yy2, xx + card_w - 8, yy2 + 38), a, 17, NAVY, bold=True, align="center")
        box_text(draw, (xx + 8, yy2 + 45, xx + card_w - 8, yy2 + 90), b, 15, INK, bold=True, align="center")
        box_text(draw, (xx + 8, yy2 + 94, xx + card_w - 8, yy2 + 138), c, 14, TEAL, bold=True, align="center")
    rect(draw, (x, y + 848, x + cw, y + 956), "#E8F2F5", GRID, 1)
    box_text(draw, (x + 18, y + 848, x + 178, y + 956), "보고서 수록", 18, NAVY, bold=True, align="center")
    box_text(draw, (x + 190, y + 848, x + cw - 18, y + 956), "후보지도 · 월별 산업활력 지수 · 공식값-추정값 오차표 · 부서별 확인목록", 18, INK, bold=True, align="center")
    rect(draw, (x, y + ch - 96, x + cw, y + ch - 13), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 14, y + ch - 96, x + cw - 14, y + ch - 13), "수상 경쟁력: 전 산업 범위 + 읍면동 정책단위 + 공식값 대조 검증 + 편집 가능한 PDF/PPT 산출물", 19, ORANGE, bold=True, align="center")

    draw.line((M, H - 83, W - M, H - 83), fill=NAVY, width=3)
    box_text(draw, (M, H - 73, W - M, H - 31), "자료: 포항시 사업체조사·공장등록·인구, 지방행정 인허가, KOSIS 지역계정·경제총조사  |  GVA 집계검증 및 GRDP 시장가격 확장 검증 · 분석 기준: 2026년 7월", 16, MUTED, align="center")

    output = OUT / "poster_pohang_industrial_vitality_a1.png"
    preview = OUT / "poster_pohang_industrial_vitality_a1_preview.png"
    img.save(output, quality=95)
    img.resize((1240, round(1240 * H / W)), Image.Resampling.LANCZOS).save(preview, quality=95)
    print(output)
    print(preview)
    print(f"png_size={W}x{H} preview={Image.open(preview).size[0]}x{Image.open(preview).size[1]} status42={status42['emd']} status43_spatial={status43['improved_spatial_cv_mae_pp']:.3f} status45_groups={status45['groups']}")


if __name__ == "__main__":
    main()
