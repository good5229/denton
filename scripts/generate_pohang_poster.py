from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pohang"
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase42_pohang"
HIERARCHICAL_VALIDATION = DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv"
W, H = 3508, 4967
M, GAP = 72, 20
BODY_W = W - 2 * M
COL_W = (BODY_W - 2 * GAP) / 3
SLIDE_W_IN, SLIDE_H_IN = 594 / 25.4, 841 / 25.4
SX, SY = SLIDE_W_IN / W, SLIDE_H_IN / H

NAVY, BLUE, SKY, PAGE = "073B67", "2B6F9F", "DCECF5", "EEF4F7"
INK, MUTED, GRID, WHITE = "14242E", "50636F", "C7D4DC", "FFFFFF"
TEAL, ORANGE, RED, GOLD, PALE = "147D78", "E06A3B", "B33B32", "B98724", "F5F8FA"
GREEN = "2D8B72"
FONT, FONT_BOLD = "NanumBarunGothic", "NanumBarunGothic Bold"
FONT_SCALE = .58


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def parent_letters(parent_section: str) -> list[str]:
    parent_section = str(parent_section)
    if parent_section == "ERS":
        return ["E", "R", "S"]
    if parent_section == "MN0":
        return ["M", "N"]
    return [parent_section[0]]


def xin(value: float): return Inches(value * SX)
def yin(value: float): return Inches(value * SY)
def win(value: float): return Inches(value * SX)
def hin(value: float): return Inches(value * SY)


def rect(slide, x, y, w, h, fill=WHITE, line_color=GRID, width=.7, rounded=False, name=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, xin(x), yin(y), win(w), hin(h))
    if name: shape.name = name
    shape.fill.solid(); shape.fill.fore_color.rgb = rgb(fill)
    if line_color is None: shape.line.fill.background()
    else: shape.line.color.rgb = rgb(line_color); shape.line.width = Pt(width)
    return shape


def line(slide, x1, y1, x2, y2, color=GRID, width=.8, name=None):
    shape = slide.shapes.add_connector(1, xin(x1), yin(y1), xin(x2), yin(y2))
    shape.line.color.rgb = rgb(color); shape.line.width = Pt(width)
    if name: shape.name = name
    return shape


def textbox(slide, x, y, w, h, value, size=18, color=INK, bold=False, align="left", valign="middle", margin=0, name=None):
    shape = slide.shapes.add_textbox(xin(x), yin(y), win(w), hin(h))
    if name: shape.name = name
    frame = shape.text_frame; frame.clear(); frame.word_wrap = True
    frame.margin_left = frame.margin_right = xin(margin); frame.margin_top = frame.margin_bottom = yin(margin)
    frame.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}[valign]
    paragraph = frame.paragraphs[0]; paragraph.text = str(value)
    paragraph.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[align]
    paragraph.space_before = paragraph.space_after = Pt(0)
    paragraph.font.name = FONT_BOLD if bold else FONT; paragraph.font.size = Pt(size * FONT_SCALE); paragraph.font.bold = bold; paragraph.font.color.rgb = rgb(color)
    return shape


def bullets(slide, x, y, w, h, items, size=17, color=INK, name=None):
    shape = slide.shapes.add_textbox(xin(x), yin(y), win(w), hin(h))
    if name: shape.name = name
    frame = shape.text_frame; frame.clear(); frame.word_wrap = True
    frame.margin_left = frame.margin_right = xin(2); frame.margin_top = frame.margin_bottom = 0; frame.vertical_anchor = MSO_ANCHOR.TOP
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = f"• {item}"; paragraph.font.name = FONT; paragraph.font.size = Pt(size * FONT_SCALE); paragraph.font.color.rgb = rgb(color)
        paragraph.space_before = Pt(0); paragraph.space_after = Pt(2.3)
    return shape


def panel(slide, x, y, w, h, number, title):
    rect(slide, x, y, w, h, WHITE, GRID, .8, name=f"panel_{number}")
    rect(slide, x, y, w, 62, NAVY, None, name=f"panel_{number}_header")
    textbox(slide, x + 10, y, 50, 62, number, 22, SKY, True, "center", name=f"panel_{number}_number")
    textbox(slide, x + 70, y, w - 86, 62, title, 27, WHITE, True, name=f"panel_{number}_title")
    return x + 16, y + 78, w - 32, h - 94


