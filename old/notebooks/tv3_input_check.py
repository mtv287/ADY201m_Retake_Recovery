import pandas as pd
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
file_path = os.path.join(base_dir, "data_processed", "clean_attempts_v1.csv")

df = pd.read_csv(file_path, low_memory=False)

print("=== TV3 INPUT CHECK ===")
print("Rows:", len(df))
print("Unique students:", df["student_id"].nunique())
print("Courses:", df["course_id"].nunique())
print("Semesters:", df["semester"].nunique())

traj = (
    df.groupby(["student_id", "course_id"])
      .size()
      .reset_index(name="attempt_count_check")
)

print("Student-Course trajectories:", len(traj))
print(">=2 attempts:", (traj["attempt_count_check"] >= 2).sum())
print(">=3 attempts:", (traj["attempt_count_check"] >= 3).sum())
print(">=4 attempts:", (traj["attempt_count_check"] >= 4).sum())

print("\nStatus groups:")
print(df["status_group"].value_counts(dropna=False))

print("\nMissing total_score:", df["total_score"].isna().sum())

# Check attempt_no sequence
ordered = df.sort_values(["student_id", "course_id", "semester_order"]).copy()
ordered["expected_attempt_no"] = (
    ordered.groupby(["student_id", "course_id"]).cumcount() + 1
)
bad_attempt = ordered[ordered["attempt_no"] != ordered["expected_attempt_no"]]
print("Attempt_no mismatch rows:", len(bad_attempt))

print("\nNếu các số trên khớp QA handoff thì TV3 có thể bắt đầu feature engineering.")
