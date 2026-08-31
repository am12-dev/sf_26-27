import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)

from sklearn.linear_model import LogisticRegression, ElasticNet
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ===========================================================================
# STEP 0: SETUP DIRECTORIES
# ===========================================================================
base_dir = "/Users/arya_murthy/Documents/Osteoporosis_SF_Project/osteoporosis_project"
data_dir = os.path.join(base_dir, "data/processed")
output_dir = os.path.join(base_dir, "outputs")

os.makedirs(data_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

print("✅ Output directory operational:", data_dir)
print("✅ Output directory operational:", output_dir)

# ===========================================================================
# STEPS 1 - 8: MOCK DATA LOAD / COHORT SELECTION (N = 1,484)
# (Replace this block if you load real preprocessed NHANES CSVs)
# ===========================================================================
np.random.seed(42)
n_samples = 1484

# Generating synthetic representation of your NHANES cohort features
X = pd.DataFrame({
    'weight_kg': np.random.normal(70, 15, n_samples),
    'age': np.random.randint(50, 85, n_samples),
    'bmi': np.random.normal(27, 5, n_samples),
    'ever_used_estrogen': np.random.binomial(1, 0.3, n_samples),
    'height_cm': np.random.normal(162, 8, n_samples),
    'poverty_income_ratio': np.random.uniform(0.5, 5.0, n_samples),
    'prior_spine_fracture': np.random.binomial(1, 0.08, n_samples),
    'prior_hip_fracture': np.random.binomial(1, 0.03, n_samples),
    'rheumatoid_arthritis': np.random.binomial(1, 0.05, n_samples),
    'steroid_use': np.random.binomial(1, 0.06, n_samples),
    'prior_wrist_fracture': np.random.binomial(1, 0.07, n_samples),
    'total_calcium_mg': np.random.normal(800, 250, n_samples),
    'total_vitd_mcg': np.random.normal(15, 8, n_samples),
    'ever_smoked': np.random.binomial(1, 0.4, n_samples),
    'alcohol_drinks_day': np.random.poisson(1, n_samples),
    'phq9_score': np.random.randint(0, 20, n_samples),
    'diabetes': np.random.binomial(1, 0.15, n_samples),
    'vigorous_activity': np.random.binomial(1, 0.2, n_samples)
})

# Construct risk score for binary osteoporosis outcome target
risk_score = (
    -0.03 * X['weight_kg'] 
    + 0.05 * X['age'] 
    - 0.02 * X['bmi'] 
    + 0.8 * X['prior_spine_fracture']
    - 0.5 * X['ever_used_estrogen']
)
y = pd.Series((risk_score + np.random.normal(0, 1, n_samples) > 1.5).astype(int), name="osteoporosis")

print(f"\n✅ Primary Study Cohort Verified: N = {len(X)} participants")

# ===========================================================================
# STEP 10: TRAIN & CROSS-VALIDATE ALL MODEL ARCHITECTURES
# ===========================================================================
print("\n===========================================================================")
print("  STEP 10: TRAIN & CROSS-VALIDATE ALL MODEL ARCHITECTURES")
print("===========================================================================")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Elastic Net": LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=1000),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "LightGBM": LGBMClassifier(random_state=42, verbose=-1),
    "XGBoost": XGBClassifier(random_state=42, eval_metric='logloss')
}

leaderboard = []

for name, model in models.items():
    train_aucs, test_aucs = [], []
    
    for train_idx, test_idx in cv.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model.fit(X_train_scaled, y_train)
        
        train_preds = model.predict_proba(X_train_scaled)[:, 1]
        test_preds = model.predict_proba(X_test_scaled)[:, 1]
        
        train_aucs.append(roc_auc_score(y_train, train_preds))
        test_aucs.append(roc_auc_score(y_test, test_preds))
        
    mean_train = np.mean(train_aucs)
    mean_test = np.mean(test_aucs)
    
    print(f"  ✅ Evaluated: {name:<20} | Test AUC: {mean_test:.3f} | Train AUC: {mean_train:.3f}")

# ===========================================================================
# STEP 13: OPTIMIZE FOR HIGH SENSITIVITY & EARLY DETECTION
# ===========================================================================
def optimize_for_early_detection(X, y):
    print("\n===========================================================================")
    print("  STEP 13: OPTIMIZE FOR HIGH SENSITIVITY & EARLY DETECTION")
    print("===========================================================================")
    
    cv_opt = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Base Model penalizing false negatives (class_weight)
    base_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=15,
        max_features="sqrt",
        class_weight={0: 1, 1: 3},
        random_state=42,
        n_jobs=-1
    )
    
    # Probability Calibration
    calibrated_rf = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=cv_opt)
    
    y_true_all, y_probs_all = [], []
    
    for train_idx, test_idx in cv_opt.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        scaler = StandardScaler()
        X_train_proc = scaler.fit_transform(X_train)
        X_test_proc = scaler.transform(X_test)
        
        calibrated_rf.fit(X_train_proc, y_train)
        probs = calibrated_rf.predict_proba(X_test_proc)[:, 1]
        
        y_true_all.extend(y_test)
        y_probs_all.extend(probs)
        
    y_true_all = np.array(y_true_all)
    y_probs_all = np.array(y_probs_all)
    
    pr_auc = average_precision_score(y_true_all, y_probs_all)
    roc_auc = roc_auc_score(y_true_all, y_probs_all)
    
    print(f"  ✅ Calibrated RF PR-AUC Score : {pr_auc:.3f}")
    print(f"  ✅ Calibrated RF ROC-AUC Score: {roc_auc:.3f}\n")
    
    thresholds = [0.50, 0.40, 0.35, 0.30, 0.25]
    threshold_results = []
    
    for t in thresholds:
        preds = (y_probs_all >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_all, preds).ravel()
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        threshold_results.append({
            "Probability Cutoff": f"≥ {t:.2f}",
            "Sensitivity (Recall)": f"{sensitivity:.1%}",
            "Specificity": f"{specificity:.1%}",
            "Precision (PPV)": f"{ppv:.1%}",
            "Missed Cases (FN)": fn,
            "Flagged for DXA (TP + FP)": tp + fp
        })
        
    results_df = pd.DataFrame(threshold_results)
    
    print("=" * 95)
    print("🎯 CLINICAL DECISION THRESHOLD TUNING SWEEP (TARGETING ≥80% SENSITIVITY)")
    print("=" * 95)
    print(results_df.to_string(index=False))
    print("=" * 95)

# Execute the complete optimization workflow
optimize_for_early_detection(X, y)