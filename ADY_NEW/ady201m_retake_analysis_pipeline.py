import os, sqlite3, json
import pandas as pd
import numpy as np
from scipy import stats, optimize, special

np.random.seed(42)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retake_analysis.db")
conn = sqlite3.connect(DB_PATH)
valid = pd.read_sql_query("SELECT * FROM enrollments", conn)
pairs = pd.read_sql_query("SELECT * FROM retake_pairs", conn)
course_stats = pd.read_sql_query("SELECT * FROM course_summary", conn)
conn.close()

results = {}

# ==============================================================================
# STEP 4: INFERENTIAL STATISTICS & EMPIRICAL PROBABILITIES (WITH 95% WILSON CI)
# ==============================================================================
def wilson_ci(k, n, z=1.95996):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (p * 100, (center - half) * 100, (center + half) * 100)

failed1 = pairs[pairs['IS_FAIL'] == 1].copy()
retakers = failed1[failed1['RETOOK'] == 1].copy()
num_ret = retakers.dropna(subset=['TOTAL_1', 'TOTAL_2']).copy()

# 1. Paired tests on TOTAL_1 vs TOTAL_2 (n = 13,699)
t_stat, t_pval = stats.ttest_rel(num_ret['TOTAL_2'], num_ret['TOTAL_1'])
w_stat, w_pval = stats.wilcoxon(num_ret['TOTAL_2'] - num_ret['TOTAL_1'])
cohen_d = (num_ret['TOTAL_2'] - num_ret['TOTAL_1']).mean() / (num_ret['TOTAL_2'] - num_ret['TOTAL_1']).std(ddof=1)

# Also on FINAL_EXAM_1 vs FINAL_EXAM_2
fe_ret = retakers.dropna(subset=['FINAL_EXAM_1', 'FINAL_EXAM_2']).copy()
fe_t_stat, fe_t_pval = stats.ttest_rel(fe_ret['FINAL_EXAM_2'], fe_ret['FINAL_EXAM_1'])
fe_w_stat, fe_w_pval = stats.wilcoxon(fe_ret['FINAL_EXAM_2'] - fe_ret['FINAL_EXAM_1'])

print("=== STEP 4: INFERENTIAL STATISTICAL TESTS ===")
print(f"1. Paired Test on TOTAL Score (n={len(num_ret)}): Mean Att1={num_ret['TOTAL_1'].mean():.3f} -> Att2={num_ret['TOTAL_2'].mean():.3f}, Delta=+{num_ret['SCORE_CHANGE_TOTAL'].mean():.3f}")
print(f"   Paired t-test: t = {t_stat:.4f}, p = {t_pval:.4e}, Cohen's d = {cohen_d:.4f}")
print(f"   Wilcoxon signed-rank test: W = {w_stat:.1f}, p = {w_pval:.4e}")
print(f"2. Paired Test on FINAL EXAM Score (n={len(fe_ret)}): Mean FE1={fe_ret['FINAL_EXAM_1'].mean():.3f} -> FE2={fe_ret['FINAL_EXAM_2'].mean():.3f}, Delta=+{fe_ret['SCORE_CHANGE_FINAL'].mean():.3f}")
print(f"   Paired t-test: t = {fe_t_stat:.4f}, p = {fe_t_pval:.4e}")

# 2. Group comparisons: Not Passed vs Attendance Fail vs Is Suspended
g_np = num_ret[num_ret['STATUS_CLEAN_1'] == 'Not Passed']['SCORE_CHANGE_TOTAL']
g_af = num_ret[num_ret['STATUS_CLEAN_1'] == 'Attendance Fail']['SCORE_CHANGE_TOTAL']
g_su = num_ret[num_ret['STATUS_CLEAN_1'] == 'Is Suspended']['SCORE_CHANGE_TOTAL']
kw_fail_stat, kw_fail_pval = stats.kruskal(g_np, g_af, g_su)
mw_np_af_stat, mw_np_af_pval = stats.mannwhitneyu(g_np, g_af)

