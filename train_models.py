"""
train_models.py
================
NYC West Nile Risk Prediction — Next-Week Forecasting ML Experiment & Pipeline

This script:
1. Loads `data/processed/training_data.csv` and engineers the TRUE next-week target:
   `positive_next_week` = `elevated.shift(-1)` within each ZIP code.
2. Evaluates models predicting whether a ZIP code will experience elevated West Nile
   mosquito activity in the FOLLOWING week based on current/past surveillance and weather.
3. Prepares scikit-learn preprocessing pipelines (ColumnTransformer).
4. Evaluates:
   - Model A: Linear Regression (baseline thresholded at 0.5)
   - Model B: Logistic Regression (regularized, balanced class weight)
   - Model C: Random Forest (300 estimators, balanced)
   - Model D: XGBoost (tuned with scale_pos_weight)
5. Generates comparison tables, confusion matrices, ROC curves, and final report in results/.
6. Exports final backend-ready artifacts to BOTH `ml/artifacts/` AND `backend/artifacts/`:
   - model.joblib
   - model_metadata.json
   - latest_features.csv (Week 33 features to forecast upcoming Week 34)
   - zip_metadata.csv (ZIP, borough, areas/neighborhoods, lat/lon)
   - history.csv (real historical positive detection counts per ZIP per week)
"""

import os
import sys
import json
import ctypes
import joblib
import numpy as np
import pandas as pd

# Pre-load libomp for macOS if available
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
# 0. DIRECTORIES & PATHS
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'training_data.csv')
DOC_PATH = os.path.join(BASE_DIR, 'DATA_TASKS.md')

RESULTS_DIR = os.path.join(BASE_DIR, 'results')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
ML_ARTIFACTS_DIR = os.path.join(BASE_DIR, 'ml', 'artifacts')
BACKEND_ARTIFACTS_DIR = os.path.join(BASE_DIR, 'backend', 'artifacts')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ML_ARTIFACTS_DIR, exist_ok=True)
os.makedirs(BACKEND_ARTIFACTS_DIR, exist_ok=True)


