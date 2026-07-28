# Phase136 KOBIS 박스오피스 기반 고양시 J59 시간패턴 진단

## 목적

KOBIS API는 사용 가능하고 KOPIS는 사용 불가하므로, KOBIS 일별 박스오피스 매출·관객을 고양시 J59(영상·오디오 제작업) 연·분기 nowcast의 시간패턴 보조지표로 시험했다. KOBIS는 전국 박스오피스 top-list 자료이므로 고양시 actual이나 공간배분 자료로 주장하지 않는다.

## API 범위 감사

| probe name | params without key | boxoffice type | show range | row count | movie codes same as baseline | sales sum 원 | response scope interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | (none) |  |  | 0 | 0 | 0 | request_failed:URLError |
| areaCd_4128_attempt | areaCd=4128 |  |  | 0 | 0 | 0 | request_failed:URLError |
| wideAreaCd_4128_attempt | wideAreaCd=4128 |  |  | 0 | 0 | 0 | request_failed:URLError |

## KOBIS 월별 수집 요약

| year | month | quarter | kobis top sales 원 | kobis top audience | daily movie rows |
| --- | --- | --- | --- | --- | --- |
| 2,021 | 1 | 1 | 14,437,245,170 | 1,619,105 | 310 |
| 2,021 | 2 | 1 | 26,641,109,990 | 2,866,533 | 280 |
| 2,021 | 3 | 1 | 27,845,731,590 | 2,985,179 | 310 |
| 2,021 | 4 | 2 | 21,494,450,050 | 2,318,600 | 300 |
| 2,021 | 5 | 2 | 37,868,677,080 | 4,015,747 | 310 |
| 2,021 | 6 | 2 | 45,426,335,860 | 4,730,539 | 300 |
| 2,021 | 7 | 3 | 66,399,328,510 | 6,735,713 | 310 |
| 2,021 | 8 | 3 | 74,742,675,910 | 7,703,378 | 310 |
| 2,021 | 9 | 3 | 49,817,765,290 | 5,137,876 | 300 |
| 2,021 | 10 | 4 | 48,738,681,080 | 4,916,632 | 310 |
| 2,021 | 11 | 4 | 63,268,433,930 | 6,180,430 | 300 |
| 2,021 | 12 | 4 | 81,355,275,970 | 8,151,822 | 310 |
| 2,022 | 1 | 1 | 53,822,905,200 | 5,517,314 | 310 |
| 2,022 | 2 | 1 | 28,617,366,130 | 3,002,199 | 280 |
| 2,022 | 3 | 1 | 25,408,606,260 | 2,603,969 | 310 |
| 2,022 | 4 | 2 | 28,331,899,030 | 2,855,377 | 300 |
| 2,022 | 5 | 2 | 148,693,021,540 | 14,315,786 | 310 |
| 2,022 | 6 | 2 | 156,648,550,730 | 15,273,547 | 300 |

## 2022~2023 J59 연간 nowcast 비교

| available quarters | vintage label | years | generic error 억원 | generic wape % | kobis sales error 억원 | kobis sales wape % | kobis audience error 억원 | kobis audience wape % | best track |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1분기+1개월 | 2022-2023 | 215.94 | 11.17 | 1,058.83 | 54.76 | 1,016.70 | 52.58 | generic |
| 2 | 1~2분기+1개월 | 2022-2023 | 50.30 | 2.60 | 195.73 | 10.12 | 144.15 | 7.45 | generic |
| 3 | 1~3분기+1개월 | 2022-2023 | 69.78 | 3.61 | 97.93 | 5.06 | 96.23 | 4.98 | generic |
| 4 | 1~4분기+1개월 | 2022-2023 | 0 | 0 | 0 | 0 | 0 | 0 | generic |

## 빈티지별 적용 판정

| available quarters | vintage label | adopt for j59 temporal nowcast | best track | error reduction 억원 | decision note |
| --- | --- | --- | --- | --- | --- |
| 1 | 1분기+1개월 | 0 | generic | -800.76 | generic seasonal share remains safer |
| 2 | 1~2분기+1개월 | 0 | generic | -93.85 | generic seasonal share remains safer |
| 3 | 1~3분기+1개월 | 0 | generic | -26.44 | generic seasonal share remains safer |
| 4 | 1~4분기+1개월 | 0 | generic | 0 | generic seasonal share remains safer |

## 2023 예시 상세

| vintage label | ytd estimate 억원 | seasonal ytd share | kobis sales ytd share | kobis audience ytd share | annual prediction 억원 | kobis sales annual prediction 억원 | kobis audience annual prediction 억원 | actual annual gva 억원 | annual error rate % | kobis sales annual error rate % | kobis audience annual error rate % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1분기+1개월 | 214.57 | 0.21 | 0.22 | 0.20 | 1,032.12 | 997.47 | 1,077.68 | 945.76 | 9.13 | 5.47 | 13.95 |
| 1~2분기+1개월 | 438.60 | 0.45 | 0.48 | 0.47 | 976.66 | 905.30 | 935.29 | 945.76 | 3.27 | 4.28 | 1.11 |
| 1~3분기+1개월 | 690.35 | 0.70 | 0.76 | 0.75 | 981.49 | 906.25 | 916.03 | 945.76 | 3.78 | 4.18 | 3.14 |
| 1~4분기+1개월 | 945.76 | 1 | 1 | 1 | 945.76 | 945.76 | 945.76 | 945.76 | 0 | 0 | 0 |

## 판정

1. KOBIS는 고양시 시군구 단위 영화 매출 actual이 아니므로 J59 금액격차 자체를 직접 검증하는 자료가 아니다.
2. 다만 전국 영화시장 월별 매출·관객의 YTD share는 J59 시간패턴 후보로 쓸 수 있다. 채택 여부는 2022~2023 rolling nowcast에서 generic seasonal share보다 오차가 작을 때만 제한적으로 허용한다.
3. KOBIS가 개선되지 않는 빈티지는 기존 계절비중을 유지해야 한다. 이 원칙은 Phase133의 금액가중 guardrail과 같다: 그럴듯한 자료라도 검증오차를 줄이지 못하면 채택하지 않는다.
4. 고양시 공간·금액 개선에는 여전히 고양시 영상기업/제작지원/촬영·상영 매출 자료가 필요하다. KOBIS는 시간축 보조지표이지 고양시 산업 총량 actual이 아니다.