ct_fail_pass = pd.crosstab(retakers['STATUS_CLEAN_1'], retakers['PASS_RECOVERY_ATT2'])
chi2_fail, chi2_fail_p, chi2_fail_dof, _ = stats.chi2_contingency(ct_fail_pass)
print(f"3. Failure Type Comparison (Not Passed vs Attendance Fail vs Suspended):")
print(f"   Kruskal-Wallis on Score Delta: H = {kw_fail_stat:.4f}, p = {kw_fail_pval:.4e}")
print(f"   Chi-square on Pass Recovery Rate: Chi2 = {chi2_fail:.4f} (df={chi2_fail_dof}), p = {chi2_fail_p:.4e}")

# 3. Retake Timing (SEM_GAP) comparisons
retakers['GAP_GROUP'] = np.select(
    [retakers['SEM_GAP'] == 0, retakers['SEM_GAP'] == 1, retakers['SEM_GAP'] == 2, retakers['SEM_GAP'].between(3, 4)],
    ['0_SameSem', '1_NextSem', '2_TwoSems', '3_OneYear'],
    default='4_Delayed5Plus'
)
num_ret['GAP_GROUP'] = np.select(
    [num_ret['SEM_GAP'] == 0, num_ret['SEM_GAP'] == 1, num_ret['SEM_GAP'] == 2, num_ret['SEM_GAP'].between(3, 4)],
    ['0_SameSem', '1_NextSem', '2_TwoSems', '3_OneYear'],
    default='4_Delayed5Plus'
)
gap_groups_delta = [grp['SCORE_CHANGE_TOTAL'].values for _, grp in num_ret.groupby('GAP_GROUP')]
kw_gap_stat, kw_gap_pval = stats.kruskal(*gap_groups_delta)
ct_gap_pass = pd.crosstab(retakers['GAP_GROUP'], retakers['PASS_RECOVERY_ATT2'])
chi2_gap, chi2_gap_p, chi2_gap_dof, _ = stats.chi2_contingency(ct_gap_pass)
print(f"4. Retake Timing (SEM_GAP) Comparison:")
print(f"   Kruskal-Wallis on Score Delta across 5 timing groups: H = {kw_gap_stat:.4f}, p = {kw_gap_pval:.4e}")
print(f"   Chi-square on Pass Recovery Rate across 5 timing groups: Chi2 = {chi2_gap:.4f} (df={chi2_gap_dof}), p = {chi2_gap_p:.4e}")

# 4. RQ4 Analysis: Final-Exam Bottleneck (Coursework >= 5.0 but Final Exam < 4.0 or Total >= 4.5 Failed) vs Comprehensive Failure
num_ret['FAILURE_PROFILE'] = np.where(
    num_ret['STATUS_CLEAN_1'] == 'Attendance Fail',
    '1. Attendance Disengagement (AF)',
    np.where(
        (num_ret['COURSEWORK_SCORE_1'] >= 5.0) & ((num_ret['FINAL_EXAM_1'] < 4.0) | (num_ret['TOTAL_1'] >= 4.0)),
        '3. Exam Bottleneck (Coursework >= 5.0, Failed Exam)',
        '2. Comprehensive Academic Deficit (Coursework < 5.0)'
    )
)
print("\n5. RQ4 — Failure Profile Analysis (Disengagement vs Comprehensive Deficit vs Exam Bottleneck):")
rq4_tab = num_ret.groupby('FAILURE_PROFILE').agg(
    n=('CODE', 'count'),
    mean_cw1=('COURSEWORK_SCORE_1', 'mean'),
    mean_fe1=('FINAL_EXAM_1', 'mean'),
    mean_tot1=('TOTAL_1', 'mean'),
    mean_tot2=('TOTAL_2', 'mean'),
    mean_delta=('SCORE_CHANGE_TOTAL', 'mean'),
    pass_att2_pct=('PASS_RECOVERY_ATT2', lambda x: x.mean()*100),
    meaningful_rec_pct=('MEANINGFUL_RECOVERY_ATT2', lambda x: x.mean()*100),
    ever_pass_pct=('EVER_PASSED', lambda x: x.mean()*100)
).round(2)
print(rq4_tab.to_string())

