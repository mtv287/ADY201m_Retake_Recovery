/* =========================================================
   TV1 WEEK 2 - SQL QA & RETAKE ANALYSIS

   Nguồn dữ liệu:
   dbo.v_attempts

   Mục tiêu chung:
   1. Kiểm tra dataset
   2. Xác định sinh viên có học lại
   3. Tìm lần thất bại đầu tiên
   4. Ghép với lần học tiếp theo
   5. Tính Recovery Rate, Score Delta, Time Gap
   ========================================================= */


/* =========================================================
   QUERY 1 - DATASET OVERVIEW
   =========================================================

   MỤC ĐÍCH:
   Xem dataset hiện tại có bao nhiêu:
   - records
   - sinh viên
   - môn học
   - học kỳ

   Đây là query QA cơ bản nhất.
   Dùng để kiểm tra xem dữ liệu import SQL có đầy đủ không.
   ========================================================= */

SELECT

    -- COUNT(*) đếm toàn bộ số dòng trong dataset
    COUNT(*) AS total_records,

    -- DISTINCT giúp mỗi student_id chỉ được đếm 1 lần
    COUNT(DISTINCT student_id) AS unique_students,

    -- Đếm số môn học khác nhau
    COUNT(DISTINCT course_id) AS total_courses,

    -- Đếm số học kỳ khác nhau
    COUNT(DISTINCT semester) AS total_semesters

FROM dbo.v_attempts;


/* Kết quả kỳ vọng của dataset hiện tại:

   total_records     ≈ 120421
   unique_students   ≈ 15235
   total_courses     = 18
   total_semesters   = 26
*/


/* =========================================================
   QUERY 2 - RECORDS BY SEMESTER
   =========================================================

   MỤC ĐÍCH:
   Xem mỗi học kỳ có:
   - bao nhiêu records
   - bao nhiêu sinh viên

   Query này giúp:
   - kiểm tra coverage dữ liệu theo thời gian
   - phát hiện học kỳ quá ít hoặc quá nhiều dữ liệu
   - xem dataset trải dài qua những semester nào
   ========================================================= */

SELECT

    -- Ví dụ: SP2023, SU2023, FA2023
    semester,

    -- Tổng số record xuất hiện trong học kỳ đó
    COUNT(*) AS total_records,

    -- Số sinh viên khác nhau trong học kỳ đó
    COUNT(DISTINCT student_id) AS unique_students

FROM dbo.v_attempts

/* GROUP BY:
   gom tất cả record của cùng một semester lại thành một nhóm.

   semester_order cũng được đưa vào GROUP BY
   để có thể ORDER BY theo đúng thứ tự thời gian.
*/
GROUP BY
    semester,
    semester_order

-- Hiển thị từ học kỳ cũ → mới
ORDER BY semester_order;


/* =========================================================
   QUERY 3 - RECORDS BY COURSE
   =========================================================

   MỤC ĐÍCH:
   Thống kê dữ liệu theo từng môn học.

   Với mỗi course, xem:
   - số records
   - số sinh viên
   - điểm trung bình

   Có thể dùng để so sánh sơ bộ giữa 18 môn.
   ========================================================= */

SELECT

    -- Mã môn như CSD201, DBI202, PRF192...
    course_id,

    -- Tổng số record của môn đó
    COUNT(*) AS total_records,

    -- Số sinh viên khác nhau đã học môn đó
    COUNT(DISTINCT student_id) AS unique_students,

    /* AVG:
       tính điểm TOTAL trung bình của môn.

       SQL tự bỏ qua NULL khi tính AVG.
    */
    AVG(total_score) AS avg_total_score

FROM dbo.v_attempts

-- Mỗi course tạo thành một nhóm
GROUP BY course_id

-- Sắp theo mã môn
ORDER BY course_id;


/* =========================================================
   QUERY 4 - RETAKE TRAJECTORIES
   =========================================================

   MỤC ĐÍCH:
   Kiểm tra có bao nhiêu Student-Course trajectory
   có từ 2, 3, 4 attempts trở lên.

   TRAJECTORY là gì?

   Một trajectory =
   lịch sử của 1 sinh viên trong 1 môn.

   Ví dụ:

   Student A + CSD201

   SP2023   Not Passed
   FA2023   Not Passed
   SP2024   Passed

   => Đây là 1 trajectory có 3 attempts.
   ========================================================= */


