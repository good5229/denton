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
        return size + 8
    if size <= 18:
        return size + 7
    if size <= 23:
        return size + 4
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
            box_text(draw, (cur, yy, cur + width * ratio, yy + row_h), str(value), sizes[j], INK, bold=(j == 0), pad=8)
            cur += width * ratio
    draw.line((x, y + row_h * (len(rows) + 1), x + width, y + row_h * (len(rows) + 1)), fill=NAVY, width=2)
    return y + row_h * (len(rows) + 1)


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
    ymin, ymax = 70, 145
    for tick in (80, 100, 120, 140):
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
    totals = monthly[monthly.period.str.startswith("2023")].groupby(["industry_code", "industry_name"], as_index=False).estimated_gva.sum().nlargest(4, "estimated_gva")
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

    text(draw, (M, 42), "포항시 산업활력 정밀지도", 78, NAVY, title=True)
    text(draw, (M, 142), "행정 읍면동·전 산업 월간 부가가치 추정과 지역격차 경보", 40, INK, bold=True)
    text(draw, (M, 204), "29개 행정 읍면동 × 산업 대·중·소분류 × 연·분기·월  |  무료 공공데이터 기반 개발통계", 22, MUTED)
    draw.line((M, 248, W - M, 248), fill=NAVY, width=7)
    rect(draw, (M, 270, W - M, 410), WHITE, GRID, 2)
    metrics = [("29개", "행정 읍면동"), ("19·74·228", "산업 대·중·소"), ("27조합", "시공간산업 해상도"), ("10.29%p", "소→중 집계 MAE"), ("17/66", "집계오차 1pp 이하"), ("D등급", "월·동 GVA actual 부재")]
    each = BODY_W / 6
    for i, (value, label) in enumerate(metrics):
        xx = M + i * each
        if i:
            draw.line((xx, 290, xx, 392), fill=GRID, width=2)
        box_text(draw, (xx + 10, 282, xx + each - 10, 340), value, 32, TEAL if i >= 4 else NAVY, bold=True, align="center")
        box_text(draw, (xx + 10, 340, xx + each - 10, 392), label, 17, MUTED, align="center")

    y1, h1 = 435, 650
    x, y, cw, ch = panel(draw, M, y1, COL_W, h1, "01", "문제 정의와 분석 목표")
    yy = subhead(draw, x, y, "정책 문제", cw)
    yy = paragraph(draw, x, yy, "시·구 연간 총량만으로는 산업 충격이 어느 읍면동에 집중되고 언제 시작됐는지 판별하기 어렵다.", 21, cw, INK, False, 8) + 18
    yy = subhead(draw, x, yy, "분석 목표", cw)
    yy = bullet(draw, x, yy, "전 산업을 동일 기준으로 29개 읍면동까지 배분", cw, 18)
    yy = bullet(draw, x, yy + 5, "월·분기·연 및 읍면동·구·시 합계를 동시 보존", cw, 18)
    yy = bullet(draw, x, yy + 5, "예측 양호·취약 산업을 구분해 활용 강도 차등화", cw, 18)
    table(draw, x, y + 350, cw, ["축", "분석 범위"], [("시간", "연·분기·월"), ("공간", "시·구·29개 읍면동"), ("산업", "산업 대·중·소분류")], [.25, .75], 26, [12, 12])
    rect(draw, (x, y + ch - 92, x + cw, y + ch - 8), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 12, y + ch - 92, x + 132, y + ch - 8), "핵심 질문", 18, ORANGE, bold=True)
    box_text(draw, (x + 140, y + ch - 92, x + cw - 12, y + ch - 8), "어느 동·산업을 먼저 확인하고 지원할 것인가?", 20, INK, bold=True)

    x2 = M + COL_W + GAP
    x, y, cw, ch = panel(draw, x2, y1, 2 * COL_W + GAP, h1, "02", "활용 데이터와 시공간 배분 절차")
    table_w = cw * .48
    rows = [("KOSIS 경제총조사", "소분류 매출·사업체·종사자"), ("포항시 사업체조사", "읍면동·구 산업 실제값"), ("포항시 공장등록 1,465건", "제조업 공간분포"), ("LOCALDATA 19종", "월 인허가·폐업 변화"), ("읍면동 인구·경계", "규모·공간 결합"), ("시 산업별 부가가치", "연·분기 상위통제")]
    table(draw, x, y, table_w, ["무료 공식자료", "모형 역할"], rows, [.50, .50], 46, [16, 16])
    flow_x = x + table_w + 28
    flow_w = cw - table_w - 28
    text(draw, (flow_x, y), "배분·검증 프로세스", 21, NAVY, bold=True)
    steps = [("1", "상위통제", "시×산업×연·분기"), ("2", "산업배분", "대→중→소"), ("3", "공간배분", "시→구→읍면동"), ("4", "시간배분", "분기→월"), ("5", "독립검증", "매출·공간·차년도"), ("6", "회계검증", "하위합→상위 실제값")]
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
    box_paragraph(draw, (flow_x + 20, matrix_y + 44, flow_x + flow_w - 20, matrix_y + 102), "매출 실제값은 학습에서 제외 · 하위합 일치는 성능점수가 아닌 회계검사", 17, INK, True, 5, align="center")

    y2, h2 = 1110, 670
    titles = [("03", "독립 검증 설계"), ("04", "GVA 신뢰도 판정"), ("05", "활용 판정 및 검증")]
    for col, (number, title_) in enumerate(titles):
        xx = M + col * (COL_W + GAP)
        x, y, cw, ch = panel(draw, xx, y2, COL_W, h2, number, title_)
        if col == 0:
            cards = [("산업축", "2015 매출 비공개\n사업체·종사자→매출"), ("공간축", "2023 읍면동×중분류\n인구·공장·인허가 검증"), ("외삽축", "2024 남·북구 매출\n목표 산업 제외 검증"), ("회계축", "소→중→대·월→분기\n읍면동→시 재집계")]
            for i, (a, b) in enumerate(cards):
                yy = y + i * 113
                rect(draw, (x, yy, x + cw, yy + 96), PALE, GRID, 1)
                box_text(draw, (x + 12, yy, x + 127, yy + 96), a, 18, NAVY, bold=True)
                box_paragraph(draw, (x + 138, yy, x + cw - 12, yy + 96), b, 17, INK, False, 5)
            table(draw, x, y + 452, cw, ["순서", "엄격 검증 원칙"], [("1", "실제값 분리"), ("2", "목표 산업 제외"), ("3", "상위합계 사후검사")], [.20, .80], 34, [14, 14])
        elif col == 1:
            text(draw, (x, y), "예측 대상과 검증축 분리", 19, NAVY, bold=True)
            rows = [
                ("A", "연×시 GVA", "공식 지역 부가가치 직접 대조"),
                ("B/C", "소→중 집계", "소분류 배분값을 중분류 actual과 비교"),
                ("C/D", "읍면동 GVA", "읍면동 산업분포 검증"),
                ("D", "월 GVA", "상위합계 보존, 실제값 부재"),
            ]
            table(draw, x, y + 42, cw, ["등급", "해상도", "검증근거"], rows, [.16, .32, .52], 56, [15, 14, 13])
            rect(draw, (x, y + 318, x + cw, y + 450), "#FFF2E8", "#FFF2E8", 1)
            box_text(draw, (x + 12, y + 318, x + 135, y + 450), "집계검증", 18, ORANGE, bold=True)
            box_paragraph(draw, (x + 145, y + 318, x + cw - 12, y + 450), "소분류 배분값을 중분류로 합산해 actual과 비교: MAE 10.29%p, 66개 중 17개가 1%p 이하.", 18, INK, True, 5)
            rect(draw, (x, y + 470, x + cw, y + 590), "#E9F5F3", "#E9F5F3", 1)
            box_text(draw, (x + 12, y + 470, x + 135, y + 590), "사용", 19, TEAL, bold=True)
            box_paragraph(draw, (x + 145, y + 470, x + cw - 12, y + 590), "하위합=상위합은 회계검사, 소→중 actual 비교는 성능검증. 두 검증을 분리해 과대해석을 막음.", 18, INK, True, 5)
        else:
            checks = [("상위합계", "최대 2.33e-10", GREEN), ("소→중 집계", "17/66개 1%p 이하", GOLD), ("공장 결합", "업종·읍면동 76.5%", GOLD), ("월 실제값", "부재 · 개발통계", RED)]
            for i, (a, b, color) in enumerate(checks):
                yy = y + i * 102
                rect(draw, (x, yy, x + cw, yy + 86), PALE, GRID, 1)
                draw.ellipse((x + 12, yy + 30, x + 36, yy + 54), fill=color)
                box_text(draw, (x + 50, yy, x + 205, yy + 86), a, 18, NAVY, bold=True)
                box_text(draw, (x + 212, yy, x + cw - 12, yy + 86), b, 17, color, bold=True)
            rect(draw, (x, y + 424, x + cw, y + 528), "#FFF2E8", "#FFF2E8", 1)
            box_paragraph(draw, (x + 12, y + 424, x + cw - 12, y + 528), "판정: 중분류 공간분포는 검증 가능\n읍면동×소분류×월은 상위합계 보존 추정으로 제한", 18, INK, True, 5, align="center")

    y3, h3 = 1810, 880
    x, y, cw, ch = panel(draw, M, y3, COL_W, h3, "06", "2023년 읍면동 산업활력 분포")
    map_plot(draw, geo, map_values, (x + 10, y + 10, x + cw - 20, y + 515))
    box_text(draw, (x, y + 525, x + cw, y + 557), "1인당 추정 부가가치 상대분포", 19, NAVY, bold=True, align="center")
    box_paragraph(draw, (x, y + 565, x + cw, y + 647), "진한 색일수록 2023년 추정 부가가치/주민등록인구가 높음. 산업시설 집중지역의 현장점검 우선순위 보조지표.", 17, MUTED, False, 5, align="center")
    rect(draw, (x, y + ch - 75, x + cw, y + ch - 13), "#E8F2F5", "#E8F2F5", 1)
    box_text(draw, (x + 12, y + ch - 75, x + cw - 12, y + ch - 13), "지도 도형 29개 개별 선택·편집 가능", 16, NAVY, bold=True, align="center")

    x, y, cw, ch = panel(draw, x2, y3, 2 * COL_W + GAP, h3, "07", "전 산업 월 변화와 산업구조")
    text(draw, (x, y), "2021년 월평균=100 · 2023년 부가가치 상위 4개 대분류", 19, NAVY, bold=True)
    line_chart(draw, x + 52, y + 86, cw - 80, 250, trends, periods)
    box_paragraph(draw, (x, y + 380, x + cw, y + 442), "월 경로는 상위 분기총량을 보존한 추정지수이며 월 실제 부가가치가 아니다. 산업 간 변동 방향 비교와 경보 후보 선별에만 사용한다.", 17, MUTED, False, 5, align="center")
    yy = subhead(draw, x, y + 456, "경보 산출", cw)
    for i, (a, b) in enumerate([("산업규모", "시 산업 부가가치"), ("공간집중", "읍면동 산업비중"), ("월 변화", "인허가 영업재고"), ("신뢰등급", "산업별 검증오차")]):
        xx = x + i * cw / 4
        rect(draw, (xx, yy, xx + cw / 4 - 10, yy + 112), PALE, GRID, 1)
        box_text(draw, (xx + 8, yy + 7, xx + cw / 4 - 18, yy + 47), a, 17, NAVY, bold=True, align="center")
        box_paragraph(draw, (xx + 8, yy + 50, xx + cw / 4 - 18, yy + 102), b, 16, INK, False, 4, align="center")
    rect(draw, (x, y + ch - 80, x + cw, y + ch - 12), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 12, y + ch - 80, x + cw - 12, y + ch - 12), "경보 = 변동 악화 × 공간집중 × 검증신뢰도  →  현장확인 후보", 19, ORANGE, bold=True, align="center")

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
    sections = [(M, "08", "집계검증 양호 중분류", hv.nsmallest(6, "abs_error_pp"), TEAL, "활용: 월 변화 경보 + 현장자료 확인"), (x2, "09", "집계검증 취약 중분류", hv.nlargest(6, "abs_error_pp"), RED, "보완: 추가 활동지표 확보 전 활용 보류")]
    for xx0, num, title_, rows_df, color, footer in sections:
        x, y, cw, ch = panel(draw, xx0, y4, COL_W, h4, num, title_)
        rows = [(r.middle_label, f"{r.actual_eok:,.0f}", f"{r.pred_eok:,.0f}", f"{r.error_eok:,.0f}\n({r.error_rate_pct:.1f}%)") for r in rows_df.itertuples()]
        table(draw, x, y, cw, ["중분류", "실제", "집계", "오차"], rows, [.48, .17, .17, .18], 63, [15, 15, 15, 13])
        explanation = "단위: 억원 환산. 실제=상위 GVA×중분류 actual 비중, 집계=상위 GVA×소분류 합산비중, 오차=억원(상대오차율)." if color == TEAL else "취약 중분류는 하위 배분이 상위 actual 구조를 충분히 복원하지 못한 영역. 원자료 보강 전 제한."
        box_paragraph(draw, (x, y + 445, x + cw, y + 560), explanation, 18, MUTED, False, 5, align="center")
        checks = [("검증축", "소→중 집계 actual 비교"), ("활용", "양호=경보 · 취약=보류"), ("단위", "% · %p 혼용 방지")]
        table(draw, x, y + 575, cw, ["항목", "판정"], checks, [.30, .70], 44, [14, 14])
        footer_fill = "#E9F5F3" if color == TEAL else "#FFF2E8"
        footer_color = color if color == TEAL else ORANGE
        rect(draw, (x, y + ch - 95, x + cw, y + ch - 13), footer_fill, footer_fill, 1)
        box_text(draw, (x + 12, y + ch - 95, x + cw - 12, y + ch - 13), footer, 18, footer_color, bold=True, align="center")
    x3 = M + 2 * (COL_W + GAP)
    x, y, cw, ch = panel(draw, x3, y4, COL_W, h4, "10", "정책 운영 산출물")
    for i, (a, b) in enumerate([("1 갱신", "연·분기 부가가치와 월 인허가"), ("2 판정", "산업별 양호·보통·취약"), ("3 탐지", "읍면동 집중·월 악화"), ("4 확인", "기업·상권·산단 현장자료"), ("5 지원", "산업·지역 맞춤사업 연결")]):
        yy = y + i * 105
        rect(draw, (x, yy, x + cw, yy + 90), PALE, GRID, 1)
        box_text(draw, (x + 12, yy, x + 137, yy + 90), a, 18, NAVY, bold=True)
        box_text(draw, (x + 145, yy, x + cw - 12, yy + 90), b, 17, INK, bold=True)
    output_rows = [("지도", "29개 읍면동×산업"), ("목록", "신뢰등급·현장확인"), ("대시보드", "월 변화·공간집중"), ("보고서", "오차·비추정 사유")]
    table(draw, x, y + 520, cw, ["산출물", "내용"], output_rows, [.28, .72], 34, [13, 13])
    box_text(draw, (x, y + 692, x + cw, y + 708), "높은 신뢰=경보 · 중간=보조지표 · 낮은 신뢰=자료수집", 12, MUTED, align="center")
    rect(draw, (x, y + ch - 95, x + cw, y + ch - 13), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 12, y + ch - 95, x + cw - 12, y + ch - 13), "정책 연결: 산단·상권·고용·창업 지원 우선순위", 18, ORANGE, bold=True, align="center")

    y5, h5 = 3650, 1200
    x, y, cw, ch = panel(draw, M, y5, COL_W, h5, "11", "자료 확보성 검토")
    for i, (a, b) in enumerate([("공식 실제값", "2023 읍면동×중분류\n2024 구×중분류 매출"), ("월 변동", "LOCALDATA 19종\n2021–2026 인허가"), ("제조업 보강", "공장 1,465건\n동·업종 결합 76.5%"), ("경계·인구", "29개 행정 읍면동\n현행 경계 기준")]):
        yy = y + i * 128
        rect(draw, (x, yy, x + cw, yy + 108), PALE, GRID, 1)
        box_text(draw, (x + 14, yy, x + 162, yy + 108), a, 18, NAVY, bold=True)
        box_paragraph(draw, (x + 174, yy, x + cw - 14, yy + 108), b, 17, INK, True, 5)
    yy = subhead(draw, x, y + 535, "판정", cw)
    for i, (a, b, color) in enumerate([("가능", "연·분기·월 × 시·구·읍면동 × 산업 대·중·소", TEAL), ("검증", "산업 매출·읍면동 분포·차년도 구 매출", ORANGE), ("주의", "읍면동×소분류×월 실제값 부재", RED)]):
        yy2 = yy + i * 92
        rect(draw, (x, yy2, x + cw, yy2 + 74), WHITE, GRID, 1)
        box_text(draw, (x + 12, yy2, x + 100, yy2 + 74), a, 18, color, bold=True, align="center")
        box_text(draw, (x + 112, yy2, x + cw - 12, yy2 + 74), b, 16, INK, bold=True)
    rect(draw, (x, y + ch - 98, x + cw, y + ch - 14), "#FBEDEA", "#FBEDEA", 1)
    box_paragraph(draw, (x + 12, y + ch - 98, x + cw - 12, y + ch - 14), "공식통계 승격이 아닌\n정책 후보 선별용 개발통계", 18, RED, True, 5, align="center")

    x, y, cw, ch = panel(draw, x2, y5, 2 * COL_W + GAP, h5, "12", "결론 및 기대효과")
    card_w = (cw - 36) / 3
    for i, (title_, items) in enumerate([("분석 성과", ["29개 읍면동·전 산업 GVA 추정", "소분류 배분값의 중분류 actual 집계검증", "소→중 집계 MAE 10.29%p", "17/66개 중분류 1%p 이하", "농업·임업 집계오차 40.45%p 취약", "월·동 GVA actual 부재 명시"]), ("정책 가치", ["시 총량을 동 단위 정책정보로 전환", "양호 산업은 월 경보에 우선 활용", "취약 산업은 검증된 활동지표만 채택", "악화 조합은 자료보완 대상으로 분리", "무료 자료 기반 반복 갱신", "현장확인 후보 목록화"]), ("공공 기여", ["지역·산업 격차의 동시 진단", "산단·상권·고용정책 연결", "오차 공개를 통한 과잉해석 방지", "타 지역 동일 검증체계 확장 가능", "공식통계 공백 보완", "과대해석 방지 체계"])]):
        xx = x + i * (card_w + 18)
        rect(draw, (xx, y, xx + card_w, y + 510), PALE, GRID, 1)
        rect(draw, (xx, y, xx + card_w, y + 52), SKY, SKY, 1)
        box_text(draw, (xx + 12, y, xx + card_w - 12, y + 52), title_, 20, NAVY, bold=True)
        yy = y + 70
        for item in items:
            yy = bullet(draw, xx + 12, yy, item, card_w - 24, 17) + 8
    rect(draw, (x, y + 535, x + cw, y + 705), "#E9F5F3", GRID, 1)
    box_text(draw, (x + 18, y + 535, x + 168, y + 705), "최종 제안", 22, TEAL, bold=True, align="center")
    box_paragraph(draw, (x + 185, y + 535, x + cw - 18, y + 705), "포항시 산업활력 정밀지도\n검증 신뢰도에 따라 산업별 활용 강도를 달리하는\n읍면동 경제경보·현장점검 지원체계", 24, INK, True, 6, align="center")
    yy = subhead(draw, x, y + 735, "기대효과", cw)
    for i, (a, b) in enumerate([("정밀성", "시·구 평균에 가린 동 격차 발견"), ("적시성", "연간 통계 사이 월 변화 후보 탐지"), ("실현성", "기존 무료 자료·반복 실행"), ("책임성", "오차·비추정·한계 공개")]):
        xx = x + i * cw / 4
        rect(draw, (xx, yy, xx + cw / 4 - 10, yy + 132), WHITE, GRID, 1)
        box_text(draw, (xx + 8, yy + 8, xx + cw / 4 - 18, yy + 50), a, 19, NAVY, bold=True, align="center")
        box_paragraph(draw, (xx + 8, yy + 54, xx + cw / 4 - 18, yy + 122), b, 16, INK, False, 5, align="center")
    rect(draw, (x, y + ch - 115, x + cw, y + ch - 13), "#FFF2E8", "#FFF2E8", 1)
    box_text(draw, (x + 14, y + ch - 115, x + cw - 14, y + ch - 13), "수상 경쟁력: 전 산업 범위 + 읍면동 정책단위 + 실제값 숨김검증 개선 + 편집·재현 가능한 산출물", 20, ORANGE, bold=True, align="center")

    draw.line((M, H - 83, W - M, H - 83), fill=NAVY, width=3)
    box_text(draw, (M, H - 73, W - M, H - 31), "자료: 포항시 사업체조사·공장등록·인구, 지방행정 인허가, KOSIS 지역계정·경제총조사  |  분석 기준: 2026년 7월", 16, MUTED, align="center")

    output = OUT / "poster_pohang_industrial_vitality_a1.png"
    preview = OUT / "poster_pohang_industrial_vitality_a1_preview.png"
    img.save(output, quality=95)
    img.resize((1240, round(1240 * H / W)), Image.Resampling.LANCZOS).save(preview, quality=95)
    print(output)
    print(preview)
    print(f"png_size={W}x{H} preview={Image.open(preview).size[0]}x{Image.open(preview).size[1]} status42={status42['emd']} status43_spatial={status43['improved_spatial_cv_mae_pp']:.3f} status45_groups={status45['groups']}")


if __name__ == "__main__":
    main()
