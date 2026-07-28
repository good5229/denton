# Phase158 부동산중개업사무소 전국자료 확보 경로 점검

## 목적

Phase157에서 외부 10개 시군구의 공시가격·건축물대장·전월세 자료는 모두 결합됐지만, `682 부동산 관련 서비스업`을 설명하는 핵심 활동자료인 공인중개사무소 수가 빠져 있었다. 이번 단계는 무료 전국 중개업소 자료를 확보할 수 있는 경로와 현재 자동 수집 가능성을 점검한다.

## 확인한 무료 자료

| 구분 | 자료명 | 링크 | 범위 | 비용 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 파일데이터 | 국토교통부_부동산중개업사무소정보_20250826 | https://www.data.go.kr/data/15147784/fileData.do?recommendDataYn=Y | 대한민국, 2025년, CSV, 전체 110,545행 | 무료 | VWorld 다운로드 페이지 확인. 자동 다운로드는 현재 빈 응답/HTML로 실패 |
| OpenAPI LINK | 국토교통부_부동산중개업정보(WMS/WFS/속성정보) | https://www.data.go.kr/data/15123990/openapi.do | 대한민국 전체, 실시간, JSON/XML | 무료 | VWorld API/WFS/속성정보. `VWORLD_API_KEY` 필요 가능성이 높음 |
| VWorld API 목록 | 부동산중개업사무소정보조회 / 부동산중개업WFS조회 | https://www.vworld.kr/dtna/dtna_apiSvcList_s001.do?searchKeyword=%EB%B6%80%EB%8F%99%EC%82%B0%EC%A4%91%EA%B0%9C%EC%97%85 | 기준일 2026-07-13 | 무료 | 인증키 발급 후 수집 후보 |

## 로컬 자동 다운로드 시도

| 시도 | 요청 | 결과 | 해석 |
| --- | --- | --- | --- |
| 파일 상세 페이지 | `https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?dsId=11&svcCde=NA` | HTML 저장 성공 | 페이지 내 CSV 다운로드 버튼과 파일번호 확인 |
| 직접 파일 다운로드 | `/dtmk/downloadResourceFile.do?ds_id=20171128DS00161&fileNo=35` | 0 byte | 단순 HTTP 다운로드 불가 |
| 쿠키 유지 재시도 | 동일 URL + 세션 쿠키 | 0 byte | 쿠키만으로 불가 |
| 선택다운로드 엔드포인트 | `/dtmk/downloadDtnaResourceFile.do?ds_file_sq=35` | HTML 반환 | 다운로드 솔루션/브라우저 흐름 필요 |

## 현재 판단

1. 자료 자체는 무료이고 전국 범위다.
2. 파일데이터는 수동 브라우저 다운로드가 가장 빠른 경로일 수 있다.
3. 자동화하려면 VWorld OpenAPI 인증키를 발급받아 `부동산중개업사무소정보조회` 또는 WFS 조회를 쓰는 경로가 더 안정적이다.
4. `VWORLD_API_KEY`는 현재 `.env`에서 확인되지 않았다.

## 사용자에게 필요한 조치

가능하면 VWorld 인증키를 발급받아 `.env`에 아래 중 하나로 저장해 주면 된다.

```text
VWORLD_API_KEY=...
```

권장 신청 항목:

- VWorld 오픈API 인증키
- 활용 API: `WFS API`, `국가중점데이터API`, 가능하면 `2D데이터 API`
- 서비스 URL/domain: 로컬 실행용이면 `http://localhost` 또는 실제 사용할 도메인

대체 경로:

- VWorld 파일데이터 페이지에서 `부동산중개업사무소정보` CSV를 브라우저로 직접 다운로드
- 저장 위치: `data/raw/phase158_broker_vworld/vworld_realestate_broker_office_20260723.csv`

## Phase157 반영 계획

중개업소 전국자료가 확보되면 다음을 수행한다.

1. 외부 10개 시군구별 중개업소 수 집계
2. `공시가격/중개업소`, `전월세 계약/중개업소`, `전월세 보증금/중개업소` 생성
3. 고양·포항에서 사용한 보수적인 681/682 분리식이 외부 10개 지역에서 비정상 값을 내지 않는지 재감사
4. 소분류 actual이 확보되지 않는 한 외부 오차율 주장은 하지 않고, 자료 일반화 가능성과 구조 일관성만 보고
