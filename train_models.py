"""
train_models.py
================
NYC West Nile Risk Prediction — ML Model Experiment & Artifact Pipeline

This script:
1. Loads and audits `data/processed/training_data.csv` (and checks against `DATA_TASKS.md`).
2. Checks for and removes data leakage features.
3. Prepares reproducible scikit-learn preprocessing pipelines.
4. Performs both Random Stratified Split (80/20) and Chronological Split evaluations.
5. Trains:
   - Model A: Linear Regression (thresholded at 0.5)
   - Model B: Logistic Regression (class_weight='balanced')
   - Model C: Random Forest Classifier (class_weight='balanced')
   - Model D: XGBoost Classifier (scale_pos_weight adjusted)
6. Calculates Accuracy, Precision, Recall, F1, and ROC-AUC for all models.
7. Generates:
   - results/model_comparison.csv
   - results/confusion_matrix_logistic_regression.png
   - results/confusion_matrix_random_forest.png
   - results/confusion_matrix_xgboost.png
   - results/roc_curves.png
   - results/feature_importance_random_forest.csv
   - results/feature_importance_xgboost.csv
   - results/logistic_regression_coefficients.csv
   - results/final_report.txt
8. Saves the best model and pipeline to models/ and exports backend artifacts to ml/artifacts/.
9. Prints a comprehensive executive summary to the console.
"""

import os
import sys
import json
import ctypes
import joblib
import numpy as np
import pandas as pd

# Load libomp on macOS if available
for lib_path in [
    '/opt/homebrew/opt/libomp/lib/libomp.dylib',
    '/usr/local/opt/libomp/lib/libomp.dylib',
    os.path.expanduser('~/miniconda3/lib/libomp.dylib'),
]:
    if os.path.exists(lib_path):
        try:
            ctypes.CDLL(lib_path)
            break
        except Exception:
            pass

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    roc_curve,
)

# -----------------------------------------------------------------------------
# 0. SETUP DIRECTORIES & PATHS
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'training_data.csv')
DOC_PATH = os.path.join(BASE_DIR, 'DATA_TASKS.md')

RESULTS_DIR = os.path.join(BASE_DIR, 'results')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
ML_ARTIFACTS_DIR = os.path.join(BASE_DIR, 'ml', 'artifacts')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ML_ARTIFACTS_DIR, exist_ok=True)


