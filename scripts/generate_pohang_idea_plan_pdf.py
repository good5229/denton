from __future__ import annotations

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pohang"
PDF = OUT / "pohang_data_analysis_idea_plan_submission.pdf"
PREVIEW = OUT / "pohang_data_analysis_idea_plan_submission_preview.png"

W, H = 1240, 1754  # A4 portrait at ~150dpi
M = 78
NAVY = "#123E63"
BLUE = "#DDEAF4"
INK = "#1B252E"
MUTED = "#53636E"
GRID = "#9EB2C1"
PALE = "#F7FAFC"
TEAL = "#147D78"
ORANGE = "#D9653B"
WHITE = "#FFFFFF"

FONT_BODY = "/Library/Fonts/NanumBarunGothic.ttf"
FONT_BOLD = "/Library/Fonts/NanumBarunGothicBold.ttf"
FONT_TITLE = "/Library/Fonts/NanumSquareExtraBold.ttf"


def font(size: int, bold: bool = False, title: bool = False):
    path = FONT_TITLE if title else FONT_BOLD if bold else FONT_BODY
    return ImageFont.truetype(path, size)


def text(draw: ImageDraw.ImageDraw, xy, value, size=28, color=INK, bold=False, title=False, anchor=None):
    draw.text(xy, str(value), font=font(size, bold, title), fill=color, anchor=anchor)


def wrap(draw: ImageDraw.ImageDraw, value: str, size: int, width: int, bold=False) -> list[str]:
    out: list[str] = []
    for para in str(value).split("\n"):
        if not para:
            out.append("")
            continue
        line = ""
        for ch in para:
            if draw.textlength(line + ch, font=font(size, bold)) <= width:
                line += ch
            else:
                if line:
                    out.append(line)
                line = ch
        if line:
            out.append(line)
    return out


def paragraph(draw, x, y, value, size=30, width=None, color=INK, bold=False, leading=10, bullet=False):
    width = width or (W - 2 * M)
    prefix_w = 30 if bullet else 0
    lines = wrap(draw, value, size, width - prefix_w, bold)
    step = size + leading
    if bullet:
        text(draw, (x, y), "•", size, ORANGE, True)
        x += prefix_w
    for i, line in enumerate(lines):
        text(draw, (x, y + i * step), line, size, color, bold)
    return y + len(lines) * step


def box_text(draw, box, value, size=28, color=INK, bold=False, align="left"):
    x0, y0, x1, y1 = box
    lines = wrap(draw, value, size, int(x1 - x0 - 24), bold)
    step = size + 8
    total_h = len(lines) * step - 8
    yy = y0 + (y1 - y0 - total_h) / 2
    for line in lines:
        tw = draw.textlength(line, font=font(size, bold))
        if align == "center":
            xx = x0 + (x1 - x0 - tw) / 2
        else:
            xx = x0 + 12
        text(draw, (xx, yy), line, size, color, bold)
        yy += step


def section(draw, y, num, title):
    draw.rounded_rectangle((M, y, M + 58, y + 58), radius=4, fill=BLUE, outline=GRID, width=2)
    box_text(draw, (M, y, M + 58, y + 58), str(num), 30, NAVY, True, "center")
    text(draw, (M + 76, y + 8), title, 34, NAVY, True)
    draw.line((M + 76, y + 58, W - M, y + 58), fill=GRID, width=2)
    return y + 84


def table(draw, x, y, width, headers, rows, ratios, row_h=62, size=24):
    xs = [x]
    for r in ratios:
        xs.append(xs[-1] + width * r)
    draw.rectangle((x, y, x + width, y + row_h), fill=BLUE, outline=GRID, width=2)
    for i, h in enumerate(headers):
        box_text(draw, (xs[i], y, xs[i+1], y + row_h), h, size, NAVY, True, "center")
    for ridx, row in enumerate(rows):
        yy = y + row_h * (ridx + 1)
        fill = WHITE if ridx % 2 == 0 else PALE
        for i, cell in enumerate(row):
            draw.rectangle((xs[i], yy, xs[i+1], yy + row_h), fill=fill, outline=GRID, width=1)
            box_text(draw, (xs[i] + 4, yy + 2, xs[i+1] - 4, yy + row_h - 2), str(cell), size - 2, INK, i == 0, "center")
    return y + row_h * (len(rows) + 1)