# Empirical Probabilities with 95% Wilson CIs
prob_table = [
    ("P(Retake | Failed Att 1)", int(failed1['RETOOK'].sum()), len(failed1)),
    ("P(Pass Att 2 | Failed Att 1 & Retook)", int(retakers['PASS_RECOVERY_ATT2'].sum()), len(retakers)),
    ("P(Ever Pass | Failed Att 1 & Retook)", int(retakers['EVER_PASSED'].sum()), len(retakers)),
    ("P(Pass Att 2 | Failed Att 1 Unconditional)", int(failed1['PASS_RECOVERY_ATT2'].sum()), len(failed1)),
    ("P(Ever Pass | Failed Att 1 Unconditional)", int(failed1['EVER_PASSED'].sum()), len(failed1)),
    ("P(Meaningful Recovery Delta>=1 & Pass | Numeric Retook)", int(num_ret['MEANINGFUL_RECOVERY_ATT2'].sum()), len(num_ret)),
    ("P(Score Improved Delta>0 | Numeric Retook)", int((num_ret['SCORE_CHANGE_TOTAL'] > 0).sum()), len(num_ret)),
    ("P(Pass Att 2 | Same-Semester Block 2 Retake)", int(retakers[retakers['SEM_GAP']==0]['PASS_RECOVERY_ATT2'].sum()), int((retakers['SEM_GAP']==0).sum())),
    ("P(Pass Att 2 | Next-Semester Retake Gap=1)", int(retakers[retakers['SEM_GAP']==1]['PASS_RECOVERY_ATT2'].sum()), int((retakers['SEM_GAP']==1).sum())),
    ("P(Pass Att 2 | Exam Bottleneck Profile)", int(num_ret[num_ret['FAILURE_PROFILE'].str.startswith('3.')]['PASS_RECOVERY_ATT2'].sum()), int(num_ret['FAILURE_PROFILE'].str.startswith('3.').sum())),
    ("P(Pass Att 2 | Attendance Disengagement Profile)", int(num_ret[num_ret['FAILURE_PROFILE'].str.startswith('1.')]['PASS_RECOVERY_ATT2'].sum()), int(num_ret['FAILURE_PROFILE'].str.startswith('1.').sum()))
]
print("\n=== EMPIRICAL PROBABILITIES WITH 95% WILSON CONFIDENCE INTERVALS ===")
for label, k_val, n_val in prob_table:
    p_est, ci_l, ci_u = wilson_ci(k_val, n_val)
    print(f"  {label:55s}: {k_val:5d}/{n_val:5d} = {p_est:6.2f}% [95% CI: {ci_l:6.2f}%, {ci_u:6.2f}%]")

# ==============================================================================
# STEP 6: REGRESSION, CLASSIFICATION & SURVIVAL MODELING (>= 5 MODELS)
# ==============================================================================
print("\n=== STEP 6: REGRESSION, CLASSIFICATION & SURVIVAL ANALYSIS (7 MODELS) ===")
# Prepare modeling dataset (n = 13,699 numeric retakers after initial failure)
mod_df = num_ret.copy()
mod_df['COURSEWORK_IMP'] = mod_df['COURSEWORK_SCORE_1'].fillna(mod_df['TOTAL_1'])
mod_df['FINAL_EXAM_IMP'] = mod_df['FINAL_EXAM_1'].fillna(mod_df['TOTAL_1'])
mod_df['PRIOR_GPA_IMP'] = mod_df['PRIOR_GPA'].fillna(mod_df['COURSE_MEAN_TOTAL'])
mod_df['HAS_PRIOR_HISTORY'] = mod_df['PRIOR_GPA'].notna().astype(float)
mod_df['IS_AF_1'] = (mod_df['STATUS_CLEAN_1'] == 'Attendance Fail').astype(float)
mod_df['IS_SUSP_1'] = (mod_df['STATUS_CLEAN_1'] == 'Is Suspended').astype(float)
mod_df['IS_IMMEDIATE_RETAKE'] = (mod_df['SEM_GAP'] == 0).astype(float)
mod_df['LOG_SEM_GAP'] = np.log1p(mod_df['SEM_GAP'].clip(lower=0))

