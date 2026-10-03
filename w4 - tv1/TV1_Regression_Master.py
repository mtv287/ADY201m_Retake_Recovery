# ============================================================
# TV1 WEEK 4 — REGRESSION MASTER (FIXED)
# Project: Retake Behavior & Recovery Analysis
# ============================================================
# Cách chạy trên Windows:
#   1) py -m pip install -r "..\requirements.txt"
#   2) py TV1_Regression_Master.py
#
# File này đã sửa:
# - Không phụ thuộc thư mục chạy hiện tại.
# - Tự tìm project root.
# - Dùng model_ready_v1.csv nếu có; nếu thiếu sẽ tạo từ
#   data_processed/retake_pairs_v1.csv.
# - Có thông báo rõ nếu thiếu scikit-learn.
# ============================================================

from pathlib import Path
import sys

# -------- 0. Kiểm tra thư viện --------
try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score, GridSearchCV
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import LinearRegression, Ridge, Lasso
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except ModuleNotFoundError as e:
    print("\n[ERROR] Thiếu thư viện Python:", e)
    print("Hãy chạy trong Terminal của VS Code:")
    print(r'  py -m pip install pandas numpy matplotlib scikit-learn')
    print("Sau đó chạy lại file này bằng cùng Python interpreter.")
    sys.exit(1)

# -------- 1. Xác định đường dẫn project --------
def find_project_root(start: Path) -> Path:
    """Tìm thư mục chứa data_processed/retake_pairs_v1.csv."""
    start = start.resolve()
    candidates = [start] + list(start.parents)
    for p in candidates:
        if (p / 'data_processed' / 'retake_pairs_v1.csv').exists():
            return p
    # Trường hợp chạy từ folder cha của project
    for child in start.iterdir() if start.exists() else []:
        if child.is_dir() and (child / 'data_processed' / 'retake_pairs_v1.csv').exists():
            return child
    raise FileNotFoundError(
        "Không tìm thấy project root. Cần có file data_processed/retake_pairs_v1.csv."
    )

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = find_project_root(SCRIPT_DIR)
W4_DIR = SCRIPT_DIR
SOURCE_DATA = PROJECT_ROOT / 'data_processed' / 'retake_pairs_v1.csv'
MODEL_READY = W4_DIR / 'model_ready_v1.csv'
OUTPUT_RESULTS = W4_DIR / 'Regression_Results.csv'
OUTPUT_TUNING = W4_DIR / 'Ridge_Tuning_Results.csv'
FIG_DIR = W4_DIR / 'figures'
FIG_DIR.mkdir(exist_ok=True)

print('Project root :', PROJECT_ROOT)
print('Week 4 folder:', W4_DIR)

# -------- 2. Tạo / đọc model-ready dataset --------
features = [
    'initial_failure_total',
    'initial_failure_type',
    'time_gap',
    'prior_attempt_count',
    'course_id'
]
target = 'score_delta'
required_cols = ['student_id'] + features + [target]

if MODEL_READY.exists():
    df = pd.read_csv(MODEL_READY)
    print('Using existing model-ready file:', MODEL_READY)
else:
    source_df = pd.read_csv(SOURCE_DATA)
    missing_cols = [c for c in required_cols if c not in source_df.columns]
    if missing_cols:
        raise ValueError(f'Missing required columns in retake_pairs_v1.csv: {missing_cols}')
    df = source_df[required_cols].copy()
    # score_delta cần có để dùng làm regression target
    df = df.dropna(subset=[target, 'student_id']).reset_index(drop=True)
    df.to_csv(MODEL_READY, index=False)
    print('Created model-ready file:', MODEL_READY)

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f'Model-ready file is missing columns: {missing_cols}')

# Luôn loại target missing để tránh sklearn lỗi
before = len(df)
df = df.dropna(subset=[target, 'student_id']).reset_index(drop=True)
print(f'Model rows   : {len(df):,} (removed {before-len(df):,} rows with missing target/student_id)')
print(f'Unique students: {df["student_id"].nunique():,}')

# -------- 3. Data leakage check --------
forbidden = {'next_attempt_total', 'next_status_group', 'pass_next_attempt', 'score_delta'}
leaked = set(features) & forbidden
if leaked:
    raise ValueError(f'DATA LEAKAGE: forbidden predictor(s): {sorted(leaked)}')
print('Leakage feature check: PASSED')

X = df[features].copy()
y = df[target].copy()
groups = df['student_id'].copy()