/* WITH ... AS tạo một CTE.

   Có thể hiểu trajectory giống như
   một bảng tạm chỉ tồn tại trong query này.
*/
WITH trajectory AS
(
    SELECT

        student_id,
        course_id,

        /* COUNT(*) ở đây đếm số lần xuất hiện
           của cùng Student + Course.

           Nếu xuất hiện 3 lần:
           attempt_count = 3
        */
        COUNT(*) AS attempt_count

    FROM dbo.v_attempts

    /* Gom theo:
       1 sinh viên
       +
       1 môn
    */
    GROUP BY
        student_id,
        course_id
)

SELECT

    /* Sau CTE, mỗi dòng = 1 trajectory.

       COUNT(*) ở đây vì vậy là:
       tổng số Student-Course trajectories.
    */
    COUNT(*) AS total_trajectories,


    /* CASE:

       nếu attempt_count >= 2
       → trả về 1

       nếu không
       → trả 0

       SUM tất cả lại
       → số trajectory có >=2 attempts.
    */
    SUM(
        CASE
            WHEN attempt_count >= 2 THEN 1
            ELSE 0
        END
    ) AS trajectories_ge_2,


    -- Số trajectory có ít nhất 3 attempts
    SUM(
        CASE
            WHEN attempt_count >= 3 THEN 1
            ELSE 0
        END
    ) AS trajectories_ge_3,


    -- Số trajectory có ít nhất 4 attempts
    SUM(
        CASE
            WHEN attempt_count >= 4 THEN 1
            ELSE 0
        END
    ) AS trajectories_ge_4

FROM trajectory;


/* Dataset hiện tại kỳ vọng khoảng:

   total trajectories = 101965
   >= 2 attempts      = 13011
   >= 3 attempts      = 3372
   >= 4 attempts      = 1155

   Ý nghĩa:
   Dataset có đủ repeated attempts
   để nghiên cứu retake behavior.
*/


/* =========================================================
   QUERY 5 - EXACT ATTEMPT COUNT DISTRIBUTION
   =========================================================

   MỤC ĐÍCH:
   Query 4 chỉ nói >=2, >=3, >=4.

   Query 5 trả lời chi tiết hơn:

   Có bao nhiêu trajectory:
   - đúng 1 attempt?
   - đúng 2 attempts?
   - đúng 3 attempts?
   - đúng 4 attempts?
   ...

   Đây là phân bố số lần học.
   ========================================================= */

WITH trajectory AS
(
    SELECT

        student_id,
        course_id,

        -- Số lần sinh viên xuất hiện trong cùng course
        COUNT(*) AS attempt_count

    FROM dbo.v_attempts

    GROUP BY
        student_id,
        course_id
)

SELECT

    -- Ví dụ: 1, 2, 3, 4...
    attempt_count,

    /* Mỗi dòng trong CTE trajectory
       là một Student-Course.

       COUNT(*) ở đây đếm xem có bao nhiêu
       trajectory có đúng số attempt đó.
    */
    COUNT(*) AS trajectories

FROM trajectory

GROUP BY attempt_count

-- Hiển thị từ ít attempt → nhiều attempt
ORDER BY attempt_count;


/* Ví dụ output:

   attempt_count | trajectories
   --------------|-------------
   1             | 88954
   2             | ...
   3             | ...
   4             | ...

   Không đọc số trên làm kết quả thật,
   chỉ là ví dụ cách hiểu.
*/


/* =========================================================
   QUERY 6 - FIRST OBSERVED FAILURE
   =========================================================

   MỤC ĐÍCH:
   Tìm lần thất bại đầu tiên
   của mỗi sinh viên trong mỗi môn.

   Failure hiện gồm:

   FAIL_ACADEMIC
   FAIL_ATTENDANCE
   SUSPENDED

   EXEMPT không được xem là failure.
   PASS cũng không phải failure.
   ========================================================= */

