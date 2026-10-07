# Tuần 4 — Interpretation & Quality Check

**Phụ trách:** TV4 — Phạm Gia Khương · **Nhóm:** AI2112 – Group 1 · **Môn:** ADY201m
**Input:** `w4 - tv1/Regression_Results.csv` (+ `Ridge_Tuning_Results.csv`, `model_ready_v1.csv`, `TV1_Regression_Master.py`)
**Hình đi kèm:** `Model_Comparison.png` · `Predicted_vs_Actual.png` · `Residual_Plot.png` · `Feature_Importance.png`

---

## 0. Tóm tắt

| # | Kết luận | Độ tin cậy |
|---|---|---|
| 1 | Cả 5 mô hình đều tốt hơn baseline khoảng 0.2 RMSE (Gradient Boosting 2.490 so với Dummy 2.715; ΔRMSE 95% CI [0.18, 0.27]). | Cao |
| 2 | **Không thể khẳng định Gradient Boosting tốt hơn Ridge/Linear.** ΔRMSE (Ridge − GB) có 95% CI [−0.016, +0.027], chứa 0. | Cao |
| 3 | Sức mạnh dự đoán thấp: R² = 0.158 (95% CI [0.127, 0.187]). Khoảng 84% biến thiên của `score_delta` chưa được giải thích. | Cao |
| 4 | Biến quan trọng gần như duy nhất là `initial_failure_total` (xáo trộn làm RMSE tăng 0.47; bỏ biến này R² còn 0.06). Hướng quan hệ: điểm rớt càng thấp thì mức tăng càng lớn, phù hợp với hiện tượng regression to the mean. | Cao |
| 5 | `time_gap` và `prior_attempt_count` gần như không đóng góp (bỏ đi RMSE đổi ≤ 0.003). | Cao |
| 6 | Leakage check **đạt** về mặt thống kê; có 1 điểm cần lưu ý về thời điểm sử dụng (`time_gap`). | Cao |
| 7 | **7 điểm cần xác minh lại** (mục 7), trong đó quan trọng nhất: cột CV trong `Regression_Results.csv` không tái lập được, và 829 cặp có `score_delta = 0` cần kiểm tra nguồn gốc. | — |

---

## 1. Kiểm tra đầu vào: `Regression_Results.csv`

| Kiểm tra | Kết quả |
|---|---|
| Cấu trúc | 6 dòng × 6 cột (`Model, CV_RMSE_Mean, CV_RMSE_SD, Test_MAE, Test_RMSE, Test_R2`), không có giá trị thiếu, đã sắp theo Test_RMSE tăng dần. |
| Đủ mô hình | Dummy, Linear, Ridge, Lasso, Random Forest, Gradient Boosting. Đủ 1 baseline + 5 mô hình. |
| Tái lập cột **Test** | Chạy lại toàn bộ 6 mô hình với cùng split (`GroupShuffleSplit`, seed 42) và cùng cấu hình: lệch tối đa RMSE 1.6e-7, R² 1.1e-7, MAE 7.5e-5. **Khớp.** |
| Nhất quán nội bộ | R² tính ngược từ RMSE và phương sai tập test (7.365) trùng với cột `Test_R2` ở cả 6 mô hình. |
| Tái lập cột **CV** | **Không khớp** (xem V1, mục 7). |
| Dòng "Ridge Regression" | Là Ridge với alpha = 1.0 (theo code), **không phải** alpha tối ưu 0.1 từ `Ridge_Tuning_Results.csv`. Ridge alpha = 0.1 cho Test RMSE 2.49568 so với 2.49568 của alpha = 1.0, nên khác biệt không có ý nghĩa thực tế. |
| `model_ready_v1.csv` | 10,786 dòng, trùng hoàn toàn các cặp có `score_delta` trong `retake_pairs_v1.csv`; không thiếu giá trị ở 5 predictors. |

---

## 2. Model Comparison (`Model_Comparison.png`)

