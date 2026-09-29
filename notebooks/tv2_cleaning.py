import pandas as pd
import os

STATUS_MAP = {
    "Passed": "Passed",
    "Pass": "Passed",
    "Passe": "Passed",
    "Not Passed": "Not Passed",
    "Not Passe": "Not Passed",
    "Attendance Fail": "Attendance Fail",
    "Attendance Fai": "Attendance Fail",
    "Is Susspended": "Is Suspended",
    "Is Susspende": "Is Suspended",
    "Is Suspended": "Is Suspended",
    "Is Exempt": "Is Exempt",
    "Is exempt": "Is Exempt",
}

GROUP_MAP = {
    "Passed": "PASS",
    "Not Passed": "FAIL_ACADEMIC",
    "Attendance Fail": "FAIL_ATTENDANCE",
    "Is Suspended": "SUSPENDED",
    "Is Exempt": "EXEMPT",
}

DESCRIPTIONS = {
    "course_id": "Mã môn học đã decode (ví dụ ADY201M, CSD201, DBI202); dùng làm định danh course trong phân tích.",
    "source_file": "Tên file CSV nguồn để truy vết.",
    "source_row": "Số dòng gốc trong source file sau header.",
    "semester": "Mã học kỳ, ví dụ SP2023, SU2023, FA2023.",
    "class_id": "Mã lớp trong file nguồn.",
    "source_no": "Số thứ tự sinh viên trong bảng nguồn.",
    "student_id": "Mã sinh viên ẩn danh lấy từ CODE.",
    "total_score": "Điểm tổng kết môn; có thể missing.",
    "status_raw": "STATUS nguyên gốc, không ghi đè.",
    "semester_order": "Thứ tự số để sắp xếp học kỳ theo thời gian.",
    "duplicate_count": "Số records có cùng course_id + student_id + semester trong master_raw.",
    "is_duplicate_candidate": "Cờ record thuộc nhóm duplicate candidate.",
    "attempt_no": "Số thứ tự lần quan sát Student-Course sau candidate dedup.",
    "status_clean": "STATUS chuẩn hóa chính tả nhưng giữ nghĩa gốc.",
    "status_group": "Nhóm PASS / FAIL_ACADEMIC / FAIL_ATTENDANCE / SUSPENDED / EXEMPT / REVIEW.",
    "needs_status_review": "1 nếu STATUS chưa đủ rõ để tự động map.",
    "score_missing_flag": "1 nếu total_score missing.",
}

def normalize_status(value):
    raw = "" if pd.isna(value) else str(value).strip()
    clean = STATUS_MAP.get(raw, "REVIEW_STATUS")
    group = GROUP_MAP.get(clean, "REVIEW")
    return clean, group, int(group == "REVIEW")

