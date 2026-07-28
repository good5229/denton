# Phase181 우선순위 공개 활동자료 API 재점검

## 목적

사용자가 추가 활용신청을 완료한 뒤, Phase180 잔여 취약 블록에 직접적으로 붙일 수 있는 무료·공개 활동자료 API가 실제로 열렸는지 소량 호출로 확인했다. 이 단계는 총부가가치(GVA)를 직접 내려받는 것이 아니라, 제조업·전문서비스·사업지원·금융·환경수도 업종의 **배분근거/시간축 보조지표** 확보 가능성을 판정하는 절차다.

## 점검 결과

| 자료 | 상태 | API코드 | 메시지 | 표본행 | 대상 업종 | 활용 판정 |
| --- | --- | --- | --- | --- | --- | --- |
| 한국산업단지공단 공장등록 생산정보 목록 | http_error |  | API not found  | 0 | C00 제조업 중분류/소분류 | 품목·생산정보가 실제로 열리면 제조업 세부 배분근거 후보. 시군구/공장주소 필드 확인 필요. |
| 한국산업단지공단 공장등록 공장 목록 v2 | http_error |  | API not found  | 0 | C00 제조업 공간 배분 | 주소·업종·종업원/생산품 필드가 열리면 제조업 공간구조 보조. 생산금액 actual은 아님. |
| 조달청 나라장터 공공데이터 개방표준 계약정보 | ok_items | 00 | 정상 | 5 | MN0/F00/사업지원/전문서비스 | 계약금액·수요기관·계약업체 지역이 열리면 공공수요 의존 업종의 금액형 활동자료 후보. |
| 조달청 나라장터 공공데이터 개방표준 낙찰정보 | ok_empty_or_needs_params |  |  | 0 | MN0/F00/사업지원/전문서비스 | 낙찰금액·업체명·수요기관이 열리면 계약정보 보완 후보. |
| 금융위원회 금융회사 기본정보 | ok_items | 00 | NORMAL SERVICE. | 5 | K00 금융·보험 | 본점·기관 분포 구조자료. 예수금/대출금 같은 금액형 지역 활동자료가 아니면 단독 개선력은 제한. |
| 한국수자원공사 하수처리장 일일 수질 | ok_empty_or_needs_params | 00 | NORMAL SERVICE. | 0 | E37/E38/ERS 환경·수도 | 처리장·수질 일자료가 열리면 환경·수도 시간축 보조. 처리량/요금 필드 유무 확인 필요. |

## 즉시 수집 가능 후보

| 자료 | 총건수 | 표본 필드 | 대상 | 활용 방식 |
| --- | --- | --- | --- | --- |
| 조달청 나라장터 공공데이터 개방표준 계약정보 | 32541 | cntrctNo, untyCntrctNo, cntrctOrd, cntrctNm, bsnsDivNm, cntrctCnclsSttusNm, cntrctCnclsMthdNm, lngtrmCtnuDivNm, cmmnCntrctYn, cntrctCnclsDate, cntrctPrd, cntrctAmt, ttalCntrctAmt, cntrctInfoUrl, bidNtceNo, bidNtceOrd, bi | MN0/F00/사업지원/전문서비스 | 계약금액·수요기관·계약업체 지역이 열리면 공공수요 의존 업종의 금액형 활동자료 후보. |
| 금융위원회 금융회사 기본정보 | 2277780 | basDt, crno, fncoNm, fncoEnsnNm, isinCd, isinCdNm, fncoRprNm, corpRegMrktDcd, corpRegMrktDcdNm, bzno, fncoAdr, fncoZpcd, fncoHmpgUrl, fncoTlno, fncoFxno, sicCd, sicNm, fncoEstbDt, fncoStacMm, fncoXchgLstgDt, fncoXchgLstg | K00 금융·보험 | 본점·기관 분포 구조자료. 예수금/대출금 같은 금액형 지역 활동자료가 아니면 단독 개선력은 제한. |

## 추가 확인 대상

| 자료 | 상태 | HTTP | 메시지 | 출처 |
| --- | --- | --- | --- | --- |
| 조달청 나라장터 공공데이터 개방표준 낙찰정보 | ok_empty_or_needs_params | 200 |  | https://www.data.go.kr/data/15058815/openapi.do |
| 한국수자원공사 하수처리장 일일 수질 | ok_empty_or_needs_params | 200 | NORMAL SERVICE. | https://www.data.go.kr/data/15099046/openapi.do |
| 한국산업단지공단 공장등록 생산정보 목록 | http_error | 404 | API not found  | https://www.data.go.kr/data/15087611/openapi.do |
| 한국산업단지공단 공장등록 공장 목록 v2 | http_error | 404 | API not found  | https://www.data.go.kr/data/15087611/openapi.do |

## 모델 반영 원칙

1. `ok_items` 후보만 다음 추정모형 입력으로 사용한다.
2. 업체·기관 목록형 자료는 금액형 actual이 아니므로, 단독으로 “정확 예측”을 주장하지 않는다.
3. 계약·생산·처리량처럼 금액 또는 물량 필드가 있는 자료는 중분류/소분류 추정값을 만든 뒤 상위 중분류·대분류 actual 집계와 비교한다.
4. 공표시점이 확인되지 않는 자료는 정밀화 후보로만 두고, 속보성 후보로 쓰지 않는다.

## 산출물

- 점검 CSV: `data/processed/phase181_priority_public_activity_api_probe/phase181_priority_api_probe_summary.csv`
- 원문 응답 캐시: `data/raw/phase181_priority_public_activity_api_probe/`
- 캐시는 serviceKey 문자열을 `[REDACTED_SERVICE_KEY]`로 치환했다.