| Model | Test MAE | Test RMSE | Test R² | Điểm mạnh / lưu ý |
|---|---:|---:|---:|---|
| **Gradient Boosting** | **2.055** | **2.490** | **0.158** | Tốt nhất trên cả 3 chỉ số; MAE thấp nhất cho thấy nó xử lý được một phần phi tuyến (chênh MAE so với Ridge khoảng 0.024). |
| Ridge | 2.079 | 2.496 | 0.154 | Gần như bằng Linear; đơn giản, dễ diễn giải, hệ số có nghĩa. |
| Linear | 2.079 | 2.496 | 0.154 | Không cần regularization vì chỉ có 5 predictors. |
| Lasso (α = 0.01) | 2.089 | 2.504 | 0.149 | Hơi kém hơn Ridge/Linear. |
| Random Forest | 2.069 | 2.520 | 0.138 | MAE thấp hơn Linear nhưng RMSE cao hơn (có thể do sai số lớn ở một số điểm cực trị). |
| Dummy Baseline | 2.184 | 2.715 | −0.001 | Mốc tham chiếu. |

**Ý nghĩa thống kê (bootstrap theo sinh viên, 600 lần, tập test 1,158 sinh viên):**

| So sánh | ΔRMSE (median) | 95% CI | Kết luận |
|---|---:|---|---|
| Dummy − Gradient Boosting | 0.226 | [0.182, 0.273] | Cải thiện so với baseline là thật |
| Dummy − Ridge | 0.217 | [0.175, 0.267] | Cải thiện so với baseline là thật |
| Ridge − Gradient Boosting | 0.006 | [−0.016, 0.027] | **Không phân biệt được** |
| Gradient Boosting − Random Forest | −0.031 | [−0.057, −0.004] | GB tốt hơn RF một chút |

Gradient Boosting: RMSE 2.490 (CI [2.421, 2.555]), R² 0.158 (CI [0.127, 0.187]).

**Khuyến nghị:** nếu mục tiêu là diễn giải (báo cáo/proposal), nên dùng **Ridge/Linear** làm mô hình chính vì không thua đáng kể mà hệ số đọc được; Gradient Boosting dùng làm mô hình tham chiếu hiệu năng.

**Kiểm tra baseline có công bằng không:** Dummy dự đoán `delta` = hằng số, tức là điểm kế tiếp = điểm đầu + hằng số. Nếu đổi sang thang điểm (dự đoán thẳng `next_attempt_total`), baseline "điểm trung bình" có RMSE 2.705, gần như bằng 2.715, còn Gradient Boosting cho 2.490 và R² thang điểm = 0.152. Vậy việc chọn target là `delta` không làm baseline yếu đi hay mạnh lên đáng kể.

---

## 3. Predicted vs Actual (`Predicted_vs_Actual.png`)

- **Độ khớp trung bình khá tốt, độ phân giải thấp.** Trung bình thực tế theo từng decile dự đoán bám sát đường y = x (ví dụ dự đoán 0.16 → thực tế 0.21; 2.10 → 2.13; 3.15 → 3.03). Mô hình không bị lệch hệ thống ở mức trung bình.
- **Dự đoán bị nén.** Độ lệch chuẩn của dự đoán là 1.13 trong khi giá trị thực là 2.71 (khoảng 42%). Mô hình hầu như không bao giờ dự đoán mức tăng rất lớn (> 5) hoặc mức giảm (< −2), trong khi thực tế `score_delta` trải từ −7.8 đến +9.7.
- **Các dải ngang/đứng:** nhiều sinh viên có cùng giá trị dự đoán quanh 2.4–3.0 (có thể do cùng nhóm loại rớt/môn học và điểm đầu gần nhau); trong mỗi dải, giá trị thực rất phân tán (từ −5 đến +8).
- Ridge và Gradient Boosting cho hình dạng gần như giống nhau, khớp với việc hai mô hình gần như tương đương về hiệu năng.

---

## 4. Residual Plot (`Residual_Plot.png`)

