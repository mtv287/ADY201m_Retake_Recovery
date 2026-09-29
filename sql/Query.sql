/* =========================================================
   TV1 WEEK 2 - SQL QA & RETAKE ANALYSIS
   Source: dbo.v_attempts
   ========================================================= */

-- Query 1: Dataset overview
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students,
    COUNT(DISTINCT course_id) AS total_courses,
    COUNT(DISTINCT semester) AS total_semesters
FROM dbo.v_attempts;

-- Query 2: Records by semester
SELECT
    semester,
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students
FROM dbo.v_attempts
GROUP BY semester, semester_order
ORDER BY semester_order;

-- Query 3: Records by course
SELECT
    course_id,
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students,
    AVG(total_score) AS avg_total_score
FROM dbo.v_attempts
GROUP BY course_id
ORDER BY course_id;

-- Query 4: Retake trajectories + cumulative counts
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