WITH failures AS
(
    SELECT

        -- Lấy toàn bộ cột của v_attempts
        *,

        /* ROW_NUMBER():

           đánh số từng failure theo thứ tự thời gian.

           PARTITION BY student_id, course_id
           nghĩa là bắt đầu đánh số lại
           cho từng sinh viên trong từng môn.

           Ví dụ:

           Student A + CSD201

           SP2023 fail → 1
           FA2023 fail → 2
           SP2024 pass → không nằm trong CTE vì đã filter

        */
        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_order

    FROM dbo.v_attempts

    /* Chỉ giữ các record được xem
       là failure-related status.
    */
    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT *

FROM failures

/* failure_order = 1
   nghĩa là chỉ lấy failure đầu tiên.
*/
WHERE failure_order = 1;


/* =========================================================
   QUERY 7 - FIRST FAILURE → NEXT ATTEMPT
   =========================================================

   Đây là một trong những query QUAN TRỌNG NHẤT.

   MỤC ĐÍCH:

   Với mỗi Student-Course:

   1. tìm first failure
   2. tìm attempt ngay sau đó
   3. lấy:
      - next score
      - next status
      - Score Delta
      - Time Gap

   Ví dụ:

   SP2023
   score = 3.5
   FAIL
       ↓
   FA2023
   score = 6.2
   PASS

   Score Delta = 6.2 - 3.5 = +2.7
   ========================================================= */


/* ---------------------------------------------------------
   CTE 1: ordered_attempts

   Chưa lọc failure.

   Phải lấy toàn bộ attempts trước
   để LEAD() có thể nhìn đúng attempt kế tiếp.
   --------------------------------------------------------- */
WITH ordered_attempts AS
(
    SELECT

        *,

        /* LEAD(column):

           lấy giá trị của dòng KẾ TIẾP
           trong cùng Student-Course.

           PARTITION BY:
           không được nhảy sang sinh viên/môn khác.

           ORDER BY semester_order:
           đảm bảo "dòng kế tiếp" là attempt tiếp theo theo thời gian.
        */

        -- Học kỳ tiếp theo
        LEAD(semester) OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS next_semester,


        -- semester_order của lần tiếp theo
        LEAD(semester_order) OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS next_semester_order,


        -- Điểm của lần tiếp theo
        LEAD(total_score) OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS next_total_score,


        -- STATUS của lần tiếp theo
        LEAD(status_group) OVER
        (
            PARTITION BY student_id, course_id
            ORDER BY semester_order
        ) AS next_status_group

    FROM dbo.v_attempts
),


/* ---------------------------------------------------------
   CTE 2: first_failure

   Sau khi đã biết attempt tiếp theo,
   mới lọc các record failure.

   ROW_NUMBER giúp xác định
   failure nào là failure đầu tiên.
   --------------------------------------------------------- */
first_failure AS
(
    SELECT

        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    student_id,

    course_id,


    /* semester hiện tại chính là semester
       của first failure.
    */
    semester AS first_failure_semester,


    -- Điểm của lần failure đầu tiên
    total_score AS initial_failure_total,


    -- Failure do học thuật / attendance / suspended
    status_group AS initial_failure_type,


    -- Học kỳ attempt tiếp theo
    next_semester,


    -- Điểm attempt tiếp theo
    next_total_score,


    -- STATUS attempt tiếp theo
    next_status_group,


    /* -----------------------------------------------------
       SCORE DELTA

       = điểm lần tiếp theo
         -
         điểm failure đầu tiên

       Ví dụ:

       6.2 - 3.5 = +2.7

       Positive → cải thiện
       0        → không đổi
       Negative → giảm điểm

       Nếu một trong hai điểm bị NULL
       thì trả NULL.
       ----------------------------------------------------- */
    CASE

        WHEN total_score IS NOT NULL
         AND next_total_score IS NOT NULL

        THEN next_total_score - total_score

        ELSE NULL

    END AS score_delta,


    /* -----------------------------------------------------
       TIME GAP

       = semester_order của lần tiếp
         -
         semester_order failure

       Ví dụ:

       SP2023 → FA2023
       có thể có Time Gap = 2
       theo hệ thống semester_order của nhóm.
       ----------------------------------------------------- */
    next_semester_order - semester_order AS time_gap

FROM first_failure

WHERE

    /* Chỉ lấy failure đầu tiên */
    failure_rank = 1

    /* Và bắt buộc phải có attempt tiếp theo.
       Nếu không có next attempt thì chưa thể
       phân tích recovery ở bước này.
    */
    AND next_semester IS NOT NULL;


/* =========================================================
   QUERY 8 - NEXT-ATTEMPT RECOVERY RATE
   =========================================================

   MỤC ĐÍCH:

   Sau first failure,
   bao nhiêu sinh viên PASS ngay
   ở attempt được quan sát tiếp theo?

   Công thức:

   Recovery Rate
   =
   Number of Next PASS
   --------------------
   First failures with next attempt
   × 100%
   ========================================================= */

WITH ordered_attempts AS
(
    SELECT

        *,

        /* Chỉ cần lấy status của attempt kế tiếp */
        LEAD(status_group) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_status

    FROM dbo.v_attempts
),

first_failure AS
(
    SELECT

        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    /* Tổng số first failure
       có next_status quan sát được */
    COUNT(*) AS first_failures_with_next_attempt,


    /* Nếu next_status = PASS
       thì đếm 1.

       SUM lại = số người recovery.
    */
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    ) AS recovered_next_attempt,


    /* -----------------------------------------------------
       Tính tỷ lệ recovery %

       100.0 giúp SQL tính dạng decimal
       thay vì integer.

       NULLIF(COUNT(*),0):

       nếu COUNT(*) = 0
       thì biến thành NULL
       để tránh lỗi chia cho 0.
       ----------------------------------------------------- */
    100.0
    *
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    )
    /
    NULLIF(COUNT(*), 0)

    AS recovery_rate_percent

FROM first_failure

WHERE

    failure_rank = 1

    -- Chỉ phân tích khi có next observed status
    AND next_status IS NOT NULL;


/* LƯU Ý:

   Query hiện tại coi mọi next_status khác PASS
   là "không recovery" trong mẫu có next_status.

   Nếu sau này muốn loại EXEMPT / REVIEW khỏi denominator,
   cần thêm điều kiện riêng.
*/


/* =========================================================
   QUERY 9 - AVERAGE SCORE DELTA
   =========================================================

   MỤC ĐÍCH:

   Trả lời phần quan trọng của RQ1:

   Sau first failure,
   điểm của sinh viên trung bình
   tăng/giảm bao nhiêu ở attempt tiếp theo?
   ========================================================= */

WITH ordered_attempts AS
(
    SELECT

        *,

        /* Lấy total_score của attempt tiếp theo */
        LEAD(total_score) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_total

    FROM dbo.v_attempts
),

first_failure AS
(
    SELECT

        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    /* Đếm số cặp có đủ cả 2 score */
    COUNT(*) AS n_complete_score_pairs,


    /* Điểm cải thiện trung bình:

       AVG(
           next score
           -
           failure score
       )
    */
    AVG
    (
        next_total - total_score
    ) AS avg_score_delta

FROM first_failure

WHERE

    -- Chỉ lấy lần failure đầu tiên
    failure_rank = 1

    /* Bắt buộc cả 2 score phải có dữ liệu */
    AND total_score IS NOT NULL
    AND next_total IS NOT NULL;


/* Cách hiểu:

   avg_score_delta > 0
   → trung bình điểm tăng

   avg_score_delta = 0
   → trung bình không thay đổi

   avg_score_delta < 0
   → trung bình điểm giảm
*/


/* =========================================================
   QUERY 10 - RECOVERY RATE BY COURSE
   =========================================================

   MỤC ĐÍCH:

   Query 8 cho recovery chung toàn dataset.

   Query 10 chia recovery theo từng môn.

   Ví dụ:

   CSD201   72%
   DBI202   65%
   PRF192   80%

   Mục tiêu:
   kiểm tra recovery pattern
   có khác nhau giữa các course hay không.
   ========================================================= */

WITH ordered_attempts AS
(
    SELECT

        *,

        LEAD(status_group) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_status

    FROM dbo.v_attempts
),

first_failure AS
(
    SELECT

        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    -- Mã môn
    course_id,


    /* Số first failures có next attempt
       trong course đó */
    COUNT(*) AS n_retakes,


    /* Số trường hợp next attempt = PASS */
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    ) AS recovered,


    -- Recovery rate của course
    100.0
    *
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    )
    /
    NULLIF(COUNT(*), 0)

    AS recovery_rate

FROM first_failure

WHERE

    failure_rank = 1

    -- Phải có next status
    AND next_status IS NOT NULL

/* Tính riêng cho từng course */
GROUP BY course_id

/* Course có recovery rate cao
   được hiển thị trước.
*/
ORDER BY recovery_rate DESC;


/* QUAN TRỌNG:

   Recovery Rate cao hơn không có nghĩa
   môn đó "dễ hơn".

   Đây chỉ là mô tả association/pattern
   trong dataset.
*/


/* =========================================================
   QUERY 11 - TIME GAP VS SCORE DELTA / RECOVERY
   =========================================================

   MỤC ĐÍCH:

   Xem khoảng cách thời gian giữa:

   First Failure
        ↓
   Next Attempt

   có liên quan như thế nào với:

   1. Score Delta
   2. Recovery Rate

   Ví dụ:

   Time Gap = 1
   Time Gap = 2
   Time Gap = 3
   ...

   rồi so sánh recovery.
   ========================================================= */

WITH ordered_attempts AS
(
    SELECT

        *,

        /* semester_order của attempt kế tiếp */
        LEAD(semester_order) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_semester_order,


        -- Điểm lần tiếp theo
        LEAD(total_score) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_total,


        -- STATUS lần tiếp theo
        LEAD(status_group) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_status

    FROM dbo.v_attempts
),

first_failure AS
(
    SELECT

        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    /* Time Gap:

       thứ tự học kỳ tiếp theo
       -
       thứ tự học kỳ failure
    */
    next_semester_order - semester_order
        AS time_gap,


    -- Số case trong mỗi Time Gap
    COUNT(*) AS n,


    /* Điểm thay đổi trung bình
       của từng nhóm Time Gap.
    */
    AVG
    (
        CASE

            WHEN total_score IS NOT NULL
             AND next_total IS NOT NULL

            THEN next_total - total_score

        END

    ) AS avg_score_delta,


    /* Recovery rate của từng nhóm Time Gap */
    100.0
    *
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    )
    /
    NULLIF(COUNT(*), 0)

    AS recovery_rate

FROM first_failure

WHERE

    -- First observed failure
    failure_rank = 1

    -- Phải có next attempt status
    AND next_status IS NOT NULL

/* Gom các sinh viên có cùng Time Gap */
GROUP BY
    next_semester_order - semester_order

-- Gap nhỏ → lớn
ORDER BY time_gap;


/* Ví dụ cách đọc:

   time_gap | n    | avg_score_delta | recovery_rate
   ---------|------|-----------------|--------------
   1        | ...  | +2.1            | 75%
   2        | ...  | +1.8            | 68%
   3        | ...  | +1.2            | 60%

   Nếu thấy pattern như vậy,
   chỉ nên nói:

   "Time Gap is associated with recovery."

   Không nên kết luận:

   "Time Gap causes lower recovery."

   vì dữ liệu observational chưa chứng minh nhân quả.
*/


/* =========================================================
   QUERY 12 - RECOVERY BY INITIAL FAILURE TYPE
   =========================================================

   MỤC ĐÍCH:

   So sánh recovery giữa các loại
   first failure:

   FAIL_ACADEMIC
   FAIL_ATTENDANCE
   SUSPENDED

   Ví dụ câu hỏi:

   Sinh viên fail vì học thuật
   có recovery giống sinh viên
   Attendance Fail hay không?
   ========================================================= */

WITH ordered_attempts AS
(
    SELECT

        *,

        /* Chúng ta chỉ cần biết
           status của attempt kế tiếp */
        LEAD(status_group) OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS next_status

    FROM dbo.v_attempts
),

first_failure AS
(
    SELECT

        *,

        /* Đánh số các failure
           của cùng Student-Course */
        ROW_NUMBER() OVER
        (
            PARTITION BY
                student_id,
                course_id

            ORDER BY semester_order

        ) AS failure_rank

    FROM ordered_attempts

    WHERE status_group IN
    (
        'FAIL_ACADEMIC',
        'FAIL_ATTENDANCE',
        'SUSPENDED'
    )
)

SELECT

    /* STATUS của first failure
       được đổi tên thành failure_type
       để output dễ đọc.
    */
    status_group AS failure_type,


    -- Số case của từng failure type
    COUNT(*) AS n,


    -- Bao nhiêu case recovery ở attempt kế tiếp
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    ) AS recovered,


    -- Recovery rate theo failure type
    100.0
    *
    SUM
    (
        CASE
            WHEN next_status = 'PASS'
            THEN 1
            ELSE 0
        END
    )
    /
    NULLIF(COUNT(*), 0)

    AS recovery_rate

FROM first_failure

WHERE

    -- Chỉ lấy failure đầu tiên
    failure_rank = 1

    -- Phải có next observed status
    AND next_status IS NOT NULL

/* Mỗi loại failure là một nhóm */
GROUP BY status_group

ORDER BY failure_type;


/* =========================================================
   TÓM TẮT 12 QUERY
   =========================================================

   Q1  → Dataset có bao nhiêu dữ liệu?
   Q2  → Dữ liệu phân bố thế nào theo semester?
   Q3  → Dữ liệu phân bố thế nào theo course?

   Q4  → Có bao nhiêu trajectory >=2, >=3, >=4 attempts?
   Q5  → Chính xác mỗi trajectory có bao nhiêu attempts?

   Q6  → Failure đầu tiên của Student-Course là gì?
   Q7  → Failure đầu tiên → attempt tiếp theo như thế nào?

   Q8  → Recovery Rate chung là bao nhiêu?
   Q9  → Điểm trung bình cải thiện bao nhiêu?

   Q10 → Recovery khác nhau thế nào theo course?
   Q11 → Time Gap liên quan thế nào với score/recovery?
   Q12 → Recovery khác nhau thế nào theo failure type?
   ========================================================= */