def subhead(slide, x, y, w, title):
    textbox(slide, x, y, w, 32, title, 20, NAVY, True)
    line(slide, x, y + 36, x + w, y + 36, GRID, .6)
    return y + 48


def metric_card(slide, x, y, w, value, label, color=NAVY):
    textbox(slide, x, y, w, 52, value, 31, color, True, "center")
    textbox(slide, x, y + 52, w, 42, label, 15, MUTED, False, "center")


def hbars(slide, x, y, w, labels, values, colors, maximum, row_h=62, suffix="%p"):
    label_w, value_w = 250, 105
    bar_w = w - label_w - value_w
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        yy = y + i * row_h
        textbox(slide, x, yy, label_w - 12, 46, label, 16, INK, True)
        rect(slide, x + label_w, yy + 8, bar_w, 28, "E6EDF1", None)
        fill_w = max(4, bar_w * float(value) / maximum)
        rect(slide, x + label_w, yy + 8, fill_w, 28, color, None)
        textbox(slide, x + label_w + bar_w + 8, yy, value_w - 8, 46, f"{value:.2f}{suffix}", 16, color, True, "right")


def rings(geometry):
    if geometry["type"] == "Polygon": return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon": return [polygon[0] for polygon in geometry["coordinates"]]
    return []


def seq_color(value, minimum, maximum):
    t = .5 if maximum == minimum else min(1, max(0, (value - minimum) / (maximum - minimum)))
    lo, hi = (225, 239, 241), (4, 92, 98)
    return "".join(f"{round(lo[i] + t * (hi[i] - lo[i])):02X}" for i in range(3))


def editable_map(slide, geo, values, x, y, w, h):
    points = [point for feature in geo["features"] for ring in rings(feature["geometry"]) for point in ring]
    minx, maxx = min(p[0] for p in points), max(p[0] for p in points); miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
    scale = min((w - 8) / (maxx - minx), (h - 8) / (maxy - miny)); ox = x + (w - (maxx - minx) * scale) / 2; oy = y + (h - (maxy - miny) * scale) / 2
    lo, hi = min(values.values()), max(values.values())
    for feature in geo["features"]:
        code = str(feature["properties"]["adm_cd"]); color = seq_color(values.get(code, lo), lo, hi)
        for part, coords in enumerate(rings(feature["geometry"])):
            local = [((p[0] - minx) * scale, (maxy - p[1]) * scale) for p in coords]
            builder = slide.shapes.build_freeform(local[0][0], local[0][1], scale=(SX * 914400, SY * 914400)); builder.add_line_segments(local[1:], close=True)
            shape = builder.convert_to_shape(xin(ox), yin(oy)); shape.name = f"pohang_emd_{code}_{part + 1}"
            shape.fill.solid(); shape.fill.fore_color.rgb = rgb(color); shape.line.color.rgb = rgb(WHITE); shape.line.width = Pt(.35)


def line_chart(slide, x, y, w, h, series, periods):
    ymin, ymax = 70, 145
    for tick in (80, 100, 120, 140):
        yy = y + h - (tick - ymin) / (ymax - ymin) * h
        line(slide, x, yy, x + w, yy, GRID, .45); textbox(slide, x - 46, yy - 12, 38, 24, str(tick), 13, MUTED, False, "right")
    for boundary in (12, 24): line(slide, x + boundary / 35 * w, y, x + boundary / 35 * w, y + h, "AEBCC5", .6)
    for label, center in (("2021", 5.5), ("2022", 17.5), ("2023", 29.5)):
        textbox(slide, x + center / 35 * w - 38, y + h + 8, 76, 28, label, 13, MUTED, False, "center")
    palette = [TEAL, ORANGE, BLUE, GOLD]
    for index, (name, values) in enumerate(series):
        points = [(x + i / 35 * w, y + h - (float(value) - ymin) / (ymax - ymin) * h) for i, value in enumerate(values)]
        for j in range(len(points) - 1): line(slide, points[j][0], points[j][1], points[j + 1][0], points[j + 1][1], palette[index], 1.5, f"trend_{index}_{j}")
        lx = x + index * w / 4; line(slide, lx, y - 27, lx + 30, y - 27, palette[index], 1.8); textbox(slide, lx + 38, y - 42, w / 4 - 42, 28, name, 13, palette[index], True)


