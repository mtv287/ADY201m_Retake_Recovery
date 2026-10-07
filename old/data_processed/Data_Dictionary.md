# Data Dictionary - Clean Dataset V1 (TV2)

**Dataset dùng cho TV3:** `clean_attempts_v1.csv`

| Tên cột | Kiểu dữ liệu | Mô tả |
|---|---|---|
| `course_id` | str | Mã môn học đã decode (ví dụ ADY201M, CSD201, DBI202); dùng làm định danh course trong phân tích. |
| `source_file` | str | Tên file CSV nguồn để truy vết. |
| `source_row` | int64 | Số dòng gốc trong source file sau header. |
| `semester` | str | Mã học kỳ, ví dụ SP2023, SU2023, FA2023. |
| `class_id` | str | Mã lớp trong file nguồn. |
| `source_no` | int64 | Số thứ tự sinh viên trong bảng nguồn. |
| `student_id` | str | Mã sinh viên ẩn danh lấy từ CODE. |
| `total_score` | float64 | Điểm tổng kết môn; có thể missing. |
| `status_raw` | str | STATUS nguyên gốc, không ghi đè. |
| `semester_order` | int64 | Thứ tự số để sắp xếp học kỳ theo thời gian. |
| `duplicate_count` | int64 | Số records có cùng course_id + student_id + semester trong master_raw. |
| `is_duplicate_candidate` | bool | Cờ record thuộc nhóm duplicate candidate. |
| `attempt_no` | int64 | Số thứ tự lần quan sát Student-Course sau candidate dedup. |
| `status_clean` | str | STATUS chuẩn hóa chính tả nhưng giữ nghĩa gốc. |
| `status_group` | str | Nhóm PASS / FAIL_ACADEMIC / FAIL_ATTENDANCE / SUSPENDED / EXEMPT / REVIEW. |
| `needs_status_review` | int64 | 1 nếu STATUS chưa đủ rõ để tự động map. |
| `score_missing_flag` | int64 | 1 nếu total_score missing. |

## Quy tắc
- Không dùng TOTAL >= 5 để tự suy ra Pass/Fail.
- EXEMPT không thuộc failure cohort.
- REVIEW cần kiểm tra trước khi dùng.
- Không impute total_score ở Week 2.
- Không dùng future Total_Attempts làm predictor cho next-attempt recovery.
