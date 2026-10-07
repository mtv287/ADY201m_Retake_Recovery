# Dashboard KPI List — Retake Behavior & Recovery Analysis

**Phụ trách:** TV4 — Phạm Gia Khương · **Mockup:** `Dashboard_Mockup.png`

Giá trị hiện tại lấy từ `retake_pairs_v1.csv` (12,058 cặp) và `clean_attempts_v1.csv`. Đối chiếu với SQL Query 7–12.

> Quy tắc chung: mọi tỉ lệ/trung bình hiển thị kèm **n**; nhóm n nhỏ bị làm mờ; ghi chú "observational — association, not causation".

---

## 0. Luồng đọc dashboard (tổng quan → chi tiết)

| Tầng | Nội dung | Câu hỏi trả lời |
|---|---|---|
| ① Overview | 5 KPI cards | Quy mô vấn đề retake lớn đến đâu, hồi phục được bao nhiêu? |
| ② Recovery drivers | Failure Type · Time Gap · Attempt Number vs Recovery | Yếu tố nào gắn với khả năng hồi phục? |
| ③ Course detail | Recovery by Course · Score Delta by Course | Môn nào khác biệt? |

## 1. KPI cards (5 KPI đề xuất, hàng đầu dashboard)

| # | KPI | Mục đích theo dõi | Định nghĩa / công thức | Giá trị hiện tại | RQ | SQL |
|---|---|---|---|---:|---|---|
| K1 | Total Students | Tổng số sinh viên trong phạm vi nghiên cứu | `COUNT(DISTINCT student_id)` trong `clean_attempts_v1` | 15,235 (6,076 có ≥1 retake pair) | Tổng quan | Q1 |
| K2 | Total Retake Trajectories | Tổng số quỹ đạo học lại cần phân tích | Số cặp *first failure → next attempt* (một Student-Course = một quỹ đạo). Tham chiếu: 13,011 trajectory có ≥ 2 lần học | 12,058 | Tổng quan | Q4, Q7 |
| K3 | Recovery Rate | Tỷ lệ phục hồi sau các lần học lại | `pass_next_attempt = 1` / số cặp có outcome rõ ràng (n = 12,057) | 54.3% | RQ2 | Q8 |
| K4 | Average Score Delta | Mức thay đổi điểm trung bình giữa các lần thi | Trung bình `next_attempt_total − initial_failure_total`, chỉ cặp đủ điểm (n = 10,786) | +1.79 | RQ1 | Q9 |
| K5 | Average Time Gap | Khoảng thời gian trung bình giữa các lần thử | Trung bình `next_semester_order − failure_semester_order` (học kỳ) | 1.73 (median 1) | RQ3 | Q11 |

## 2. KPI phụ (tooltip / trang chi tiết)

| # | KPI | Định nghĩa | Giá trị hiện tại | RQ |
|---|---|---|---:|---|
| S1 | Median score delta | Trung vị của `score_delta` | +1.70 | RQ1 |
| S2 | % improved | Tỉ lệ cặp có `score_delta > 0` (trong 10,786) | 71.7% | RQ1 |
| S3 | % no change / declined | `score_delta = 0` / `< 0` | 7.7% / 20.6% | RQ1 |
| S4 | First observed failures | Số lần rớt đầu tiên trong cohort | 22,248 | Tổng quan |
| S5 | Retake coverage | Cặp có lần học kế tiếp / lần rớt đầu tiên | 54.2% (12,058/22,248) | RQ3 |
| S6 | Share of retakes at time_gap = 1 | Học lại ngay học kỳ kế tiếp | 68.1% | RQ3 |
| S7 | Complete score pairs | Cặp có cả hai điểm | 10,786 | RQ1 |
| S8 | Missing-score rate (pairs) | Cặp thiếu `score_delta` | 10.5% (1,272/12,058) | QA |
| S9 | Best model RMSE | Test RMSE thấp nhất (Gradient Boosting, R² 0.16); baseline 2.71 | 2.49 | Week 4 |

## 3. Danh sách biểu đồ (5 chart đề xuất + biểu đồ bổ sung)

