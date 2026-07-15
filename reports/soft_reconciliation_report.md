# Soft Reconciliation 비교

- 부모 총량 보정 후보: `parent_baseline`

## 방법별 성능

| method | WMAPE | MAPE | improvement % | degraded | material degraded | worst | oracle regret |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hard_reconciliation_best_parent | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| hard_reconciliation_forecast_parent | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| no_reconciliation | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| soft_reconciliation_global_025 | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| soft_reconciliation_global_050 | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| soft_reconciliation_global_075 | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |
| soft_reconciliation_uncertainty | 4.230372 | 6.702529 | 3.606707 | 28 | 21 | -62.748315 | 0.092152 |

## Parent Shock

| method | shock | WMAPE | MAPE | parent error | worst | degraded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hard_reconciliation | -0.1 | 10.177724 | 11.598615 | 9.257675 | -558.380236 | 69 |
| soft_reconciliation_global_050 | -0.1 | 6.151936 | 8.192574 | 4.216434 | -222.297884 | 58 |
| soft_reconciliation_global_025 | -0.1 | 4.730756 | 7.085566 | 1.695814 | -103.907729 | 49 |
| hard_reconciliation | -0.05 | 6.151936 | 8.192574 | 4.216434 | -222.297884 | 58 |
| soft_reconciliation_global_050 | -0.05 | 4.730756 | 7.085566 | 1.695814 | -103.907729 | 49 |
| soft_reconciliation_global_025 | -0.05 | 4.365151 | 6.789417 | 0.435504 | -48.96738 | 44 |
| hard_reconciliation | -0.03 | 4.967272 | 7.260277 | 2.199938 | -125.883869 | 51 |
| soft_reconciliation_global_050 | -0.03 | 4.424157 | 6.832505 | 0.687566 | -59.95545 | 46 |
| soft_reconciliation_global_025 | -0.03 | 4.276287 | 6.727907 | 0.06862 | -27.002173 | 40 |
| hard_reconciliation | -0.01 | 4.316793 | 6.75515 | 0.183442 | -37.979311 | 42 |
| soft_reconciliation_global_050 | -0.01 | 4.24622 | 6.709102 | 0.320682 | -16.396224 | 38 |
| soft_reconciliation_global_025 | -0.01 | 4.233977 | 6.701782 | 0.572744 | -13.998892 | 37 |
| hard_reconciliation | 0.0 | 4.230372 | 6.702529 | 0.824806 | -13.804916 | 28 |
| soft_reconciliation_global_050 | 0.0 | 4.230372 | 6.702529 | 0.824806 | -13.804916 | 28 |
| soft_reconciliation_global_025 | 0.0 | 4.230372 | 6.702529 | 0.824806 | -13.804916 | 28 |
| hard_reconciliation | 0.01 | 4.305144 | 6.80668 | 1.833054 | -19.67539 | 33 |
| soft_reconciliation_global_050 | 0.01 | 4.243256 | 6.73376 | 1.32893 | -15.300685 | 31 |
| soft_reconciliation_global_025 | 0.01 | 4.233732 | 6.714584 | 1.076868 | -14.067583 | 33 |
| hard_reconciliation | 0.03 | 5.112654 | 7.526045 | 3.84955 | -118.591621 | 50 |
| soft_reconciliation_global_050 | 0.03 | 4.421855 | 6.928043 | 2.337178 | -35.119107 | 39 |
| soft_reconciliation_global_025 | 0.03 | 4.26492 | 6.763238 | 1.580992 | -17.362616 | 32 |
| hard_reconciliation | 0.05 | 6.570884 | 8.741305 | 5.866046 | -251.873457 | 60 |
| soft_reconciliation_global_050 | 0.05 | 4.842815 | 7.294541 | 3.345426 | -85.961517 | 47 |
| soft_reconciliation_global_025 | 0.05 | 4.35819 | 6.861953 | 2.085116 | -24.952206 | 35 |
| hard_reconciliation | 0.1 | 11.183109 | 12.800512 | 10.907286 | -588.496609 | 74 |
| soft_reconciliation_global_050 | 0.1 | 6.570884 | 8.741305 | 5.866046 | -251.873457 | 60 |
| soft_reconciliation_global_025 | 0.1 | 4.842815 | 7.294541 | 3.345426 | -85.961517 | 47 |