# Model Data Report (TV3)

### Dataset Specification
*   **Source Dataset**: `data_processed/retake_pairs_v1.csv`
*   **Rows**: 12,058
*   **Target Variable**: `score_delta`
*   **Predictors**: `initial_score`, `initial_failure_type`, `time_gap`, `prior_attempt_count`, `course_id`.

### Preprocessing & Leakage Exclusions
*   **Data Leakage Exclusions**: `next_attempt_total`, `next_status_group`, `pass_next_attempt`, `score_delta` (as input), `future total attempt count`.
*   **Train/Test Grouping Rule**: `GroupShuffleSplit` or `GroupKFold` applied on `student_id`.