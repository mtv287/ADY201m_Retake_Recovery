# Methodology — Retake Behavior & Recovery Analysis

**Môn:** ADY201m · **Lớp:** AI2112 · **Group:** 1
**Phụ trách:** TV4 — Phạm Gia Khương (Methodology · Dashboard · Model Interpretation)

---

## 1. Mục tiêu và phạm vi

Dự án nghiên cứu hành vi học lại (retake) và khả năng hồi phục của sinh viên sau lần rớt môn đầu tiên, dựa trên dữ liệu điểm đã ẩn danh theo thời gian.

Bốn câu hỏi nghiên cứu (RQ):

| RQ | Câu hỏi | Biến chính |
|---|---|---|
| RQ1 | Điểm thay đổi thế nào từ lần rớt đầu tiên đến lần học kế tiếp, và khác nhau ra sao giữa các môn? | `score_delta`, `course_id` |
| RQ2 | Yếu tố nào liên quan đến việc pass ở lần học kế tiếp? | `pass_next_attempt`, `initial_failure_total`, `initial_failure_type`, `time_gap`, `course_id` |
| RQ3 | Cần bao lâu để hồi phục sau lần rớt đầu tiên? | `time_gap`, recovery |
| RQ4 | Số lần học lại liên quan thế nào đến điểm và khả năng hồi phục? | `attempt_no`, `prior_attempt_count` |

**Nguyên tắc diễn giải:** dữ liệu mang tính quan sát (observational), mọi kết quả chỉ được mô tả là *association*, không phải *causal effect*.

---

## 2. Dữ liệu

| Mục | Giá trị |
|---|---|
| Nguồn | 17 file CSV thô theo môn (`data_raw/`), giữ nguyên, không chỉnh sửa |
| Sau làm sạch (`clean_attempts_v1.csv`) | 120,421 dòng · 15,235 sinh viên · 18 môn · 26 học kỳ (SP2017 → SU2025) |
| Student-Course trajectories | 101,965 (13,011 có ≥ 2 lần học; 3,372 có ≥ 3; 1,155 có ≥ 4) |
| Retake pairs (`retake_pairs_v1.csv`) | 12,058 cặp *first failure → next attempt* |
| Cặp có đủ điểm cả hai lần | 10,786 (dùng cho hồi quy `score_delta`) |
| Điểm `total_score` bị thiếu | 10,972 dòng trong dữ liệu sạch, không impute |

---

## 3. Quy trình xử lý dữ liệu (pipeline)

```
data_raw (17 CSV) ─▶ master_raw ─▶ clean_attempts_v1 ─▶ retake_pairs_v1 ─▶ model_ready_v1
        gộp file        TV2: làm sạch,       TV3: ghép first failure     TV1: chọn cột
        + decode môn    chuẩn hóa status,    với next attempt,           cho modeling
                        flag duplicate       tạo features
```

Các bước chính:

1. **Decode môn học:** proxy `C01–C18` được ánh xạ sang mã môn thật (ADY201M, CSD201, DBI202, ...).
2. **Duplicate:** khóa `course_id + student_id + semester`. Có 4,928 dòng thừa được flag; còn lại 120,421 dòng candidate sau dedup. `master_raw` được giữ nguyên.
3. **Chuẩn hóa STATUS** thành 6 nhóm: `PASS`, `FAIL_ACADEMIC`, `FAIL_ATTENDANCE`, `SUSPENDED`, `EXEMPT`, `REVIEW` (chỉ 1 dòng REVIEW, cần kiểm tra thủ công).
4. **Thứ tự thời gian:** dùng `semester_order` vì không có ngày chính xác.
5. **Ghép cặp:** với mỗi Student-Course, lấy lần rớt đầu tiên (thuộc `FAIL_ACADEMIC`, `FAIL_ATTENDANCE`, `SUSPENDED`) và lần quan sát kế tiếp.
6. **Kiểm chứng chéo:** đối chiếu sample size giữa Python và SQL (Query 7/8/9), kiểm tra thủ công mẫu 30 cặp (`TV3_Manual_Check_Sample.csv`).

### Quy tắc dữ liệu

- Pass/Fail lấy từ `status_group`, **không** suy ra từ `total_score >= 5`.
- `EXEMPT` không phải failure; `SUSPENDED` được giữ riêng.
- `score_delta` chỉ tính khi cả hai điểm đều có.
- Không impute điểm thiếu.

