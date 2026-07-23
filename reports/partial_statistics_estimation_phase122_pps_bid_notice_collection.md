# Phase122 조달청 나라장터 입찰공고 수집

## 목적

고양시와 포항시의 건설업, 전문서비스, 연구개발, 사업지원, 공공·비영리 관련 총부가가치(GVA) 추정에서 사용할 수 있는 공공발주 활동자료를 추가 확보했다. 이번 단계는 성능 재계산이 아니라 무료 공개자료 수집과 원천 범위 기록이 목적이다.

## 수집 방식

| 구분 | 내용 |
|---|---|
| 원천 | 조달청_나라장터 입찰공고정보서비스 |
| 링크 | `https://www.data.go.kr/data/15129394/openapi.do` |
| 사용 게이트웨이 | `http://apis.data.go.kr/1230000/ad/BidPublicInfoService` |
| 수집 기간 | 2023년 1~9월 |
| 업무구분 | 용역, 공사, 물품 |
| 지역 추출 | 수요기관명 검색 operation(`PPSSrch`)의 `dminsttNm` 조건 |
| 고양 조건 | `dminsttNm=고양시` |
| 포항 조건 | `dminsttNm=경상북도 포항시` |

일반 목록 operation은 `dminsttNm` 조건을 붙여도 전체 건수가 줄지 않아 지역 조건이 무시되는 것으로 확인했다. 따라서 전국 전량을 계속 훑는 방식 대신 검색용 `PPSSrch` operation을 사용했다.

## 생성 파일

| 파일 | 내용 |
|---|---|
| `scripts/collect_phase122_pps_bid_notices.py` | 조달청 입찰공고 수집 스크립트 |
| `data/raw/phase122_pps_bid_notices/` | API 원문 캐시 |
| `data/processed/phase122_pps_bid_notices/phase122_pps_goyang_pohang_combined_notices.csv` | 고양·포항 결합 공고 후보 |
| `data/processed/phase122_pps_bid_notices/phase122_pps_goyang_pohang_combined_summary.csv` | 지역×업무구분 요약 |
| `data/processed/phase122_pps_bid_notices/phase122_pps_goyang_pohang_monthly_summary.csv` | 지역×월×업무구분 요약 |
| `data/processed/phase122_pps_bid_notices/phase122_pps_collection_errors_dminstt_goyang.csv` | 고양 수집 오류 |
| `data/processed/phase122_pps_bid_notices/phase122_pps_collection_errors_dminstt_pohang.csv` | 포항 수집 오류 |

## 수집 결과

결합 산출물은 중복 제거 후 3,547건이다.

| 지역 | 업무구분 | 공고 수 | 배정예산 합계(억원) | 추정가격 합계(억원) |
|---|---:|---:|---:|---:|
| 고양시 | 공사 검색 | 734 | 0.0 | 950.1 |
| 고양시 | 용역 검색 | 509 | 1,151.4 | 1,056.3 |
| 고양시 | 물품 검색 | 112 | 253.8 | 231.0 |
| 고양시 | 2023년 1월 전국캐시 내 공사 매칭 | 48 | 0.0 | 57.8 |
| 고양시 | 2023년 1월 전국캐시 내 용역 매칭 | 86 | 95.3 | 87.2 |
| 고양시 | 2023년 1월 전국캐시 내 물품 매칭 | 15 | 10.5 | 9.5 |
| 포항시 | 공사 검색 | 887 | 0.0 | 1,834.4 |
| 포항시 | 용역 검색 | 468 | 1,036.4 | 943.0 |
| 포항시 | 물품 검색 | 292 | 371.9 | 340.1 |
| 포항시 | 2023년 1월 전국캐시 내 공사 매칭 | 130 | 0.0 | 666.6 |
| 포항시 | 2023년 1월 전국캐시 내 용역 매칭 | 180 | 422.4 | 384.1 |
| 포항시 | 2023년 1월 전국캐시 내 물품 매칭 | 86 | 105.2 | 96.1 |

공사의 배정예산 합계가 0으로 보이는 것은 공사 operation에서 `asignBdgtAmt`가 비어 있고 `presmptPrce` 중심으로 금액이 제공되기 때문이다. 분석에서는 업무구분별로 사용 가능한 금액 필드를 분리해서 써야 한다.

## 미수집·오류

포항시 수요기관명 검색은 45초 timeout 재시도 후 2023년 1~9월 전 조합을 수집했다.

고양시는 `202303 thng_pps` 1개 조합이 45초 timeout에서도 실패했다. 이 조합은 `data/processed/phase122_pps_bid_notices/phase122_pps_collection_errors_dminstt_goyang.csv`에 남겼다.

## 원천 범위 주의

조달청 API의 원천 범위는 전국 공고다. 다만 이번 로컬 산출물은 두 종류가 섞여 있다.

1. `servc/cnstwk/thng_202301_*` 일반 operation 원문 캐시는 전국 페이지다.
2. `*_pps_*dminsttNm-*` 검색 operation 원문 캐시는 고양·포항 수요기관명 조건으로 호출한 지역 검색 결과다.

따라서 타 지역 분석 때는 현재 고양·포항 CSV를 재사용하면 안 되고, 같은 스크립트에 `dminsttNm` 조건을 대상 지역명으로 바꿔 재수집해야 한다. 전국 전량 캐시는 2023년 1월 일부만 있으므로 전국 완결 원본으로 간주하지 않는다.

## GVA 실험 투입 전 검증 포인트

1. 수요기관명 기준 자료이므로 실제 사업 수행지가 고양·포항인지 별도 확인이 필요하다.
2. 공고명에 다른 지역 사업이 포함될 수 있어, 금액이 큰 공고는 `bidNtceDtlUrl` 또는 첨부문서 검토가 필요하다.
3. 전문서비스·건설업에는 직접 활동자료 후보로 유용하지만, 총부가가치 actual이 아니므로 중분류 집계검증에서만 성능을 평가해야 한다.
4. 검색 operation 결과와 전국 전량 텍스트 매칭 결과가 중복될 수 있으므로 `bidNtceNo + bidNtceOrd + dminsttNm` 기준 중복 제거를 유지해야 한다.
