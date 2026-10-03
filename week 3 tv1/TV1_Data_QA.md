# TV1 Week 3 - Data QA Summary

**Project:** Retake Behavior & Recovery Analysis  
**Member:** Trần Đại Hữu (TV1 / Team Leader)  
**Data used:** `data_processed/master_sql_ready.csv` / SQL view `dbo.v_attempts`  
**Week 3 status:** TV1 data QA completed; dataset can be used for EDA and model preparation, subject to the cautions below.

## 1. Core dataset validation

| Check | Verified value | Status |
|---|---:|---|
| Total records | 120,421 | PASS |
| Unique students | 15,235 | PASS |
| Courses | 18 | PASS |
| Semesters | 26 (SP2017 to SU2025) | PASS |
| Student-Course trajectories | 101,965 | PASS |
| Trajectories with >=2 attempts | 13,011 | PASS |
| Trajectories with >=3 attempts | 3,372 | PASS |
| Trajectories with >=4 attempts | 1,155 | PASS |

**Conclusion:** repeated Student-Course observations are sufficiently present for the planned retake/recovery analyses, including exploratory repeated-attempt analysis for RQ4.

## 2. Attempt-count distribution

| Exact attempt count | Trajectories |
|---:|---:|
| 1 | 88,954 |
| 2 | 9,639 |
| 3 | 2,217 |
| 4 | 642 |
| 5 | 280 |
| 6 | 144 |
| 7 | 40 |
| 8 | 30 |
| 9 | 10 |
| 10 | 5 |
| 11 | 3 |
| 13 | 1 |


## 3. Status quality check

| Normalized status group | Records |
|---|---:|
| PASS | 89,347 |
| FAIL_ACADEMIC | 20,972 |
| FAIL_ATTENDANCE | 9,564 |
| SUSPENDED | 483 |
| EXEMPT | 54 |
| REVIEW | 1 |


- `PASS` is determined from `status_group`, **not** from `total_score >= 5`.
- `EXEMPT` is not treated as failure.
- `SUSPENDED` remains a separate failure-related group rather than being merged into academic failure.
- There is **1 REVIEW record** that should remain flagged for manual inspection.
- `total_score` is missing in **10,972 records**. Week 3 does not use mean/median imputation to rewrite the source data.

## 4. First-failure -> next-attempt validation

| Metric | Verified value |
|---|---:|
| First observed failures | 22,248 |
| First failures with a next observed attempt | 12,058 |
| Recovered on next observed attempt | 6,545 |
| Next-attempt recovery rate | 54.28% |
| Complete score pairs | 10,786 |
| Mean Score Delta | +1.795 points |

**Definition used:** Recovery at this step means the next observed attempt has `status_group = PASS` after the first observed failure. This is a descriptive outcome, not a causal claim.

## 5. Recovery by initial failure type

| Failure type | n | Recovered | Recovery rate |
|---|---:|---:|---:|
| FAIL_ACADEMIC | 9,141 | 5,227 | 57.18% |
| FAIL_ATTENDANCE | 2,672 | 1,145 | 42.85% |
| SUSPENDED | 245 | 173 | 70.61% |


## 6. Week 3 QA findings / cautions

1. **Course-level averages are not automatically comparable.** Some courses may encode `TOTAL` differently. For example, `LAB211` has an unusually low average `total_score`; this should be investigated before using raw course-average score as a cross-course quality judgment.
2. **Small-n course recovery rates are unstable.** Course-level recovery must always be shown together with `n_retakes`; avoid ranking courses based only on a percentage when the sample is small.
3. **Time Gap is observational.** A relationship between `time_gap` and recovery/Score Delta should be described as an association, not as a causal effect.
4. **Selection / survivorship matters for later attempts.** Students observed at attempt 3 or 4+ are selected from those who did not recover earlier, so RQ4 must not be interpreted as the causal effect of taking more attempts.
5. **Future-information leakage must be prevented in Week 4.** For predicting `score_delta`, do not use `next_attempt_total`, `next_status_group`, or any feature derived from information after the prediction point.

## 7. RQ mapping for SQL work

- **RQ1:** Queries 7, 9, 10 - first failure to next attempt, Score Delta, course comparison.
- **RQ2:** Queries 7, 8, 10, 12 - next-attempt PASS and associated observed factors.
- **RQ3:** Query 11 - Time Gap vs Score Delta / recovery; full time-to-recovery can be extended later.
- **RQ4:** Queries 4 and 5 - repeated-attempt feasibility and distribution; trajectory-level Python analysis follows.

## 8. TV1 handoff

- TV2 can use `clean_attempts_v1.csv` for EDA and visualization.
- TV3 can use `retake_pairs_v1.csv` for RQ1/RQ2 statistics and create `model_ready_v1.csv`.
- TV4 can use retake-pair summaries for RQ3/RQ4, proposal methodology, and dashboard planning.
- TV1 will keep this QA summary and `TV1_SQL_EDA.sql` as the Week 3 reproducibility record.
