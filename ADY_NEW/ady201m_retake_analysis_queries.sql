-- ============================================================================
-- ADY201m PROJECT: RETAKE BEHAVIOR & SCORE RECOVERY ANALYSIS
-- STEP 3: DATA ANALYSIS WITH SQL (SQLite3 Dialect)
-- Database: retake_analysis.db
-- Tables:
--   1. enrollments (123,696 clean student-course-attempt records across 18 courses)
--   2. retake_pairs (101,965 unique student-course pairs with Attempt 1 -> Attempt 2 & trajectory)
--   3. course_summary (18 course-level difficulty and baseline metrics)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 0: DATA QUALITY & FORENSIC AUDIT SUMMARY
-- Verifies total clean enrollments, unique students, and attempt distribution
-- ----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_clean_enrollments,
    COUNT(DISTINCT CODE) AS unique_students,
    COUNT(DISTINCT COURSE_ID) AS unique_courses,
    SUM(CASE WHEN ATTEMPT_NO = 1 THEN 1 ELSE 0 END) AS first_attempts,
    SUM(CASE WHEN ATTEMPT_NO >= 2 THEN 1 ELSE 0 END) AS retake_enrollments,
    MAX(ATTEMPT_NO) AS max_attempts_observed
FROM enrollments;

-- ----------------------------------------------------------------------------
-- QUERY 1 (RQ1): COURSE-LEVEL RETAKE BEHAVIOR, SCORE DELTA & RECOVERY RATE
-- Answers RQ1: How do retake rates, score changes (Score_Change = Total_2 - Total_1),
-- and pass recovery probabilities vary across the 18 IT courses?
-- ----------------------------------------------------------------------------
SELECT 
    COURSE_ID,
    COURSE_CODE,
    COURSE_NAME,
    COUNT(*) AS total_student_course_pairs,
    SUM(IS_FAIL) AS failed_att1_count,
    ROUND(100.0 * SUM(IS_FAIL) / COUNT(*), 2) AS fail_rate_att1_pct,
    SUM(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN 1 ELSE 0 END) AS mandatory_retakers,
    ROUND(100.0 * SUM(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN 1 ELSE 0 END) / NULLIF(SUM(IS_FAIL), 0), 2) AS retake_continuation_pct,
    ROUND(AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN TOTAL_1 END), 2) AS mean_total_att1,
    ROUND(AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN TOTAL_2 END), 2) AS mean_total_att2,
    ROUND(AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN SCORE_CHANGE_TOTAL END), 2) AS mean_score_delta,
    ROUND(100.0 * AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN PASS_RECOVERY_ATT2 END), 2) AS pass_recovery_att2_pct,
    ROUND(100.0 * AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN MEANINGFUL_RECOVERY_ATT2 END), 2) AS meaningful_recovery_pct,
    ROUND(100.0 * AVG(CASE WHEN IS_FAIL = 1 AND RETOOK = 1 THEN EVER_PASSED END), 2) AS ultimate_pass_recovery_pct
FROM retake_pairs
GROUP BY COURSE_ID, COURSE_CODE, COURSE_NAME
ORDER BY mandatory_retakers DESC;

-- ----------------------------------------------------------------------------
-- QUERY 2 (RQ2): THE LEVEL-VS-GAIN PARADOX BY FAILURE TYPE & INITIAL SCORE BAND
-- Answers RQ2: How do initial failure mechanism (Not Passed vs Attendance Fail
-- vs Is Suspended) and Attempt-1 score level relate to score gain vs pass recovery?
-- ----------------------------------------------------------------------------
SELECT 
    STATUS_CLEAN_1 AS att1_failure_status,
    CASE 
        WHEN TOTAL_1 IS NULL THEN '0. Missing Numeric Score (LAB211 Pass/Fail)'
        WHEN TOTAL_1 < 2.0 THEN '1. Very Low (< 2.0)'
        WHEN TOTAL_1 < 3.5 THEN '2. Low (2.0 - 3.49)'
        WHEN TOTAL_1 < 4.5 THEN '3. Near Threshold (3.5 - 4.49)'
        ELSE '4. Borderline Fail (>= 4.5, Exam Bottleneck)'
    END AS initial_score_band,
    COUNT(*) AS retake_pairs_n,
    ROUND(AVG(TOTAL_1), 2) AS mean_att1_score,
    ROUND(AVG(TOTAL_2), 2) AS mean_att2_score,
    ROUND(AVG(SCORE_CHANGE_TOTAL), 2) AS mean_score_delta,
    ROUND(100.0 * AVG(PASS_RECOVERY_ATT2), 2) AS pass_recovery_att2_pct,
    ROUND(100.0 * AVG(MEANINGFUL_RECOVERY_ATT2), 2) AS meaningful_recovery_pct,
    ROUND(100.0 * AVG(EVER_PASSED), 2) AS ultimate_pass_pct