| Chỉ số (Gradient Boosting, test) | Giá trị | Nhận xét |
|---|---:|---|
| Residual trung bình | −0.07 | Gần 0, không lệch tổng thể |
| Residual SD | 2.49 | Bằng RMSE |
| Skew / Excess kurtosis | −0.23 / −0.63 | Hơi lệch trái, đuôi **nhẹ** hơn chuẩn (do điểm bị chặn trong [0, 10]) |
| Điểm ngoài ±3 SD | 1 điểm (|res| lớn nhất = 7.99) | Không có outlier nặng |
| |Residual| ≥ 6 | 11 điểm (0.5%) | Ít, không ảnh hưởng đáng kể |

**Dấu hiệu sai lệch hệ thống:**

1. **Phương sai không đồng đều (heteroscedasticity):** residual SD tăng dần theo mức dự đoán, từ 2.13 (quintile thấp nhất) lên 2.93 (cao nhất). Khoảng tin cậy dự đoán nếu có xây dựng thì không nên dùng một độ rộng chung.
2. **Cấu trúc điểm 0:** 11.7% cặp có `initial_failure_total = 0`; trong đó 395 cặp có điểm kế tiếp cũng bằng 0. Các điểm này tạo thành **đường chéo** (residual = −dự đoán) trong biểu đồ, và nhóm `score_delta = 0` có residual trung bình −2.16. Mô hình tuyến tính/cây nông không bắt được cấu trúc "0 → 0" này.
3. **Thiên lệch theo môn (nhỏ nhưng có):** mean residual từ −0.44 (PRJ321) đến +0.21 (CEA201); DBI202 −0.32, PRJ30X −0.30, IOT102 −0.25. Nghĩa là mô hình dự đoán cao hơn thực tế cho các môn này và thấp hơn cho CEA201. Theo loại rớt: ACADEMIC −0.10, ATTENDANCE −0.005 (nhưng SD cao nhất 2.97), SUSPENDED +0.34 (n = 52).
4. **Không có đường cong rõ rệt** trong residual vs predicted, nên quan hệ tuyến tính với `initial_failure_total` là đủ cho phần lớn tín hiệu.

---

## 5. Feature Importance (`Feature_Importance.png`)

**Permutation importance** (tăng RMSE trên tập test khi xáo trộn biến, 30 lần lặp) và **ablation** (huấn luyện lại khi bỏ biến):

| Biến | PI – GB | PI – Ridge | Ablation RMSE – GB (đủ biến: 2.4895) | Ablation RMSE – Ridge (đủ biến: 2.4957) |
|---|---:|---:|---:|---:|
| `initial_failure_total` | **0.467** | **0.431** | 2.630 (R² 0.061) | 2.640 (R² 0.054) |
| `course_id` | 0.040 | 0.063 | 2.502 | 2.523 |
| `initial_failure_type` | 0.019 | 0.004 | 2.500 | 2.497 |
| `time_gap` | 0.008 | −0.0002 | 2.493 | 2.4955 |
| `prior_attempt_count` | 0.000 | 0.0005 | 2.4894 | 2.4959 |

**Hệ số Ridge (biến số đã chuẩn hóa):** `initial_failure_total` −1.08; `initial_failure_type` SUSPENDED +0.41, ATTENDANCE −0.28, ACADEMIC −0.13; `time_gap` +0.003; `prior_attempt_count` −0.03.

**Diễn giải:**

