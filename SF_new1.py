"""
================================================================================
NHANES OSTEOPOROSIS STUDY — COMPLETE PIPELINE WITH STACKING, CALIBRATION & SHAP
================================================================================
Study:      Early osteoporosis risk detection without DXA scan
Population: Non-Hispanic White women aged 50–65
Cycles:     2005-06, 2007-08, 2009-10, 2013-14, 2017-18, 2017-20
Models:     Logistic Regression (L2), Elastic Net, Random Forest, LightGBM, 
            XGBoost, Stacking Ensemble (Meta-Classifier), SHAP & Calibration
================================================================================
"""

import os
import io
import warnings
import requests
from functools import reduce

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Core Machine Learning Dependencies
from sklearn import set_config
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV, calibration_curve

# Boosting Engines
import lightgbm as lgb
import xgboost as xgb

# Model Interpretability
import shap

# Configure scikit-learn to preserve Pandas DataFrames across transforms
set_config(transform_output="pandas")

warnings.filterwarnings('ignore')

# ================================================================================
# CONFIGURATION
# ================================================================================
BASE_DIR = "/Users/arya_murthy/Documents/Osteoporosis_SF_Project/osteoporosis_project"
DATA_DIR = f"{BASE_DIR}/data/raw"
PROC_DIR = f"{BASE_DIR}/data/processed"
OUT_DIR  = f"{BASE_DIR}/outputs"

CYCLES = [
    {'name': '2005_2006', 'suffix': 'D', 'prefix': ''},
    {'name': '2007_2008', 'suffix': 'E', 'prefix': ''},
    {'name': '2009_2010', 'suffix': 'F', 'prefix': ''},
    {'name': '2013_2014', 'suffix': 'H', 'prefix': ''},
    {'name': '2017_2018', 'suffix': 'J', 'prefix': ''},
    {'name': '2017_2020', 'suffix': 'P', 'prefix': 'P_'},
]

