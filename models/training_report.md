# Downscaling Model -- Training Report

Train period: 2025-01-01 to 2025-10-31  |  Test period: 2025-11-01 to 2025-12-31

## rainfall
- Grid column: `grid_rainfall_mm`  |  GP column: `gp_rainfall_mm`
- Overall test MAE/RMSE -- delta: 1.793 / 1.861
- Overall test MAE/RMSE -- random forest: 0.225 / 0.472
- **Best method: random_forest**

| gram_panchayat   |   delta_mae |   delta_rmse |   rf_mae |   rf_rmse |
|:-----------------|------------:|-------------:|---------:|----------:|
| Bethupalli       |    1.74631  |     1.79339  | 0.259877 |  0.454096 |
| Buggapadu        |    1.86738  |     1.90135  | 0.191541 |  0.391397 |
| Cherukupalli     |    1.93148  |     1.97854  | 0.206295 |  0.473491 |
| Gangaram         |    1.74631  |     1.79339  | 0.263402 |  0.454707 |
| Gowrigudem       |    1.81725  |     1.87516  | 0.22427  |  0.505619 |
| Kakarlapalli     |    1.93148  |     1.97854  | 0.206746 |  0.474303 |
| Kistapuram       |    1.72707  |     1.80708  | 0.317115 |  0.580156 |
| Kistaram         |    1.81725  |     1.87516  | 0.223434 |  0.50286  |
| Kothuru          |    0.751861 |     0.873513 | 0.265074 |  0.46715  |
| Narayanapuram    |    1.81725  |     1.87516  | 0.225795 |  0.50304  |
| Pakalagudem      |    1.74631  |     1.79339  | 0.263492 |  0.454723 |
| Ramagovindapuram |    1.74631  |     1.79339  | 0.262344 |  0.454612 |
| Ramanagaram      |    1.86738  |     1.90135  | 0.190885 |  0.38984  |
| Regallapadu      |    2.10431  |     2.11775  | 0.101123 |  0.300962 |
| Rejerla          |    1.81725  |     1.87516  | 0.224746 |  0.507218 |
| Rudrakshapalli   |    1.93148  |     1.97854  | 0.206746 |  0.474303 |
| Sadasivunipalem  |    1.81725  |     1.87516  | 0.232787 |  0.511176 |
| Siddaram         |    1.81725  |     1.87516  | 0.224139 |  0.505181 |
| Thallamada       |    1.81725  |     1.87516  | 0.224574 |  0.506636 |
| Thumburu         |    1.72707  |     1.80708  | 0.317115 |  0.580156 |
| Yatalakunta      |    2.10431  |     2.11775  | 0.101123 |  0.300962 |