### Định nghĩa biến chính

| Biến | Định nghĩa |
|---|---|
| `score_delta` | `next_attempt_total − initial_failure_total` |
| `pass_next_attempt` | 1 nếu `next_status_group = PASS`, 0 nếu vẫn fail/suspended |
| `time_gap` | `next_semester_order − failure_semester_order` |
| `prior_attempt_count` | Số lần học trước lần rớt đầu tiên |
| Recovery rate | Tỉ lệ cặp có `pass_next_attempt = 1` |

---

## 4. Research Design và phương pháp phân tích theo RQ

**Thiết kế nghiên cứu:** observational, longitudinal, retrospective cohort.

- **Cohort:** mọi Student-Course trajectory có ít nhất một lần rớt (`FAIL_ACADEMIC`, `FAIL_ATTENDANCE`, `SUSPENDED`); 22,248 lần rớt đầu tiên.
- **Đơn vị phân tích:** một dòng = *lần rớt đầu tiên → lần quan sát kế tiếp* của một Student-Course (12,058 cặp). RQ4 dùng thêm cấp trajectory (`clean_attempts_v1`) vì `retake_pairs` chỉ chứa lần rớt đầu tiên.
- **Outcome:** `score_delta` (liên tục) và `pass_next_attempt` (nhị phân).
- **Exposure/biến giải thích:** loại rớt, điểm rớt ban đầu, `time_gap`, số lần học trước, môn học.
- **Kiểm soát sai lệch:** split/CV theo sinh viên, không dùng biến tương lai, không impute, luôn báo cáo n.
- **Quy trình:** SQL (kiểm tra và dựng cohort) → Python (EDA, thống kê, mô hình) → dashboard.


| RQ | Phương pháp | Output |
|---|---|---|
| RQ1 | Thống kê mô tả `score_delta` theo môn (chỉ nhóm đủ n), boxplot/violin | Biểu đồ so sánh môn |
| RQ2 | Recovery rate theo `initial_failure_type`, theo nhóm điểm rớt; sau đó mô hình phân loại nếu cần | Bar/line chart, bảng |
| RQ3 | Recovery rate và `score_delta` theo `time_gap` (mô tả, kèm n) | Line chart |
| RQ4 | Phân bố số lần học, so sánh theo `attempt_no` có lưu ý survivorship bias | Phân tích trajectory |

Luôn hiển thị **n** cạnh mỗi tỉ lệ/trung bình để tránh diễn giải quá mức ở nhóm nhỏ.

---

## 5. Thiết kế mô hình hồi quy (Week 4)

- **Target:** `score_delta`.
- **Predictors:** `initial_failure_total`, `initial_failure_type`, `time_gap`, `prior_attempt_count`, `course_id`.
- **Split:** `GroupShuffleSplit` 80/20 theo `student_id` (`random_state=42`) — 8,557 train / 2,229 test, không sinh viên nào xuất hiện ở cả hai tập.
- **Cross-validation:** 5-fold `GroupKFold`, group = `student_id`, metric RMSE.
- **Preprocessing:** `StandardScaler` cho biến số, `OneHotEncoder` cho biến phân loại.
- **Mô hình:** Dummy Baseline, Linear, Ridge (tuning alpha ∈ {0.01, 0.1, 1, 10, 100}, best = 0.1), Lasso, Random Forest, Gradient Boosting.
- **Metric:** MAE, RMSE, R².

### Kiểm tra data leakage

Không dùng làm predictor: `next_attempt_total`, `next_status_group`, `pass_next_attempt`, `score_delta`, tổng số attempts cuối của trajectory. Code có assert chặn các cột này và kiểm tra overlap sinh viên giữa train/test bằng 0.

---

## 6. Kết quả mô hình

| Model | CV RMSE | Test MAE | Test RMSE | Test R² |
|---|---:|---:|---:|---:|
| Dummy Baseline | 2.703 | 2.184 | 2.715 | −0.001 |
| Linear Regression | 2.476 | 2.079 | 2.496 | 0.154 |
| Ridge Regression | 2.476 | 2.079 | 2.496 | 0.154 |
| Lasso Regression | 2.482 | 2.089 | 2.504 | 0.149 |
| Random Forest | 2.484 | 2.069 | 2.520 | 0.138 |
| **Gradient Boosting** | **2.451** | **2.055** | **2.490** | **0.158** |