- **`initial_failure_total` chiếm gần như toàn bộ tín hiệu.** Hệ số âm: mỗi 1 SD điểm đầu cao hơn thì `score_delta` thấp hơn khoảng 1.08. Dữ liệu thô cho thấy `corr(delta, initial) = −0.375`, và hồi quy điểm kế tiếp theo điểm đầu có hệ số dốc 0.47 (chỉ khoảng một nửa điểm đầu được "mang theo"). Đây là regression to the mean; một phần cũng là quan hệ cơ học vì `initial_failure_total` nằm trong định nghĩa của `score_delta`.
- **`course_id`** đóng góp nhỏ (0.04–0.06) nhưng ổn định giữa hai mô hình. Riêng môn học giải thích khoảng 2.4% phương sai `delta` (η² = 0.024, đã loại LAB211).
- **`initial_failure_type`:** đóng góp nhỏ; SUSPENDED có hệ số dương nhưng chỉ 245 cặp.
- **`time_gap`, `prior_attempt_count`:** không có tác dụng; `prior_attempt_count` có 10,781/10,786 dòng bằng 0, tức gần như hằng số.
- **Cảnh báo về hệ số môn học:** LAB211 (4 dòng), DAP391M (16), PRF193 (14), ADY201M (21) có hệ số rất lớn (LAB211 −2.65; DAP391M +1.88; PRF193 +1.39) nhưng dựa trên số mẫu quá ít, **không nên diễn giải**.

---

## 6. Interpretation theo Research Question

| RQ | Kết luận có thể nói | Mức hỗ trợ từ mô hình | Bằng chứng / giới hạn |
|---|---|---|---|
| **RQ1** — Điểm thay đổi thế nào, khác nhau giữa các môn ra sao? | Điểm tăng trung bình +1.79 (71.7% tăng, 7.7% không đổi, 20.6% giảm). Mức tăng khác nhau giữa các môn (IOT102 +3.24 đến OSG202 +1.04) nhưng khác biệt giữa môn nhỏ so với dao động giữa các cá nhân. | **Yếu–trung bình** | `course_id` có PI 0.04–0.06, η² = 2.4%; bỏ `course_id` làm RMSE tăng 0.013 (GB) / 0.028 (Ridge). Residual vẫn lệch theo môn (−0.44 đến +0.21). LAB211 không có dữ liệu điểm dùng được. |
| **RQ2** — Yếu tố nào liên quan đến việc pass ở lần kế tiếp? | Điểm rớt ban đầu là tín hiệu mạnh nhất cho mức tăng điểm; loại rớt liên quan đến recovery (Suspended 70.6%, Academic 57.2%, Attendance 42.9%) nhưng đóng góp nhỏ trong mô hình điểm. | **Yếu** (mô hình hồi quy không dự đoán trực tiếp pass/fail) | Phân tích bổ sung (logistic, split theo sinh viên): AUC 0.641 với đủ biến, 0.621 chỉ với điểm đầu, 0.554 chỉ với loại rớt, 0.6405 khi bỏ `time_gap`; tỉ lệ nền 54.3%. Mức phân biệt khiêm tốn. Đây là kiểm tra bổ sung ngoài pipeline Week 4. |
| **RQ3** — Mất bao lâu để hồi phục? | Không có bằng chứng về quan hệ tuyến tính giữa `time_gap` và mức tăng điểm (hệ số +0.003, tương quan −0.02). Tỉ lệ recovery theo time gap có dạng không đơn điệu (xem dashboard). | **Không hỗ trợ** | Bỏ `time_gap` không đổi RMSE (±0.003). Biến này chỉ biết sau khi học lại, và đa số cặp (68%) có time_gap = 1 nên biến thiên hạn chế. |
| **RQ4** — Số lần học lại liên quan thế nào đến điểm và recovery? | Chỉ có thể trả lời bằng phân tích mô tả: recovery giảm 54.3% → 45.8% → 32.8% → 25.7% theo số lần rớt. | **Không hỗ trợ** | `prior_attempt_count` gần như hằng số (5 giá trị khác 0 trên 10,786). Phân tích mô tả có survivorship bias; không được diễn giải là "học thêm làm giảm khả năng pass". |

**Thông điệp chính cho báo cáo:** với 5 predictors hiện có, mô hình chỉ bắt được một xu hướng chung (điểm đầu thấp thì tăng nhiều hơn, khác biệt nhỏ giữa môn). Mô hình **không đủ để dự đoán cá nhân** (RMSE ≈ 2.5 điểm, gần bằng độ lệch chuẩn của `delta` là 2.7) và **không đủ để kết luận nhân quả** về học lại.