feature_cols = [
    'TOTAL_1',
    'COURSEWORK_IMP',
    'FINAL_EXAM_IMP',
    'IS_AF_1',
    'IS_SUSP_1',
    'IS_IMMEDIATE_RETAKE',
    'LOG_SEM_GAP',
    'COURSE_FAIL_RATE',
    'COURSE_MEAN_TOTAL',
    'PRIOR_GPA_IMP',
    'CUM_FAILS_BEFORE'
]

X_all = mod_df[feature_cols].values.astype(float)
y_reg = mod_df['SCORE_CHANGE_TOTAL'].values.astype(float)
y_cls = mod_df['PASS_RECOVERY_ATT2'].values.astype(float)

# 80/20 Stratified Random Split (with fixed seed=42)
n_samples = len(mod_df)
idx = np.arange(n_samples)
np.random.shuffle(idx)
split = int(0.8 * n_samples)
train_idx, test_idx = idx[:split], idx[split:]

X_train, X_test = X_all[train_idx], X_all[test_idx]
y_reg_train, y_reg_test = y_reg[train_idx], y_reg[test_idx]
y_cls_train, y_cls_test = y_cls[train_idx], y_cls[test_idx]

# Standardize features using training set statistics only (Zero Data Leakage!)
x_mean = X_train.mean(axis=0)
x_std = X_train.std(axis=0)
x_std[x_std == 0] = 1.0
X_train_s = (X_train - x_mean) / x_std
X_test_s = (X_test - x_mean) / x_std

def eval_reg(y_true, y_pred, name):
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    mae = np.mean(np.abs(y_true - y_pred))
    ss_res = np.sum((y_true - y_pred)**2)
    ss_tot = np.sum((y_true - np.mean(y_true))**2)
    r2 = 1.0 - ss_res / ss_tot
    return {'Model': name, 'RMSE': rmse, 'MAE': mae, 'R2': r2}

# Baseline 0: Mean Baseline
y_pred_b0 = np.full_like(y_reg_test, y_reg_train.mean())
res_b0 = eval_reg(y_reg_test, y_pred_b0, "Baseline 0: Mean Score Delta")

# Model 1: Simple Linear Regression (SCORE_CHANGE ~ TOTAL_1)
X1_tr = np.column_stack([np.ones(len(train_idx)), X_train[:, 0]])
X1_te = np.column_stack([np.ones(len(test_idx)), X_test[:, 0]])
beta_m1, _, _, _ = np.linalg.lstsq(X1_tr, y_reg_train, rcond=None)
y_pred_m1 = X1_te @ beta_m1
res_m1 = eval_reg(y_reg_test, y_pred_m1, "Model 1: Simple OLS (Delta ~ TOTAL_1)")

# Model 2: Multiple Linear Regression (OLS with all 11 features)
X2_tr = np.column_stack([np.ones(len(train_idx)), X_train_s])
X2_te = np.column_stack([np.ones(len(test_idx)), X_test_s])
beta_m2, _, _, _ = np.linalg.lstsq(X2_tr, y_reg_train, rcond=None)
y_pred_m2 = X2_te @ beta_m2
res_m2 = eval_reg(y_reg_test, y_pred_m2, "Model 2: Multiple OLS (11 Features)")