(Số liệu lấy từ `w4 - tv1/Regression_Results.csv`; chạy lại Ridge và Gradient Boosting cho ra đúng các giá trị test này.)

Gradient Boosting có Test RMSE thấp nhất, nhưng chênh lệch giữa các mô hình rất nhỏ so với độ lệch chuẩn CV (~0.03–0.05). Tất cả đều tốt hơn baseline rõ rệt (RMSE giảm khoảng 0.22) nhưng R² chỉ khoảng 0.14–0.16, tức là các biến hiện có chỉ giải thích được một phần nhỏ biến thiên của `score_delta`.

---

## 7. Diễn giải mô hình (Model Interpretation)

Hình: `Model_Interpretation.png` (Predicted vs Actual, Residual plot, Permutation importance, Ridge coefficients).

**Mức độ quan trọng của biến** (permutation importance trên Gradient Boosting, tăng RMSE khi xáo trộn biến):

| Biến | Tăng RMSE |
|---|---:|
| `initial_failure_total` | 0.468 |
| `course_id` | 0.041 |
| `initial_failure_type` | 0.019 |
| `time_gap` | 0.008 |
| `prior_attempt_count` | 0.000 |

**Nhận xét:**

1. **`initial_failure_total` là biến chi phối.** Hệ số Ridge âm (−1.08 trên thang chuẩn hóa): điểm rớt ban đầu càng thấp thì mức tăng điểm càng lớn. Theo nhóm điểm, nhóm ≤ 2 tăng trung bình +2.81, còn nhóm > 5 gần như không tăng (−0.10). Xu hướng này có thể một phần là *regression to the mean* (điểm quá thấp thì có nhiều chỗ để tăng hơn), nên không nên đọc là "học lại giúp tăng điểm nhiều hơn".
2. **`course_id` có đóng góp nhỏ nhưng khác biệt giữa môn có thật** (ví dụ IOT102 trung bình +3.24, OSG202 +1.04), tuy nhiên cần cẩn trọng vì thang điểm TOTAL giữa các môn có thể không tương đương.
3. **`initial_failure_type`:** nhóm SUSPENDED có hệ số dương, ATTENDANCE âm nhẹ. Hệ số nhỏ so với `initial_failure_total`.
4. **`time_gap` và `prior_attempt_count` gần như không có tác dụng dự đoán.** Trong tập first-failure, `prior_attempt_count` bằng 0 ở 12,053/12,058 cặp nên hầu như không có biến thiên.
5. **Residual plot:** phần dư có dạng dải rộng quanh 0, không có xu hướng cong rõ rệt, nhưng độ phân tán lớn (±4–6 điểm) và các dự đoán tập trung quanh 0–3 điểm. Điều này khớp với R² thấp: mô hình bắt được xu hướng chung nhưng không dự đoán tốt từng trường hợp.
6. **Gradient Boosting chỉ nhỉnh hơn Linear/Ridge một chút**, cho thấy quan hệ gần như tuyến tính và không có tương tác phức tạp đáng kể trong các biến hiện có.

---

## 8. Hạn chế (Limitations)

1. **Dữ liệu quan sát:** không kết luận nhân quả; `time_gap` và `score_delta` chỉ là association.
2. **Survivorship/selection bias:** sinh viên xuất hiện ở lần học thứ 3, 4+ là những người chưa hồi phục ở lần trước, nên RQ4 không đo được "tác động của việc học thêm".
3. **Censoring:** không có lần học kế tiếp không đồng nghĩa với việc sinh viên rớt tiếp; có thể do hết cửa sổ quan sát hoặc bỏ học. 22,248 lần rớt đầu tiên nhưng chỉ 12,058 có lần học kế tiếp.
4. **Thang điểm giữa các môn không đồng nhất.** Ví dụ **LAB211** có 1,275 retake pairs nhưng chỉ 4 cặp có đủ điểm (đều bằng 0), nên hệ số `course_id_LAB211` trong Ridge (−3.39) là hệ quả của dữ liệu điểm gần như thiếu, không phải đặc tính thật của môn. Cần kiểm tra trước khi so sánh môn.
5. **Môn có n nhỏ** (PRF193 n=14, DAP391M n=16, ADY201M n=21 cặp) cho tỉ lệ/trung bình không ổn định, không nên xếp hạng.
6. **Predictors ít thông tin:** `prior_attempt_count` gần như hằng số; chưa có biến về sinh viên (GPA, số tín chỉ, ngành) hay về lớp/giảng viên. Đây là lý do chính khiến R² thấp.
7. **`time_gap` chỉ biết sau khi lần học lại đã xảy ra.** Nếu mục tiêu là dự đoán *trước* khi sinh viên đăng ký học lại, biến này không khả dụng tại thời điểm dự đoán. Nên báo cáo thêm kết quả mô hình bỏ `time_gap`.
8. **Một sinh viên có thể có nhiều cặp** (10,786 cặp từ khoảng 5,788 sinh viên); đã xử lý bằng group split/CV, nhưng độc lập giữa các cặp vẫn không hoàn toàn.
9. **Một split cố định (`random_state=42`):** các khác biệt nhỏ giữa mô hình có thể thay đổi khi đổi split.
10. **Điểm thiếu không được impute:** 1,272 cặp bị loại khỏi hồi quy vì thiếu điểm; nếu việc thiếu không ngẫu nhiên thì kết quả có thể lệch.

