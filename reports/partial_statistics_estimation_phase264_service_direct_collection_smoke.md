# Phase264 비건설 서비스업 직접 활동자료 수집 smoke

생성시각: 2026-07-29T21:35:00+09:00

## 1. 목적

Phase263에서 우선 후보로 정리한 운수·창고업 및 숙박·음식점업 직접 활동자료를 실제 수집 가능한지 소량 smoke로 확인했다. 이번 단계는 원자료 전량 수집이 아니라 API/파일 접근 가능성 확인이며, 응답 실패 원인을 기록해 다음 활용신청·수동수집 대상을 좁히는 것이 목적이다.

## 2. 시도 결과

| 자료 | 시도 방식 | 결과 | 판단 |
| --- | --- | --- | --- |
| LOCALDATA 물류창고업 전체 파일 | `https://file.localdata.go.kr/file/download/logistics_warehouses/info` 및 도시별 `orgCode` 포함 URL | 302 후 403 Forbidden | 기존 두 도시용 cache는 있으나, 현재 파일 서버 직접 다운로드는 차단. 전체자료는 포털 UI 또는 LOCALDATA authKey/공공데이터포털 이관 경로 확인 필요 |
| LOCALDATA 일반음식점 전체 파일 | `https://file.localdata.go.kr/file/download/general_restaurants/info` 및 도시별 `orgCode` 포함 URL | 302 후 403 Forbidden | 음식점·숙박업 전국 원천 자동 수집은 현재 URL만으로 불가 |
| 국토교통부 물류창고업등록정보 OpenAPI | `http://apis.data.go.kr/1611000/whsinfoview2/WhsInfoList`, `ServiceKey`, `pageNo=1`, `numOfRows=3`, `type=json` | 403 Forbidden | 공식 문서상 무료·자동승인이지만, 현재 `.env`의 공공데이터포털 키로는 호출 실패. 해당 API 활용신청 상태 또는 기관 게이트웨이 권한 재확인 필요 |

## 3. 공식 문서상 확인한 조건

| 자료 | 공식 조건 |
| --- | --- |
| 국토교통부 물류창고업등록정보 | REST, JSON+XML, 무료, 개발/운영 자동승인, 개발계정 10,000건, 업데이트 주기 실시간, 요청주소 `http://apis.data.go.kr/1611000/whsinfoview2/WhsInfoList` |
| LOCALDATA 전체자료 | 데이터 다운로드는 업종별·지역별 전체자료 제공, 전체자료는 전월까지 마감, 변동분 API는 당월 1일~2일 전 자료 제공 |

## 4. 필요한 사용자 조치

1. 공공데이터포털 `국토교통부_물류창고업등록정보` 활용신청 여부 확인  
   링크: https://www.data.go.kr/data/3048029/openapi.do
2. LOCALDATA 전체자료 다운로드 경로 확인 또는 authKey 확보  
   전체자료 다운로드: https://www.localdata.kr/devcenter/dataDown.do?menuNo=20001  
   데이터활용가이드: https://www.localdata.go.kr/portal/portalDataGuide.do?menuNo=30002
3. 위 둘 중 하나라도 접근 가능해지면, 전국 원본을 먼저 저장하고 고양·포항 등 지역 파생자료는 원본에서 필터링한 것으로 manifest에 남긴다.

## 5. 현재 판정

수집 후보는 유효하지만, 이번 smoke에서는 새 전국 원자료를 확보하지 못했다. 따라서 운수·창고업과 숙박·음식점업 route는 아직 미채택이며, 기존 고양·포항 LOCALDATA cache 또는 두 도시용 물류창고 자료를 전국 일반화 근거로 쓰면 안 된다.