---

## 7. Quality Check

### 7.1 Leakage Check

| # | Hạng mục | Kết quả |
|---|---|---|
| L1 | Không dùng `next_attempt_total`, `next_status_group`, `pass_next_attempt`, `score_delta` làm predictor | **Đạt** (kiểm tra danh sách cột và assert trong code) |
| L2 | Target đúng định nghĩa `next − initial` | **Đạt** (sai số tối đa 8.9e-16) |
| L3 | Không trùng sinh viên giữa train/test (8,557/2,229 dòng; 4,630/1,158 sinh viên) | **Đạt** (overlap = 0) |
| L4 | CV theo nhóm | **Đạt** (5-fold `GroupKFold`, group = `student_id`) |
| L5 | Không có Student-Course lặp trong `retake_pairs` | **Đạt** (0 trùng) |
| L6 | `model_ready_v1.csv` khớp `retake_pairs_v1.csv` | **Đạt** (10,786 dòng, giá trị `score_delta` trùng) |
| L7 | Tiền xử lý (scaler, encoder, imputer) nằm trong Pipeline nên chỉ fit trên dữ liệu train của từng fold | **Đạt** |
| L8 | Test set không dùng để tuning | **Đạt** (alpha Ridge tuning bằng GridSearchCV trên train; RF/GB dùng tham số cố định) |
| L9 | `time_gap` chỉ biết **sau** khi sinh viên học lại | **Lưu ý.** Không phải leakage thống kê, nhưng không dùng được nếu muốn dự đoán trước khi đăng ký học lại. Ablation: bỏ `time_gap` không làm mô hình kém đi. |
| L10 | `initial_failure_total` là một vế của target | **Lưu ý.** Không phải leakage (là thông tin có trước), nhưng làm cho tín hiệu mang tính cơ học/regression to the mean. |
| L11 | Chọn "mô hình tốt nhất" bằng chính tập test | **Lưu ý.** Có thể hơi lạc quan; do chênh lệch giữa các mô hình nằm trong CI nên không ảnh hưởng kết luận. |

### 7.2 Limitations

1. **Sức mạnh dự đoán thấp:** R² ≈ 0.16, khoảng 84% phương sai chưa giải thích; residual SD 2.1–2.9 tùy mức dự đoán.
2. **Predictors nghèo thông tin:** thiếu GPA, số tín chỉ, ngành, giảng viên, hành vi học tập. `prior_attempt_count` gần như hằng số.
3. **Dự đoán bị nén và phương sai không đồng đều:** không phù hợp để dự đoán các trường hợp cực đoan.
4. **Cấu trúc điểm 0 và điểm lặp lại:** 11.7% cặp có điểm đầu bằng 0; 829 cặp có `delta = 0` (xem V5, V6) làm méo phân phối target.
5. **Hệ số môn học có n nhỏ** (LAB211 4, DAP391M 16, PRF193 14, ADY201M 21) không ổn định.
6. **Dữ liệu quan sát:** mọi quan hệ chỉ là association; có regression to the mean, survivorship bias (RQ4) và censoring (không có lần học kế tiếp ≠ rớt tiếp).
7. **Loại bỏ cặp thiếu điểm** (1,272/12,058 cặp = 10.5%): nếu việc thiếu điểm không ngẫu nhiên thì kết quả có thể lệch.
8. **Một split cố định (seed 42):** khác biệt nhỏ giữa mô hình có thể đổi khi đổi split; CI bootstrap chỉ phản ánh biến thiên mẫu test.
9. **Một sinh viên có nhiều cặp** (10,786 cặp / 5,788 sinh viên): đã xử lý bằng group split và CV, nhưng độc lập hoàn toàn giữa các cặp vẫn chưa chắc.
10. **Kiểm tra RQ2 bằng logistic là phân tích bổ sung** (dùng 12,057 cặp, trong đó 1,238 cặp thiếu `initial_failure_total` được impute bằng median), chưa nằm trong pipeline chính.