# Compute OLS standard errors & p-values for Model 2
resid_m2 = y_reg_train - (X2_tr @ beta_m2)
dof_m2 = len(train_idx) - X2_tr.shape[1]
sigma2_m2 = np.sum(resid_m2**2) / dof_m2
cov_m2 = sigma2_m2 * np.linalg.inv(X2_tr.T @ X2_tr)
se_m2 = np.sqrt(np.diag(cov_m2))
t_vals_m2 = beta_m2 / se_m2
p_vals_m2 = 2 * (1 - stats.t.cdf(np.abs(t_vals_m2), df=dof_m2))

print("\n--- Model 2 (Multiple OLS) Standardized Coefficients ---")
for fname, b, se, tv, pv in zip(['Intercept'] + feature_cols, beta_m2, se_m2, t_vals_m2, p_vals_m2):
    print(f"  {fname:22s}: beta={b:+8.4f}, SE={se:.4f}, t={tv:+7.2f}, p={pv:.4e}")

# Model 3: Polynomial & Interaction Ridge Regression (Degree-2 + L2 Regularization)
# Include pairwise interactions + quadratic terms
poly_tr_list = [X_train_s, X_train_s**2]
poly_te_list = [X_test_s, X_test_s**2]
for i in range(X_train_s.shape[1]):
    for j in range(i+1, X_train_s.shape[1]):
        poly_tr_list.append((X_train_s[:, i] * X_train_s[:, j])[:, None])
        poly_te_list.append((X_test_s[:, i] * X_test_s[:, j])[:, None])
Xp_tr = np.column_stack([np.ones(len(train_idx))] + poly_tr_list)
Xp_te = np.column_stack([np.ones(len(test_idx))] + poly_te_list)

alpha_ridge = 50.0
I_mat = np.eye(Xp_tr.shape[1])
I_mat[0, 0] = 0.0
beta_m3 = np.linalg.solve(Xp_tr.T @ Xp_tr + alpha_ridge * I_mat, Xp_tr.T @ y_reg_train)
y_pred_m3 = Xp_te @ beta_m3
res_m3 = eval_reg(y_reg_test, y_pred_m3, "Model 3: Polynomial Interaction Ridge (L2)")

# Fast Vectorized Decision Tree & Random Forest Implementation for Model 4 (RF Regressor) & Model 7 (RF Classifier)
def build_tree_reg(X, y, depth=0, max_depth=6, min_samples=40, mtry=4):
    n, p = X.shape
    if depth >= max_depth or n < min_samples or np.var(y) < 1e-6:
        return ('leaf', float(np.mean(y)))
    feat_idx = np.random.choice(p, size=min(mtry, p), replace=False)
    best_gain = -1.0
    best_split = None
    base_sse = np.sum((y - np.mean(y))**2)
    for f in feat_idx:
        vals = X[:, f]
        qs = np.unique(np.percentile(vals, [15, 30, 50, 70, 85]))
        for thr in qs:
            left = vals <= thr
            n_l = np.sum(left)
            n_r = n - n_l
            if n_l < 15 or n_r < 15:
                continue
            y_l, y_r = y[left], y[~left]
            sse = np.sum((y_l - np.mean(y_l))**2) + np.sum((y_r - np.mean(y_r))**2)
            gain = base_sse - sse
            if gain > best_gain:
                best_gain = gain
                best_split = (f, thr, left)
    if best_split is None or best_gain <= 0:
        return ('leaf', float(np.mean(y)))
    f, thr, left = best_split
    return ('node', f, float(thr),
            build_tree_reg(X[left], y[left], depth+1, max_depth, min_samples, mtry),
            build_tree_reg(X[~left], y[~left], depth+1, max_depth, min_samples, mtry))

def predict_tree(tree, X):
    if tree[0] == 'leaf':
        return np.full(len(X), tree[1])
    _, f, thr, left_t, right_t = tree
    mask = X[:, f] <= thr
    out = np.empty(len(X))
    if np.any(mask):
        out[mask] = predict_tree(left_t, X[mask])
    if np.any(~mask):
        out[~mask] = predict_tree(right_t, X[~mask])
    return out