def make_page(page_no: int):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    text(draw, (M, 54), "포항시 데이터 분석 아이디어 공모전 기획서", 42, NAVY, True, True)
    text(draw, (M, 112), "포항시 읍면동·업종별 월간 산업활력 정책지도", 28, MUTED, True)
    draw.line((M, 156, W - M, 156), fill=NAVY, width=4)
    text(draw, (W - M, H - 48), f"- {page_no} -", 22, MUTED, anchor="ra")
    return img, draw


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages: list[Image.Image] = []

    img, draw = make_page(1)
    y = 190
    y = section(draw, y, "요약", "아이디어 요약서")
    draw.rounded_rectangle((M, y, W - M, y + 152), radius=8, fill="#EAF5F3", outline=GRID, width=2)
    box_text(draw, (M + 18, y + 16, W - M - 18, y + 70), "공식통계가 늦게 보여주는 산업 변화를 읍면동×업종×월 단위로 먼저 포착", 30, TEAL, True, "center")
    box_text(draw, (M + 18, y + 78, W - M - 18, y + 136), "산단·항만·상권·고용지원 우선 점검 후보를 제시하는 정책지도", 28, INK, True, "center")
    y += 190
    y = section(draw, y, 1, "아이디어 명칭")
    y = paragraph(draw, M + 10, y, "포항시 읍면동·업종별 월간 산업활력 정책지도", 32, bold=True) + 24
    y = section(draw, y, 2, "분석 목적")
    for item in [
        "철강·산단·항만·상권·고용지원 현안이 읍면동과 업종 단위에서 다르게 변화",
        "연간·상위 산업 중심 공식통계만으로는 조기 대응 후보를 찾기 어려움",
        "29개 읍면동의 월별 총부가가치(GVA) 기반 산업활력 지수를 산출해 우선 점검 후보를 축소",
        "산단관리, 항만물류, 민생상권, 일자리 대응을 같은 기준으로 비교하는 행정 운영판 구축",
    ]:
        y = paragraph(draw, M + 10, y, item, 27, bullet=True) + 8
    y = section(draw, y + 8, 3, "핵심 내용")
    for item in [
        "29개 읍면동×전 산업 대·중·소분류×월 단위 산업활력 지수 산출",
        "하위 추정값을 중분류·대분류·분기·연 단위로 다시 합산해 상위 공식통계와 대조",
        "오차 크기와 정밀화 악화 여부에 따라 모니터링, 부서확인, 현장자료 결합 단계로 구분",
    ]:
        y = paragraph(draw, M + 10, y, item, 27, bullet=True) + 8
    y += 30
    card_w = (W - 2 * M - 28) / 3
    for i, (title, body, color) in enumerate([
        ("산출 규모", "29읍면동·36개월·228소분류", TEAL),
        ("집계검증", "중분류 WAPE 5.98%", NAVY),
        ("속보 검증", "3분기+1개월 WAPE 1.25%", ORANGE),
    ]):
        xx = M + i * (card_w + 14)
        draw.rounded_rectangle((xx, y, xx + card_w, y + 160), radius=8, fill=PALE, outline=GRID, width=2)
        box_text(draw, (xx + 10, y + 12, xx + card_w - 10, y + 52), title, 27, color, True, "center")
        box_text(draw, (xx + 14, y + 58, xx + card_w - 14, y + 148), body, 23, INK, True, "center")
    pages.append(img)

    img, draw = make_page(2)
    y = 190
    y = section(draw, y, 4, "분석 방법")
    methods = [
        ("1", "상위 공식값 확보", "KOSIS 지역계정·경제총조사에서 포항시 산업별 공식 총량과 산업 구조 확보"),
        ("2", "하위 활동자료 구성", "사업체조사, 공장등록, 인구, 인허가, 광공업 월지수를 읍면동·업종·월 단위로 결합"),
        ("3", "배분·외삽", "공식값이 없는 하위 단위는 활동자료 비중으로 나누고 월별 변화는 월간 지표로 외삽"),
        ("4", "집계검증", "하위 추정값을 시·구·상위 산업·분기·연 단위로 다시 합산해 공식값과 비교"),
        ("5", "정책 판정", "정밀화 악화 산업은 자동 채택하지 않고 부서확인·현장자료 결합으로 분리"),
    ]
    for n, title, desc in methods:
        draw.rounded_rectangle((M, y, M + 72, y + 72), radius=6, fill=BLUE, outline=GRID, width=1)
        box_text(draw, (M, y, M + 72, y + 72), n, 30, NAVY, True, "center")
        text(draw, (M + 92, y + 2), title, 28, NAVY, True)
        paragraph(draw, M + 92, y + 38, desc, 24, W - 2 * M - 100, MUTED)
        y += 112
    y = section(draw, y + 8, "결과", "대표 분석 결과")
    result_rows = [
        ("공간 검증", "읍면동 산업분포 MAE 2.95%p"),
        ("작은 오차", "음식점·주점 0.07%, 육상운송 0.31%, 1차 금속 1.19%"),
        ("점검 대상", "건축기술·엔지니어링, 전문서비스, 보험·연금"),
        ("후보 지역", "제철동·대송면·청하면 등 산단·항만 배후 후보"),
    ]
    y = table(draw, M, y, W - 2 * M, ["구분", "결과"], result_rows, [.28, .72], 54, 22) + 30
    y = section(draw, y, 5, "필요 데이터")
    rows = [
        ("공식 경제통계", "KOSIS 지역계정·경제총조사", "총량·검증"),
        ("지역 산업구조", "포항시 사업체조사", "읍면동 산업비중"),
        ("제조업 공간자료", "포항시 공장등록현황", "산단 후보 동"),
        ("월간 변화자료", "인허가·광공업 월지수", "변화 감지"),
        ("공간·규모자료", "읍면동 경계·인구", "표준화"),
        ("추가 확보 희망", "항만·고용·기업상담", "오차 보완"),
    ]
    table(draw, M, y, W - 2 * M, ["구분", "활용 데이터", "역할"], rows, [.24, .50, .26], 60, 23)
    pages.append(img)

    img, draw = make_page(3)
    y = 190
    y = section(draw, y, 6, "활용방안(계획)")
    rows = [
        ("산단 경쟁력", "제조업 후보 읍면동", "기업지원·산단관리"),
        ("영일만항·물류", "운수·창고업 변화 신호", "항만·물류 점검"),
        ("민생경제·상권", "도소매·음식점 위축 후보", "소상공인 지원"),
        ("일자리 대응", "활력 하락 산업과 읍면동", "고용지원 연계"),
        ("예산·사업 검토", "공식값·추정값·오차표", "사업 우선순위 보조"),
    ]
    y = table(draw, M, y, W - 2 * M, ["시정 현안", "정책 산출물", "활용 방식"], rows, [.28, .38, .34], 68, 23) + 44
    y = section(draw, y, "효과", "활용 전후 변화")
    for title, desc, color in [
        ("기존", "연간·상위 산업 공식통계 확인 후 사후 대응", ORANGE),
        ("개선", "분기 종료 후 1개월 내 자료로 읍면동·업종 후보 조기 점검", TEAL),
        ("기대효과", "현장확인 대상 축소, 정책사업 우선순위 보조, 2027년 빅데이터 분석 과제 후보화", NAVY),
    ]:
        draw.rounded_rectangle((M, y, W - M, y + 112), radius=8, fill=PALE, outline=GRID, width=2)
        box_text(draw, (M + 12, y, M + 170, y + 112), title, 27, color, True, "center")
        box_text(draw, (M + 188, y, W - M - 12, y + 112), desc, 26, INK, True, "center")
        y += 132
    y = section(draw, y + 16, "심사", "심사항목 대응")
    rows = [
        ("창의성", "미공표 하위 산업활력 지표를 상위 공식통계로 검증"),
        ("필요성·시급성", "산단·항만·상권·고용지원 현안의 우선 점검 후보 제시"),
        ("적절성·활용성", "무료 공공데이터 기반, 오차 공개, 부서별 확인목록 제공"),
    ]
    table(draw, M, y, W - 2 * M, ["항목", "대응"], rows, [.26, .74], 64, 23)
    pages.append(img)

    pages[0].save(PDF, save_all=True, append_images=pages[1:], resolution=150.0)
    preview = Image.new("RGB", (W, H * 3), "white")
    for i, page in enumerate(pages):
        preview.paste(page, (0, H * i))
    preview.resize((620, round(620 * preview.height / preview.width))).save(PREVIEW, quality=92)
    print(PDF)
    print(PREVIEW)


if __name__ == "__main__":
    main()
