# 국가물류통합정보센터 물류창고업 등록현황 source metadata

생성시각: 2026-07-29T21:50:41+09:00

## 원천

| 항목 | 내용 |
| --- | --- |
| 자료명 | 지역별 물류창고업 등록현황 |
| 공식 연결 | 공공데이터포털 fileData `15083282`, 국가물류통합정보센터 통계 다운로드 |
| 다운로드 URL | `https://www.nlic.go.kr/nlic/WhsStatsWarehouseLocation.action?command=DWLOAD&S_D_FROM={year}&S_D_TO={year}` |
| 로컬 원본 | `data/raw/phase266_nlic_warehouse_location/nlic_warehouse_location_YYYY.xls` |
| 수집기간 | 2015~2025 |
| 지역 해상도 | 시도 |
| 시간 해상도 | 연간 |
| 측정값 | 등록건수 flow/stock 성격의 행정 등록 현황 |
| 사용 가능 역할 | H52 창고업 또는 운수 및 창고업 시도 단위 보조 신호 후보 |
| 금지 해석 | GVA actual 아님, 시군구 공간배분 근거 아님, route 채택 근거 아님 |

## 공표·운영 메모

- 다운로드 endpoint는 별도 API key 없이 XLS attachment를 반환한다.
- 파일명은 다운로드일을 포함하므로 재수집 시 파일명은 달라질 수 있다.
- 일부 연도는 원본 표에서 등록건수 0으로 보이는 시도 행이 생략된다. 파싱 산출물은 17개 시도 패널 유지를 위해 생략 시도를 0으로 채우고 `source_row_present=False`로 표시한다.
- 자료는 시도별 등록건수이므로 Q+1개월 속보성 또는 월별 직접지표로 쓰지 않는다.
- 향후 H52 창고업 시도 검증, 항만 물동량·사업체·전력 등과 결합한 보조 gate에서만 후보로 사용한다.
