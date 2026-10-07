# TV3 HANDOFF - Week 2 Feature Engineering & Validation

## File đầu vào chính
Dùng: `data_processed/clean_attempts_v1.csv`

Không dùng trực tiếp `master_raw.csv` để tạo features, vì file raw còn duplicate candidates.

## QA của input hiện tại
- Rows: 120,421
- Unique students: 15,235
- Decoded course codes: 18
- Unique semesters: 26
- Semester range: SP2017 -> SU2025
- Student-Course trajectories: 101,965
- >=2 attempts: 13,011
- >=3 attempts: 3,372
- >=4 attempts: 1,155
- Missing total_score: 10,972

## Các cột TV3 nên dùng
- `student_id`
- `course_id`
- `semester`
- `semester_order`
- `attempt_no`
- `total_score`
- `status_raw`
- `status_clean`
- `status_group`
- `score_missing_flag`

## Quy tắc status
- `PASS` -> Passed
- `FAIL_ACADEMIC` -> Not Passed
- `FAIL_ATTENDANCE` -> Attendance Fail
- `SUSPENDED` -> Is Suspended
- `EXEMPT` -> không thuộc failure cohort
- `REVIEW` -> kiểm tra thủ công, chưa tự động dùng làm Pass/Fail

## Nhiệm vụ TV3
1. Sort theo `student_id`, `course_id`, `semester_order`.
2. Kiểm tra `attempt_no` có tăng tuần tự trong từng Student-Course.
3. Xác định **first observed failure** trong các nhóm:
   `FAIL_ACADEMIC`, `FAIL_ATTENDANCE`, `SUSPENDED`.
4. Ghép first failure với **next observed attempt** của cùng Student-Course.
5. Tạo:
   - `Initial_Failure_Total`
   - `Next_Attempt_Total`
   - `Score_Delta = Next_Attempt_Total - Initial_Failure_Total`
   - `Pass_Next_Attempt` = 1 nếu next status_group = PASS, ngược lại 0
   - `Time_Gap = Next_Semester_Order - Failure_Semester_Order`
   - `Prior_Attempt_Count`
   - `Initial_Failure_Type`
6. Với `Score_Delta`, chỉ dùng pair có cả hai score khác missing.
7. Với classification, không dùng biến tương lai như:
   `Next_Attempt_Total`, `Next_Status`, eventual `Total_Attempts`.
8. Không dùng `TOTAL >= 5` để tự tạo Pass/Fail.
9. Kiểm tra thủ công ít nhất 20-30 trajectories.
10. Đối chiếu sample size giữa Python và SQL Query 7/8/9.

## Output TV3 cần nộp
- `data_processed/retake_pairs_v1.csv`
- `data_processed/Feature_Definitions.md`
- `data_processed/TV3_Validation_Report.txt`
- Notebook/script feature engineering của TV3.

## Leakage checklist
Không dùng làm predictor:
- `Next_Attempt_Total`
- `Next_Status`
- `Score_Delta`
- `Pass_Next_Attempt`
- tổng số attempts cuối cùng của trajectory (`Total_Attempts`) nếu nó dùng thông tin tương lai.

Có thể dùng nếu được tính chỉ từ quá khứ:
- `Initial_Failure_Total`
- `Initial_Failure_Type`
- `Prior_Attempt_Count`
- prior failures trước thời điểm dự đoán
- course-level historical failure rate (phải tính leakage-safe).