# -------- 4. Group-aware train/test split --------
gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=groups))
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
groups_train, groups_test = groups.iloc[train_idx], groups.iloc[test_idx]

overlap = set(groups_train) & set(groups_test)
print('Train rows      :', len(train_idx))
print('Test rows       :', len(test_idx))
print('Train students  :', groups_train.nunique())
print('Test students   :', groups_test.nunique())
print('Student overlap :', len(overlap))
assert len(overlap) == 0, 'Student leakage between train and test!'

# -------- 5. Preprocessing --------
numeric_features = ['initial_failure_total', 'time_gap', 'prior_attempt_count']
categorical_features = ['initial_failure_type', 'course_id']

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer([
    ('num', numeric_transformer, numeric_features),
    ('cat', categorical_transformer, categorical_features)
])

def make_pipeline(model):
    return Pipeline([
        ('preprocessor', preprocessor),
        ('model', model)
    ])

# -------- 6. Baseline + 5 regression models --------
models = {
    'Dummy Baseline': make_pipeline(DummyRegressor(strategy='mean')),
    'Linear Regression': make_pipeline(LinearRegression()),
    'Ridge Regression': make_pipeline(Ridge(alpha=1.0)),
    'Lasso Regression': make_pipeline(Lasso(alpha=0.01, max_iter=10000)),
    'Random Forest': make_pipeline(RandomForestRegressor(
        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
    )),
    'Gradient Boosting': make_pipeline(GradientBoostingRegressor(
        n_estimators=150, learning_rate=0.05, max_depth=3, random_state=42
    ))
}

# -------- 7. 5-fold Group CV + test metrics --------
gkf = GroupKFold(n_splits=5)
results = []
fitted_models = {}

for name, model in models.items():
    print(f'\nTraining: {name}')
    cv_rmse = -cross_val_score(
        model,
        X_train,
        y_train,
        groups=groups_train,
        cv=gkf,
        scoring='neg_root_mean_squared_error',
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    results.append({
        'Model': name,
        'CV_RMSE_Mean': cv_rmse.mean(),
        'CV_RMSE_SD': cv_rmse.std(),
        'Test_MAE': mean_absolute_error(y_test, pred),
        'Test_RMSE': mean_squared_error(y_test, pred) ** 0.5,
        'Test_R2': r2_score(y_test, pred)
    })
    fitted_models[name] = model

results_df = pd.DataFrame(results).sort_values('Test_RMSE').reset_index(drop=True)
print('\n===== MODEL RESULTS =====')
print(results_df.round(4).to_string(index=False))
results_df.to_csv(OUTPUT_RESULTS, index=False)
print('Saved:', OUTPUT_RESULTS)

# -------- 8. Ridge tuning --------
ridge_pipe = make_pipeline(Ridge())
param_grid = {'model__alpha': [0.01, 0.1, 1, 10, 100]}

grid = GridSearchCV(
    ridge_pipe,
    param_grid,
    cv=gkf,
    scoring='neg_root_mean_squared_error',
    n_jobs=-1,
    return_train_score=False
)
grid.fit(X_train, y_train, groups=groups_train)

ridge_tuning_df = pd.DataFrame({
    'alpha': [p['model__alpha'] for p in grid.cv_results_['params']],
    'CV_RMSE': -grid.cv_results_['mean_test_score'],
    'CV_RMSE_SD': grid.cv_results_['std_test_score'],
    'rank': grid.cv_results_['rank_test_score']
}).sort_values('rank')
ridge_tuning_df.to_csv(OUTPUT_TUNING, index=False)

print('\nBest Ridge alpha   :', grid.best_params_['model__alpha'])
print('Best Ridge CV RMSE :', -grid.best_score_)
print('Saved:', OUTPUT_TUNING)

# -------- 9. Model comparison chart --------
plot_df = results_df.sort_values('Test_RMSE')
plt.figure(figsize=(9, 5))
plt.bar(plot_df['Model'], plot_df['Test_RMSE'])
plt.title('Week 4 Model Comparison - Test RMSE')
plt.ylabel('RMSE (lower is better)')
plt.xlabel('Model')
plt.xticks(rotation=25)
plt.tight_layout()
chart_path = FIG_DIR / 'model_comparison_rmse.png'
plt.savefig(chart_path, dpi=160)
plt.close()
print('Saved chart:', chart_path)

print('\nDONE. Week 4 TV1 pipeline ran successfully.')