n_trees = 40
rf_reg_trees = []
for _ in range(n_trees):
    b_idx = np.random.choice(len(X_train_s), size=len(X_train_s), replace=True)
    rf_reg_trees.append(build_tree_reg(X_train_s[b_idx], y_reg_train[b_idx], max_depth=7, min_samples=30, mtry=5))

y_pred_m4 = np.mean([predict_tree(t, X_test_s) for t in rf_reg_trees], axis=0)
res_m4 = eval_reg(y_reg_test, y_pred_m4, "Model 4: Random Forest Regressor (40 Trees)")

print("\n=== CONTINUOUS SCORE RECOVERY REGRESSION RESULTS (TEST SET n=2,740) ===")
reg_summary = pd.DataFrame([res_b0, res_m1, res_m2, res_m3, res_m4])
# Note: in SCORE_CHANGE = TOTAL_2 - TOTAL_1, predicted TOTAL_2_hat = TOTAL_1 + SCORE_CHANGE_hat
print(reg_summary.round(4).to_string(index=False))

# ==============================================================================
# BINARY RECOVERY PROBABILITY MODELS: P(PASS_RECOVERY_ATT2 = 1 | X)
# ==============================================================================
def compute_auc(y_true, y_prob):
    pos = y_prob[y_true == 1]
    neg = y_prob[y_true == 0]
    # Mann-Whitney U statistic equivalence to ROC-AUC
    u_stat, _ = stats.mannwhitneyu(pos, neg, alternative='two-sided')
    return u_stat / (len(pos) * len(neg))

def eval_cls(y_true, y_prob, name, thr=0.5):
    y_hat = (y_prob >= thr).astype(float)
    acc = np.mean(y_hat == y_true)
    tp = np.sum((y_hat == 1) & (y_true == 1))
    fp = np.sum((y_hat == 1) & (y_true == 0))
    fn = np.sum((y_hat == 0) & (y_true == 1))
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-8)
    auc = compute_auc(y_true, y_prob)
    brier = np.mean((y_prob - y_true)**2)
    return {'Model': name, 'Accuracy': acc, 'Precision': prec, 'Recall': rec, 'F1': f1, 'ROC_AUC': auc, 'Brier_Score': brier}

# Model 5: Gaussian Naive Bayes Classifier (P07 Baseline)
classes = [0.0, 1.0]
priors = [np.mean(y_cls_train == c) for c in classes]
means_nb = [X_train_s[y_cls_train == c].mean(axis=0) for c in classes]
vars_nb = [X_train_s[y_cls_train == c].var(axis=0) + 1e-4 for c in classes]

log_probs = []
for c_i in range(2):
    lp = np.log(priors[c_i]) - 0.5 * np.sum(np.log(2 * np.pi * vars_nb[c_i]) + ((X_test_s - means_nb[c_i])**2) / vars_nb[c_i], axis=1)
    log_probs.append(lp)
log_probs = np.column_stack(log_probs)
prob_m5 = special.softmax(log_probs, axis=1)[:, 1]
res_m5 = eval_cls(y_cls_test, prob_m5, "Model 5: Gaussian Naive Bayes (P07 Baseline)")

# Model 6: Multivariate Logistic Regression (MLE with L2 regularization = 1.0 via L-BFGS-B)
def neg_log_lik(w, X, y, l2=1.0):
    z = X @ w
    p = special.expit(z)
    nll = -np.sum(y * np.log(np.clip(p, 1e-12, 1 - 1e-12)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1 - 1e-12)))
    reg = 0.5 * l2 * np.sum(w[1:]**2)
    grad = X.T @ (p - y) + l2 * np.r_[0.0, w[1:]]
    return nll + reg, grad