SUPP_URLS = [
    ('2007_2008', 'DSQTOT_E', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DSQTOT_E.xpt'),
    ('2009_2010', 'DSQTOT_F', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DSQTOT_F.xpt'),
    ('2013_2014', 'DSQTOT_H', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DSQTOT_H.xpt'),
    ('2017_2018', 'DSQTOT_J', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DSQTOT_J.xpt'),
    ('2017_2020', 'P_DSQTOT', 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DSQTOT.xpt'),
]

PHQ_COLS = ['DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050', 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090']
REFUSED = [7, 9, 77, 99, 777, 999, 7777, 9999]

FEMORAL_NECK_MEAN = 0.858
FEMORAL_NECK_SD   = 0.120
TOTAL_HIP_MEAN    = 0.942
TOTAL_HIP_SD      = 0.122

# ================================================================================
# DATA PIPELINE HARVESTING FUNCTIONS
# ================================================================================

def load_file(cycle_name, filename):
    path = os.path.join(DATA_DIR, cycle_name, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)

def keep_cols(df, cols):
    if len(df) == 0:
        return pd.DataFrame()
    existing = ['SEQN'] + [c for c in cols if c in df.columns]
    return df[existing].copy()

def merge_files(dfs):
    dfs = [d for d in dfs if len(d) > 0 and 'SEQN' in d.columns]
    if not dfs:
        return pd.DataFrame()
    return reduce(lambda l, r: pd.merge(l, r, on='SEQN', how='left'), dfs)

def recode_yesno(series):
    def _r(x):
        if pd.isna(x): return np.nan
        x = str(x).strip().lower()
        if x in ['yes', '1', '1.0']: return 1.0
        if x in ['no',  '2', '2.0']: return 0.0
        return np.nan
    return series.apply(_r)

def print_section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def setup_directories():
    print_section("STEP 0: SETUP")
    for d in [PROC_DIR, OUT_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f"  ✅ {d}")

def download_supplement_files():
    print_section("STEP 1: SUPPLEMENT FILES")
    all_supp = []
    for cycle, name, url in SUPP_URLS:
        folder   = os.path.join(DATA_DIR, cycle)
        csv_path = os.path.join(folder, f"{name}.csv")
        os.makedirs(folder, exist_ok=True)

        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 10000:
            tmp = pd.read_csv(csv_path, low_memory=False)
            print(f"  📁 {name:15s} (cached) {len(tmp):>6,} rows")
        else:
            print(f"  ⬇️  Downloading {name}...", end=' ', flush=True)
            try:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    tmp = pd.read_sas(io.BytesIO(resp.content), format='xport', encoding='utf-8')
                    tmp.to_csv(csv_path, index=False)
                    print(f"✅ {len(tmp):,} rows")
                else:
                    print(f"❌ HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"❌ {str(e)[:60]}")
                continue

        if 'DSQTCALC' in tmp.columns:
            sub = tmp[['SEQN', 'DSQTCALC', 'DSQTVD']].copy()
            sub.columns = ['SEQN', 'supp_calcium_mg', 'supp_vitd_mcg']
            all_supp.append(sub)

    if all_supp:
        supp_all = pd.concat(all_supp, ignore_index=True)
        return supp_all.groupby('SEQN').first().reset_index()
    return pd.DataFrame()

def load_and_merge_cycles():
    print_section("STEP 2: LOAD AND MERGE ALL 6 CYCLES")
    all_cycles = []
    for cy in CYCLES:
        name, sfx, pre = cy['name'], cy['suffix'], cy['prefix']
        def fn(mod, _pre=pre, _sfx=sfx): return f"{_pre}{mod}.csv" if _pre else f"{mod}_{_sfx}.csv"

        demo = load_file(name, fn('DEMO'))
        bmx  = load_file(name, fn('BMX'))
        dxa  = load_file(name, fn('DXXFEM'))
        slq  = load_file(name, fn('SLQ'))
        dr1  = load_file(name, fn('DR1TOT'))
        vid  = load_file(name, fn('VID'))
        paq  = load_file(name, fn('PAQ'))
        dpq  = load_file(name, fn('DPQ'))
        smq  = load_file(name, fn('SMQ'))
        alq  = load_file(name, fn('ALQ'))
        mcq  = load_file(name, fn('MCQ'))
        osq  = load_file(name, fn('OSQ'))
        rhq  = load_file(name, fn('RHQ'))
        diq  = load_file(name, fn('DIQ'))

        demo_c = keep_cols(demo, ['RIAGENDR','RIDRETH1','RIDAGEYR','INDFMPIR','DMDEDUC2'])
        bmx_c  = keep_cols(bmx,  ['BMXBMI','BMXWT','BMXHT'])
        dxa_c  = keep_cols(dxa,  ['DXXNKBMD','DXXOFBMD'])
        dr1_c  = keep_cols(dr1,  ['DR1TCALC','DR1TVD'])
        vid_c  = keep_cols(vid,  ['VIDOXBLD'])
        paq_c  = keep_cols(paq,  ['PAD680','PAQ650'])
        dpq_c  = keep_cols(dpq,  PHQ_COLS)
        smq_c  = keep_cols(smq,  ['SMQ020'])
        alq_c  = keep_cols(alq,  ['ALQ130'])
        mcq_c  = keep_cols(mcq,  ['MCQ160A'])
        osq_c  = keep_cols(osq,  ['OSQ010A','OSQ010B','OSQ010C','OSQ130'])
        rhq_c  = keep_cols(rhq,  ['RHQ074','RHQ540'])
        diq_c  = keep_cols(diq,  ['DIQ010'])

        slq_keep = [c for c in ['SLD012','SLD010H'] if c in (slq.columns if len(slq) > 0 else [])]
        slq_c = keep_cols(slq, slq_keep) if slq_keep else pd.DataFrame()

        merged = merge_files([demo_c, bmx_c, dxa_c, slq_c, dr1_c, vid_c, paq_c, dpq_c, smq_c, alq_c, mcq_c, osq_c, rhq_c, diq_c])
        merged['survey_cycle'] = name
        all_cycles.append(merged)

    return pd.concat(all_cycles, ignore_index=True)

def recode_refused(df):
    print_section("STEP 3: RECODE REFUSED/DON'T KNOW TO NaN")
    numeric_cols = [c for c in df.columns if df[c].dtype in ['float64','int64']]
    for col in numeric_cols:
        df[col] = df[col].replace(REFUSED, np.nan)
    return df

def apply_filters(df):
    print_section("STEP 4: INCLUSION FILTERS — ATTRITION TABLE")
    df = df[df['RIAGENDR'].isin([2, 2.0, 'Female'])].copy()
    df = df[df['RIDRETH1'].isin([3, 3.0, 'Non-Hispanic White'])].copy()
    df = df[(df['RIDAGEYR'] >= 50) & (df['RIDAGEYR'] <= 65)].copy()
    df = df[df['DXXNKBMD'].notna()].copy()
    assert len(df) == 1484, f"Expected 1,484 women, got {len(df)}"
    print(f"  ✅ Verified final cohort sample: {len(df):,} women")
    return df

def compute_tscores(df):
    print_section("STEP 5: T-SCORES AND TARGET VARIABLE")
    df['t_femoral_neck'] = (df['DXXNKBMD'] - FEMORAL_NECK_MEAN) / FEMORAL_NECK_SD
    df['t_total_hip']    = (df['DXXOFBMD'] - TOTAL_HIP_MEAN)    / TOTAL_HIP_SD
    df['t_score'] = df[['t_femoral_neck', 't_total_hip']].min(axis=1)
    df['bone_status'] = pd.cut(df['t_score'], bins=[-99, -2.5, -1.0, 99], labels=['Osteoporosis', 'Low Bone Mass', 'Normal'])
    df['at_risk'] = (df['t_score'] <= -1.0).astype(int)
    return df

def compute_derived_variables(df, supp_df):
    print_section("STEP 6: DERIVED VARIABLES")
    if 'SLD012' in df.columns and 'SLD010H' in df.columns:
        df['sleep_hrs'] = df['SLD012'].fillna(df['SLD010H'])
    else:
        df['sleep_hrs'] = df['SLD012'] if 'SLD012' in df.columns else (df['SLD010H'] if 'SLD010H' in df.columns else np.nan)
    
    df['sleep_hrs']  = pd.to_numeric(df['sleep_hrs'], errors='coerce')
    df['sleep_risk'] = (df['sleep_hrs'] < 7).astype(float)
    df.loc[df['sleep_hrs'].isna(), 'sleep_risk'] = np.nan

    avail_phq = [c for c in PHQ_COLS if c in df.columns]
    df['phq9_score'] = df[avail_phq].apply(pd.to_numeric, errors='coerce').clip(0, 3).sum(axis=1, min_count=5)

    if len(supp_df) > 0:
        df = df.merge(supp_df, on='SEQN', how='left')
    else:
        df['supp_calcium_mg'] = 0
        df['supp_vitd_mcg']   = 0

    df['supp_calcium_mg'] = pd.to_numeric(df['supp_calcium_mg'], errors='coerce').fillna(0)
    df['supp_vitd_mcg']   = pd.to_numeric(df['supp_vitd_mcg'],   errors='coerce').fillna(0)

    diet_ca = pd.to_numeric(df['DR1TCALC'], errors='coerce')
    diet_vd = pd.to_numeric(df['DR1TVD'],   errors='coerce')
    df['total_calcium_mg'] = diet_ca.add(df['supp_calcium_mg'], fill_value=0)
    df['total_vitd_mcg']   = diet_vd.add(df['supp_vitd_mcg'],   fill_value=0)
    return df

def recode_binary_variables(df):
    print_section("STEP 7: RECODE BINARY CLINICAL VARIABLES")
    binary_sources = []
    for cy in CYCLES:
        n, sfx, pre = cy['name'], cy['suffix'], cy['prefix']
        def fn2(mod, _pre=pre, _sfx=sfx): return f"{_pre}{mod}.csv" if _pre else f"{mod}_{_sfx}.csv"

        for module, col, new_name in [
            ('MCQ', 'MCQ160A', 'rheumatoid_arthritis'), ('OSQ', 'OSQ010A', 'prior_hip_fracture'),
            ('OSQ', 'OSQ010B', 'prior_spine_fracture'), ('OSQ', 'OSQ010C', 'prior_wrist_fracture'),
            ('OSQ', 'OSQ130',  'steroid_use'),           ('SMQ', 'SMQ020',  'ever_smoked'),
            ('RHQ', 'RHQ540',  'ever_used_estrogen'),    ('PAQ', 'PAQ650',  'vigorous_activity'),
            ('DIQ', 'DIQ010',  'diabetes'),
        ]:
            tmp = load_file(n, fn2(module))
            if len(tmp) > 0 and col in tmp.columns:
                sub = tmp[['SEQN', col]].copy()
                sub[new_name] = recode_yesno(sub[col])
                binary_sources.append(sub[['SEQN', new_name]])

    if binary_sources:
        binary_all = pd.concat(binary_sources).groupby('SEQN').first().reset_index()
        df = df.merge(binary_all, on='SEQN', how='left')
    return df

def rename_and_save(df):
    print_section("STEP 8: RENAME AND SAVE")
    rename = {
        'RIDAGEYR': 'age', 'INDFMPIR': 'poverty_income_ratio', 'DMDEDUC2': 'education',
        'BMXBMI': 'bmi', 'BMXWT': 'weight_kg', 'BMXHT': 'height_cm', 'DR1TCALC': 'dietary_calcium_mg',
        'DR1TVD': 'dietary_vitd_mcg', 'VIDOXBLD': 'serum_vitd_nmol', 'PAD680': 'sedentary_min_day',
        'ALQ130': 'alcohol_drinks_day', 'DXXNKBMD': 'femoral_neck_bmd', 'DXXOFBMD': 'total_hip_bmd',
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df.to_csv(os.path.join(PROC_DIR, 'option_b_v4_final.csv'), index=False)
    return df

def define_features(df):
    print_section("STEP 9: DEFINE FEATURE SETS")
    exclude = [
        'SEQN', 'RIAGENDR', 'RIDRETH1', 'survey_cycle', 'age_group',
        'femoral_neck_bmd', 'total_hip_bmd', 't_femoral_neck', 't_total_hip', 't_score', 'bone_status',
        'at_risk', 'DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050', 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090',
        'cigarettes_per_day', 'menopause_confirmed', 'dietary_calcium_mg', 'dietary_vitd_mcg',
        'supp_calcium_mg', 'supp_vitd_mcg', 'sleep_hrs', 'SLD012', 'SLD010H', 'sedentary_min_day',
    ]
    feat_with = [c for c in df.columns if c not in exclude]
    X_with = df[feat_with].copy()
    y = df['at_risk'].copy()
    X_with = X_with.drop(columns=X_with.select_dtypes(include=['object', 'category']).columns.tolist())
    X_without = X_with.drop(columns=['sleep_risk'], errors='ignore')
    
    # Clean Inf values to NaN to ensure feature scaling and model steps run safely
    X_with = X_with.replace([np.inf, -np.inf], np.nan)
    X_without = X_without.replace([np.inf, -np.inf], np.nan)
    return X_with, X_without, y

# ================================================================================
# STEP 10: MODEL DEFINITION & CROSS-VALIDATION (INCL. STACKING)
# ================================================================================

def get_base_estimators(pos_weight):
    return [
        ('lr', LogisticRegression(
            max_iter=1000, 
            random_state=42, 
            class_weight='balanced'
        )),
        ('elastic', LogisticRegression(
            penalty='elasticnet',
            solver='saga',
            l1_ratio=0.5,
            max_iter=2000,
            random_state=42,
            class_weight='balanced'
        )),
        ('rf', RandomForestClassifier(
            n_estimators=500, 
            min_samples_leaf=5, 
            class_weight='balanced', 
            random_state=42, 
            n_jobs=-1
        )),
        ('lgb', lgb.LGBMClassifier(
            n_estimators=150, max_depth=2, num_leaves=4, min_child_samples=50, reg_lambda=50.0,
            class_weight='balanced', random_state=42, verbose=-1, n_jobs=-1
        )),
        ('xgb', xgb.XGBClassifier(
            n_estimators=150, max_depth=2, min_child_weight=15, reg_lambda=50.0,
            scale_pos_weight=pos_weight, random_state=42, eval_metric='logloss', n_jobs=-1
        ))
    ]

def run_model(pipe, X, y, cv):
    res = cross_validate(pipe, X, y, cv=cv, scoring=['roc_auc', 'recall', 'precision', 'f1'], return_train_score=True)
    y_pred = cross_val_predict(pipe, X, y, cv=cv)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    pipe.fit(X, y)
    return {
        'auc': res['test_roc_auc'].mean(),
        'train_auc': res['train_roc_auc'].mean(),
        'sens': tp / (tp + fn),
        'spec': tn / (tn + fp),
        'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp
    }

def train_models(X_without, y):
    print_section("STEP 10: TRAIN AND AUDIT ALL MODALITY ARCHITECTURES (INCL. STACKING)")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pos_weight = (y == 0).sum() / (y == 1).sum() if (y == 1).sum() > 0 else 1.0
    
    estimators = get_base_estimators(pos_weight)
    
    # Construct Base Dictionary
    models = {
        'Logistic Regression (L2)': estimators[0][1],
        'Elastic Net Logistic Regression': estimators[1][1],
        'Random Forest': estimators[2][1],
        'LightGBM (Aggressive Reg)': estimators[3][1],
        'XGBoost (Aggressive Reg)': estimators[4][1]
    }

    # Wrap base estimators in pipelines for StackingClassifier to eliminate numerical explosion
    stacking_estimators = []
    for est_name, est_obj in estimators:
        if est_name in ['lr', 'elastic']:
            pipe_est = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler()),
                ('model', est_obj)
            ])
            stacking_estimators.append((est_name, pipe_est))
        else:
            stacking_estimators.append((est_name, est_obj))

    # Add Stacking Ensemble Classifier
    stacking_meta = StackingClassifier(
        estimators=stacking_estimators,
        final_estimator=LogisticRegression(random_state=42),
        cv=5,
        n_jobs=-1
    )
    models['Stacking Ensemble Meta-Learner'] = stacking_meta

    results = []
    trained_pipelines = {}
    
    for name, model in models.items():
        pipe = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        metrics = run_model(pipe, X_without, y, cv)
        metrics['Model'] = name
        results.append(metrics)
        trained_pipelines[name] = pipe
        print(f"  ✅ Evaluated: {name:<32} | Test AUC: {metrics['auc']:.3f} | Train AUC: {metrics['train_auc']:.3f}")
        
    return pd.DataFrame(results), trained_pipelines

# ================================================================================
# STEP 11: FEATURE WEIGHTAGE & IMPORTANCE ANALYSIS
# ================================================================================

def audit_feature_weights(X, y):
    print_section("STEP 11: FEATURE WEIGHTS & IMPORTANCE AUDIT")
    
    pos_weight = (y == 0).sum() / (y == 1).sum() if (y == 1).sum() > 0 else 1.0
    estimators = get_base_estimators(pos_weight)
    
    imputer = SimpleImputer(strategy='median')
    scaler = StandardScaler()
    
    # Safe preprocessing step to transform into DataFrame
    X_proc = scaler.fit_transform(imputer.fit_transform(X))
    feature_names = X.columns.tolist()
    
    importance_dict = {'Feature': feature_names}
    
    for est_name, model in estimators:
        model.fit(X_proc, y)
        
        if hasattr(model, 'coef_'):
            weights = model.coef_[0]
        elif hasattr(model, 'feature_importances_'):
            weights = model.feature_importances_
        else:
            weights = np.zeros(len(feature_names))
            
        importance_dict[est_name] = weights

    importance_df = pd.DataFrame(importance_dict)
    
    # Normalize LightGBM column to 0-1 scale if present
    if 'lgb' in importance_df.columns:
        lgb_sum = importance_df['lgb'].sum()
        if lgb_sum > 0:
            importance_df['lgb'] = importance_df['lgb'] / lgb_sum

    importance_df['abs_ref'] = importance_df['elastic'].abs()
    importance_df = importance_df.sort_values(by='abs_ref', ascending=False).drop(columns=['abs_ref'])

    print("=" * 110)
    print("📊 FEATURE WEIGHTS & IMPORTANCE CONTRIBUTION MATRIX")
    print("   Note: Logistic/Elastic Net values = Scaled Coefficients (Log-Odds)")
    print("   Note: Tree Model values = Relative Importance (Normalized)")
    print("=" * 110)
    print(importance_df.to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
    print("=" * 110)

    out_csv = os.path.join(OUT_DIR, "feature_weights_matrix.csv")
    importance_df.to_csv(out_csv, index=False)
    print(f"  ✅ Saved feature weightage matrix to: {out_csv}")
    
    return importance_df

# ================================================================================
# STEP 12: PROBABILITY CALIBRATION, BRIER SCORE & SHAP EXPLAINABILITY
# ================================================================================

def evaluate_calibration_and_shap(trained_pipelines, X, y):
    print_section("STEP 12: CALIBRATION ANALYSIS & SHAP EXPLAINABILITY")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # 1. Calibration Analysis on Stacking Ensemble Pipeline
    stacking_pipe = trained_pipelines['Stacking Ensemble Meta-Learner']
    
    y_probs = cross_val_predict(stacking_pipe, X, y, cv=cv, method='predict_proba')[:, 1]
    
    brier = brier_score_loss(y, y_probs)
    print(f"  ✅ Stacking Ensemble Brier Score Loss: {brier:.4f}")
    
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y, y_probs, n_bins=10, strategy='uniform'
    )
    
    plt.figure(figsize=(7, 5))
    plt.plot(mean_predicted_value, fraction_of_positives, "s-", label=f"Stacking Model (Brier = {brier:.3f})")
    plt.plot([0, 1], [0, 1], "k--", label="Perfectly Calibrated")
    plt.xlabel("Mean Predicted Probability")
    plt.ylabel("Fraction of Positives")
    plt.title("Probability Calibration Curve (Reliability Diagram)")
    plt.legend(loc="lower right")
    plt.tight_layout()
    calib_fig_path = os.path.join(OUT_DIR, "calibration_curve.png")
    plt.savefig(calib_fig_path, dpi=300)
    plt.close()
    print(f"  ✅ Saved Calibration Plot to: {calib_fig_path}")

    # 2. SHAP Explainability on Base Tree Model (Random Forest)
    imputer = SimpleImputer(strategy='median')
    scaler = StandardScaler()
    X_proc = scaler.fit_transform(imputer.fit_transform(X))
    
    rf_model = trained_pipelines['Random Forest'].named_steps['model']
    rf_model.fit(X_proc, y)
    
    explainer = shap.TreeExplainer(rf_model)
    shap_values = explainer(X_proc)
    
    shap_vals_to_plot = shap_values[:, :, 1] if len(shap_values.shape) == 3 else shap_values
    
    plt.figure()
    shap.summary_plot(shap_vals_to_plot, X_proc, show=False)
    shap_summary_path = os.path.join(OUT_DIR, "shap_summary_plot.png")
    plt.savefig(shap_summary_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"  ✅ Saved Global SHAP Summary Plot to: {shap_summary_path}")

    plt.figure()
    shap.plots.waterfall(shap_vals_to_plot[0], show=False)
    shap_waterfall_path = os.path.join(OUT_DIR, "shap_waterfall_patient0.png")
    plt.savefig(shap_waterfall_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"  ✅ Saved Patient 0 Local SHAP Waterfall Plot to: {shap_waterfall_path}")

# ================================================================================
# STEP 13: SENSITIVITY OPTIMIZATION & THRESHOLD SWEEP
# ================================================================================

def optimize_for_early_detection(X, y):
    print_section("STEP 13: OPTIMIZE FOR HIGH SENSITIVITY & EARLY DETECTION")
    
    cv_opt = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    base_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=15,
        max_features="sqrt",
        class_weight={0: 1, 1: 3},
        random_state=42,
        n_jobs=-1
    )
    
    calibrated_rf = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=cv_opt)
    
    y_true_all, y_probs_all = [], []
    
    for train_idx, test_idx in cv_opt.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        imputer = SimpleImputer(strategy='median')
        scaler = StandardScaler()
        
        X_train_proc = scaler.fit_transform(imputer.fit_transform(X_train))
        X_test_proc = scaler.transform(imputer.transform(X_test))
        
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

# ================================================================================
# MAIN EXECUTION ROUTINE
# ================================================================================

def main():
    print("\n" + "=" * 60)
    print("  NHANES OSTEOPOROSIS PIPELINE — COMPLETE AUDIT")
    print("=" * 60)

    setup_directories()
    supp_df      = download_supplement_files()
    full         = load_and_merge_cycles()
    full         = recode_refused(full)
    df           = apply_filters(full)
    df           = compute_tscores(df)
    df           = compute_derived_variables(df, supp_df)
    df           = recode_binary_variables(df)
    df           = rename_and_save(df)
    X_with, X_without, y = define_features(df)
    
    leaderboard, trained_pipelines = train_models(X_without, y)
    
    leaderboard = leaderboard.rename(columns={
        'Model': 'Model Architecture',
        'auc': 'Test AUC-ROC',
        'train_auc': 'Train AUC-ROC',
        'sens': 'Sensitivity (Recall)',
        'spec': 'Specificity'
    })
    
    print("\n" + "="*95)
    print("🏆 FINAL COMPARATIVE STUDY LEADERBOARD")
    print("="*95)
    print(leaderboard[['Model Architecture', 'Test AUC-ROC', 'Train AUC-ROC', 'Sensitivity (Recall)', 'Specificity']].to_string(index=False, formatters={
        'Test AUC-ROC': '{:,.3f}'.format, 
        'Train AUC-ROC': '{:,.3f}'.format,
        'Sensitivity (Recall)': '{:.1%}'.format, 
        'Specificity': '{:.1%}'.format
    }))
    print("="*95 + "\n")

    # Step 11: Audit Feature Weights & Importances
    audit_feature_weights(X_without, y)

    # Step 12: Evaluate Calibration & SHAP Explainability
    evaluate_calibration_and_shap(trained_pipelines, X_without, y)

    # Step 13: Run Threshold Optimization Experiment
    optimize_for_early_detection(X_without, y)


if __name__ == '__main__':
    main()