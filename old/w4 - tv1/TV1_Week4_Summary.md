# TV1 Week 4 — Regression Master Summary

## 1. Mục tiêu
Theo kế hoạch môn học, Week 4 cần **so sánh 5 mô hình với baseline, dùng cross-validation và tuning, đồng thời kiểm tra data leakage**.

TV1 chịu trách nhiệm xây dựng pipeline chung và chạy phần cốt lõi: **Dummy Baseline, Linear Regression, Ridge Regression**, thiết lập split/CV chung, tuning Ridge và tổng hợp bảng kết quả master. Để nhóm có kết quả tham chiếu ngay, notebook master cũng chạy Lasso, Random Forest và Gradient Boosting; TV2/TV3 vẫn nên chạy lại model được phân công trong notebook của mình.

## 2. Dataset dùng cho modeling
- Nguồn: `data_processed/retake_pairs_v1.csv` trong bản course-code-updated.
- Tổng retake pairs: 12,058
- Rows có `score_delta` đầy đủ dùng cho regression: 10,786
- Unique students trong modeling set: 5,788
- Train rows: 8,557
- Test rows: 2,229
- Train students: 4,630
- Test students: 1,158
- Student overlap train/test: 0

## 3. Target và predictors
**Target:** `score_delta = next_attempt_total - initial_failure_total`

Predictors:
- `initial_failure_total`
- `initial_failure_type`
- `time_gap`
- `prior_attempt_count`
- `course_id`

`prior_attempt_count` có rất ít biến thiên trong first-failure cohort (đa số bằng 0), vì vậy cần xem đây là một limitation khi diễn giải.

## 4. Data leakage check
Không dùng các cột sau làm predictor:
- `next_attempt_total`
- `next_status_group`
- `pass_next_attempt`
- `score_delta` trong X

Ngoài ra, split được thực hiện theo **student_id** bằng `GroupShuffleSplit`, nên cùng một sinh viên không xuất hiện đồng thời ở train và test.

## 5. Cross-validation
- 5-fold `GroupKFold`
- Group = `student_id`
- Metric dùng cho CV: RMSE
- Mục đích: giảm nguy cơ đánh giá quá lạc quan do một sinh viên xuất hiện ở nhiều Student-Course trajectories.

## 6. Kết quả tham chiếu
| Model             | Owner_Assignment   |   CV_RMSE_Mean |   CV_RMSE_SD |   Test_MAE |   Test_RMSE |   Test_R2 |
|:------------------|:-------------------|---------------:|-------------:|-----------:|------------:|----------:|
| Dummy Baseline    | TV1                |         2.7031 |       0.0503 |     2.1844 |      2.7147 |   -0.0006 |
| Linear Regression | TV1                |         2.4772 |       0.0432 |     2.0785 |      2.4957 |    0.1543 |
| Ridge Regression  | TV1                |         2.4773 |       0.0433 |     2.0791 |      2.4957 |    0.1543 |
| Lasso Regression  | TV2                |         2.4818 |       0.0467 |     2.0885 |      2.5038 |    0.1488 |
| Random Forest     | TV3                |         2.4911 |       0.0485 |     2.069  |      2.5202 |    0.1376 |
| Gradient Boosting | TV3                |         2.4548 |       0.0409 |     2.0555 |      2.4895 |    0.1585 |

### Ridge tuning
- Grid alpha: 0.01, 0.1, 1, 10, 100
- Best alpha: **0.1**
- Best CV RMSE: **2.4772**
- Tuned Ridge test MAE: **2.0786**
- Tuned Ridge test RMSE: **2.4957**
- Tuned Ridge test R²: **0.1543**

## 7. Cách đọc kết quả
- **MAE thấp hơn**: sai số tuyệt đối trung bình nhỏ hơn.
- **RMSE thấp hơn**: model ít bị các sai số lớn hơn.
- **R² cao hơn**: model giải thích được nhiều biến thiên của `score_delta` hơn.
- Baseline là mốc tối thiểu; model học được pattern nên cần vượt baseline một cách nhất quán trên CV/test.

Trong lần chạy tham chiếu này, **Gradient Boosting** có Test RMSE thấp nhất trong các cấu hình đã chạy. Đây chỉ là kết quả cho split và hyperparameter hiện tại, không phải kết luận nhân quả hay khẳng định mô hình tối ưu tuyệt đối.

## 8. Files bàn giao
- `TV1_Regression_Master.ipynb`
- `TV1_Regression_Master.py`
- `Regression_Results.csv`
- `Regression_Results_MASTER.csv`
- `Ridge_Tuning_Results.csv`
- `model_ready_v1.csv` (generated from `data_processed/retake_pairs_v1.csv`)
- `TV1_Data_Leakage_Check.md`
- `Week4_Group_Checklist.md`
- `figures/`


## 9. Fixes added in corrected version
- Added `requirements.txt` and `INSTALL_WEEK4.bat` for missing `sklearn`.
- Fixed dataset path logic; no longer looks for nonexistent `model_ready_v1_TV1_fallback.csv`.
- Notebook outputs/errors were cleared.
- Added a guard so the chart explains that `results_df` must be created first instead of raising a confusing NameError.
