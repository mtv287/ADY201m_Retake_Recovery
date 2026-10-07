import pandas as pd
import numpy as np
import os


# ============================================================
# TV3 - FEATURE ENGINEERING & VALIDATION
# Retake Behavior & Recovery Analysis
# ============================================================


def get_project_dir():
    """
    Script có thể nằm trong:
    project/notebooks/tv3_feature_engineering.py
    hoặc ngay trong project/
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if os.path.basename(script_dir).lower() == "notebooks":
        return os.path.dirname(script_dir)

    return script_dir


def main():

    # ========================================================
    # 1. PATH
    # ========================================================

    project_dir = get_project_dir()

    processed_dir = os.path.join(
        project_dir,
        "data_processed"
    )

    input_file = os.path.join(
        processed_dir,
        "clean_attempts_v1.csv"
    )

    output_pairs = os.path.join(
        processed_dir,
        "retake_pairs_v1.csv"
    )

    output_definitions = os.path.join(
        processed_dir,
        "Feature_Definitions.md"
    )

    output_report = os.path.join(
        processed_dir,
        "TV3_Validation_Report.txt"
    )

    output_sample = os.path.join(
        processed_dir,
        "TV3_Manual_Check_Sample.csv"
    )

    print("=" * 60)
    print("TV3 - FEATURE ENGINEERING & VALIDATION")
    print("=" * 60)

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Không tìm thấy:\n{input_file}"
        )

    # ========================================================
    # 2. LOAD DATA
    # ========================================================

    df = pd.read_csv(
        input_file,
        low_memory=False
    )

    print(f"\nInput rows: {len(df):,}")

    # ========================================================
    # 3. REQUIRED COLUMNS
    # ========================================================

    required_columns = [
        "student_id",
        "course_id",
        "semester",
        "semester_order",
        "attempt_no",
        "total_score",
        "status_group"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Thiếu các cột: "
            + ", ".join(missing_columns)
        )

    print("✓ Required columns OK")

    # ========================================================
    # 4. DATA TYPES
    # ========================================================

    df["semester_order"] = pd.to_numeric(
        df["semester_order"],
        errors="coerce"
    )

    df["attempt_no"] = pd.to_numeric(
        df["attempt_no"],
        errors="coerce"
    )

    df["total_score"] = pd.to_numeric(
        df["total_score"],
        errors="coerce"
    )

    # ========================================================
    # 5. SORT TRAJECTORIES
    # ========================================================

    sort_columns = [
        "student_id",
        "course_id",
        "semester_order"
    ]

    if "source_row" in df.columns:
        sort_columns.append("source_row")

    df = (
        df
        .sort_values(sort_columns)
        .reset_index(drop=True)
    )

    # ========================================================
    # 6. VALIDATE ATTEMPT NUMBER
    # ========================================================

    df["attempt_no_check"] = (
        df
        .groupby(
            ["student_id", "course_id"]
        )
        .cumcount()
        + 1
    )

    attempt_mismatch = (
        df["attempt_no"]
        != df["attempt_no_check"]
    ).sum()

    print(
        f"Attempt number mismatch: "
        f"{attempt_mismatch:,}"
    )

    # Dùng attempt number tính lại để đảm bảo đúng thứ tự
    df["attempt_no_used"] = (
        df["attempt_no_check"]
    )

    # ========================================================
    # 7. DEFINE STATUS
    # ========================================================

    failure_groups = [
        "FAIL_ACADEMIC",
        "FAIL_ATTENDANCE",
        "SUSPENDED"
    ]

    df["is_failure"] = (
        df["status_group"]
        .isin(failure_groups)
    )

    # ========================================================
    # 8. CREATE NEXT ATTEMPT FEATURES
    # ========================================================

    group_keys = [
        "student_id",
        "course_id"
    ]

    grouped = df.groupby(
        group_keys,
        sort=False
    )

    df["next_semester"] = (
        grouped["semester"]
        .shift(-1)
    )

    df["next_semester_order"] = (
        grouped["semester_order"]
        .shift(-1)
    )

    df["next_attempt_no"] = (
        grouped["attempt_no_used"]
        .shift(-1)
    )

    df["next_attempt_total"] = (
        grouped["total_score"]
        .shift(-1)
    )

    df["next_status_group"] = (
        grouped["status_group"]
        .shift(-1)
    )

    # ========================================================
    # 9. FIND FIRST OBSERVED FAILURE
    # ========================================================

    failure_df = df[
        df["is_failure"]
    ].copy()

    failure_df["failure_rank"] = (
        failure_df
        .groupby(group_keys)
        .cumcount()
        + 1
    )

    first_failure = failure_df[
        failure_df["failure_rank"] == 1
    ].copy()

    print(
        "First observed failures:",
        f"{len(first_failure):,}"
    )

    # Chỉ giữ first failure có next observed attempt
    retake_pairs = first_failure[
        first_failure["next_semester"].notna()
    ].copy()

    print(
        "First failures with next attempt:",
        f"{len(retake_pairs):,}"
    )

    # ========================================================
    # 10. FEATURE ENGINEERING
    # ========================================================

    # Điểm lần fail đầu tiên
    retake_pairs[
        "initial_failure_total"
    ] = retake_pairs["total_score"]

    # Loại failure
    retake_pairs[
        "initial_failure_type"
    ] = retake_pairs["status_group"]

    # Số attempts đã có trước lần failure này
    retake_pairs[
        "prior_attempt_count"
    ] = (
        retake_pairs["attempt_no_used"]
        - 1
    )

    # Khoảng cách học kỳ
    retake_pairs[
        "time_gap"
    ] = (
        retake_pairs["next_semester_order"]
        - retake_pairs["semester_order"]
    )

    # Điểm thay đổi
    retake_pairs[
        "score_delta"
    ] = (
        retake_pairs["next_attempt_total"]
        - retake_pairs["initial_failure_total"]
    )

    # ========================================================
    # 11. PASS NEXT ATTEMPT
    # ========================================================
    #
    # QUAN TRỌNG:
    # KHÔNG dùng next_score >= 5.
    #
    # PASS => 1
    #
    # Failure/Suspended => 0
    #
    # EXEMPT / REVIEW / unknown
    # => để missing, không ép thành fail.
    # ========================================================

    retake_pairs[
        "pass_next_attempt"
    ] = np.nan

    retake_pairs.loc[
        retake_pairs["next_status_group"] == "PASS",
        "pass_next_attempt"
    ] = 1

    retake_pairs.loc[
        retake_pairs[
            "next_status_group"
        ].isin(failure_groups),
        "pass_next_attempt"
    ] = 0

    retake_pairs[
        "pass_next_attempt"
    ] = retake_pairs[
        "pass_next_attempt"
    ].astype("Int64")

    # ========================================================
    # 12. SCORE COMPLETENESS FLAG
    # ========================================================

    retake_pairs[
        "complete_score_pair"
    ] = (
        retake_pairs[
            "initial_failure_total"
        ].notna()
        &
        retake_pairs[
            "next_attempt_total"
        ].notna()
    )

    # ========================================================
    # 13. RENAME OUTPUT COLUMNS
    # ========================================================

    retake_pairs[
        "failure_semester"
    ] = retake_pairs["semester"]

    retake_pairs[
        "failure_semester_order"
    ] = retake_pairs["semester_order"]

    retake_pairs[
        "failure_attempt_no"
    ] = retake_pairs["attempt_no_used"]

    # ========================================================
    # 14. FINAL OUTPUT COLUMNS
    # ========================================================

    final_columns = [
        "student_id",
        "course_id",

        "failure_semester",
        "failure_semester_order",
        "failure_attempt_no",

        "initial_failure_total",
        "initial_failure_type",

        "next_semester",
        "next_semester_order",
        "next_attempt_no",

        "next_attempt_total",
        "next_status_group",

        "score_delta",
        "pass_next_attempt",

        "time_gap",
        "prior_attempt_count",

        "complete_score_pair"
    ]

    retake_pairs = (
        retake_pairs[final_columns]
        .copy()
    )

    # ========================================================
    # 15. VALIDATION
    # ========================================================

    invalid_gap = (
        retake_pairs["time_gap"] <= 0
    ).sum()

    complete_score_pairs = (
        retake_pairs[
            "complete_score_pair"
        ].sum()
    )

    classification_pairs = (
        retake_pairs[
            "pass_next_attempt"
        ].notna()
        .sum()
    )

    recovered = (
        retake_pairs[
            "pass_next_attempt"
        ]
        == 1
    ).sum()

    not_recovered = (
        retake_pairs[
            "pass_next_attempt"
        ]
        == 0
    ).sum()

    # ========================================================
    # 16. EXPORT RETAKE PAIRS
    # ========================================================

    retake_pairs.to_csv(
        output_pairs,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 17. MANUAL VALIDATION SAMPLE
    # ========================================================

    sample_size = min(
        30,
        len(retake_pairs)
    )

    if sample_size > 0:

        manual_sample = (
            retake_pairs
            .sample(
                n=sample_size,
                random_state=42
            )
            .sort_values(
                [
                    "student_id",
                    "course_id"
                ]
            )
        )

        manual_sample.to_csv(
            output_sample,
            index=False,
            encoding="utf-8-sig"
        )

    # ========================================================
    # 18. FEATURE DEFINITIONS
    # ========================================================

    feature_text = """
