/* =========================================================
   TV1 WEEK 3 - SQL EDA & DATA QA
   Project: Retake Behavior & Recovery Analysis
   Owner: Trần Đại Hữu (TV1 / Team Leader)
   Source: dbo.v_attempts

   PURPOSE
   1) Validate the SQL dataset before Week 3 analysis.
   2) Reproduce the 12 required SQL analyses.
   3) Link each query to the project's Research Questions.
   4) Provide a stable SQL foundation for Python EDA and Week 4 modeling.

   VERIFIED REFERENCE VALUES (from master_sql_ready.csv)
   - Records: 120,421
   - Unique students: 15,235
   - Courses: 18
   - Semesters: 26 (SP2017 -> SU2025)
   - Student-Course trajectories: 101,965
   - >=2 attempts: 13,011
   - >=3 attempts: 3,372
   - >=4 attempts: 1,155

   RQ MAP
   - RQ1: score change after first failure; variation by course.
   - RQ2: factors associated with next-attempt pass.
   - RQ3: time-to-recovery / time gap.
   - RQ4: repeated attempt number and recovery / score improvement.

   IMPORTANT
   PASS/FAIL is determined from status_group, NOT total_score >= 5.
   EXEMPT is not a failure. REVIEW requires manual attention.
   ========================================================= */

/* =========================================================
   TV1 WEEK 2 - SQL QA & RETAKE ANALYSIS
   Source: dbo.v_attempts
   ========================================================= */

-- Query 1: Dataset overview
-- Role: DATA QA; supports all RQs by confirming the analysis base.
-- Expected: 120,421 records; 15,235 students; 18 courses; 26 semesters.
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students,
    COUNT(DISTINCT course_id) AS total_courses,
    COUNT(DISTINCT semester) AS total_semesters
FROM dbo.v_attempts;

-- Query 2: Records by semester
-- Role: DATA QA / temporal coverage; supports RQ3 and overall validity.
-- Read it as: how much data and how many students exist in each semester?
SELECT
    semester,
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students
FROM dbo.v_attempts
GROUP BY semester, semester_order
ORDER BY semester_order;

-- Query 3: Records by course
-- Role: COURSE-LEVEL EDA; supports RQ1/RQ2 comparisons by course.
-- Caution: average total_score is descriptive only; course grading structures may differ.
SELECT
    course_id,
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students,
    AVG(total_score) AS avg_total_score
FROM dbo.v_attempts
GROUP BY course_id
ORDER BY course_id;

-- Query 4: Retake trajectories + cumulative counts
-- Link: RQ4.
-- One trajectory = one Student + one Course across all observed semesters.
-- Expected: 101,965 total; 13,011 >=2; 3,372 >=3; 1,155 >=4 attempts.
WITH trajectory AS
(
    SELECT student_id, course_id, COUNT(*) AS attempt_count
    FROM dbo.v_attempts
    GROUP BY student_id, course_id
)
SELECT
    COUNT(*) AS total_trajectories,
    SUM(CASE WHEN attempt_count >= 2 THEN 1 ELSE 0 END) AS trajectories_ge_2,
    SUM(CASE WHEN attempt_count >= 3 THEN 1 ELSE 0 END) AS trajectories_ge_3,
    SUM(CASE WHEN attempt_count >= 4 THEN 1 ELSE 0 END) AS trajectories_ge_4
FROM trajectory;

-- Query 5: Exact attempt-count distribution
-- Link: RQ4.
-- Shows how many trajectories have exactly 1, 2, 3, ... attempts.
WITH trajectory AS
(
    SELECT student_id, course_id, COUNT(*) AS attempt_count
    FROM dbo.v_attempts
    GROUP BY student_id, course_id
)
SELECT attempt_count, COUNT(*) AS trajectories
FROM trajectory
GROUP BY attempt_count
ORDER BY attempt_count;

-- Query 6: First observed failure per Student-Course
-- Foundation for RQ1/RQ2/RQ3.
-- Failure statuses: FAIL_ACADEMIC, FAIL_ATTENDANCE, SUSPENDED.
-- ROW_NUMBER() ranks failure records chronologically inside each Student-Course.
WITH failures AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_order
    FROM dbo.v_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT *
FROM failures
WHERE failure_order = 1;

-- Query 7: First Failure -> Next Attempt
-- Core query for RQ1/RQ2/RQ3.
-- LEAD() is calculated BEFORE filtering failures, so it points to the true next observed attempt.
-- Outputs score_delta and time_gap for the first failure -> next attempt pair.
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(semester) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_semester,
        LEAD(semester_order) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_semester_order,
        LEAD(total_score) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_total_score,
        LEAD(status_group) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_status_group
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    student_id,
    course_id,
    semester AS first_failure_semester,
    total_score AS initial_failure_total,
    status_group AS initial_failure_type,
    next_semester,
    next_total_score,
    next_status_group,
    CASE
        WHEN total_score IS NOT NULL AND next_total_score IS NOT NULL
        THEN next_total_score - total_score
        ELSE NULL
    END AS score_delta,
    next_semester_order - semester_order AS time_gap
