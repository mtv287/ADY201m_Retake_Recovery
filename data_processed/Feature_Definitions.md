# Feature Definitions - TV3

## Unit of analysis

One row represents:

**First observed failure -> next observed attempt**

for one Student-Course trajectory.

| Feature | Definition |
|---|---|
| `student_id` | Student identifier |
| `course_id` | Decoded FPT course code (e.g., ADY201M, CSD201, DBI202) |
| `failure_semester` | Semester of first observed failure |
| `failure_semester_order` | Numeric chronological order of failure semester |
| `failure_attempt_no` | Attempt number of first observed failure |
| `initial_failure_total` | Total score at first observed failure |
| `initial_failure_type` | Failure type: academic, attendance, or suspended |
| `next_semester` | Semester of next observed attempt |
| `next_semester_order` | Numeric order of next semester |
| `next_attempt_no` | Attempt number of next observed attempt |
| `next_attempt_total` | Total score of next observed attempt |
| `next_status_group` | Outcome status of next observed attempt |
| `score_delta` | Next_Attempt_Total - Initial_Failure_Total |
| `pass_next_attempt` | 1 = PASS; 0 = observed failure/suspended; missing = exempt/review |
| `time_gap` | Next_Semester_Order - Failure_Semester_Order |
| `prior_attempt_count` | Number of attempts before first observed failure |
| `complete_score_pair` | True when both failure and next scores are available |

## Important rules

- Pass/Fail is determined from `status_group`, not from `total_score >= 5`.
- `EXEMPT` is not considered a failure.
- `REVIEW` is not automatically classified.
- Missing total scores are not imputed.
- Score Delta is only valid when both scores are available.

## Leakage warning

Do NOT use the following variables as predictors for next-attempt recovery:

- `next_attempt_total`
- `next_status_group`
- `score_delta`
- `pass_next_attempt`
- total number of future attempts in the full trajectory

They contain future information.