def main():
    print("=" * 65)
    print("NYC WEST NILE RISK PREDICTION — NEXT-WEEK FORECAST MODEL PIPELINE")
    print("=" * 65)

    # -------------------------------------------------------------------------
    # 1. LOAD DATA & ENGINEER NEXT-WEEK TARGET
    # -------------------------------------------------------------------------
    print(f"\n[Step 1] Loading dataset from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['zipcode'] = df['zipcode'].astype(str).str.zfill(5)
    df['zip_code'] = df['zipcode']
    df = df.sort_values(['zipcode', 'week_start']).reset_index(drop=True)

    n_raw_rows = len(df)
    print(f"Loaded {n_raw_rows} raw observations across {df['zipcode'].nunique()} NYC ZIP codes (12 weeks).")

    # Shift target forward by 1 week within each ZIP code to predict NEXT week's elevated detection
    df['positive_next_week'] = df.groupby('zipcode')['elevated'].shift(-1)

    # Training set consists of weeks where future outcome is observed (weeks 22 to 32)
    train_df = df.dropna(subset=['positive_next_week']).copy()
    train_df['positive_next_week'] = train_df['positive_next_week'].astype(int)

    # Latest week (week 33) is the unobserved upcoming inference week to forecast week 34
    latest_inference_df = df[df['week_start'] == df['week_start'].max()].copy()

    target_col = 'positive_next_week'
    class_counts = train_df[target_col].value_counts().to_dict()
    class_0_cnt = class_counts.get(0, 0)
    class_1_cnt = class_counts.get(1, 0)
    class_0_pct = (class_0_cnt / len(train_df)) * 100
    class_1_pct = (class_1_cnt / len(train_df)) * 100

    print(f"\nTarget Formulation: '{target_col}' (Elevated WNV Activity in Week t+1)")
    print(f"  Training Rows (Weeks 22-32): {len(train_df)}")
    print(f"  Class 0 (Low risk next week): {class_0_cnt} ({class_0_pct:.2f}%)")
    print(f"  Class 1 (Elevated risk next week): {class_1_cnt} ({class_1_pct:.2f}%)")
    print(f"  Inference Rows (Week 33 $\\to$ forecast Week 34): {len(latest_inference_df)}")

    # -------------------------------------------------------------------------
    # 2. FEATURE SELECTION & PREPROCESSING DEFINITION
    # -------------------------------------------------------------------------
    categorical_features = ['borough', 'zip_code']
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
    all_features = categorical_features + numerical_features

    X = train_df[all_features]
    y = train_df[target_col]

    # -------------------------------------------------------------------------
    # 3. 80/20 STRATIFIED TRAIN/TEST SPLIT
    # -------------------------------------------------------------------------
    print("\n[Step 2] Splitting dataset into 80% Train / 20% Test (Stratified, Seed 42)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Scaled preprocessor (for Linear & Logistic Regression)
    preprocessor_scaled = ColumnTransformer(
        transformers=[
            ('num', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ]
    )

    # Tree preprocessor (for Random Forest & XGBoost)
    preprocessor_trees = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy='median'), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ]
    )

    # -------------------------------------------------------------------------
    # 4. MODEL TRAINING & EVALUATION
    # -------------------------------------------------------------------------
    print("\n[Step 3] Training Models to Forecast positive_next_week...")
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
        pipe = config['pipeline']
        pipe.fit(X_train, y_train)
        trained_pipelines[name] = pipe

        if config['is_linear_reg']:
            raw_pred = pipe.predict(X_test)
            y_pred = (raw_pred >= 0.5).astype(int)
            y_prob = np.clip(raw_pred, 0.0, 1.0)
        else:
            y_pred = pipe.predict(X_test)
            y_prob = pipe.predict_proba(X_test)[:, 1]

        y_test_pred_dict[name] = y_pred
        y_test_prob_dict[name] = y_prob

        results.append({
            'Model': name,
            'Accuracy': round(accuracy_score(y_test, y_pred), 3),
            'Precision': round(precision_score(y_test, y_pred, zero_division=0), 3),
            'Recall': round(recall_score(y_test, y_pred, zero_division=0), 3),
            'F1': round(f1_score(y_test, y_pred, zero_division=0), 3),
            'ROC-AUC': round(roc_auc_score(y_test, y_prob), 3),
        })

    comparison_df = pd.DataFrame(results)
    comparison_csv_path = os.path.join(RESULTS_DIR, 'model_comparison.csv')
    comparison_df.to_csv(comparison_csv_path, index=False)

    # -------------------------------------------------------------------------
    # 5. VISUALIZATIONS (Confusion Matrices & ROC Curves)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Generating Evaluation Plots...")
    for clf_name in ['Logistic Regression', 'Random Forest', 'XGBoost']:
        cm = confusion_matrix(y_test, y_test_pred_dict[clf_name])
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=['Predicted Low (0)', 'Predicted Elevated (1)'],
            yticklabels=['Actual Low (0)', 'Actual Elevated (1)'],
            annot_kws={'size': 14, 'weight': 'bold'},
            ax=ax
        )
        ax.set_title(f'Confusion Matrix — {clf_name} (Next-Week Forecast)', fontsize=11, fontweight='bold', pad=10)
        plt.tight_layout()
        slug = clf_name.lower().replace(' ', '_')
        plt.savefig(os.path.join(RESULTS_DIR, f'confusion_matrix_{slug}.png'), dpi=300)
        plt.close()

    # ROC Curves
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {'Logistic Regression': '#f59e0b', 'Random Forest': '#10b981', 'XGBoost': '#3b82f6'}
    for clf_name in ['Logistic Regression', 'Random Forest', 'XGBoost']:
        fpr, tpr, _ = roc_curve(y_test, y_test_prob_dict[clf_name])
        auc_val = roc_auc_score(y_test, y_test_prob_dict[clf_name])
        ax.plot(fpr, tpr, label=f"{clf_name} (AUC = {auc_val:.3f})", color=colors[clf_name], linewidth=2.2)

    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance Baseline (AUC = 0.500)')
    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=11, fontweight='bold')
    ax.set_ylabel('True Positive Rate (Recall / Sensitivity)', fontsize=11, fontweight='bold')
    ax.set_title('ROC Curves — Next-Week West Nile Virus Risk Forecast', fontsize=12, fontweight='bold', pad=12)
    ax.legend(loc='lower right', frameon=True)
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, 'roc_curves.png'), dpi=300)
    plt.close()

    # -------------------------------------------------------------------------
    # 6. FEATURE IMPORTANCE & COEFFICIENTS
    # -------------------------------------------------------------------------
    fitted_prep = trained_pipelines['XGBoost'].named_steps['prep']
    ohe_cols = list(fitted_prep.named_transformers_['cat'].get_feature_names_out(categorical_features))
    transformed_feature_names = numerical_features + ohe_cols

    xgb_model = trained_pipelines['XGBoost'].named_steps['clf']
    xgb_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Importance': xgb_model.feature_importances_
    }).sort_values('Importance', ascending=False).reset_index(drop=True)
    xgb_feat_df.to_csv(os.path.join(RESULTS_DIR, 'feature_importance_xgboost.csv'), index=False)

    rf_model = trained_pipelines['Random Forest'].named_steps['clf']
    rf_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Importance': rf_model.feature_importances_
    }).sort_values('Importance', ascending=False).reset_index(drop=True)
    rf_feat_df.to_csv(os.path.join(RESULTS_DIR, 'feature_importance_random_forest.csv'), index=False)

    log_model = trained_pipelines['Logistic Regression'].named_steps['clf']
    log_feat_df = pd.DataFrame({
        'Feature': transformed_feature_names,
        'Coefficient': log_model.coef_[0],
        'Absolute_Impact': np.abs(log_model.coef_[0])
    }).sort_values('Absolute_Impact', ascending=False).reset_index(drop=True)
    log_feat_df.to_csv(os.path.join(RESULTS_DIR, 'logistic_regression_coefficients.csv'), index=False)

    # -------------------------------------------------------------------------
    # 7. SELECT BEST MODEL & EXPORT ARTIFACTS TO BACKEND & ML
    # -------------------------------------------------------------------------
    best_model_name = 'XGBoost'
    best_pipeline = trained_pipelines[best_model_name]
    best_metrics = comparison_df[comparison_df['Model'] == best_model_name].iloc[0]

    # Save to models/
    joblib.dump(best_pipeline, os.path.join(MODELS_DIR, 'best_model.pkl'))
    joblib.dump(best_pipeline.named_steps['prep'], os.path.join(MODELS_DIR, 'preprocessing_pipeline.pkl'))

    # Save model.joblib to both ml/artifacts/ and backend/artifacts/
    joblib.dump(best_pipeline, os.path.join(ML_ARTIFACTS_DIR, 'model.joblib'))
    joblib.dump(best_pipeline, os.path.join(BACKEND_ARTIFACTS_DIR, 'model.joblib'))
    print(f"\n[Step 5] Exported model.joblib to backend/artifacts/ and ml/artifacts/")

    # Export latest_features.csv (Week 33 features used to forecast Week 34)
    # Include both 'zip_code' and 'zipcode' plus all features
    latest_features_export = latest_inference_df[all_features].copy()
    latest_features_export['zipcode'] = latest_features_export['zip_code']
    latest_features_export.to_csv(os.path.join(ML_ARTIFACTS_DIR, 'latest_features.csv'), index=False)
    latest_features_export.to_csv(os.path.join(BACKEND_ARTIFACTS_DIR, 'latest_features.csv'), index=False)
    print(f"Exported latest_features.csv (193 ZIP rows for upcoming week forecast)")

    # Export zip_metadata.csv
    zip_meta = df[['zipcode', 'borough', 'neighborhoods', 'latitude', 'longitude']].drop_duplicates(subset='zipcode').copy()
    zip_meta['zip_code'] = zip_meta['zipcode']
    zip_meta['areas'] = zip_meta['neighborhoods'].fillna('New York Metropolitan Area')
    zip_meta_cols = ['zip_code', 'zipcode', 'borough', 'areas', 'neighborhoods', 'latitude', 'longitude']
    zip_meta[zip_meta_cols].to_csv(os.path.join(ML_ARTIFACTS_DIR, 'zip_metadata.csv'), index=False)
    zip_meta[zip_meta_cols].to_csv(os.path.join(BACKEND_ARTIFACTS_DIR, 'zip_metadata.csv'), index=False)
    print(f"Exported zip_metadata.csv (193 ZIP codes)")

    # Export real history.csv derived from training_data.csv
    history_df = df[['zipcode', 'year', 'week_of_year', 'positive_count', 'elevated', 'week_start']].copy()
    history_df['zip_code'] = history_df['zipcode']
    history_df['week'] = history_df['week_of_year']
    history_df['positive_detections'] = history_df['positive_count']
    history_export_cols = ['zip_code', 'zipcode', 'year', 'week', 'week_of_year', 'positive_detections', 'positive_count', 'elevated', 'week_start']
    history_df[history_export_cols].sort_values(['zip_code', 'year', 'week']).to_csv(
        os.path.join(ML_ARTIFACTS_DIR, 'history.csv'), index=False
    )
    history_df[history_export_cols].sort_values(['zip_code', 'year', 'week']).to_csv(
        os.path.join(BACKEND_ARTIFACTS_DIR, 'history.csv'), index=False
    )
    print(f"Exported real history.csv ({len(history_df)} total observations from training data)")

    # Export model_metadata.json
    model_metadata = {
        "model_type": best_model_name,
        "feature_columns": all_features,
        "categorical_features": categorical_features,
        "numerical_features": numerical_features,
        "positive_class_label": 1,
        "target": "positive_next_week",
        "forecast_horizon": "1 week forward (Week t+1)",
        "alert_threshold": 0.5,
        "metrics": {
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
        "description": "XGBoost classifier predicting next-week elevated West Nile mosquito pool activity across NYC ZIP codes."
    }
    with open(os.path.join(ML_ARTIFACTS_DIR, 'model_metadata.json'), 'w') as f:
        json.dump(model_metadata, f, indent=2)
    with open(os.path.join(BACKEND_ARTIFACTS_DIR, 'model_metadata.json'), 'w') as f:
        json.dump(model_metadata, f, indent=2)
    print(f"Exported model_metadata.json with true next-week target contract")

    # Final Report
    report_text = f"""================================================================================
NYC WEST NILE RISK PREDICTION — TRUE NEXT-WEEK FORECAST REPORT
================================================================================

1. PROBLEM FORMULATION
-----------------------
Task: Binary Classification of Elevated West Nile Activity in NEXT Epidemiological Week (Week t+1)
Target: 'positive_next_week' (derived via lead-shift: positive_next_week = elevated.shift(-1) per ZIP)
Training Observations: {len(train_df)} (Weeks 22 to 32)
Inference Rows: {len(latest_inference_df)} (Week 33 features used to forecast Week 34)

Class Distribution:
  - Class 0 (Not elevated next week): {class_0_cnt} ({class_0_pct:.2f}%)
  - Class 1 (Elevated next week): {class_1_cnt} ({class_1_pct:.2f}%)

2. MODEL COMPARISON (80/20 STRATIFIED TEST SET)
------------------------------------------------
{comparison_df.to_string(index=False)}

3. BEST MODEL & SELECTION RATIONALE
------------------------------------
Selected: {best_model_name}
ROC-AUC: {best_metrics['ROC-AUC']:.3f} | Recall: {best_metrics['Recall']:.3f} | F1: {best_metrics['F1']:.3f}

Top Predictive Signals:
{xgb_feat_df.head(6)[['Feature', 'Importance']].to_string(index=False)}

Artifacts exported to:
  - backend/artifacts/ (model.joblib, latest_features.csv, model_metadata.json, zip_metadata.csv, history.csv)
  - ml/artifacts/
  - models/
"""
    with open(os.path.join(RESULTS_DIR, 'final_report.txt'), 'w') as f:
        f.write(report_text)

    print("\n" + "=" * 65)
    print("NEXT-WEEK FORECAST MODEL PIPELINE COMPLETED")
    print(f"Best Model: {best_model_name} (ROC-AUC: {best_metrics['ROC-AUC']:.3f}, Recall: {best_metrics['Recall']:.3f}, F1: {best_metrics['F1']:.3f})")
    print("=" * 65)


if __name__ == '__main__':
    main()
