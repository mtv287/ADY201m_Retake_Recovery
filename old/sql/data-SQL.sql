USE ADY201m_Project;
GO

/*
TV1/TV2 SQL setup.
Assumption: master_sql_ready.csv has already been imported into dbo.master_sql_ready.
The import wizard may store columns as VARCHAR; this view converts them safely.
*/

CREATE OR ALTER VIEW dbo.v_attempts
AS
SELECT
    LTRIM(RTRIM(course_id)) AS course_id,
    LTRIM(RTRIM(source_file)) AS source_file,
    TRY_CONVERT(INT, source_row) AS source_row,
    LTRIM(RTRIM(semester)) AS semester,
    LTRIM(RTRIM(class_id)) AS class_id,
    TRY_CONVERT(INT, source_no) AS source_no,
    LTRIM(RTRIM(student_id)) AS student_id,
    TRY_CONVERT(DECIMAL(5,2), NULLIF(LTRIM(RTRIM(total_score)), '')) AS total_score,
    LTRIM(RTRIM(status_raw)) AS status_raw,
    TRY_CONVERT(INT, semester_order) AS semester_order,
    TRY_CONVERT(INT, duplicate_count) AS duplicate_count,
    CASE
        WHEN LOWER(LTRIM(RTRIM(is_duplicate_candidate))) IN ('true','1','yes') THEN 1
        WHEN LOWER(LTRIM(RTRIM(is_duplicate_candidate))) IN ('false','0','no') THEN 0
        ELSE NULL
    END AS is_duplicate_candidate,
    TRY_CONVERT(INT, attempt_no) AS attempt_no,

    CASE
        WHEN LTRIM(RTRIM(status_raw)) IN ('Passed','Pass','Passe') THEN 'Passed'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Not Passed','Not Passe') THEN 'Not Passed'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Attendance Fail','Attendance Fai') THEN 'Attendance Fail'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Is Susspended','Is Susspende','Is Suspended') THEN 'Is Suspended'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Is Exempt','Is exempt') THEN 'Is Exempt'
        ELSE 'REVIEW_STATUS'
    END AS status_clean,

    CASE
        WHEN LTRIM(RTRIM(status_raw)) IN ('Passed','Pass','Passe') THEN 'PASS'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Not Passed','Not Passe') THEN 'FAIL_ACADEMIC'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Attendance Fail','Attendance Fai') THEN 'FAIL_ATTENDANCE'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Is Susspended','Is Susspende','Is Suspended') THEN 'SUSPENDED'
        WHEN LTRIM(RTRIM(status_raw)) IN ('Is Exempt','Is exempt') THEN 'EXEMPT'
        ELSE 'REVIEW'
    END AS status_group
FROM dbo.master_sql_ready;
GO

-- Basic QA after view creation
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT student_id) AS unique_students,
    COUNT(DISTINCT course_id) AS total_courses,
    COUNT(DISTINCT semester) AS total_semesters
FROM dbo.v_attempts;
GO
