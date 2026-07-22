# Phase57 잔여 무료자료 수집 상태 정정

## 결론

- 경기데이터드림 `경기도 정류소 별 승하차 인원 집계`는 File 탭에서 연구목적 선택 후 다운로드해야 하는 UI 절차형 자료로 확인했다. 단순 `curl` 다운로드 endpoint 호출은 `/portal/mainPage.do`로 302 redirect되어 자동 수집하지 못했다.
- 주택 공시가격은 공공데이터포털 파일을 다운로드한 뒤 Parquet/Zstd로 변환했고, 변환 검증 후 원본 ZIP을 삭제했다.
- 항만 물동량의 기존 공공데이터포털 검색결과 3건은 접근 불안정/404가 맞다. 해양수산부 통계 API는 2025-02-06 공지 기준으로 해양수산통계 공유서비스로 전환되었으므로, 현재는 `mof.go.kr/statPortal/api` 쪽을 우선 링크로 본다.
- 나머지 신청 완료 API들은 승인 후 정상 endpoint/키 인코딩 방식을 별도 probe해야 한다. `15126469` 실거래가처럼 잘못된 endpoint로 판단하면 수집 가능 자료를 놓칠 수 있다.

## 경기버스 자료

| 항목 | 내용 |
| --- | --- |
| 자료명 | 경기도 정류소 별 승하차 인원 집계 |
| 사용 목적 | 운수 및 창고업 중 육상 여객 운송업 월별·공간 활동지표 |
| 사용자 제공 링크 | `https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=2` |
| 확인된 다운로드 endpoint | `/portal/service/fileDownload.do` |
| 자동 수집 결과 | `302 Found → /portal/mainPage.do` |
| 판정 | UI에서 File 항목 다운로드 버튼 클릭 후 연구목적 선택이 필요한 수동 다운로드 대상 |

수동으로 받은 파일이 생기면 `data/raw/phase57_gg_bus/`에 넣고, 정류소 주소/좌표 기준으로 고양시 정류소만 추출해 행정동 또는 구 단위 승하차 월별 피처로 변환한다.

## 주택 공시가격 변환

| 항목 | 값 |
| --- | ---: |
| 전체 행수 | 15,580,435 |
| 고양·포항 추출 행수 | 495,846 |
| 원본 ZIP 크기 | 144.2MB |
| 전체 Parquet 크기 | 82.9MB |
| 고양·포항 Parquet 크기 | 2.3MB |
| 원본 ZIP 삭제 | 완료 |

상세 결과: `reports/partial_statistics_estimation_phase56_housing_price_parquet.md`

## 항만 물동량 현재 링크

| 구분 | 링크 | 판정 |
| --- | --- | --- |
| 공공데이터포털 기존 검색결과 | `https://www.data.go.kr/dataset/3036255/openapi.do?lang=ko` | 검색결과에는 남아 있으나 사용자 확인상 페이지 없음/접근 불안정 |
| 공공데이터포털 중단 공지 | `https://www.data.go.kr/bbs/ntc/selectNotice.do?atchFileId=&nttApiYn=N&originId=NOTICE_0000000003942&pageIndex=1&searchCondition2=2&searchKeyword1=` | 해양수산통계 API 전환 공지 |
| 대체 서비스 | `https://www.mof.go.kr/statPortal/api/idx/main.do` | 해양수산통계 공유서비스. API 인증키 신청 필요 |

포항 운수·창고업 보강에는 포항항 월별 화물처리실적 또는 컨테이너 처리실적이 필요하다. 기존 공공데이터포털 링크가 죽어 있으므로, 향후에는 해양수산통계 공유서비스에서 통계표 목록과 API 파라미터를 다시 받아야 한다.

## 다음 처리 순서

1. 경기버스 파일을 수동 다운로드 후 `data/raw/phase57_gg_bus/`에 배치한다.
2. 해양수산통계 공유서비스 API 키가 승인되면 통계목록에서 화물처리실적/컨테이너 처리실적 표 ID를 확인한다.
3. 주택 공시가격 Parquet는 부동산업 `681 부동산 임대 및 공급업`의 구·법정동 단위 stock/가격 가중치로 연결한다.
4. 승인 완료된 나머지 API는 각 API별 공식 Swagger endpoint와 키 인코딩 방식을 먼저 probe한 뒤 배치 수집한다.
