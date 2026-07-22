# Phase60 경기버스 정류소 좌표 수집 및 고양시 공간결합

## 결론

- 사용자가 `.env`에 추가한 `DATA_GG_KEY`로 경기데이터드림 `BusStation` API를 호출해 경기도 버스정류소 좌표를 수집했다.
- 전체 정류소 좌표 34,585건, 고양시 정류소 좌표 2,197건을 확보했다.
- Phase58 승하차 원자료의 고양시 `정류소×월` 집계 123,976행에 좌표를 결합했다.
- 정류소ID 단독 매칭률은 90.2%, 보조매칭 포함 최종 매칭률은 92.6%다.

## 사용 API

| 항목 | 값 |
|---|---|
| 데이터셋 | 버스정류소 현황 |
| 요청주소 | `https://openapi.gg.go.kr/BusStation` |
| 인증키 환경변수 | `DATA_GG_KEY` |
| 주요 출력 | `SIGUN_NM`, `STATION_ID`, `STATION_MANAGE_NO`, `LOCPLC_LOC`, `WGS84_LAT`, `WGS84_LOGT` |
| 출처 페이지 | `https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=GDKWAGWYRKJYIRVX110226832213&infSeq=3` |

## 매칭 결과

| 매칭 방식 | 행 수 |
|---|---:|
| 정류소ID 일치 | 111,841 |
| 정류소관리번호 일치 | 759 |
| 고양시+정류소명 일치 | 2,204 |
| 미매칭 | 9,172 |
| 전체 | 123,976 |

최종 매칭률: 92.6%

## 산출물

- `data/processed/phase60_gg_bus_station_coordinates/gg_bus_station_coordinates.csv`
- `data/processed/phase60_gg_bus_station_coordinates/gg_bus_station_coordinates_goyang.csv`
- `data/processed/phase60_gg_bus_station_coordinates/goyang_bus_station_monthly_with_coordinates.csv`
- `data/processed/phase60_gg_bus_station_coordinates/phase60_manifest.json`
- `data/processed/phase60_gg_bus_station_coordinates/phase60_enrichment_manifest.json`

## 적용 판단

- 고양시 행정동 단위 운수 활동지표 구축의 핵심 병목이었던 정류소 좌표가 확보됐다.
- 다음 단계는 정류소 좌표를 고양시 행정동 경계와 공간결합해 `행정동×월` 승하차 활동지표를 만드는 것이다.
- 다만 현재 좌표 자료 자체가 “영문명 부여 사업 중단으로 갱신 불가” 주석이 있는 자료이므로, 최신 정류소의 일부 미매칭은 남을 수 있다.
- 포스터/공모전 표현에서는 `프록시` 대신 `정류소별 월간 승하차 활동지표`, `행정동 이동수요 지표`로 쓰는 것이 적절하다.