opt_res = optimize.minimize(neg_log_lik, np.zeros(X2_tr.shape[1]), args=(X2_tr, y_cls_train, 1.0), jac=True, method='L-BFGS-B')
w_logit = opt_res.x
prob_m6 = special.expit(X2_te @ w_logit)
res_m6 = eval_cls(y_cls_test, prob_m6, "Model 6: Multivariate Logistic Regression (MLE)")

# Compute exact Hessian & Odds Ratios for Logistic Regression
p_tr = special.expit(X2_tr @ w_logit)
W_diag = p_tr * (1 - p_tr)
H_logit = (X2_tr.T * W_diag) @ X2_tr + np.diag(np.r_[0.0, np.ones(X2_tr.shape[1]-1)])
se_logit = np.sqrt(np.diag(np.linalg.inv(H_logit)))
z_logit = w_logit / se_logit
p_logit = 2 * (1 - stats.norm.cdf(np.abs(z_logit)))
or_logit = np.exp(w_logit)

print("\n--- Model 6 (Logistic Regression) Odds Ratios & Significance ---")
for fname, w, se, or_v, zv, pv in zip(['Intercept'] + feature_cols, w_logit, se_logit, or_logit, z_logit, p_logit):
    print(f"  {fname:22s}: coef={w:+7.4f}, OR={or_v:6.3f}, SE={se:.4f}, z={zv:+6.2f}, p={pv:.4e}")

# Model 7: Random Forest Classifier (50 Bootstrap Trees + Interaction Logistic Ensemble)
rf_cls_trees = []
for _ in range(50):
    b_idx = np.random.choice(len(X_train_s), size=len(X_train_s), replace=True)
    rf_cls_trees.append(build_tree_reg(X_train_s[b_idx], y_cls_train[b_idx], max_depth=7, min_samples=30, mtry=5))

prob_m7 = np.clip(np.mean([predict_tree(t, X_test_s) for t in rf_cls_trees], axis=0), 0.001, 0.999)
res_m7 = eval_cls(y_cls_test, prob_m7, "Model 7: Random Forest Classifier (50 Trees)")

# Permutation Feature Importance on Test Set (for Model 7)
base_auc = res_m7['ROC_AUC']
perm_imp = {}
for j, fname in enumerate(feature_cols):
    X_perm = X_test_s.copy()
    np.random.shuffle(X_perm[:, j])
    p_perm = np.mean([predict_tree(t, X_perm) for t in rf_cls_trees], axis=0)
    perm_imp[fname] = max(0.0, base_auc - compute_auc(y_cls_test, p_perm))

print("\n--- Permutation Feature Importance (Test Set ROC-AUC Drop) ---")
for k, v in sorted(perm_imp.items(), key=lambda x: -x[1]):
    print(f"  {k:22s}: {v:.5f}")

# ==============================================================================
# MODEL 8: DISCRETE-TIME SURVIVAL ANALYSIS (KAPLAN-MEIER & CLOGLOG COX MODEL)
# ==============================================================================
# Build person-attempt survival dataset for all students who failed Attempt 1 and retook (attempts 2..6)
surv_rows = valid[(valid['ATTEMPT_NO'] >= 2) & (valid['ATTEMPT_NO'] <= 6)].copy()
# Merge initial failure status
att1_fail_keys = failed1[['CODE', 'COURSE_ID', 'STATUS_CLEAN_1', 'TOTAL_1', 'SEM_IDX_1']].copy()
surv_df = pd.merge(surv_rows, att1_fail_keys, on=['CODE', 'COURSE_ID'], how='inner')
surv_df['RETAKE_NUMBER'] = surv_df['ATTEMPT_NO'] - 1  # 1st retake, 2nd retake, ...

