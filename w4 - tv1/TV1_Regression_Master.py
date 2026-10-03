# TV1 Week 4 — Regression Master
# Chạy file này từ thư mục Week4/TV1_Regression.
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE = Path(__file__).resolve().parent
canonical = BASE.parent / 'model_ready_v1.csv'
fallback = BASE.parent / 'model_ready_v1_TV1_fallback.csv'
DATA = canonical if canonical.exists() else fallback
print('Using:', DATA)
df = pd.read_csv(DATA)

features = ['initial_failure_total','initial_failure_type','time_gap','prior_attempt_count','course_id']
target = 'score_delta'
forbidden = {'next_attempt_total','next_status_group','pass_next_attempt','score_delta'}
assert not (set(features) & forbidden), 'DATA LEAKAGE: forbidden feature detected.'

X = df[features]
y = df[target]
groups = df['student_id']

# Group-aware split: cùng student không được xuất hiện ở cả train và test.
gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=groups))
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
groups_train = groups.iloc[train_idx]

numeric = ['initial_failure_total','time_gap','prior_attempt_count']
categorical = ['initial_failure_type','course_id']
preprocessor = ColumnTransformer([
    ('num', Pipeline([('imputer',SimpleImputer(strategy='median')),('scaler',StandardScaler())]), numeric),
    ('cat', Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]), categorical)
])

def pipe(model):
    return Pipeline([('preprocessor', preprocessor), ('model', model)])

models = {
    'Dummy Baseline': pipe(DummyRegressor(strategy='mean')),
    'Linear Regression': pipe(LinearRegression()),
    'Ridge Regression': pipe(Ridge(alpha=1.0)),
    'Lasso Regression': pipe(Lasso(alpha=0.01, max_iter=10000)),
    'Random Forest': pipe(RandomForestRegressor(n_estimators=200,max_depth=12,random_state=42,n_jobs=-1)),
    'Gradient Boosting': pipe(GradientBoostingRegressor(n_estimators=150,learning_rate=0.05,max_depth=3,random_state=42)),
}

gkf = GroupKFold(n_splits=5)
rows=[]
for name, model in models.items():
    cv = -cross_val_score(model, X_train, y_train, groups=groups_train, cv=gkf,
                          scoring='neg_root_mean_squared_error', n_jobs=-1)
    model.fit(X_train,y_train)
    pred=model.predict(X_test)
    rows.append({
        'Model':name,
        'CV_RMSE_Mean':cv.mean(),
        'CV_RMSE_SD':cv.std(),
        'Test_MAE':mean_absolute_error(y_test,pred),
        'Test_RMSE':mean_squared_error(y_test,pred)**0.5,
        'Test_R2':r2_score(y_test,pred)
    })

results=pd.DataFrame(rows)
print(results.sort_values('Test_RMSE').to_string(index=False))
results.to_csv(BASE.parent/'Regression_Results_rerun.csv',index=False)

# Ridge tuning
ridge=pipe(Ridge())
grid=GridSearchCV(ridge, {'model__alpha':[0.01,0.1,1,10,100]}, cv=gkf,
                  scoring='neg_root_mean_squared_error', n_jobs=-1)
grid.fit(X_train,y_train,groups=groups_train)
print('Best Ridge params:', grid.best_params_)
print('Best Ridge CV RMSE:', -grid.best_score_)