# Feature Definitions - TV3

## Unit of analysis

One row represents:

**First observed failure -> next observed attempt**

for one Student-Course trajectory.

| Feature | Definition |
|---|---|
| `student_id` | Student identifier |
| `course_id` | Decoded FPT course code (e.g., ADY201M, CSD201, DBI202) |
| `failure_semester` | Semester of first observed failure |
| `failure_semester_order` | Numeric chronological order of failure semester |
| `failure_attempt_no` | Attempt number of first observed failure |
| `initial_failure_total` | Total score at first observed failure |
| `initial_failure_type` | Failure type: academic, attendance, or suspended |
| `next_semester` | Semester of next observed attempt |
| `next_semester_order` | Numeric order of next semester |
| `next_attempt_no` | Attempt number of next observed attempt |
| `next_attempt_total` | Total score of next observed attempt |
| `next_status_group` | Outcome status of next observed attempt |
| `score_delta` | Next_Attempt_Total - Initial_Failure_Total |
| `pass_next_attempt` | 1 = PASS; 0 = observed failure/suspended; missing = exempt/review |
| `time_gap` | Next_Semester_Order - Failure_Semester_Order |
| `prior_attempt_count` | Number of attempts before first observed failure |
| `complete_score_pair` | True when both failure and next scores are available |