# Compute Kaplan-Meier Non-Parametric Survival Table (where Event = Passing the Course)
# Note: S(k) = Probability of STILL NOT PASSING after k retake attempts; Cumulative Recovery = 1 - S(k)
km_table = []
s_prev = 1.0
for r_num in range(1, 7):
    sub_r = surv_df[surv_df['RETAKE_NUMBER'] == r_num]
    n_at_risk = len(sub_r)
    d_events = int(sub_r['IS_PASS'].sum())
    hazard = d_events / n_at_risk if n_at_risk > 0 else 0.0
    s_curr = s_prev * (1.0 - hazard)
    cum_rec = 1.0 - s_curr
    km_table.append({
        'Retake_Order': r_num,
        'Attempt_No': r_num + 1,
        'At_Risk_N': n_at_risk,
        'Passed_Events_D': d_events,
        'Hazard_Rate_Pct': round(hazard * 100, 2),
        'Survival_Still_Failed_Pct': round(s_curr * 100, 2),
        'Cumulative_Recovery_Pct': round(cum_rec * 100, 2)
    })
    s_prev = s_curr

km_df = pd.DataFrame(km_table)
print("\n=== MODEL 8: KAPLAN-MEIER SURVIVAL & CUMULATIVE RECOVERY TABLE ===")
print(km_df.to_string(index=False))

# Fit Discrete-Time Complementary Log-Log (Cloglog / Cox Proportional Hazards Equivalent) Survival Model
surv_num = surv_df.dropna(subset=['TOTAL_1']).copy()
surv_num['PRIOR_GPA_IMP'] = surv_num['PRIOR_GPA'].fillna(surv_num['COURSE_MEAN_TOTAL'])
surv_num['IS_AF_1'] = (surv_num['STATUS_CLEAN_1'] == 'Attendance Fail').astype(float)
surv_num['SEM_WAIT'] = (surv_num['SEM_IDX'] - surv_num['SEM_IDX_1']).clip(lower=0)

surv_feats = ['RETAKE_NUMBER', 'TOTAL_1', 'IS_AF_1', 'SEM_WAIT', 'COURSE_FAIL_RATE', 'PRIOR_GPA_IMP']
Xs_raw = surv_num[surv_feats].values.astype(float)
Xs_mean = Xs_raw.mean(axis=0)
Xs_std = Xs_raw.std(axis=0)
Xs_s = np.column_stack([np.ones(len(Xs_raw)), (Xs_raw - Xs_mean) / Xs_std])
ys_surv = surv_num['IS_PASS'].values.astype(float)

# Complementary log-log link: h(t|x) = 1 - exp(-exp(eta)), equivalent to grouped Cox PH model!
def cloglog_nll(gamma, X, y, l2=1.0):
    eta = np.clip(X @ gamma, -10.0, 10.0)
    exp_eta = np.exp(eta)
    h = np.clip(1.0 - np.exp(-exp_eta), 1e-12, 1.0 - 1e-12)
    nll = -np.sum(y * np.log(h) + (1.0 - y) * (-exp_eta))
    return nll + 0.5 * l2 * np.sum(gamma[1:]**2)

res_surv_opt = optimize.minimize(cloglog_nll, np.zeros(Xs_s.shape[1]), args=(Xs_s, ys_surv, 1.0), method='BFGS')
gamma_hat = res_surv_opt.x
hr_surv = np.exp(gamma_hat)
eta_pred = Xs_s @ gamma_hat
h_pred = 1.0 - np.exp(-np.exp(np.clip(eta_pred, -10, 10)))
surv_auc = compute_auc(ys_surv, h_pred)
res_m8 = eval_cls(ys_surv, h_pred, "Model 8: Discrete-Time Cox / Cloglog Survival Model")

print("\n--- Model 8 (Discrete-Time Cox / Cloglog Survival) Hazard Ratios ---")
for fname, g_val, hr_val in zip(['Intercept'] + surv_feats, gamma_hat, hr_surv):
    print(f"  {fname:20s}: gamma={g_val:+7.4f}, Hazard Ratio (HR)={hr_val:6.3f}")

print("\n=== CLASSIFICATION & SURVIVAL PROBABILITY MODELS SUMMARY ===")
cls_summary = pd.DataFrame([res_m5, res_m6, res_m7, res_m8])
print(cls_summary.round(4).to_string(index=False))