### 7.3 Nhật ký các điểm cần xác minh lại

| ID | Vấn đề | Chi tiết | Đề xuất / người xác minh |
|---|---|---|---|
| V1 | **Cột CV trong `Regression_Results.csv` không tái lập được** | CSV: Ridge 2.4762 ± 0.0283, GB 2.4506 ± 0.0325, Dummy 2.7028 ± 0.0523. Chạy lại: Ridge 2.4773 ± 0.0433, GB 2.4548 ± 0.0409, Dummy 2.7031 ± 0.0503. Số chạy lại **trùng với bảng trong `TV1_Week4_Summary.md`**, còn CSV thì khác (có thể do khác phiên bản scikit-learn/cách chia fold của `GroupKFold`). Cột Test thì khớp. | TV1 chạy lại và chốt một bộ số duy nhất trước Week 5. |
| V2 | Dòng Ridge trong CSV dùng alpha = 1.0, không phải alpha tối ưu 0.1 | Chênh lệch không đáng kể (< 1e-5 RMSE) nhưng báo cáo nên ghi rõ alpha. | TV1 ghi chú alpha vào bảng kết quả. |
| V3 | **Tài liệu và file không nhất quán** | Summary/checklist nhắc `Regression_Results_MASTER.csv`, `TV1_Data_Leakage_Check.md`, `INSTALL_WEEK4.bat`, cột `Owner_Assignment`; trong thư mục thực tế chỉ có `Regression_Results.csv` (không có cột này) và `.bat` tên khác. | TV1 bổ sung hoặc sửa tên. |
| V4 | **Chưa có kết quả độc lập từ TV2/TV3** | Checklist: TV2 (Lasso) và TV3 (RF, GB) chưa tick; `TEST_RUN_OK.txt` ghi nhận chạy trong "ChatGPT container". Lần kiểm tra này đã tái lập số Test, nhưng chưa phải do chủ sở hữu mô hình xác nhận. | TV2, TV3 chạy lại và gửi metrics. |
| V5 | **829 cặp (7.7%) có `score_delta = 0` chính xác** | 395 là cặp 0 → 0; 434 cặp có điểm đầu > 0 nhưng điểm kế tiếp **đúng bằng** điểm đầu (371 vẫn FAIL_ACADEMIC, 34 PASS, 28 FAIL_ATTENDANCE; 399 ở time_gap = 1). Cần kiểm tra điểm có bị sao chép/giữ nguyên giữa các lần không. | TV2/TV3 kiểm tra trong dữ liệu gốc. |
| V6 | **`initial_failure_total = 0` ở 1,265 cặp (11.7%)** | Chưa rõ 0 là điểm thật, bỏ thi, hay mã thay cho thiếu điểm. Ảnh hưởng residual (nhóm ATTENDANCE có SD 2.97). | TV2 xác nhận ý nghĩa của điểm 0. |
| V7 | **Môn có n rất nhỏ** | LAB211 (4 cặp, đều delta = 0), DAP391M (16), PRF193 (14), ADY201M (21). Hệ số one-hot không ổn định. | Gộp thành nhóm "Other" hoặc loại khỏi mô hình. |
| V8 | `time_gap` và `prior_attempt_count` | `time_gap` biết sau khi học lại; `prior_attempt_count` có 5 giá trị khác 0. Nên quyết định giữ hay bỏ ở bản mô hình cuối. | Cả nhóm thống nhất trước Week 5. |

---

## 8. Cập nhật trạng thái checklist TV4 (Week 4)

- [x] Confirm final model comparison table (có lưu ý V1, V2)
- [x] Predicted vs Actual chart
- [x] Residual plot
- [x] Feature importance / coefficient interpretation
- [x] Write limitations
- [x] Leakage check và nhật ký xác minh

> Ghi chú: phần AI Audit Log không nằm trong tài liệu này.