FROM retake_pairs
WHERE IS_FAIL = 1 AND RETOOK = 1
GROUP BY STATUS_CLEAN_1, initial_score_band
ORDER BY STATUS_CLEAN_1, initial_score_band;

-- ----------------------------------------------------------------------------
-- QUERY 3 (RQ3): IMPACT OF RETAKE TIMING (SEMESTER GAP) ON SCORE RECOVERY
-- Answers RQ3: Does retaking immediately in the same semester (Block 2) or next
-- semester yield higher recovery probability than delayed retakes?
-- ----------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN SEM_GAP = 0 THEN '0. Same Semester (Immediate Block 2 Retake)'
        WHEN SEM_GAP = 1 THEN '1. Next Semester (1 Term Gap)'
        WHEN SEM_GAP = 2 THEN '2. Two Semesters (2 Terms Gap)'
        WHEN SEM_GAP BETWEEN 3 AND 4 THEN '3. One Year (3-4 Terms Gap)'
        ELSE '4. Delayed (>= 5 Terms Gap)'
    END AS retake_timing_window,
    COUNT(*) AS retake_pairs_n,
    ROUND(AVG(TOTAL_1), 2) AS mean_att1_score,
    ROUND(AVG(TOTAL_2), 2) AS mean_att2_score,
    ROUND(AVG(SCORE_CHANGE_TOTAL), 2) AS mean_score_delta,
    ROUND(100.0 * AVG(PASS_RECOVERY_ATT2), 2) AS pass_recovery_att2_pct,
    ROUND(100.0 * AVG(MEANINGFUL_RECOVERY_ATT2), 2) AS meaningful_recovery_pct,
    ROUND(100.0 * AVG(EVER_PASSED), 2) AS ultimate_pass_pct
FROM retake_pairs
WHERE IS_FAIL = 1 AND RETOOK = 1
GROUP BY retake_timing_window
ORDER BY retake_timing_window;

-- ----------------------------------------------------------------------------
-- QUERY 4 (RQ3 SURVIVAL): MULTI-ATTEMPT CONDITIONAL HAZARD & TRAJECTORY
-- Computes empirical conditional pass probability h(k) across attempt numbers 1..8
-- ----------------------------------------------------------------------------
SELECT 
    ATTEMPT_NO,
    COUNT(*) AS enrollments_at_risk,
    SUM(IS_PASS) AS passed_count,
    ROUND(100.0 * AVG(IS_PASS), 2) AS conditional_pass_hazard_pct,
    ROUND(AVG(TOTAL), 2) AS mean_total_score,
    ROUND(AVG(COURSEWORK_SCORE), 2) AS mean_coursework_score,
    ROUND(AVG(FINAL_EXAM), 2) AS mean_final_exam_score
FROM enrollments
WHERE ATTEMPT_NO <= 8
GROUP BY ATTEMPT_NO
ORDER BY ATTEMPT_NO;

-- ----------------------------------------------------------------------------
-- QUERY 5 (RQ4 - WEEK 6 EXTENDED RQ): COMPONENT BOTTLENECK vs COMPREHENSIVE DEFICIT
-- Distinguishes students who failed due to Final Exam bottleneck despite passing
-- coursework (Coursework >= 5.0) vs comprehensive failure vs attendance failure,
-- alongside voluntary grade-improvement retakers.
-- ----------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN IS_FAIL = 0 THEN '4. Voluntary Grade Improvement (Passed Att 1)'
        WHEN STATUS_CLEAN_1 = 'Attendance Fail' THEN '1. Attendance Disengagement (AF)'
        WHEN COURSEWORK_SCORE_1 >= 5.0 AND (FINAL_EXAM_1 < 4.0 OR TOTAL_1 >= 4.0) THEN '3. Final-Exam Bottleneck (Coursework >= 5.0)'
        ELSE '2. Comprehensive Academic Deficit (Coursework < 5.0)'
    END AS student_retake_profile,
    COUNT(*) AS n_retakers,
    ROUND(AVG(COURSEWORK_SCORE_1), 2) AS mean_coursework_att1,
    ROUND(AVG(FINAL_EXAM_1), 2) AS mean_final_exam_att1,
    ROUND(AVG(TOTAL_1), 2) AS mean_total_att1,
    ROUND(AVG(TOTAL_2), 2) AS mean_total_att2,
    ROUND(AVG(SCORE_CHANGE_TOTAL), 2) AS mean_score_delta,
    ROUND(100.0 * AVG(PASS_RECOVERY_ATT2), 2) AS pass_att2_pct,
    ROUND(100.0 * AVG(EVER_PASSED), 2) AS ultimate_pass_pct
FROM retake_pairs
WHERE RETOOK = 1 AND TOTAL_1 IS NOT NULL AND TOTAL_2 IS NOT NULL
GROUP BY student_retake_profile
ORDER BY student_retake_profile;