def run_tv2_cleaning():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "data_processed")

    master_raw_file = os.path.join(processed_dir, "master_raw.csv")
    sql_ready_file = os.path.join(processed_dir, "master_sql_ready.csv")

    output_csv = os.path.join(processed_dir, "clean_attempts_v1.csv")
    output_duplicates = os.path.join(processed_dir, "duplicate_candidates_tv2.csv")
    output_report = os.path.join(processed_dir, "Missing_Duplicate_Report.txt")
    output_dict = os.path.join(processed_dir, "Data_Dictionary.md")

    if not os.path.exists(master_raw_file) or not os.path.exists(sql_ready_file):
        raise FileNotFoundError("Thiếu master_raw.csv hoặc master_sql_ready.csv trong data_processed.")

    print("Đang đọc master_raw.csv và master_sql_ready.csv...")
    raw = pd.read_csv(master_raw_file, low_memory=False)
    clean = pd.read_csv(sql_ready_file, low_memory=False)

    raw.columns = raw.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    clean.columns = clean.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)

    # 1) Duplicate audit: SAME Course + Student + Semester
    duplicate_key = ["course_id", "student_id", "semester"]
    extra_duplicate_rows = int(raw.duplicated(subset=duplicate_key, keep="first").sum())

    dup_groups = raw[raw.duplicated(subset=duplicate_key, keep=False)].copy()
    dup_groups["duplicate_key_count"] = (
        dup_groups.groupby(duplicate_key)["student_id"].transform("size")
    )
    dup_groups["review_action"] = ""
    dup_groups["review_note"] = ""
    dup_groups = dup_groups.sort_values(duplicate_key + ["source_row"])
    dup_groups.to_csv(output_duplicates, index=False, encoding="utf-8-sig")

    # 2) Status normalization. Preserve status_raw.
    normalized = clean["status_raw"].apply(normalize_status)
    clean["status_clean"] = normalized.apply(lambda x: x[0])
    clean["status_group"] = normalized.apply(lambda x: x[1])
    clean["needs_status_review"] = normalized.apply(lambda x: x[2])

    # 3) Missing score: audit only, DO NOT impute.
    clean["score_missing_flag"] = clean["total_score"].isna().astype(int)

    clean.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # 4) QA summaries
    trajectory = (
        clean.groupby(["student_id", "course_id"])
        .size()
        .reset_index(name="attempt_count_check")
    )
    semester_table = (
        clean[["semester", "semester_order"]]
        .drop_duplicates()
        .sort_values("semester_order")
    )

    # 5) Report
    with open(output_report, "w", encoding="utf-8") as f:
        f.write("=== BÁO CÁO DATA CLEANING & QA (TV2) ===\n\n")
        f.write("1. DUPLICATE AUDIT\n")
        f.write(f"- Valid rows trong master_raw.csv: {len(raw):,}\n")
        f.write("- Duplicate key: course_id + student_id + semester\n")
        f.write(f"- Extra duplicate candidate rows: {extra_duplicate_rows:,}\n")
        f.write(f"- Tổng rows nằm trong duplicate groups: {len(dup_groups):,}\n")
        f.write(f"- Candidate rows sau dedup: {len(clean):,}\n")
        f.write("- master_raw.csv được giữ nguyên; duplicate chỉ được flag/review.\n\n")

        f.write("2. MISSING VALUES\n")
        f.write(f"- total_score missing trong master_raw: {raw['total_score'].isna().sum():,}\n")
        f.write(f"- total_score missing trong clean_attempts_v1: {clean['total_score'].isna().sum():,}\n")
        f.write("- Không impute mean/median ở Week 2.\n\n")

        f.write("3. STATUS NORMALIZATION\n")
        for value, count in clean["status_clean"].value_counts(dropna=False).items():
            f.write(f"- {value}: {count:,}\n")
        f.write("\nStatus groups:\n")
        for value, count in clean["status_group"].value_counts(dropna=False).items():
            f.write(f"- {value}: {count:,}\n")
        f.write("- REVIEW phải kiểm tra thủ công trước khi đưa vào recovery analysis.\n\n")

        f.write("4. QA SUMMARY FOR TV3\n")
        f.write(f"- Clean rows: {len(clean):,}\n")
        f.write(f"- Unique students: {clean['student_id'].nunique():,}\n")
        f.write(f"- Decoded course codes: {clean['course_id'].nunique():,}\n")
        f.write(f"- Unique semesters: {clean['semester'].nunique():,}\n")
        f.write(f"- Semester range: {semester_table.iloc[0]['semester']} -> {semester_table.iloc[-1]['semester']}\n")
        f.write(f"- Student-Course trajectories: {len(trajectory):,}\n")
        f.write(f"- Trajectories >=2 attempts: {(trajectory['attempt_count_check'] >= 2).sum():,}\n")
        f.write(f"- Trajectories >=3 attempts: {(trajectory['attempt_count_check'] >= 3).sum():,}\n")
        f.write(f"- Trajectories >=4 attempts: {(trajectory['attempt_count_check'] >= 4).sum():,}\n")

    # 6) Data Dictionary
    with open(output_dict, "w", encoding="utf-8") as f:
        f.write("# Data Dictionary - Clean Dataset V1 (TV2)\n\n")
        f.write("**Dataset dùng cho TV3:** `clean_attempts_v1.csv`\n\n")
        f.write("| Tên cột | Kiểu dữ liệu | Mô tả |\n|---|---|---|\n")
        for col in clean.columns:
            f.write(f"| `{col}` | {clean[col].dtype} | {DESCRIPTIONS.get(col, 'Cột kỹ thuật/provenance từ TV1.')} |\n")
        f.write("\n## Quy tắc\n")
        f.write("- Không dùng TOTAL >= 5 để tự suy ra Pass/Fail.\n")
        f.write("- EXEMPT không thuộc failure cohort.\n")
        f.write("- REVIEW cần kiểm tra trước khi dùng.\n")
        f.write("- Không impute total_score ở Week 2.\n")
        f.write("- Không dùng future Total_Attempts làm predictor cho next-attempt recovery.\n")

    print("✓ Hoàn thành TV2 cleaning.")
    print(f"  master_raw rows: {len(raw):,}")
    print(f"  extra duplicate candidate rows: {extra_duplicate_rows:,}")
    print(f"  clean rows: {len(clean):,}")
    print(f"  output: {output_csv}")
    print(f"  duplicate review: {output_duplicates}")
    print(f"  report: {output_report}")
    print(f"  dictionary: {output_dict}")

if __name__ == "__main__":
    run_tv2_cleaning()