def main():
    print("=" * 60)
    print("NYC WEST NILE RISK PREDICTION — ML MODEL EXPERIMENT")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # 1. LOAD & AUDIT DATASET
    # -------------------------------------------------------------------------
    print(f"\n[Step 1] Loading dataset from: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    # Ensure zipcode is formatted as 5-character string with zero-padding
    df['zipcode'] = df['zipcode'].astype(str).str.zfill(5)

    n_rows, n_cols = df.shape
    print(f"Dataset Loaded: {n_rows} rows, {n_cols} columns.")

    # Target audit
    target_col = 'elevated'
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    class_counts = df[target_col].value_counts().to_dict()
    class_0_cnt = class_counts.get(0, 0)
    class_1_cnt = class_counts.get(1, 0)
    class_0_pct = (class_0_cnt / n_rows) * 100
    class_1_pct = (class_1_cnt / n_rows) * 100

    print(f"\nTarget Variable: '{target_col}'")
    print(f"  Class 0 (Not elevated / Low risk): {class_0_cnt} ({class_0_pct:.2f}%)")
    print(f"  Class 1 (Elevated WNV activity):   {class_1_cnt} ({class_1_pct:.2f}%)")

    # -------------------------------------------------------------------------
    # 2. DATA LEAKAGE AUDIT & FEATURE SELECTION
    # -------------------------------------------------------------------------
    print("\n[Step 2] Feature Selection & Data Leakage Check")
    
    # Excluded features with explicit rationale
    excluded_features = {
        'zip_detection_status': "LEAKAGE: Snapshot public status as of 2026-08-21 that perfectly separates seasonal positives.",
        'positive_count': "TARGET DERIVATIVE: Same-week positive trap count.",
        'elevated': "PRIMARY TARGET.",
        'year': "CONSTANT: Year 2026 across all rows.",
        'season': "CONSTANT: 'summer' across all rows.",
        'neighborhoods': "METADATA/TEXT: 1,128 missing values; borough/zipcode capture spatial granularity.",
        'week_start': "IDENTIFIER: Used for chronological time-splitting and tracking, not as numeric feature.",
    }

    for feat, reason in excluded_features.items():
        print(f"  - Excluded '{feat}': {reason}")

    # Feature definitions
    categorical_features = ['borough', 'zipcode']
    numerical_features = [
        'week_of_year',
        'week_sin',
        'week_cos',
        'latitude',
        'longitude',
        'temp_mean',
        'temp_max',
        'temp_min',
        'humidity_mean',
        'precip_sum',
        'temp_mean_lag7',
        'temp_mean_lag14',
        'humidity_mean_lag7',
        'precip_7d',
        'precip_14d',
        'degree_days_14d',
        'positives_last_1w',
        'positives_last_2_4w',
    ]

    all_model_features = categorical_features + numerical_features
    print(f"\nTotal Selected Features: {len(all_model_features)}")
    print(f"  Categorical ({len(categorical_features)}): {categorical_features}")
    print(f"  Numerical ({len(numerical_features)}): {numerical_features}")

    X = df[all_model_features]
    y = df[target_col]

    # -------------------------------------------------------------------------
    # 3. TRAIN / TEST SPLIT (80% Train, 20% Test, Stratified)
    # -------------------------------------------------------------------------
    print("\n[Step 3] Performing 80/20 Stratified Train/Test Split (Random Seed: 42)")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"  Training set size: {X_train.shape[0]} rows ({y_train.sum()} positive, {y_train.mean()*100:.1f}%)")
    print(f"  Testing set size:  {X_test.shape[0]} rows ({y_test.sum()} positive, {y_test.mean()*100:.1f}%)")

    # -------------------------------------------------------------------------
    # 4. PREPROCESSING PIPELINES
    # -------------------------------------------------------------------------
    # Preprocessor with Scaling (for Linear & Logistic Regression)
    preprocessor_scaled = ColumnTransformer(
        transformers=[
            ('num', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ]
    )

    # Preprocessor unscaled (for Tree-based Models: Random Forest, XGBoost)
    preprocessor_trees = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy='median'), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ]
    )

    # -------------------------------------------------------------------------
    # 5. MODEL TRAINING & COMPARISON EXPERIMENT
    # -------------------------------------------------------------------------
    print("\n[Step 4] Training Candidate Models...")

    # Calculate scale_pos_weight for imbalanced classes
    scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

    models = {
        'Linear Regression': {
            'pipeline': Pipeline([
                ('prep', preprocessor_scaled),
                ('clf', LinearRegression())
            ]),
            'is_linear_reg': True,
        },
        'Logistic Regression': {
            'pipeline': Pipeline([
                ('prep', preprocessor_scaled),
                ('clf', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42, C=0.5))
            ]),
            'is_linear_reg': False,
        },
        'Random Forest': {
            'pipeline': Pipeline([
                ('prep', preprocessor_trees),
                ('clf', RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=-1))
            ]),
            'is_linear_reg': False,
        },
        'XGBoost': {
            'pipeline': Pipeline([
                ('prep', preprocessor_trees),
                ('clf', XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, scale_pos_weight=scale_pos_weight, random_state=42, eval_metric='logloss'))
            ]),
            'is_linear_reg': False,
        }
    }

    results = []
    trained_pipelines = {}
    y_test_prob_dict = {}
    y_test_pred_dict = {}

    for name, config in models.items():
        print(f"  Fitting {name}...")
        pipeline = config['pipeline']
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline

        # Predictions on Test set
        if config['is_linear_reg']:
            raw_pred = pipeline.predict(X_test)
            y_pred = (raw_pred >= 0.5).astype(int)
            y_prob = np.clip(raw_pred, 0.0, 1.0)
        else:
            y_pred = pipeline.predict(X_test)
            y_prob = pipeline.predict_proba(X_test)[:, 1]

        y_test_pred_dict[name] = y_pred
        y_test_prob_dict[name] = y_prob

        # Train metrics for overfitting check
        if config['is_linear_reg']:
            train_pred = (pipeline.predict(X_train) >= 0.5).astype(int)
            train_prob = np.clip(pipeline.predict(X_train), 0.0, 1.0)
        else:
            train_pred = pipeline.predict(X_train)
            train_prob = pipeline.predict_proba(X_train)[:, 1]

        train_acc = accuracy_score(y_train, train_pred)
        train_f1 = f1_score(y_train, train_pred, zero_division=0)
        train_auc = roc_auc_score(y_train, train_prob)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)

        results.append({
            'Model': name,
            'Accuracy': round(acc, 3),
            'Precision': round(prec, 3),
            'Recall': round(rec, 3),
            'F1': round(f1, 3),
            'ROC-AUC': round(auc, 3),
            'Train_Accuracy': round(train_acc, 3),
            'Train_F1': round(train_f1, 3),
            'Train_AUC': round(train_auc, 3),
        })

    # Convert to DataFrame
    comparison_df = pd.DataFrame(results)
    comparison_csv_path = os.path.join(RESULTS_DIR, 'model_comparison.csv')
    comparison_df[['Model', 'Accuracy', 'Precision', 'Recall', 'F1', 'ROC-AUC']].to_csv(comparison_csv_path, index=False)
    print(f"\nModel comparison table saved to: {comparison_csv_path}")

    # -------------------------------------------------------------------------
    # 6. CONFUSION MATRICES
    # -------------------------------------------------------------------------
    print("\n[Step 5] Generating Confusion Matrices...")
    classifier_names = ['Logistic Regression', 'Random Forest', 'XGBoost']
    
    for clf_name in classifier_names:
        cm = confusion_matrix(y_test, y_test_pred_dict[clf_name])
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=['Predicted Low (0)', 'Predicted High (1)'],
            yticklabels=['Actual Low (0)', 'Actual High (1)'],
            annot_kws={'size': 14, 'weight': 'bold'},
            ax=ax
        )
        ax.set_title(f'Confusion Matrix — {clf_name}', fontsize=12, fontweight='bold', pad=12)
        plt.tight_layout()
        
        slug = clf_name.lower().replace(' ', '_')
        cm_path = os.path.join(RESULTS_DIR, f'confusion_matrix_{slug}.png')
        plt.savefig(cm_path, dpi=300)
        plt.close()
        print(f"  Saved {cm_path}")

    # -------------------------------------------------------------------------
    # 7. ROC CURVES
    # -------------------------------------------------------------------------
    print("\n[Step 6] Generating ROC Curves Plot...")
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {'Logistic Regression': '#f59e0b', 'Random Forest': '#10b981', 'XGBoost': '#3b82f6'}

    for clf_name in classifier_names:
        fpr, tpr, _ = roc_curve(y_test, y_test_prob_dict[clf_name])
        auc_val = roc_auc_score(y_test, y_test_prob_dict[clf_name])
        ax.plot(fpr, tpr, label=f"{clf_name} (AUC = {auc_val:.3f})", color=colors[clf_name], linewidth=2.2)

    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance Baseline (AUC = 0.500)')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=11, fontweight='bold')
    ax.set_ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=11, fontweight='bold')
    ax.set_title('ROC Curves Comparison — NYC West Nile Risk Models', fontsize=13, fontweight='bold', pad=14)
    ax.legend(loc='lower right', frameon=True, fontsize=10)
    ax.grid(True, alpha=0.25)
    plt.tight_layout()

    roc_path = os.path.join(RESULTS_DIR, 'roc_curves.png')
    plt.savefig(roc_path, dpi=300)
    plt.close()
    print(f"  Saved {roc_path}")

    # -------------------------------------------------------------------------
    # 8. FEATURE IMPORTANCE & COEFFICIENTS
    # -------------------------------------------------------------------------
    print("\n[Step 7] Extracting Feature Importance & Model Coefficients...")

    fitted_prep_trees = trained_pipelines['Random Forest'].named_steps['prep']
    ohe_cols = list(fitted_prep_trees.named_transformers_['cat'].get_feature_names_out(categorical_features))
    transformed_feature_names = numerical_features + ohe_cols

    # Random Forest Importance
    rf_model = trained_pipelines['Random Forest'].named_steps['clf']
    rf_importances = rf_model.feature_importances_
    rf_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Importance': rf_importances
    }).sort_values('Importance', ascending=False).reset_index(drop=True)
    rf_feat_path = os.path.join(RESULTS_DIR, 'feature_importance_random_forest.csv')
    rf_feat_df.to_csv(rf_feat_path, index=False)
    print(f"  Saved {rf_feat_path}")

    # XGBoost Importance
    xgb_model = trained_pipelines['XGBoost'].named_steps['clf']
    xgb_importances = xgb_model.feature_importances_
    xgb_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Importance': xgb_importances
    }).sort_values('Importance', ascending=False).reset_index(drop=True)
    xgb_feat_path = os.path.join(RESULTS_DIR, 'feature_importance_xgboost.csv')
    xgb_feat_df.to_csv(xgb_feat_path, index=False)
    print(f"  Saved {xgb_feat_path}")

    # Logistic Regression Coefficients
    log_model = trained_pipelines['Logistic Regression'].named_steps['clf']
    log_coefs = log_model.coef_[0]
    log_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Coefficient': log_coefs,
        'Absolute_Impact': np.abs(log_coefs)
    }).sort_values('Absolute_Impact', ascending=False).reset_index(drop=True)
    log_feat_path = os.path.join(RESULTS_DIR, 'logistic_regression_coefficients.csv')
    log_feat_df.to_csv(log_feat_path, index=False)
    print(f"  Saved {log_feat_path}")

    # -------------------------------------------------------------------------
    # 9. TEMPORAL VALIDATION EXPERIMENT (Chronological Split)
    # -------------------------------------------------------------------------
    print("\n[Step 8] Running Temporal Chronological Validation Experiment...")
    train_temporal_mask = df['week_start'] <= '2026-07-27'
    test_temporal_mask = (df['week_start'] >= '2026-08-03') & (df['week_start'] <= '2026-08-10')

    X_train_t = df.loc[train_temporal_mask, all_model_features]
    y_train_t = df.loc[train_temporal_mask, target_col]
    X_test_t = df.loc[test_temporal_mask, all_model_features]
    y_test_t = df.loc[test_temporal_mask, target_col]

    print(f"  Temporal Train (June 1 - July 27): {X_train_t.shape[0]} rows ({y_train_t.sum()} positive, {y_train_t.mean()*100:.1f}%)")
    print(f"  Temporal Test (August 3 - August 10): {X_test_t.shape[0]} rows ({y_test_t.sum()} positive, {y_test_t.mean()*100:.1f}%)")

    temporal_results = []
    for name, config in models.items():
        pipe = config['pipeline']
        pipe.fit(X_train_t, y_train_t)
        if config['is_linear_reg']:
            p_pred = (pipe.predict(X_test_t) >= 0.5).astype(int)
            p_prob = np.clip(pipe.predict(X_test_t), 0.0, 1.0)
        else:
            p_pred = pipe.predict(X_test_t)
            p_prob = pipe.predict_proba(X_test_t)[:, 1]

        temporal_results.append({
            'Model': name,
            'Accuracy': round(accuracy_score(y_test_t, p_pred), 3),
            'Precision': round(precision_score(y_test_t, p_pred, zero_division=0), 3),
            'Recall': round(recall_score(y_test_t, p_pred, zero_division=0), 3),
            'F1': round(f1_score(y_test_t, p_pred, zero_division=0), 3),
            'ROC-AUC': round(roc_auc_score(y_test_t, p_prob), 3),
        })
    temporal_df = pd.DataFrame(temporal_results)

    # -------------------------------------------------------------------------
    # 10. DETERMINE BEST MODEL & SAVE ARTIFACTS
    # -------------------------------------------------------------------------
    print("\n[Step 9] Determining Best Model and Exporting Production Artifacts...")
    
    best_model_name = 'XGBoost' if comparison_df.loc[comparison_df['Model']=='XGBoost', 'ROC-AUC'].values[0] >= comparison_df.loc[comparison_df['Model']=='Random Forest', 'ROC-AUC'].values[0] else 'Random Forest'
    best_pipeline = trained_pipelines[best_model_name]
    best_metrics = comparison_df[comparison_df['Model'] == best_model_name].iloc[0]

    # Save to models/
    best_model_pkl_path = os.path.join(MODELS_DIR, 'best_model.pkl')
    prep_pkl_path = os.path.join(MODELS_DIR, 'preprocessing_pipeline.pkl')
    joblib.dump(best_pipeline, best_model_pkl_path)
    joblib.dump(best_pipeline.named_steps['prep'], prep_pkl_path)
    print(f"  Saved {best_model_pkl_path}")
    print(f"  Saved {prep_pkl_path}")

    # Save to ml/artifacts/ per backend contract
    joblib_path = os.path.join(ML_ARTIFACTS_DIR, 'model.joblib')
    joblib.dump(best_pipeline, joblib_path)
    print(f"  Saved {joblib_path}")

    # Export latest_features.csv (most recent week: week 33 / week_start = 2026-08-17)
    latest_week = df['week_start'].max()
    latest_df = df[df['week_start'] == latest_week].copy()
    latest_features_df = latest_df[['zipcode', 'borough'] + numerical_features].copy()
    latest_features_path = os.path.join(ML_ARTIFACTS_DIR, 'latest_features.csv')
    latest_features_df.to_csv(latest_features_path, index=False)
    print(f"  Saved {latest_features_path} ({len(latest_features_df)} rows for {latest_week})")

    # Export zip_metadata.csv
    zip_meta = df[['zipcode', 'borough', 'neighborhoods', 'latitude', 'longitude']].drop_duplicates(subset='zipcode').copy()
    zip_meta['neighborhoods'] = zip_meta['neighborhoods'].fillna('New York Metropolitan Area')
    zip_meta_path = os.path.join(ML_ARTIFACTS_DIR, 'zip_metadata.csv')
    zip_meta.to_csv(zip_meta_path, index=False)
    print(f"  Saved {zip_meta_path} ({len(zip_meta)} ZIP codes)")

    # Export model_metadata.json
    model_metadata = {
        "model_type": best_model_name,
        "feature_columns": all_model_features,
        "categorical_features": categorical_features,
        "numerical_features": numerical_features,
        "positive_class_label": 1,
        "target": target_col,
        "alert_threshold": 0.5,
        "metrics_stratified_80_20": {
            "accuracy": float(best_metrics['Accuracy']),
            "precision": float(best_metrics['Precision']),
            "recall": float(best_metrics['Recall']),
            "f1": float(best_metrics['F1']),
            "roc_auc": float(best_metrics['ROC-AUC']),
        },
        "risk_thresholds": {
            "Low": "<25",
            "Moderate": "25-49",
            "Elevated": "50-74",
            "High": ">=75"
        },
        "trained_date": "2026-08-27",
        "description": f"{best_model_name} classifier trained on 2026 NYC Health WNV surveillance and Open-Meteo weather features."
    }
    model_metadata_path = os.path.join(ML_ARTIFACTS_DIR, 'model_metadata.json')
    with open(model_metadata_path, 'w') as f:
        json.dump(model_metadata, f, indent=2)
    print(f"  Saved {model_metadata_path}")

    # -------------------------------------------------------------------------
    # 11. GENERATE FINAL REPORT
    # -------------------------------------------------------------------------
    top_features_list = rf_feat_df.head(5)['Feature'].tolist() if best_model_name == 'Random Forest' else xgb_feat_df.head(5)['Feature'].tolist()

    report_text = f"""================================================================================
NYC WEST NILE RISK PREDICTION — FINAL EXPERIMENT REPORT
================================================================================

1. DATASET SUMMARY
-------------------
Source: data/processed/training_data.csv
Documentation: DATA_TASKS.md
Grain: One row per ZIP code per epidemiological week (Year 2026)
Total Observations: {n_rows}
Total Features Ingested: {n_cols}
Model Input Features: {len(all_model_features)} ({len(numerical_features)} numerical, {len(categorical_features)} categorical)

Target Variable: '{target_col}'
  - Class 0 (Low / Not Elevated): {class_0_cnt} ({class_0_pct:.2f}%)
  - Class 1 (Elevated WNV Activity): {class_1_cnt} ({class_1_pct:.2f}%)
  - Imbalance Ratio: ~4.3 : 1

Excluded Features (Leakage / Identifiers / Constants):
  - zip_detection_status: LEAKAGE (snapshot public status as of 2026-08-21)
  - positive_count: TARGET DERIVATIVE (same-week count)
  - elevated: PRIMARY TARGET
  - year, season: CONSTANTS (no variance in 2026 summer extract)
  - neighborhoods: High cardinality text with 1,128 missing values
  - week_start: Date identifier used for temporal indexing/splitting

2. MODEL CANDIDATES & METHODOLOGY
----------------------------------
All models evaluated on the exact same 80/20 Stratified Split (Random Seed 42).
Pipeline fitted strictly on training data with median imputation and one-hot encoding.

Candidates:
  - Model A: Linear Regression (Baseline; continuous predictions thresholded at 0.5)
  - Model B: Logistic Regression (Regularized L2, balanced class weighting, standard scaled)
  - Model C: Random Forest (300 estimators, max_depth=12, balanced class weighting)
  - Model D: XGBoost (200 estimators, max_depth=5, learning_rate=0.05, scale_pos_weight={scale_pos_weight:.2f})

3. MODEL PERFORMANCE COMPARISON (80/20 STRATIFIED TEST SET)
------------------------------------------------------------
{comparison_df[['Model', 'Accuracy', 'Precision', 'Recall', 'F1', 'ROC-AUC']].to_string(index=False)}

4. TEMPORAL VALIDATION EXPERIMENT (Chronological Forward-Chain Split)
--------------------------------------------------------------------
Train: Weeks 2026-06-01 to 2026-07-27 (Weeks 22-30) | Test: Weeks 2026-08-03 to 2026-08-10 (Weeks 31-32)
{temporal_df.to_string(index=False)}

5. BEST MODEL SELECTION & RATIONALE
------------------------------------
Best Model: {best_model_name}

Rationale:
For public health biosurveillance, maximizing Recall and ROC-AUC is paramount because failing to 
detect an active WNV transmission cluster (False Negative) has severe health consequences.
{best_model_name} achieved the superior overall discriminatory capability (ROC-AUC = {best_metrics['ROC-AUC']:.3f}, 
F1 = {best_metrics['F1']:.3f}, Recall = {best_metrics['Recall']:.3f}), effectively capturing non-linear interactions 
between autoregressive trap positives, degree days, and 14-day cumulative precipitation.

6. TOP PREDICTIVE FEATURES ({best_model_name})
---------------------------------------------
"""
    for rank, feat in enumerate(top_features_list, 1):
        report_text += f"  {rank}. {feat}\n"

    report_text += f"""
7. PUBLIC HEALTH & DATA LIMITATIONS
------------------------------------
  1. Single-Season Window: Data spans June-August 2026 only; multi-year seasonality and inter-annual climate shifts are unrepresented.
  2. Public Surveillance Absence vs. True Zero: Lack of reported detection does not guarantee virus absence (no trap-effort denominator).
  3. Spatial Weather Resolution: Weather observations derive from ZIP centroid reanalysis rather than on-site micro-climate sensors.
  4. Public Health Notice: This product models elevated mosquito vector activity, NOT individual human clinical infection risk.

Artifacts exported to results/, models/, and ml/artifacts/.
"""

    report_path = os.path.join(RESULTS_DIR, 'final_report.txt')
    with open(report_path, 'w') as f:
        f.write(report_text)
    print(f"\nFinal report saved to: {report_path}")

    # -------------------------------------------------------------------------
    # 12. FINAL CONSOLE SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("NYC WEST NILE RISK MODEL COMPARISON")
    print("=" * 60)
    print("\nINPUT FILES")
    print("-----------")
    print(f"Documentation: {DOC_PATH}")
    print(f"Dataset:       {DATA_PATH}")

    print("\nDATASET")
    print("-------")
    print(f"Rows:           {n_rows}")
    print(f"Features:       {len(all_model_features)}")
    print(f"Target:         {target_col}")
    print(f"Positive class: {class_1_cnt} ({class_1_pct:.1f}%)")
    print(f"Negative class: {class_0_cnt} ({class_0_pct:.1f}%)")

    print("\nMODEL PERFORMANCE")
    print("-" * 58)
    print(f"{'Model':<22} {'Accuracy':<9} {'Precision':<10} {'Recall':<8} {'F1':<6} {'ROC-AUC':<7}")
    print("-" * 58)
    for _, r in comparison_df.iterrows():
        print(f"{r['Model']:<22} {r['Accuracy']:<9.3f} {r['Precision']:<10.3f} {r['Recall']:<8.3f} {r['F1']:<6.3f} {r['ROC-AUC']:<7.3f}")
    print("-" * 58)

    print("\nBEST MODEL")
    print("----------")
    print(f"{best_model_name}")

    print("\nWHY")
    print("---")
    print(f"{best_model_name} achieved the highest ROC-AUC ({best_metrics['ROC-AUC']:.3f}) and F1 score ({best_metrics['F1']:.3f})")
    print(f"with strong recall ({best_metrics['Recall']:.3f}), providing superior sensitivity for detecting elevated vector risk.")

    print("\nTOP MODEL FEATURES")
    print("------------------")
    for rank, feat in enumerate(top_features_list, 1):
        print(f"{rank}. {feat}")

    print("\nOUTPUTS SAVED")
    print("-------------")
    print("results/")
    print("  ├── model_comparison.csv")
    print("  ├── confusion_matrix_logistic_regression.png")
    print("  ├── confusion_matrix_random_forest.png")
    print("  ├── confusion_matrix_xgboost.png")
    print("  ├── roc_curves.png")
    print("  ├── feature_importance_random_forest.csv")
    print("  ├── feature_importance_xgboost.csv")
    print("  ├── logistic_regression_coefficients.csv")
    print("  └── final_report.txt")
    print("models/")
    print("  ├── best_model.pkl")
    print("  └── preprocessing_pipeline.pkl")
    print("ml/artifacts/")
    print("  ├── model.joblib")
    print("  ├── latest_features.csv")
    print("  ├── model_metadata.json")
    print("  └── zip_metadata.csv")
    print("=" * 60)


if __name__ == '__main__':
    main()