## Important rules

- Pass/Fail is determined from `status_group`, not from `total_score >= 5`.
- `EXEMPT` is not considered a failure.
- `REVIEW` is not automatically classified.
- Missing total scores are not imputed.
- Score Delta is only valid when both scores are available.

## Leakage warning

Do NOT use the following variables as predictors for next-attempt recovery:

- `next_attempt_total`
- `next_status_group`
- `score_delta`
- `pass_next_attempt`
- total number of future attempts in the full trajectory

They contain future information.
"""

    with open(
        output_definitions,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(feature_text.strip())

    # ========================================================
    # 19. VALIDATION REPORT
    # ========================================================

    trajectory = (
        df
        .groupby(
            ["student_id", "course_id"]
        )
        .size()
        .reset_index(
            name="attempt_count"
        )
    )

    report = f"""
============================================================
TV3 VALIDATION REPORT
============================================================

1. INPUT DATA
------------------------------------------------------------
Rows:
{len(df):,}

Unique students:
{df["student_id"].nunique():,}

Courses:
{df["course_id"].nunique():,}

Semesters:
{df["semester"].nunique():,}

Student-Course trajectories:
{len(trajectory):,}

Trajectories >= 2 attempts:
{(trajectory["attempt_count"] >= 2).sum():,}

Trajectories >= 3 attempts:
{(trajectory["attempt_count"] >= 3).sum():,}

Trajectories >= 4 attempts:
{(trajectory["attempt_count"] >= 4).sum():,}


2. ATTEMPT VALIDATION
------------------------------------------------------------
Attempt number mismatch rows:
{attempt_mismatch:,}


3. FIRST FAILURE -> NEXT ATTEMPT
------------------------------------------------------------
First observed failures:
{len(first_failure):,}

First failures with next observed attempt:
{len(retake_pairs):,}

Complete score pairs:
{complete_score_pairs:,}

Valid classification pairs:
{classification_pairs:,}


4. RECOVERY OUTCOME
------------------------------------------------------------
Pass next attempt:
{recovered:,}

Not pass next attempt:
{not_recovered:,}


5. TIME GAP VALIDATION
------------------------------------------------------------
Time gap <= 0:
{invalid_gap:,}


6. MISSING SCORE
------------------------------------------------------------
Initial failure score missing:
{retake_pairs["initial_failure_total"].isna().sum():,}

Next attempt score missing:
{retake_pairs["next_attempt_total"].isna().sum():,}


7. FAILURE TYPE DISTRIBUTION
------------------------------------------------------------
{retake_pairs["initial_failure_type"].value_counts(dropna=False).to_string()}


8. NEXT STATUS DISTRIBUTION
------------------------------------------------------------
{retake_pairs["next_status_group"].value_counts(dropna=False).to_string()}


9. LEAKAGE CHECK
------------------------------------------------------------
Do NOT use these as predictors:
- next_attempt_total
- next_status_group
- score_delta
- pass_next_attempt
- future total attempts

Potential pre-outcome features:
- initial_failure_total
- initial_failure_type
- prior_attempt_count
- course_id
- time information known before outcome


10. MANUAL CHECK
------------------------------------------------------------
A random sample of {sample_size} retake pairs was exported to:

TV3_Manual_Check_Sample.csv

Please manually compare these rows with the original trajectory.
"""

    with open(
        output_report,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(report.strip())

    # ========================================================
    # 20. CONSOLE SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("TV3 COMPLETED")
    print("=" * 60)

    print(
        f"Retake pairs: "
        f"{len(retake_pairs):,}"
    )

    print(
        f"Complete score pairs: "
        f"{complete_score_pairs:,}"
    )

    print(
        f"Classification pairs: "
        f"{classification_pairs:,}"
    )

    print(
        f"Invalid time gaps: "
        f"{invalid_gap:,}"
    )

    print("\nFiles created:")

    print(
        "1.",
        os.path.basename(output_pairs)
    )

    print(
        "2.",
        os.path.basename(
            output_definitions
        )
    )

    print(
        "3.",
        os.path.basename(
            output_report
        )
    )

    print(
        "4.",
        os.path.basename(
            output_sample
        )
    )

    print("\nDone.")


if __name__ == "__main__":
    main()