| # | Chart đề xuất | Câu hỏi hỗ trợ | Trục / chiều | RQ | Insight hiện tại |
|---|---|---|---|---|---|
| C1 | Failure Type vs Recovery | Loại thất bại nào gắn với kết quả phục hồi khác nhau? | x: failure type · y: % pass · nhãn n | RQ2 | Suspended 70.6% (n=245) · Academic 57.2% (n=9,141) · Attendance 42.9% (n=2,672) |
| C2 | Time Gap vs Recovery | Khoảng cách thời gian có liên hệ với khả năng phục hồi không? | x: time gap (1–6) · nhãn n | RQ3 | Cao nhất ở gap 1 (55.5%); gap 2–3 thấp hơn (~50%); không đơn điệu |
| C3 | Attempt Number vs Recovery | Số lần thử ảnh hưởng thế nào đến Recovery Rate? | x: lần rớt thứ k (1, 2, 3, 4+) | RQ4 | 54.3% → 45.8% → 32.8% → 25.7% (n = 12,053 / 3,325 / 1,153 / 918) |
| C4 | Recovery by Course | Khóa học nào có tỷ lệ phục hồi cao hoặc thấp? | n ≥ 100 retakes · đường tham chiếu 54.3% | RQ1/RQ2 | IOT102 67.3% cao nhất; PRJ321 36.0% thấp nhất |
| C5 | Score Delta by Course | Mức cải thiện điểm khác nhau thế nào giữa các khóa học? | n ≥ 100 cặp có điểm | RQ1 | IOT102 +3.24 cao nhất; OSG202 +1.04 thấp nhất; LAB211 loại vì thiếu điểm |
| X1 | (bổ sung) Recovery & Score Delta theo nhóm điểm rớt | Điểm rớt ban đầu liên quan thế nào? | x: bin `initial_failure_total` | RQ2 | Điểm ≤ 2: recovery 39.5%, delta +2.81; điểm > 5: recovery 67.7%, delta −0.10 |
| X2 | (bổ sung) Test RMSE các mô hình | Mô hình nào dự đoán `score_delta` tốt nhất? | 6 mô hình | Week 4 | Gradient Boosting 2.490 < Ridge 2.496 < Dummy 2.715 |

`Dashboard_Mockup.png` hiển thị 5 KPI (K1–K5) và 5 chart (C1–C5) theo luồng ① → ② → ③. X1 và X2 dành cho trang chi tiết/modeling.

## 4. Bộ lọc

| Bộ lọc | Giá trị |
|---|---|
| Semester range | SP2017 → SU2025 |
| Course | 16 môn có retake (2 môn không có cặp nào) |
| Initial failure type | Academic / Attendance / Suspended |
| Initial score bin | ≤2, 2–3, 3–4, 4–5, >5 |
| Min n per group | Mặc định 100 |

## 5. Cảnh báo hiển thị

1. **LAB211:** 1,275 cặp nhưng chỉ 4 cặp có đủ điểm → C5 (Score Delta) loại môn này; C4 (Recovery) vẫn hiển thị vì không cần điểm (60.3%, n=1,275).
2. **Môn n nhỏ** (PRF193 n=14, DAP391M n=16, ADY201M n=21): ẩn hoặc làm mờ.
3. **C3 (RQ4):** survivorship bias — sinh viên ở lần rớt thứ 3, 4+ là người chưa hồi phục trước đó; không diễn giải là tác động của việc học thêm. C3 tính trên mọi lần rớt có lần học kế tiếp trong `clean_attempts_v1`, không chỉ lần rớt đầu tiên.
4. **Không có lần học kế tiếp ≠ rớt tiếp:** có thể bị censoring (hết cửa sổ quan sát).
5. **Score delta theo nhóm điểm (X1):** một phần là regression to the mean.
6. **Pass/Fail** lấy từ `status_group`, không suy từ `total_score ≥ 5`.

## 6. Nguồn dữ liệu cho từng KPI

| Nguồn | Dùng cho |
|---|---|
| `retake_pairs_v1.csv` | K2–K5, S1–S8, C1, C2, C4, C5, X1 |
| `clean_attempts_v1.csv` | K1, C3 |
| `w4 - tv1/Regression_Results.csv` | S9, X2 |