FROM first_failure
WHERE failure_rank = 1
  AND next_semester IS NOT NULL;

-- Query 8: Next-attempt recovery rate
-- Link: RQ2.
-- Recovery here = next observed status is PASS after the first observed failure.
-- Verified reference: 6,545 recovered among 12,058 first-failure cases with a next status (~54.28%).
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(status_group) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_status
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    COUNT(*) AS first_failures_with_next_attempt,
    SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END) AS recovered_next_attempt,
    100.0 * SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0) AS recovery_rate_percent
FROM first_failure
WHERE failure_rank = 1
  AND next_status IS NOT NULL;

-- Query 9: Average Score Delta
-- Link: RQ1.
-- Score Delta = next attempt score - initial failure score.
-- Verified reference: 10,786 complete score pairs; mean delta ~ +1.795.
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(total_score) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_total
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    COUNT(*) AS n_complete_score_pairs,
    AVG(next_total - total_score) AS avg_score_delta
FROM first_failure
WHERE failure_rank = 1
  AND total_score IS NOT NULL
  AND next_total IS NOT NULL;

-- Query 10: Recovery rate by course
-- Link: RQ1/RQ2.
-- Compare course-level recovery descriptively.
-- IMPORTANT: always read recovery_rate together with n_retakes; very small n is unstable.
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(status_group) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_status
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    course_id,
    COUNT(*) AS n_retakes,
    SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END) AS recovered,
    100.0 * SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0) AS recovery_rate
FROM first_failure
WHERE failure_rank = 1
  AND next_status IS NOT NULL
GROUP BY course_id
ORDER BY recovery_rate DESC;

-- Query 11: Time Gap vs Score Delta / Recovery
-- Link: RQ3.
-- Time Gap = next_semester_order - first_failure semester_order.
-- Interpret as ASSOCIATION only; do not claim that waiting longer/shorter causes recovery.
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(semester_order) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_semester_order,
        LEAD(total_score) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_total,
        LEAD(status_group) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_status
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    next_semester_order - semester_order AS time_gap,
    COUNT(*) AS n,
    AVG(CASE
        WHEN total_score IS NOT NULL AND next_total IS NOT NULL
        THEN next_total - total_score
    END) AS avg_score_delta,
    100.0 * SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0) AS recovery_rate
FROM first_failure
WHERE failure_rank = 1
  AND next_status IS NOT NULL
GROUP BY next_semester_order - semester_order
ORDER BY time_gap;

-- Query 12: Recovery by initial failure type
-- Link: RQ2.
-- Compares next-attempt recovery across FAIL_ACADEMIC, FAIL_ATTENDANCE and SUSPENDED.
-- Interpret descriptively; the groups may differ in composition and sample size.
WITH ordered_attempts AS
(
    SELECT *,
        LEAD(status_group) OVER
            (PARTITION BY student_id, course_id ORDER BY semester_order) AS next_status
    FROM dbo.v_attempts
),
first_failure AS
(
    SELECT *,
        ROW_NUMBER() OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS failure_rank
    FROM ordered_attempts
    WHERE status_group IN ('FAIL_ACADEMIC','FAIL_ATTENDANCE','SUSPENDED')
)
SELECT
    status_group AS failure_type,
    COUNT(*) AS n,
    SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END) AS recovered,
    100.0 * SUM(CASE WHEN next_status = 'PASS' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0) AS recovery_rate
FROM first_failure
WHERE failure_rank = 1
  AND next_status IS NOT NULL
GROUP BY status_group
ORDER BY failure_type;


/* =========================================================
   OPTIONAL WEEK 3 QA (not counted among the required 12)
   ========================================================= */

-- QA-A: Status-group distribution
SELECT status_group, COUNT(*) AS n
FROM dbo.v_attempts
GROUP BY status_group
ORDER BY n DESC;

-- QA-B: Missing total score count
SELECT
    COUNT(*) AS total_records,
    SUM(CASE WHEN total_score IS NULL THEN 1 ELSE 0 END) AS missing_total_score
FROM dbo.v_attempts;

-- QA-C: Review statuses requiring manual inspection
SELECT status_raw, COUNT(*) AS n
FROM dbo.v_attempts
WHERE status_group = 'REVIEW'
GROUP BY status_raw
ORDER BY n DESC;