def native_table(slide, x, y, w, headers, rows, ratios, row_h=48, sizes=None):
    sizes = sizes or [15] * len(headers); widths = [w * ratio for ratio in ratios]
    xx = x
    for header, width in zip(headers, widths):
        rect(slide, xx, y, width, row_h, SKY, None); textbox(slide, xx + 8, y, width - 16, row_h, header, 16, NAVY, True); xx += width
    for row_index, row in enumerate(rows):
        yy = y + (row_index + 1) * row_h; xx = x
        for column_index, (value, width) in enumerate(zip(row, widths)):
            rect(slide, xx, yy, width, row_h, PALE if row_index % 2 else WHITE, GRID, .3)
            textbox(slide, xx + 8, yy, width - 16, row_h, value, sizes[column_index], INK, column_index == 0); xx += width


def main() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    status42 = json.loads((DATA / "partial_stats_phase42_pohang_status.json").read_text())
    status43 = json.loads((DATA / "partial_stats_phase43_pohang_status.json").read_text())
    status45 = json.loads((DATA / "partial_stats_phase45_pohang_status.json").read_text())
    diagnostics = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv", encoding="utf-8-sig", dtype={"industry_code": str})
    hierarchical = pd.read_csv(HIERARCHICAL_VALIDATION)
    complete = diagnostics.dropna(subset=["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"])
    good = complete.nsmallest(6, "combined_cv_score_pp"); bad = complete.nlargest(6, "combined_cv_score_pp")
    cube = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")
    monthly = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("대분류"))].copy()
    annual_large = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("연")) & (cube.industry_level.eq("대분류")) & (cube.period.astype(str).eq("2023"))].copy()
    large_gva_by_code = annual_large.groupby("industry_code").estimated_gva.sum().to_dict()
    totals = monthly[monthly.period.str.startswith("2023")].groupby(["industry_code", "industry_name"], as_index=False).estimated_gva.sum().nlargest(4, "estimated_gva")
    periods = sorted(monthly.period.unique()); trends = []
    for row in totals.itertuples():
        z = monthly[monthly.industry_code.eq(row.industry_code)].set_index("period").reindex(periods)
        base = z[z.index.str.startswith("2021")].estimated_gva.mean(); trends.append((str(row.industry_name).replace(" 서비스업", "").replace("업", ""), (z.estimated_gva / base * 100).tolist()))
    base = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet")
    emd_gva = base[base.year.eq(2023)].groupby(["emd_code", "emd_name"], as_index=False).estimated_emd_group_monthly_gva.sum()
    population = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_population.csv", dtype={"emd_code": str})
    emd_gva = emd_gva.merge(population[["emd_code", "population"]], on="emd_code"); emd_gva["gva_per_capita"] = emd_gva.estimated_emd_group_monthly_gva / emd_gva.population
    map_values = dict(zip(emd_gva.emd_code, emd_gva.gva_per_capita)); geo = json.loads((RAW / "administrative_dong_20260401.geojson").read_text())
    geo["features"] = [feature for feature in geo["features"] if feature["properties"].get("sggnm") in {"포항시남구", "포항시북구"}]

    prs = Presentation(); prs.slide_width = Inches(SLIDE_W_IN); prs.slide_height = Inches(SLIDE_H_IN)
    slide = prs.slides.add_slide(prs.slide_layouts[6]); slide.background.fill.solid(); slide.background.fill.fore_color.rgb = rgb(PAGE)
    textbox(slide, M, 42, BODY_W, 88, "포항시 산업활력 정밀지도", 76, NAVY, True, name="poster_title")
    textbox(slide, M, 136, BODY_W, 48, "행정 읍면동·전 산업 월간 부가가치 추정과 지역격차 경보", 38, INK, True, name="poster_subtitle")
    textbox(slide, M, 194, BODY_W, 32, "29개 행정 읍면동 × 산업 대·중·소분류 × 연·분기·월  |  무료 공공데이터 기반 총부가가치 추정", 20, MUTED, name="poster_meta")
    line(slide, M, 238, W - M, 238, NAVY, 2.5)
    rect(slide, M, 260, BODY_W, 142, WHITE, GRID)
    metrics = [("GVA→읍면동·월", "시 총량을 정책단위로 전환"), ("19·74·228", "전 산업 대·중·소분류"), ("집계검증", "실제-추정 격차 확인"), ("무료 공공자료", "반복 갱신 가능"), ("공간격차 지도", "동별 산업활력 비교"), ("신뢰도 차등", "활용·주의·보류 구분")]
    each = BODY_W / 6
    for i, (value, label) in enumerate(metrics):
        if i: line(slide, M + i * each, 280, M + i * each, 383, GRID, .55)
        metric_card(slide, M + i * each + 8, 274, each - 16, value, label, TEAL if i >= 4 else NAVY)

    y1, h1 = 430, 650
    x, y, cw, ch = panel(slide, M, y1, COL_W, h1, "01", "문제 정의와 분석 목표")
    yy = subhead(slide, x, y, cw, "정책 문제")
    textbox(slide, x, yy, cw, 88, "시·구 연간 총량만으로는 산업 충격이 어느 읍면동에 집중되고 언제 시작됐는지 판별하기 어렵다.", 20, INK, valign="top")
    yy += 98; yy = subhead(slide, x, yy, cw, "분석 목표")
    bullets(slide, x, yy, cw, 96, ["전 산업을 동일 기준으로 29개 읍면동까지 배분", "월·분기·연 및 읍면동·구·시 합계를 동시 보존", "산업별 실제-추정 격차로 활용 등급을 구분"], 16)
    rows = [("시간", "연·분기·월"), ("공간", "시·구·29개 읍면동"), ("산업", "산업 대·중·소분류")]
    native_table(slide, x, y + 350, cw, ["축", "분석 범위"], rows, [.25, .75], 26, [12, 12])
    rect(slide, x, y + ch - 92, cw, 84, "FFF2E8", None)
    textbox(slide, x + 12, y + ch - 92, 120, 84, "핵심 질문", 17, ORANGE, True)
    textbox(slide, x + 140, y + ch - 92, cw - 152, 84, "어느 동·산업을 먼저 확인하고 지원할 것인가?", 19, INK, True)

    x2 = M + COL_W + GAP
    x, y, cw, ch = panel(slide, x2, y1, 2 * COL_W + GAP, h1, "02", "활용 데이터와 시공간 배분 절차")
    table_w = cw * .48
    rows = [("KOSIS 경제총조사", "소분류 매출·사업체·종사자"), ("포항시 사업체조사", "읍면동·구 산업 실제값"), ("포항시 공장등록 1,465건", "제조업 공간분포"), ("LOCALDATA 19종", "월 인허가·폐업 변화"), ("읍면동 인구·경계", "규모·공간 결합"), ("시 산업별 부가가치", "연·분기 기준값")]
    native_table(slide, x, y, table_w, ["무료 공식자료", "모형 역할"], rows, [.50, .50], 46, [15, 15])
    flow_x = x + table_w + 28; flow_w = cw - table_w - 28
    textbox(slide, flow_x, y, flow_w, 30, "배분·검증 프로세스", 20, NAVY, True)
    steps = [("1", "상위 기준", "시×산업×연·분기"), ("2", "산업배분", "대→중→소"), ("3", "공간배분", "시→구→읍면동"), ("4", "시간배분", "분기→월"), ("5", "독립검증", "매출·공간·차년도"), ("6", "집계검증", "하위합→상위 실제값")]
    step_w = (flow_w - 30) / 3
    for i, (n, title, desc) in enumerate(steps):
        col, row = i % 3, i // 3; xx = flow_x + col * (step_w + 15); yy2 = y + 50 + row * 152
        rect(slide, xx, yy2, step_w, 132, PALE, GRID, .5, rounded=True)
        rect(slide, xx + 8, yy2 + 8, 38, 38, TEAL, None, rounded=True)
        textbox(slide, xx + 8, yy2 + 8, 38, 38, n, 18, WHITE, True, "center")
        textbox(slide, xx + 54, yy2 + 5, step_w - 62, 48, title, 17, NAVY, True)
        textbox(slide, xx + 12, yy2 + 56, step_w - 24, 62, desc, 15, INK, False, "center")
    matrix_y = y + ch - 122
    rect(slide, x, matrix_y, table_w, 112, "E8F2F5", GRID, .5)
    textbox(slide, x + 12, matrix_y + 10, table_w - 24, 28, "생성 해상도 범위", 18, NAVY, True, "center")
    scope_rows = [("시간", "연·분기·월"), ("공간", "시·구·읍면동"), ("산업", "대·중·소분류")]
    for i, (a, b) in enumerate(scope_rows):
        xx = x + 18 + i * (table_w - 36) / 3
        textbox(slide, xx, matrix_y + 50, (table_w - 46) / 3, 24, a, 15, MUTED, True, "center")
        textbox(slide, xx, matrix_y + 74, (table_w - 46) / 3, 28, b, 16, TEAL, True, "center")
    rect(slide, flow_x, matrix_y, flow_w, 112, "FFF2E8", GRID, .5)
    textbox(slide, flow_x + 12, matrix_y + 10, flow_w - 24, 28, "검증 원칙", 18, ORANGE, True, "center")
    textbox(slide, flow_x + 20, matrix_y + 46, flow_w - 40, 54, "소분류 추정값을 중분류로 재집계해 실제 GVA와 비교", 16, INK, True, "center")

    y2, h2 = 1110, 670
    for col, number, title in [(0, "03", "독립 검증 설계"), (1, "04", "GVA 신뢰도 판정"), (2, "05", "활용 판정 및 검증")]:
        xx = M + col * (COL_W + GAP); x, y, cw, ch = panel(slide, xx, y2, COL_W, h2, number, title)
        if col == 0:
            cards = [("산업축", "2015 매출 비공개\n사업체·종사자→매출"), ("공간축", "2023 읍면동×중분류\n인구·공장·인허가 검증"), ("외삽축", "2024 남·북구 매출\n목표 산업 제외 검증"), ("회계축", "소→중→대·월→분기\n읍면동→시 재집계")]
            for i, (a, b) in enumerate(cards):
                yy = y + i * 113; rect(slide, x, yy, cw, 96, PALE, GRID, .5); textbox(slide, x + 12, yy, 115, 96, a, 17, NAVY, True); textbox(slide, x + 138, yy, cw - 150, 96, b, 16, INK)
            rows = [("1", "실제값 분리"), ("2", "목표 산업 제외"), ("3", "상위합계 사후검사")]
            native_table(slide, x, y + 452, cw, ["순서", "엄격 검증 원칙"], rows, [.20, .80], 34, [13, 13])
        elif col == 1:
            textbox(slide, x, y, cw, 28, "예측 대상과 검증축 분리", 18, NAVY, True)
            rows = [("A", "연×시 GVA", "공식 지역 부가가치 직접 대조"), ("B/C", "소→중 집계", "소분류 배분값을 중분류 실제값과 비교"), ("C/D", "읍면동 GVA", "읍면동 산업분포 검증"), ("D", "월 GVA", "연·분기 합계와 월 경로 대조")]
            native_table(slide, x, y + 42, cw, ["등급", "해상도", "검증근거"], rows, [.16, .32, .52], 56, [14, 13, 12])
            rect(slide, x, y + 338, cw, 112, "FFF2E8", None); textbox(slide, x + 12, y + 338, 123, 112, "집계검증", 17, ORANGE, True); textbox(slide, x + 145, y + 338, cw - 157, 112, "소분류 배분값을 중분류로 합산해 실제값과 비교: MAE 10.29%p, 66개 중 17개가 1%p 이하.", 16, INK, True)
            rect(slide, x, y + 474, cw, 116, "E9F5F3", None); textbox(slide, x + 12, y + 474, 123, 116, "사용", 18, TEAL, True); textbox(slide, x + 145, y + 474, cw - 157, 116, "소분류 추정값을 중분류 단위로 다시 합산한 뒤, 실제 중분류 GVA와 직접 비교해 산업별 오차를 산출.", 16, INK, True)
        else:
            checks = [("집계검증", "최대 2.33e-10", GREEN), ("소→중 집계", "17/66개 1%p 이하", GOLD), ("공장 결합", "업종·읍면동 76.5%", GOLD), ("월 경보값", "산업별 변화", TEAL)]
            for i, (a, b, color) in enumerate(checks):
                yy = y + i * 102; rect(slide, x, yy, cw, 86, PALE, GRID, .5); rect(slide, x + 12, yy + 22, 24, 24, color, None, rounded=True); textbox(slide, x + 50, yy, 155, 86, a, 17, NAVY, True); textbox(slide, x + 212, yy, cw - 224, 86, b, 16, color, True)
            rect(slide, x, y + 424, cw, 104, "FFF2E8", None); textbox(slide, x + 12, y + 424, cw - 24, 104, "판정: 중분류 실제 GVA로 산업별 격차 확인\n읍면동×소분류×월은 신뢰등급과 함께 활용", 17, INK, True, "center")

    y3, h3 = 1810, 880
    x, y, cw, ch = panel(slide, M, y3, COL_W, h3, "06", "2023년 읍면동 산업활력 분포")
    editable_map(slide, geo, map_values, x + 10, y + 10, cw - 20, 505)
    textbox(slide, x, y + 525, cw, 32, "1인당 추정 부가가치 상대분포", 18, NAVY, True, "center")
    textbox(slide, x, y + 565, cw, 82, "진한 색일수록 2023년 추정 부가가치/주민등록인구가 높음. 산업시설 집중지역의 현장점검 우선순위 보조지표.", 16, MUTED, False, "center")
    rect(slide, x, y + ch - 75, cw, 62, "E8F2F5", None); textbox(slide, x + 12, y + ch - 75, cw - 24, 62, "지도 도형 29개 개별 선택·편집 가능", 15, NAVY, True, "center")

    x, y, cw, ch = panel(slide, x2, y3, 2 * COL_W + GAP, h3, "07", "전 산업 월 변화와 산업구조")
    textbox(slide, x, y, cw, 30, "2021년 월평균=100 · 2023년 부가가치 상위 4개 대분류", 18, NAVY, True)
    line_chart(slide, x + 52, y + 86, cw - 80, 250, trends, periods)
    textbox(slide, x, y + 380, cw, 62, "월 경로는 연·분기 기준값을 월별 활동 변화로 나눈 추정지수다. 산업 간 변동 방향 비교와 경보 후보 선별에 사용한다.", 16, MUTED, False, "center")
    yy = subhead(slide, x, y + 456, cw, "경보 산출")
    items = [("산업규모", "시 산업 부가가치"), ("공간집중", "읍면동 산업비중"), ("월 변화", "인허가 영업재고"), ("신뢰등급", "산업별 검증오차")]
    for i, (a, b) in enumerate(items):
        xx = x + i * cw / 4; rect(slide, xx, yy, cw / 4 - 10, 112, PALE, GRID, .4); textbox(slide, xx + 8, yy + 7, cw / 4 - 26, 40, a, 16, NAVY, True, "center"); textbox(slide, xx + 8, yy + 50, cw / 4 - 26, 52, b, 15, INK, False, "center")
    rect(slide, x, y + ch - 80, cw, 68, "FFF2E8", None); textbox(slide, x + 12, y + ch - 80, cw - 24, 68, "경보 = 변동 악화 × 공간집중 × 검증신뢰도  →  현장확인 후보", 18, ORANGE, True, "center")

    y4, h4 = 2720, 900
    hv = hierarchical[hierarchical.city.eq("포항시")].copy()
    hv["middle_label"] = hv.middle_name.fillna(hv.middle_code.astype(str))
    hv["actual_pct"] = hv.actual_middle_share * 100
    hv["pred_pct"] = hv.predicted_small_aggregated_share * 100
    hv["error_pct"] = hv.abs_error_pp
    hv["parent_gva_eok"] = hv.parent_section.map(lambda code: sum(large_gva_by_code.get(letter, 0.0) for letter in parent_letters(code)) / 100)
    hv["actual_eok"] = hv.actual_middle_share * hv.parent_gva_eok
    hv["pred_eok"] = hv.predicted_small_aggregated_share * hv.parent_gva_eok
    hv["error_eok"] = (hv.pred_eok - hv.actual_eok).abs()
    hv["error_rate_pct"] = hv.error_eok / hv.actual_eok.replace(0, pd.NA) * 100
    hv = hv[hv.actual_middle_share.between(0.001, 0.999)]

    precise_frame = hv[hv.error_rate_pct.le(10)].nsmallest(6, ["error_rate_pct", "error_eok"])
    gap_frame = hv.nlargest(6, "error_eok")
    for xx0, num, title, frame, color, footer in [(M, "08", "격차 작은 중분류 · 오차율 10% 이하", precise_frame, TEAL, "활용: 월 변화 경보 + 현장자료 확인"), (x2, "09", "금액격차 큰 중분류 · 정확도 진단", gap_frame, RED, "Phase100 판정: strict 통과 0개 · 운영 참고 2묶음")]:
        x, y, cw, ch = panel(slide, xx0, y4, COL_W, h4, num, title)
        rows = [(r.middle_label, f"{r.actual_eok:,.0f}", f"{r.pred_eok:,.0f}", f"{r.error_eok:,.0f}\n({r.error_rate_pct:.1f}%)") for r in frame.itertuples()]
        native_table(slide, x, y, cw, ["중분류", "실제", "추정", "오차"], rows, [.48, .17, .17, .18], 63, [14, 14, 14, 12])
        desc = "단위: 억원 환산. 실제=상위 GVA×중분류 실제 비중, 추정=상위 GVA×소분류 합산비중, 오차=억원(상대오차율). 10% 초과는 정밀판정 제외." if color == TEAL else "포항 취약묶음 7개 중 2개는 운영 참고 후보, 5개는 자료보강 대상. 대외 주장은 strict 통과 기준으로 제한한다."
        textbox(slide, x, y + 445, cw, 115, desc, 16, MUTED, False, "center")
        rows = [("중분류 추정", "실제값과 직접 비교"), ("격차진단", "금액오차 상위 산업 우선"), ("단위", "억원 · 상대오차 병기")]
        native_table(slide, x, y + 560, cw, ["항목", "판정"], rows, [.30, .70], 38, [12, 12])
        fill = "E9F5F3" if color == TEAL else "FFF2E8"
        rect(slide, x, y + ch - 52, cw, 40, fill, None); textbox(slide, x + 12, y + ch - 52, cw - 24, 40, footer, 13, color if color == TEAL else ORANGE, True, "center")

    x3 = M + 2 * (COL_W + GAP); x, y, cw, ch = panel(slide, x3, y4, COL_W, h4, "10", "정책 운영 산출물")
    stages = [("1 갱신", "연·분기 부가가치와 월 인허가"), ("2 판정", "산업별 실제-추정 격차"), ("3 탐지", "읍면동 집중·월 악화"), ("4 확인", "기업·상권·산단 현장자료"), ("5 지원", "산업·지역 맞춤사업 연결")]
    for i, (a, b) in enumerate(stages):
        yy = y + i * 105; rect(slide, x, yy, cw, 90, PALE, GRID, .5); textbox(slide, x + 12, yy, 125, 90, a, 17, NAVY, True); textbox(slide, x + 145, yy, cw - 157, 90, b, 16, INK, True)
    rows = [("지도", "29개 읍면동×산업"), ("목록", "신뢰등급·현장확인"), ("대시보드", "월 변화·공간집중"), ("보고서", "오차·비추정 사유")]
    native_table(slide, x, y + 520, cw, ["산출물", "내용"], rows, [.28, .72], 34, [12, 12])
    textbox(slide, x, y + 692, cw, 16, "높은 신뢰=경보 · 중간=보조지표 · 낮은 신뢰=자료수집", 12, MUTED, False, "center")
    rect(slide, x, y + ch - 95, cw, 82, "FFF2E8", None); textbox(slide, x + 12, y + ch - 95, cw - 24, 82, "정책 연결: 산단·상권·고용·창업 지원 우선순위", 17, ORANGE, True, "center")

    y5, h5 = 3650, 1200
    x, y, cw, ch = panel(slide, M, y5, COL_W, h5, "11", "자료 확보성 검토")
    source_rows = [("공식 실제값", "2023 읍면동×중분류\n2024 구×중분류 매출"), ("월 변동", "LOCALDATA 19종\n2021–2026 인허가"), ("취약묶음 판정", "strict 0개\n운영참고 2개"), ("경계·인구", "29개 행정 읍면동\n현행 경계 기준")]
    for i, (a, b) in enumerate(source_rows):
        yy = y + i * 128
        rect(slide, x, yy, cw, 108, PALE, GRID, .5)
        textbox(slide, x + 14, yy, 148, 108, a, 17, NAVY, True)
        textbox(slide, x + 174, yy, cw - 188, 108, b, 16, INK, True)
    yy = subhead(slide, x, y + 535, cw, "판정")
    verdicts = [("가능", "연·분기·월 × 시·구·읍면동 × 산업 대·중·소"), ("검증", "산업 매출·읍면동 분포·차년도 구 매출"), ("보강", "취약 중분류 직접 활동자료 확대")]
    for i, (a, b) in enumerate(verdicts):
        yy2 = yy + i * 92
        color = TEAL if a == "가능" else ORANGE if a == "검증" else RED
        rect(slide, x, yy2, cw, 74, WHITE, GRID, .4)
        textbox(slide, x + 12, yy2, 88, 74, a, 17, color, True, "center")
        textbox(slide, x + 112, yy2, cw - 124, 74, b, 15, INK, True)
    rect(slide, x, y + ch - 98, cw, 84, "FBEDEA", None)
    textbox(slide, x + 12, y + ch - 98, cw - 24, 84, "산업별 실제-추정 격차와\n정책 후보 선별 기준", 18, RED, True, "center")

    x, y, cw, ch = panel(slide, x2, y5, 2 * COL_W + GAP, h5, "12", "핵심 기여 및 기대효과")
    conclusion_cards = [("방법론 기여", ["공식 GVA를 읍면동×월×산업으로 전환", "전 산업 19대·74중·228소분류 동시 산출", "공간·시간·산업 총량 제약 보존", "중분류 실제값과 비교해 오차 위치 식별", "동·월·산업별 신뢰등급 동시 표시", "고양·포항 공통 구조로 확장성 확인"]), ("검증 기여", ["소분류 합산값을 중분류 실제값과 대조", "소→중 집계 MAE 10.29%p 공개", "17/66개 중분류 집계오차 1%p 이하", "억원·상대오차를 함께 표기", "strict 통과 0개를 명시", "운영 참고·자료보강 묶음 분리"]), ("정책 기여", ["29개 읍면동 산업활력 격차 지도화", "월 변화로 조기경보 후보 선별", "산단·항만·상권·고용정책 우선순위 연결", "유료 카드자료 없이 무료 자료 기반 갱신", "취약 묶음은 자료보강 대상으로 분리", "공모전 평가요소: 정확성·실현성·공공성 대응"])]
    card_w = (cw - 36) / 3
    for i, (title, items) in enumerate(conclusion_cards):
        xx = x + i * (card_w + 18); rect(slide, xx, y, card_w, 510, PALE, GRID, .5); rect(slide, xx, y, card_w, 52, SKY, None); textbox(slide, xx + 12, y, card_w - 24, 52, title, 19, NAVY, True); bullets(slide, xx + 12, y + 70, card_w - 24, 410, items, 16)
    rect(slide, x, y + 535, cw, 170, "E9F5F3", GRID, .6)
    textbox(slide, x + 18, y + 535, 150, 170, "최종 제안", 21, TEAL, True, "center")
    textbox(slide, x + 185, y + 535, cw - 203, 170, "최종 판정: 포항 취약묶음 7개 중 strict 통과 0개\n운영 참고 2개·자료보강 5개로 구분\n총부가가치 실제-추정 격차를 공개하는 검증형 정책지도", 23, INK, True, "center")
    yy = subhead(slide, x, y + 735, cw, "기대효과")
    effects = [("정밀성", "시·구 평균에 가린 동 격차 발견"), ("적시성", "연간 통계 사이 월 변화 후보 탐지"), ("실현성", "기존 무료 자료·반복 실행"), ("검증성", "실제·추정·오차 공개")]
    for i, (a, b) in enumerate(effects):
        xx = x + i * cw / 4; rect(slide, xx, yy, cw / 4 - 10, 132, WHITE, GRID, .5); textbox(slide, xx + 8, yy + 8, cw / 4 - 26, 42, a, 18, NAVY, True, "center"); textbox(slide, xx + 8, yy + 54, cw / 4 - 26, 68, b, 15, INK, False, "center")
    rect(slide, x, y + ch - 115, cw, 102, "FFF2E8", None); textbox(slide, x + 14, y + ch - 115, cw - 28, 102, "수상 경쟁력: 전 산업 범위 + 읍면동 정책단위 + 실제-추정 격차 공개 + 편집·재현 가능한 산출물", 19, ORANGE, True, "center")

    line(slide, M, H - 83, W - M, H - 83, NAVY, 1.2)
    textbox(slide, M, H - 73, BODY_W, 42, "자료: 포항시 사업체조사·공장등록·인구, 지방행정 인허가, KOSIS 지역계정·경제총조사  |  분석 기준: 2026년 7월", 15, MUTED, False, "center")
    output = OUT / "poster_pohang_industrial_vitality_a1_editable.pptx"; prs.save(output)
    print(output); print(f"slide_size_mm={prs.slide_width / 36000:.1f}x{prs.slide_height / 36000:.1f} shapes={len(slide.shapes)}")
    return output


if __name__ == "__main__":
    main()