---

## 9. Dashboard

Hình mockup: `Dashboard_Mockup.png` (số liệu trên mockup lấy từ dữ liệu thật của `retake_pairs_v1.csv`).

### Luồng đọc

① Overview (KPI) → ② Recovery drivers (Failure Type · Time Gap · Attempt Number vs Recovery) → ③ Course detail (Recovery by Course · Score Delta by Course).

### KPI cards

| KPI | Mục đích theo dõi | Giá trị hiện tại |
|---|---|---|
| Total Students | Tổng số sinh viên trong phạm vi nghiên cứu | 15,235 (6,076 có ≥ 1 retake pair) |
| Total Retake Trajectories | Tổng số quỹ đạo học lại cần phân tích | 12,058 |
| Recovery Rate | Tỷ lệ phục hồi sau các lần học lại | 54.3% |
| Average Score Delta | Mức thay đổi điểm trung bình giữa các lần thi | +1.79 (n = 10,786) |
| Average Time Gap | Khoảng thời gian trung bình giữa các lần thử | 1.73 học kỳ (median 1) |

### Danh sách biểu đồ

| # | Biểu đồ | Câu hỏi hỗ trợ | RQ |
|---|---|---|---|
| 1 | Failure Type vs Recovery | Loại thất bại nào gắn với kết quả phục hồi khác nhau? (Suspended 70.6% · Academic 57.2% · Attendance 42.9%) | RQ2 |
| 2 | Time Gap vs Recovery | Khoảng cách thời gian có liên hệ với khả năng phục hồi không? (không đơn điệu, cao nhất ở gap 1) | RQ3 |
| 3 | Attempt Number vs Recovery | Số lần thử ảnh hưởng thế nào đến Recovery Rate? (54.3% → 45.8% → 32.8% → 25.7%, có survivorship bias) | RQ4 |
| 4 | Recovery by Course | Khóa học nào có tỷ lệ phục hồi cao hoặc thấp? (IOT102 67.3% · PRJ321 36.0%) | RQ1/RQ2 |
| 5 | Score Delta by Course | Mức cải thiện điểm khác nhau thế nào giữa các khóa học? (IOT102 +3.24 · OSG202 +1.04; loại LAB211) | RQ1 |

Chi tiết định nghĩa, công thức và KPI phụ: xem `Dashboard_KPI_List.md`.

### Bộ lọc

Semester range · Course · Initial failure type · Initial score bin · Min n per group (ẩn/làm mờ nhóm nhỏ).

### Quy tắc hiển thị

- Mọi tỉ lệ đều kèm n.
- Ghi chú "observational, association not causation" trên dashboard.
- Trục của biểu đồ model comparison bắt đầu từ 2.3 (đã ghi rõ trên trục) để thấy khác biệt nhỏ giữa các mô hình.

---

## 10. Deliverables của TV4

| File | Nội dung |
|---|---|
| `Methodology.md` | Tài liệu này |
| `Dashboard_Mockup.png` | Mockup dashboard với số liệu thật (5 KPI + 5 chart) |
| `Dashboard_KPI_List.md` | Danh sách KPI/chart, định nghĩa, công thức, cảnh báo hiển thị |
| `Model_Interpretation.png` | Predicted vs Actual, Residual, Feature importance, Coefficients |

> Ghi chú: phần AI Audit Log không nằm trong file này.
