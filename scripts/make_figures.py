from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures"
DATA = ROOT / "data" / "processed"
W, H = 1920, 1080

BG = "#f7f8fa"
INK = "#17212b"
MUTED = "#5c6875"
BORDER = "#d3d9e2"
WHITE = "#ffffff"
BLUE = "#2f6fbb"
TEAL = "#21867a"
GREEN = "#50884f"
GOLD = "#b07822"
RED = "#b6544a"
PURPLE = "#7a5fa8"
SLATE = "#475569"


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


class Svg:
    def __init__(self) -> None:
        self.parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            "<defs>",
            "<style>",
            "@font-face{font-family:NB;src:local('NanumBarunGothic');}",
            "text{font-family:NB, Apple SD Gothic Neo, Arial, sans-serif; dominant-baseline:hanging;}",
            ".title{font-size:54px;font-weight:700;fill:#17212b;}",
            ".h1{font-size:36px;font-weight:700;}",
            ".h2{font-size:30px;font-weight:700;fill:#17212b;}",
            ".body{font-size:27px;fill:#17212b;}",
            ".small{font-size:23px;fill:#5c6875;}",
            ".badge{font-size:25px;font-weight:700;fill:#fff;}",
            "</style>",
            "</defs>",
            f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        ]

    def rect(self, x: int, y: int, w: int, h: int, fill: str, stroke: str = BORDER, sw: int = 2, r: int = 8) -> None:
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def line(self, x1: int, y1: int, x2: int, y2: int, stroke: str = SLATE, sw: int = 5) -> None:
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>')

    def arrow(self, x1: int, y1: int, x2: int, y2: int, stroke: str = SLATE) -> None:
        self.line(x1, y1, x2, y2, stroke)
        angle = math.atan2(y2 - y1, x2 - x1)
        size = 18
        pts = [
            (x2, y2),
            (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
            (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
        ]
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.parts.append(f'<polygon points="{points}" fill="{stroke}"/>')

    def text(self, x: int, y: int, text: object, cls: str = "body", fill: str | None = None, anchor: str = "start") -> None:
        style = f' style="fill:{fill}"' if fill else ""
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{style}>{esc(text)}</text>')

    def centered_text(self, x: int, y: int, w: int, h: int, text: object, cls: str = "body", fill: str | None = None) -> None:
        style = f' style="fill:{fill}"' if fill else ""
        self.parts.append(
            f'<text x="{x + w / 2:.1f}" y="{y + h / 2 - 15:.1f}" class="{cls}" text-anchor="middle"{style}>{esc(text)}</text>'
        )

    def multiline(self, x: int, y: int, lines: list[str], cls: str = "body", fill: str | None = None, gap: int = 38, anchor: str = "start") -> None:
        style = f' style="fill:{fill}"' if fill else ""
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{style}>')
        for i, line in enumerate(lines):
            dy = 0 if i == 0 else gap
            self.parts.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
        self.parts.append("</text>")

    def badge(self, x: int, y: int, w: int, text: str, fill: str) -> None:
        self.rect(x, y, w, 56, fill, fill, 0, 8)
        self.text(x + w // 2, y + 14, text, "badge", anchor="middle")

    def save(self, path: Path) -> None:
        self.parts.append("</svg>")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.parts), encoding="utf-8")


def read_errors() -> list[dict[str, str]]:
    with (DATA / "all_industries_2023_extrapolation_errors.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_summary() -> dict[str, str]:
    with (DATA / "all_industries_error_summary.csv").open(encoding="utf-8") as f:
        return next(csv.DictReader(f))


def fig01_pipeline() -> None:
    s = Svg()
    s.text(84, 58, "지역경기상황지수 복원 파이프라인", "title")
    cols = [
        (90, "원천 데이터", BLUE, [("연간 GVA", "2,340행"), ("생산지수", "5,752행"), ("GDP·디플레이터", "1,500행"), ("건설수주", "2,640행")]),
        (555, "업종별 참고지표", TEAL, [("생산지수", "광업·제조업"), ("서비스 지수", "10개 업종"), ("건설 수주", "12/24분기"), ("전국 GDP", "무지표 업종")]),
        (1020, "비례형 덴튼", GOLD, [("배분", "2019-2022"), ("외삽", "2023"), ("제약", "연간 GVA"), ("BI 비율", "직전분기")]),
        (1485, "검증·보정", GREEN, [("외삽 오차", "288개"), ("MAPE", "7.33%"), ("GDP 보정", "1:1 업종"), ("산출물", "5,760행")]),
    ]
    for i, (x, title, color, items) in enumerate(cols):
        s.rect(x, 170, 340, 620, WHITE, "#cad2de")
        s.rect(x, 170, 340, 84, color, color)
        s.text(x + 28, 194, title, "h1", WHITE)
        y = 294
        for label, value in items:
            s.rect(x + 28, y, 284, 96, "#f9fbfd", "#d9e0ea")
            s.text(x + 52, y + 16, label, "h2")
            s.text(x + 52, y + 56, value, "body", color)
            y += 122
        if i < len(cols) - 1:
            s.arrow(x + 370, 480, cols[i + 1][0] - 30, 480, "#6b7785")
    s.text(95, 930, "원문 방식: 연간 GRDP 제약 + 분기 참고지표 흐름 + 전국 GDP 정합성", "h2")
    s.text(95, 980, "주: 한국은행 GDP 묶음 업종은 임의 분할 없이 보정 제외 상태로 표시", "small")
    s.save(OUT / "fig01_pipeline.svg")


def fig02_methods() -> None:
    s = Svg()
    s.text(84, 58, "전 업종 추정 전략", "title")
    lanes = [
        ("지역 생산지수", BLUE, ["광업", "제조업", "전기가스"], "비례형 덴튼"),
        ("서비스업 지수", TEAL, ["도소매·운수", "정보통신·금융", "교육·보건", "기타서비스"], "비례형 덴튼"),
        ("건설수주", GOLD, ["건축 12분기", "토목 24분기"], "분산 후 덴튼"),
        ("전국 GDP 비중", PURPLE, ["농림어업", "공공행정", "무지표 업종"], "분기비중 덴튼"),
    ]
    x = 95
    for title, color, chips, method in lanes:
        s.rect(x, 170, 405, 620, WHITE, "#ccd4df")
        s.text(x + 28, 198, title, "h1", color)
        s.badge(x + 28, 266, 230, method, color)
        y = 360
        for chip in chips:
            s.rect(x + 28, y, 349, 70, "#f8fafc", "#d7dee8")
            s.text(x + 52, y + 18, chip, "body")
            y += 88
        x += 453
    s.rect(170, 850, 1580, 110, WHITE, "#cad2de")
    s.text(215, 878, "공통 산식", "h1")
    s.text(460, 885, "2019-2022 배분 → 2023 외삽 → 실제 2023 GVA와 오차 비교", "h2", SLATE)
    s.text(170, 1010, "주: 생산지수 없는 산업은 원문 취지에 따라 전국 GDP 분기 흐름을 참고지표로 사용", "small")
    s.save(OUT / "fig02_methods.svg")


def fig03_errors() -> None:
    rows = read_errors()
    summary = read_summary()
    by_method: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(float(row["absolute_percent_error"]))
    labels = {
        "regional production index": "생산지수",
        "regional service production index": "서비스지수",
        "construction orders distributed 12/24 quarters": "건설수주",
        "national quarterly GDP share": "GDP비중",
    }
    bars = sorted(
        [(labels.get(method, method), sum(vals) / len(vals), len(vals)) for method, vals in by_method.items()],
        key=lambda item: item[1],
        reverse=True,
    )
    max_v = max(v for _, v, _ in bars) * 1.15
    colors = [PURPLE, GOLD, BLUE, TEAL]
    s = Svg()
    s.text(84, 58, "2023년 외삽 오차 요약", "title")
    s.badge(1415, 62, 190, f"MAPE {float(summary['mape']):.2f}%", RED)
    s.badge(1640, 62, 115, f"N {summary['n']}", SLATE)
    s.rect(170, 210, 1110, 650, WHITE, "#cad2de")
    s.text(210, 245, "방법별 평균 절대오차율", "h1")
    y = 335
    for i, (label, value, n) in enumerate(bars):
        s.text(220, y + 14, label, "body")
        bw = int((value / max_v) * 610)
        s.rect(500, y, bw, 58, colors[i % len(colors)], colors[i % len(colors)])
        s.text(500 + bw + 24, y + 13, f"{value:.1f}% · {n}개", "body", SLATE)
        y += 105
    s.rect(1360, 210, 400, 650, WHITE, "#cad2de")
    s.text(1400, 245, "상위 오차", "h1")
    top = sorted(rows, key=lambda r: float(r["absolute_percent_error"]), reverse=True)[:5]
    y = 330
    for row in top:
        value = float(row["percent_error"])
        s.text(1400, y, f"{row['area_code']} · {row['sector_code']}", "body")
        s.text(1640, y, f"{value:+.1f}%", "body", RED if value >= 0 else BLUE)
        y += 74
    s.multiline(1400, 760, ["큰 오차는 소규모·변동성", "높은 업종에 집중"], "small", gap=34)
    s.text(170, 1005, "주: 2019-2022년 배분 후 2023년을 직전 BI 비율로 외삽하여 실제 2023년 연간 GVA와 비교", "small")
    s.save(OUT / "fig03_errors.svg")


def draw_cells(s: Svg, x: int, y: int, w: int, h: int, labels: list[str], fill: str, stroke: str = "#173a63") -> None:
    cell_w = w // len(labels)
    for idx, label in enumerate(labels):
        cx = x + idx * cell_w
        cw = cell_w if idx < len(labels) - 1 else w - cell_w * idx
        s.rect(cx, y, cw, h, fill, stroke, 3, 0)
        s.centered_text(cx, y, cw, h, label, "h2", WHITE)


def draw_weight_cells(
    s: Svg,
    x: int,
    y: int,
    w: int,
    h: int,
    labels: list[str],
    weights: list[float],
    fill: str,
    stroke: str,
) -> None:
    total = sum(weights)
    used = 0
    for idx, (label, weight) in enumerate(zip(labels, weights)):
        cw = int(round(w * weight / total)) if idx < len(labels) - 1 else w - used
        cx = x + used
        s.rect(cx, y, cw, h, fill, stroke, 3, 0)
        s.centered_text(cx, y, cw, h, label, "h2", WHITE)
        used += cw


def fig04_proportional_denton_method() -> None:
    s = Svg()
    s.text(84, 58, "연간 총부가가치의 분기 배분 방식", "title")
    s.badge(1470, 65, 265, "현재 로직 기준", SLATE)

    row_x = 350
    row_w = 1370
    label_x = 95
    y_annual = 245
    y_indicator = 430
    y_ratio = 615
    y_result = 800
    h = 84
    q_labels = ["2022 1Q", "2022 2Q", "2022 3Q", "2022 4Q"]

    s.text(label_x, y_annual + 26, "연간 총부가가치", "h2", SLATE)
    s.rect(row_x, y_annual, row_w, h, BLUE, "#173a63", 3, 0)
    s.centered_text(row_x, y_annual, row_w, h, "A_2022: 연간 지역·업종 GVA", "h2", WHITE)
    for idx in range(1, 4):
        x = row_x + idx * row_w // 4
        s.line(x, y_annual, x, y_annual + h, "#173a63", 3)
    s.text(row_x + 20, y_annual + 108, "네 분기의 합이 반드시 연간값과 일치", "small", SLATE)

    s.text(label_x, y_indicator + 10, "분기 참고지표", "h2", SLATE)
    s.text(label_x, y_indicator + 48, "생산지수 등", "small", SLATE)
    draw_cells(s, row_x, y_indicator, row_w, h, q_labels, "#4f84bf")
    s.text(row_x + 20, y_indicator + 108, "I_1, I_2, I_3, I_4: 분기별 경기 흐름", "small", SLATE)

    s.text(label_x, y_ratio + 12, "비례형 덴튼", "h2", SLATE)
    s.text(label_x, y_ratio + 50, "비율 변동 최소화", "small", SLATE)
    s.rect(row_x, y_ratio, row_w, h, WHITE, "#b8c2d0", 3, 0)
    s.centered_text(row_x, y_ratio, row_w, h, "I_q / ΣI_q 비중을 따르되 X_t / I_t 변화를 평활화", "h2", INK)
    s.arrow(row_x + row_w // 2, y_indicator + h + 38, row_x + row_w // 2, y_ratio - 14, "#6b7785")
    s.arrow(row_x + row_w // 2, y_annual + h + 38, row_x + row_w // 2, y_ratio - 14, "#6b7785")

    s.text(label_x, y_result + 4, "추정 분기 GVA", "h2", SLATE)
    s.text(label_x, y_result + 42, "배분 결과", "small", SLATE)
    draw_cells(s, row_x, y_result, row_w, h, ["X_1", "X_2", "X_3", "X_4"], TEAL, "#145b55")
    s.arrow(row_x + row_w // 2, y_ratio + h + 38, row_x + row_w // 2, y_result - 14, "#6b7785")

    s.rect(285, 930, 1470, 86, "#ffffff", "#cad2de", 2, 8)
    s.text(330, 956, "제약", "h1", BLUE)
    s.text(470, 963, "X_1 + X_2 + X_3 + X_4 = A_2022", "h2", INK)
    s.text(945, 963, "2023 외삽: X_2023,q = I_2023,q × (X_2022,4Q / I_2022,4Q)", "h2", SLATE)
    s.save(OUT / "fig04_proportional_denton_method.svg")


def fig05_proportional_denton_detail() -> None:
    s = Svg()
    s.text(84, 50, "비례형 덴튼 배분 상세 로직", "title")
    s.badge(1508, 58, 230, "분기 GVA 추정", SLATE)

    top_y = 155
    left_x = 85
    mid_x = 675
    right_x = 1290
    card_h = 300

    s.rect(left_x, top_y, 515, card_h, WHITE, "#cad2de")
    s.text(left_x + 34, top_y + 30, "입력 1: 연간 기준값", "h1", BLUE)
    s.text(left_x + 34, top_y + 92, "지역 r · 업종 s", "body", SLATE)
    s.rect(left_x + 34, top_y + 150, 447, 70, BLUE, "#173a63", 3, 0)
    s.centered_text(left_x + 34, top_y + 150, 447, 70, "Aᵧ = 연간 총부가가치", "h2", WHITE)
    s.text(left_x + 34, top_y + 238, "제약: 해당 연도 4개 분기 합", "small", SLATE)

    s.rect(mid_x, top_y, 515, card_h, WHITE, "#cad2de")
    s.text(mid_x + 34, top_y + 30, "입력 2: 분기 참고지표", "h1", TEAL)
    s.text(mid_x + 34, top_y + 92, "생산지수·서비스지수·건설수주·GDP", "body", SLATE)
    draw_weight_cells(s, mid_x + 34, top_y + 150, 447, 70, ["I₁", "I₂", "I₃", "I₄"], [22, 18, 29, 31], "#4f84bf", "#173a63")
    s.text(mid_x + 34, top_y + 238, "분기별 경기 흐름: 22 · 18 · 29 · 31%", "small", SLATE)

    s.rect(right_x, top_y, 545, card_h, WHITE, "#cad2de")
    s.text(right_x + 34, top_y + 30, "초기 비례 배분", "h1", GOLD)
    s.text(right_x + 34, top_y + 92, "먼저 지표 비중으로 연간값을 나눔", "body", SLATE)
    s.rect(right_x + 34, top_y + 150, 477, 70, "#fff8ed", "#d7b77d", 3, 0)
    s.centered_text(right_x + 34, top_y + 150, 477, 70, "Aᵧ × Iq / ΣIq", "h2", INK)
    s.text(right_x + 34, top_y + 238, "단순 비례값은 덴튼의 출발점", "small", SLATE)

    s.arrow(604, 305, 660, 305, "#6b7785")
    s.arrow(1194, 305, 1275, 305, "#6b7785")

    opt_y = 505
    s.rect(135, opt_y, 1650, 215, WHITE, "#cad2de")
    s.text(180, opt_y + 28, "비례형 덴튼 조정", "h1", PURPLE)
    s.text(180, opt_y + 88, "목적", "h2", PURPLE)
    s.text(310, opt_y + 92, "Σ [(Xₜ / Iₜ) - (Xₜ₋₁ / Iₜ₋₁)]² 최소화", "h2", INK)
    s.text(180, opt_y + 148, "제약", "h2", BLUE)
    s.text(310, opt_y + 152, "각 연도마다 Σ분기 Xᵧq = Aᵧ", "h2", INK)
    s.text(995, opt_y + 152, "즉, 연간 총량은 고정하고 분기 흐름만 조정", "h2", SLATE)

    s.arrow(960, 455, 960, 500, "#6b7785")
    s.arrow(960, 720, 960, 765, "#6b7785")

    out_y = 770
    s.rect(135, out_y, 1015, 210, WHITE, "#cad2de")
    s.text(180, out_y + 28, "배분 결과", "h1", TEAL)
    draw_weight_cells(s, 180, out_y + 98, 895, 70, ["X₁", "X₂", "X₃", "X₄"], [24, 19, 27, 30], TEAL, "#145b55")
    s.text(180, out_y + 178, "분기별 추정 GVA: 합계는 Aᵧ, 움직임은 Iq 흐름을 따름", "small", SLATE)

    s.rect(1210, out_y, 575, 210, WHITE, "#cad2de")
    s.text(1250, out_y + 28, "2023 외삽 검증", "h1", RED)
    s.text(1250, out_y + 88, "직전 비율 유지", "h2", SLATE)
    s.text(1250, out_y + 132, "2023년 Xq = Iq × (B / I직전)", "h2", INK)
    s.text(1250, out_y + 178, "B = 2022년 4분기 덴튼 추정값", "small", SLATE)

    s.text(150, 1015, "해석: 지표 비중을 그대로 베끼는 방식이 아니라, 연간 기준값을 지키면서 추정값/지표 비율이 부드럽게 이어지도록 배분", "small")
    s.save(OUT / "fig05_proportional_denton_detail.svg")


def fig06_portfolio_implementation() -> None:
    s = Svg()
    s.text(84, 50, "통계 지표 기반 지역 GVA 분기화 엔진", "title")
    s.badge(1460, 58, 285, "Portfolio Tech", SLATE)

    s.text(90, 130, "KOSIS 원천통계와 한국은행 방법론을 연결해 연간 지역 총부가가치를 분기 시계열로 복원", "h2", SLATE)

    # Top pipeline.
    steps = [
        ("1", "수집", "KOSIS OpenAPI", "GVA·생산지수·GDP", BLUE),
        ("2", "매핑", "지역 × 업종 × 분기", "지표 우선순위 적용", TEAL),
        ("3", "추정", "비례형 덴튼", "연간합 제약 + 평활화", PURPLE),
        ("4", "검증", "2023 외삽 오차", "실제 GVA와 비교", RED),
    ]
    x = 88
    for idx, (num, title, line1, line2, color) in enumerate(steps):
        s.rect(x, 205, 380, 180, WHITE, "#cad2de")
        s.rect(x + 26, 232, 56, 56, color, color, 0, 28)
        s.text(x + 54, 247, num, "badge", anchor="middle")
        s.text(x + 108, 227, title, "h1", color)
        s.text(x + 108, 282, line1, "body")
        s.text(x + 108, 326, line2, "small", SLATE)
        if idx < len(steps) - 1:
            s.arrow(x + 390, 295, x + 438, 295, "#6b7785")
        x += 455

    # Main implementation panel.
    s.rect(110, 450, 1080, 410, WHITE, "#cad2de")
    s.text(155, 485, "핵심 구현", "h1", INK)
    s.text(155, 545, "입력 벡터", "h2", BLUE)
    s.text(360, 545, "Aᵧ: 연간 GVA", "h2")
    draw_weight_cells(s, 610, 526, 410, 62, ["I₁", "I₂", "I₃", "I₄"], [22, 18, 29, 31], "#4f84bf", "#173a63")
    s.text(1040, 545, "분기 지표", "small", SLATE)

    s.line(170, 630, 1135, 630, "#d5dbe5", 3)
    s.text(155, 675, "최적화", "h2", PURPLE)
    s.text(360, 672, "min Σ [(Xₜ/Iₜ) - (Xₜ₋₁/Iₜ₋₁)]²", "h2")
    s.text(360, 730, "s.t. 각 연도 Σ분기 Xᵧq = Aᵧ", "h2", SLATE)
    s.text(155, 790, "산출", "h2", TEAL)
    draw_weight_cells(s, 360, 772, 660, 62, ["X₁", "X₂", "X₃", "X₄"], [24, 19, 27, 30], TEAL, "#145b55")
    s.text(1040, 790, "분기 GVA", "small", SLATE)

    # Right results panel.
    s.rect(1260, 450, 575, 410, WHITE, "#cad2de")
    s.text(1305, 485, "구현 결과", "h1", INK)
    metrics = [
        ("5,760", "분기 GVA 추정 행", GREEN),
        ("288", "2023 외삽 검증 건", RED),
        ("7.33%", "외삽 MAPE", GOLD),
    ]
    y = 550
    for value, label, color in metrics:
        s.text(1305, y, value, "title", color)
        s.text(1518, y + 20, label, "body", SLATE)
        y += 92
    s.rect(1305, 805, 480, 36, "#eef3f8", "#eef3f8", 0, 6)
    s.text(1325, 811, "재현 가능한 Python 파이프라인 + CSV 산출물", "small", SLATE)

    # Bottom notes as concise portfolio talking points.
    note_y = 910
    notes = [
        ("데이터 엔지니어링", "API 수집 · 정규화"),
        ("알고리즘 구현", "Denton 최적화"),
        ("검증 설계", "외삽 오차 비교"),
    ]
    x = 135
    for title, body in notes:
        s.rect(x, note_y, 500, 78, "#ffffff", "#cad2de")
        s.text(x + 28, note_y + 16, title, "body", BLUE)
        s.text(x + 265, note_y + 18, body, "small", SLATE)
        x += 560

    s.save(OUT / "fig06_portfolio_implementation.svg")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fig01_pipeline()
    fig02_methods()
    fig03_errors()
    fig04_proportional_denton_method()
    fig05_proportional_denton_detail()
    fig06_portfolio_implementation()
    print("generated svg:")
    for path in sorted(OUT.glob("fig*.svg")):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
