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
W, H = 3508, 4967
M, GAP = 86, 26
BODY_W = W - 2 * M
COL_W = (BODY_W - 2 * GAP) / 3
SLIDE_W_IN, SLIDE_H_IN = 594 / 25.4, 841 / 25.4
SX, SY = SLIDE_W_IN / W, SLIDE_H_IN / H

NAVY, BLUE, SKY, PAGE = "073B67", "2B6F9F", "DCECF5", "EEF4F7"
INK, MUTED, GRID, WHITE = "14242E", "50636F", "C7D4DC", "FFFFFF"
TEAL, ORANGE, RED, GOLD, PALE = "147D78", "E06A3B", "B33B32", "B98724", "F5F8FA"
GREEN = "2D8B72"
FONT, FONT_BOLD = "NanumBarunGothic", "NanumBarunGothic Bold"


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


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
    paragraph.font.name = FONT_BOLD if bold else FONT; paragraph.font.size = Pt(size * .48); paragraph.font.bold = bold; paragraph.font.color.rgb = rgb(color)
    return shape


def bullets(slide, x, y, w, h, items, size=17, color=INK, name=None):
    shape = slide.shapes.add_textbox(xin(x), yin(y), win(w), hin(h))
    if name: shape.name = name
    frame = shape.text_frame; frame.clear(); frame.word_wrap = True
    frame.margin_left = frame.margin_right = xin(2); frame.margin_top = frame.margin_bottom = 0; frame.vertical_anchor = MSO_ANCHOR.TOP
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = f"• {item}"; paragraph.font.name = FONT; paragraph.font.size = Pt(size * .48); paragraph.font.color.rgb = rgb(color)
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
    complete = diagnostics.dropna(subset=["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"])
    good = complete.nsmallest(6, "combined_cv_score_pp"); bad = complete.nlargest(6, "combined_cv_score_pp")
    cube = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")
    monthly = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("대분류"))].copy()
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
    textbox(slide, M, 48, BODY_W, 82, "포항시 산업활력 시공간 추정과 지역격차 진단", 66, NAVY, True, name="poster_title")
    textbox(slide, M, 140, BODY_W, 45, "29개 행정 읍면동 × KSIC 전 산업 × 월간 GVA 제약추정·교차검증", 32, INK, True, name="poster_subtitle")
    textbox(slide, M, 195, BODY_W, 30, "무료 공공데이터 기반 개발통계  |  공식 상위합계 보존  |  오차·한계 동시 공개", 18, MUTED, name="poster_meta")
    line(slide, M, 238, W - M, 238, NAVY, 2.5)
    rect(slide, M, 260, BODY_W, 142, WHITE, GRID)
    metrics = [("29개", "행정 읍면동"), ("19·74·228", "KSIC 대·중·소"), ("36개월", "2021–2023"), ("8.49·4.98%p", "중·소 산업 CV"), ("2.95%p", "읍면동 공간 CV"), ("8.81%p", "남·북구 매출 CV")]
    each = BODY_W / 6
    for i, (value, label) in enumerate(metrics):
        if i: line(slide, M + i * each, 280, M + i * each, 383, GRID, .55)
        metric_card(slide, M + i * each + 8, 274, each - 16, value, label, TEAL if i >= 4 else NAVY)

    y1, h1 = 430, 650
    x, y, cw, ch = panel(slide, M, y1, COL_W, h1, "01", "문제 정의와 분석 목표")
    yy = subhead(slide, x, y, cw, "정책 문제")
    textbox(slide, x, yy, cw, 88, "시·구 연간 총량만으로는 산업 충격이 어느 읍면동에 집중되고 언제 시작됐는지 판별하기 어렵다.", 20, INK, valign="top")
    yy += 98; yy = subhead(slide, x, yy, cw, "분석 목표")
    bullets(slide, x, yy, cw, 142, ["전 산업을 동일 기준으로 29개 읍면동까지 배분", "월·분기·연 및 읍면동·구·시 합계를 동시 보존", "예측 양호·취약 산업을 구분해 활용 강도 차등화"], 16)
    rect(slide, x, y + ch - 92, cw, 84, "FFF2E8", None)
    textbox(slide, x + 12, y + ch - 92, 120, 84, "핵심 질문", 17, ORANGE, True)
    textbox(slide, x + 140, y + ch - 92, cw - 152, 84, "어느 동·산업을 먼저 확인하고 지원할 것인가?", 19, INK, True)

    x2 = M + COL_W + GAP
    x, y, cw, ch = panel(slide, x2, y1, 2 * COL_W + GAP, h1, "02", "활용 데이터와 시공간 배분 절차")
    table_w = cw * .48
    rows = [("KOSIS 경제총조사", "산업 매출 홀드아웃"), ("포항시 사업체조사", "읍면동·구 actual"), ("포항시 공장등록", "제조업 공간분포"), ("LOCALDATA 19종", "월 인허가 변화"), ("읍면동 인구·경계", "규모·공간 결합"), ("시 산업별 GVA", "연·분기 상위통제")]
    native_table(slide, x, y, table_w, ["무료 공식자료", "모형 역할"], rows, [.50, .50], 46, [15, 15])
    flow_x = x + table_w + 28; flow_w = cw - table_w - 28
    textbox(slide, flow_x, y, flow_w, 30, "배분·검증 프로세스", 20, NAVY, True)
    steps = [("1", "상위통제", "시×산업×연·분기"), ("2", "산업배분", "대→중→소"), ("3", "공간배분", "시→구→읍면동"), ("4", "시간배분", "분기→월"), ("5", "독립검증", "매출·공간·차년도"), ("6", "회계검증", "하위합→상위 actual")]
    step_w = (flow_w - 30) / 3
    for i, (n, title, desc) in enumerate(steps):
        col, row = i % 3, i // 3; xx = flow_x + col * (step_w + 15); yy2 = y + 50 + row * 152
        rect(slide, xx, yy2, step_w, 132, PALE, GRID, .5, rounded=True)
        rect(slide, xx + 8, yy2 + 8, 38, 38, TEAL, None, rounded=True)
        textbox(slide, xx + 8, yy2 + 8, 38, 38, n, 18, WHITE, True, "center")
        textbox(slide, xx + 54, yy2 + 5, step_w - 62, 48, title, 17, NAVY, True)
        textbox(slide, xx + 12, yy2 + 56, step_w - 24, 62, desc, 15, INK, False, "center")
    rect(slide, flow_x, y + ch - 68, flow_w, 58, "E8F2F5", None)
    textbox(slide, flow_x + 12, y + ch - 68, flow_w - 24, 58, "매출은 적합에서 제외 · 합계 일치는 성능점수가 아닌 제약검사", 16, NAVY, True, "center")

    y2, h2 = 1110, 670
    for col, number, title in [(0, "03", "독립 검증 설계"), (1, "04", "성능개선 결과"), (2, "05", "활용 판정 및 검증")]:
        xx = M + col * (COL_W + GAP); x, y, cw, ch = panel(slide, xx, y2, COL_W, h2, number, title)
        if col == 0:
            cards = [("산업축", "2015 매출 비공개\n사업체·종사자→매출"), ("공간축", "2023 읍면동×중분류\n인구·공장·인허가 검증"), ("외삽축", "2024 남·북구 매출\n목표 산업 제외 검증"), ("회계축", "소→중→대·월→분기\n읍면동→시 재집계")]
            for i, (a, b) in enumerate(cards):
                yy = y + i * 113; rect(slide, x, yy, cw, 96, PALE, GRID, .5); textbox(slide, x + 12, yy, 115, 96, a, 17, NAVY, True); textbox(slide, x + 138, yy, cw - 150, 96, b, 16, INK)
        elif col == 1:
            textbox(slide, x, y, cw, 28, "실제 홀드아웃 평균절대오차", 18, NAVY, True)
            hbars(slide, x, y + 42, cw, ["공간 기존", "공간 개선", "구 매출 기존", "구 매출 개선"], [3.380, 2.947, 14.007, 8.809], [MUTED, TEAL, MUTED, ORANGE], 15, 70)
            rect(slide, x, y + 350, cw, 93, "E9F5F3", None); textbox(slide, x + 12, y + 350, 150, 93, "개선 폭", 18, TEAL, True); textbox(slide, x + 170, y + 350, cw - 182, 93, "공간 -0.433%p\n구 매출 -5.198%p", 21, INK, True)
            textbox(slide, x, y + 455, cw, 72, "74개 산업을 하나씩 제외한 중첩교차검증 결과", 16, MUTED, False, "center")
        else:
            checks = [("상위합계", "최대 2.33×10⁻¹⁰", GREEN), ("공간 프로필", "중분류 0 · 소분류 4/19", GOLD), ("공장 결합", "업종·읍면동 76.5%", GOLD), ("월 actual", "부재 · 개발통계", RED)]
            for i, (a, b, color) in enumerate(checks):
                yy = y + i * 102; rect(slide, x, yy, cw, 86, PALE, GRID, .5); rect(slide, x + 12, yy + 22, 24, 24, color, None, rounded=True); textbox(slide, x + 50, yy, 155, 86, a, 17, NAVY, True); textbox(slide, x + 212, yy, cw - 224, 86, b, 16, color, True)
            rect(slide, x, y + 424, cw, 104, "FFF2E8", None); textbox(slide, x + 12, y + 424, cw - 24, 104, "판정: 중분류 공간분포는 검증 가능\n읍면동×소분류×월은 제약추정으로 제한", 17, INK, True, "center")

    y3, h3 = 1810, 880
    x, y, cw, ch = panel(slide, M, y3, COL_W, h3, "06", "2023년 읍면동 산업활력 분포")
    editable_map(slide, geo, map_values, x + 10, y + 10, cw - 20, 505)
    textbox(slide, x, y + 525, cw, 32, "1인당 추정 GVA 상대분포", 18, NAVY, True, "center")
    textbox(slide, x, y + 565, cw, 82, "진한 색일수록 2023년 추정 GVA/주민등록인구가 높음. 산업시설 집중지역의 현장점검 우선순위 보조지표.", 16, MUTED, False, "center")
    rect(slide, x, y + ch - 75, cw, 62, "E8F2F5", None); textbox(slide, x + 12, y + ch - 75, cw - 24, 62, "지도 도형 29개 개별 선택·편집 가능", 15, NAVY, True, "center")

    x, y, cw, ch = panel(slide, x2, y3, 2 * COL_W + GAP, h3, "07", "전 산업 월 변화와 산업구조")
    textbox(slide, x, y, cw, 30, "2021년 월평균=100 · 2023년 GVA 상위 4개 대분류", 18, NAVY, True)
    line_chart(slide, x + 52, y + 86, cw - 80, 250, trends, periods)
    textbox(slide, x, y + 380, cw, 62, "월 경로는 상위 분기총량을 보존한 추정지수이며 월 실제 GVA가 아니다. 산업 간 변동 방향 비교와 경보 후보 선별에만 사용한다.", 16, MUTED, False, "center")
    yy = subhead(slide, x, y + 456, cw, "경보 산출")
    items = [("산업규모", "시 산업 GVA"), ("공간집중", "읍면동 산업비중"), ("월 변화", "인허가 영업재고"), ("신뢰등급", "산업별 CV 오차")]
    for i, (a, b) in enumerate(items):
        xx = x + i * cw / 4; rect(slide, xx, yy, cw / 4 - 10, 112, PALE, GRID, .4); textbox(slide, xx + 8, yy + 7, cw / 4 - 26, 40, a, 16, NAVY, True, "center"); textbox(slide, xx + 8, yy + 50, cw / 4 - 26, 52, b, 15, INK, False, "center")
    rect(slide, x, y + ch - 80, cw, 68, "FFF2E8", None); textbox(slide, x + 12, y + ch - 80, cw - 24, 68, "경보 = 변동 악화 × 공간집중 × 검증신뢰도  →  현장확인 후보", 18, ORANGE, True, "center")

    y4, h4 = 2720, 900
    x, y, cw, ch = panel(slide, M, y4, COL_W, h4, "08", "예측 양호 산업")
    rows = [(r.industry_name, f"{r.combined_cv_score_pp:.2f}%p") for r in good.itertuples()]
    native_table(slide, x, y, cw, ["KSIC 실제 업종명", "종합오차"], rows, [.72, .28], 58, [15, 16])
    textbox(slide, x, y + 425, cw, 86, "산업·읍면동·차년도 구 매출의 세 오차 평균. 상대적으로 정책 모니터링에 우선 활용 가능.", 16, MUTED, False, "center")
    rect(slide, x, y + ch - 95, cw, 82, "E9F5F3", None); textbox(slide, x + 12, y + ch - 95, cw - 24, 82, "활용: 월 변화 경보 + 현장자료 확인", 18, TEAL, True, "center")

    x, y, cw, ch = panel(slide, x2, y4, COL_W, h4, "09", "예측 취약 산업")
    rows = [(r.industry_name, f"{r.combined_cv_score_pp:.2f}%p") for r in bad.itertuples()]
    native_table(slide, x, y, cw, ["KSIC 실제 업종명", "종합오차"], rows, [.72, .28], 58, [15, 16])
    textbox(slide, x, y + 425, cw, 86, "소수 대형사업장·자본집약·거래액 차이로 사업체·고용 프록시가 매출·부가가치를 충분히 설명하지 못함.", 16, MUTED, False, "center")
    rect(slide, x, y + ch - 95, cw, 82, "FBEDEA", None); textbox(slide, x + 12, y + ch - 95, cw - 24, 82, "제한: 단독 정책판단 금지 · 산업 실적자료 병행", 18, RED, True, "center")

    x3 = M + 2 * (COL_W + GAP); x, y, cw, ch = panel(slide, x3, y4, COL_W, h4, "10", "정책 운영 산출물")
    stages = [("1 갱신", "연·분기 GVA와 월 인허가"), ("2 판정", "산업별 양호·보통·취약"), ("3 탐지", "읍면동 집중·월 악화"), ("4 확인", "기업·상권·산단 현장자료"), ("5 지원", "산업·지역 맞춤사업 연결")]
    for i, (a, b) in enumerate(stages):
        yy = y + i * 105; rect(slide, x, yy, cw, 90, PALE, GRID, .5); textbox(slide, x + 12, yy, 125, 90, a, 17, NAVY, True); textbox(slide, x + 145, yy, cw - 157, 90, b, 16, INK, True)
    rect(slide, x, y + 545, cw, 120, "E8F2F5", None); textbox(slide, x + 12, y + 545, cw - 24, 120, "산출물\n29개 읍면동 산업활력 지도\n산업별 신뢰등급·현장확인 목록", 17, NAVY, True, "center")
    rect(slide, x, y + ch - 95, cw, 82, "FFF2E8", None); textbox(slide, x + 12, y + ch - 95, cw - 24, 82, "정책 연결: 산단·상권·고용·창업 지원 우선순위", 17, ORANGE, True, "center")

    y5, h5 = 3650, 1200
    x, y, cw, ch = panel(slide, M, y5, COL_W, h5, "11", "한계와 후속 보완")
    limits = [("산업 시차", "2015 구조·2023 공간"), ("월 실제값", "부재 · 분기 제약추정"), ("소분류 공간", "중분류 actual까지만"), ("공장 주소", "업종·동 결합 76.5%"), ("구 매출", "매출은 GVA와 상이"), ("행정경계", "2026 현행 기준")]
    for i, (a, b) in enumerate(limits):
        yy = y + i * 91; textbox(slide, x, yy, 160, 76, a, 16, NAVY, True); textbox(slide, x + 170, yy, cw - 170, 76, b, 16, INK); line(slide, x, yy + 79, x + cw, yy + 79, GRID, .35)
    yy = subhead(slide, x, y + 565, cw, "무료 보완자료 우선순위")
    bullets(slide, x, yy, cw, 220, ["산단·기업별 생산·출하 또는 전력사용량", "건축착공·거래·병상·학생·관광객 물량", "과거 행정동 경계와 월별 고용보험"], 16)
    rect(slide, x, y + ch - 110, cw, 96, "FBEDEA", None); textbox(slide, x + 12, y + ch - 110, cw - 24, 96, "읍면동×소분류×월 수치는\n공식통계가 아닌 개발통계", 18, RED, True, "center")

    x, y, cw, ch = panel(slide, x2, y5, 2 * COL_W + GAP, h5, "12", "결론 및 기대효과")
    conclusion_cards = [("분석 성과", ["29개 읍면동·전 산업·36개월 통합", "산업·공간·외삽 actual 교차검증", "상위합계 오차 2.33×10⁻¹⁰", "전면복제: 중분류 0·소분류 4/19"]), ("정책 가치", ["시 총량을 동 단위 정책정보로 전환", "양호 산업은 월 경보에 우선 활용", "취약 산업은 현장자료 수집 우선순위", "무료 자료로 반복 갱신 가능한 구조"]), ("공공 기여", ["지역·산업 격차의 동시 진단", "산단·상권·고용정책 연결", "오차 공개를 통한 과잉해석 방지", "타 지역 동일 검증체계 확장 가능"])]
    card_w = (cw - 36) / 3
    for i, (title, items) in enumerate(conclusion_cards):
        xx = x + i * (card_w + 18); rect(slide, xx, y, card_w, 510, PALE, GRID, .5); rect(slide, xx, y, card_w, 52, SKY, None); textbox(slide, xx + 12, y, card_w - 24, 52, title, 19, NAVY, True); bullets(slide, xx + 12, y + 70, card_w - 24, 410, items, 16)
    rect(slide, x, y + 535, cw, 170, "E9F5F3", GRID, .6)
    textbox(slide, x + 18, y + 535, 150, 170, "최종 제안", 21, TEAL, True, "center")
    textbox(slide, x + 185, y + 535, cw - 203, 170, "포항시 산업활력 정밀지도\n검증 신뢰도에 따라 산업별 활용 강도를 달리하는\n읍면동 경제경보·현장점검 지원체계", 23, INK, True, "center")
    yy = subhead(slide, x, y + 735, cw, "기대효과")
    effects = [("정밀성", "시·구 평균에 가린 동 격차 발견"), ("적시성", "연간 통계 사이 월 변화 후보 탐지"), ("실현성", "기존 무료 자료·반복 실행"), ("책임성", "오차·비추정·한계 공개")]
    for i, (a, b) in enumerate(effects):
        xx = x + i * cw / 4; rect(slide, xx, yy, cw / 4 - 10, 132, WHITE, GRID, .5); textbox(slide, xx + 8, yy + 8, cw / 4 - 26, 42, a, 18, NAVY, True, "center"); textbox(slide, xx + 8, yy + 54, cw / 4 - 26, 68, b, 15, INK, False, "center")
    rect(slide, x, y + ch - 115, cw, 102, "FFF2E8", None); textbox(slide, x + 14, y + ch - 115, cw - 28, 102, "수상 경쟁력: 전 산업 범위 + 읍면동 정책단위 + 실제 홀드아웃 개선 + 편집·재현 가능한 산출물", 19, ORANGE, True, "center")

    line(slide, M, H - 83, W - M, H - 83, NAVY, 1.2)
    textbox(slide, M, H - 73, BODY_W, 42, "자료: 포항시 사업체조사·공장등록·인구, 지방행정 인허가, KOSIS 지역계정·경제총조사  |  분석 기준: 2026년 7월", 15, MUTED, False, "center")
    output = OUT / "poster_pohang_industrial_vitality_a1_editable.pptx"; prs.save(output)
    print(output); print(f"slide_size_mm={prs.slide_width / 36000:.1f}x{prs.slide_height / 36000:.1f} shapes={len(slide.shapes)}")
    return output


if __name__ == "__main__":
    main()
