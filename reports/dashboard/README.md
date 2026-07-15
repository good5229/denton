# Dashboard

정적 HTML 대시보드다. 원천 CSV는 `data/processed/` 아래의 CP949 CSV를 직접 읽는다.

로컬 브라우저 보안 정책 때문에 파일을 더블클릭하면 CSV fetch가 막힐 수 있다. 대시보드를 업데이트한 뒤에는 이전 서버를 먼저 종료하고 새 서버를 띄운다.

```bash
python3 scripts/stop_dashboard_server.py 8000
```

저장소 루트에서 아래 명령으로 서버를 띄운 뒤 접속한다.

```bash
python3 -m http.server 8000
```

접속 URL:

```text
http://localhost:8000/reports/dashboard/
```

현재 표시 범위:

- 시도: 연도별 롤링 예측 vs 실제, 분기별 예측. 전국 분기는 경제활동별 GDP 실측치와 비교
- 시군구: 연도별 벤치마크 제약 진단, 분기별 추정값
- 읍면동: 2015 경제총조사 프록시로 시군구 분기 GVA를 하향 배분한 추정값

산업군 필터의 `전체`는 선택 지역과 기간 안에서 산업별 예측/실제 행을 합산한 비교 시계열이다. 읍면동 및 시군구 세부산업 대용량 CSV는 선택 시점에 지연 로딩한다. 서울 자치구 연간 총량은 `scripts/collect_seoul_district_grdp.py`로 `DT_201012_D040028`를 수집하면 `seoul_district_grdp_annual.csv`로 보강된다.

시군구 세부산업 필터는 KSIC 상세 수준을 `중분류`, `소분류`, `세분류` 그룹으로 나누어 표시한다.

서울 자치구 분기 추정치의 정합성은 `scripts/check_seoul_sigungu_consistency.py`로 확인한다. 이 스크립트는 25개 자치구 분기 추정 합계와 서울시 부모 분기 경로를 산업별·전체로 비교해 `seoul_sigungu_quarterly_consistency.csv`와 `seoul_sigungu_annual_consistency.csv`를 생성한다.

월간 예측값은 아직 생성하지 않았으므로 UI에서 안내 메시지만 표시한다.
