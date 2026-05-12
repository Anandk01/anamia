"""
train_supervised.py
-------------------
Labels the CBC dataset using WHO/clinical HGB thresholds and splits it
80/20 into train and test sets.

Labelling rules
---------------
anemia_detected:
  - Sex == 1 (female): HGB < 12.0  → 1 (anemia), else 0
  - Sex == 0 (male):   HGB < 13.0  → 1 (anemia), else 0
  - If Sex column is absent or value is NaN: HGB < 12.0 → 1, else 0

severity_label (WHO thresholds):
  HGB >= 12.0          → 0  (None)
  10.0 <= HGB < 12.0   → 1  (Mild)
  8.0  <= HGB < 10.0   → 2  (Moderate)
  HGB < 8.0            → 3  (Severe)

Output
------
  backend/data/train.csv
  backend/data/test.csv
  backend/models/rf_anemia_classifier.pkl
  backend/models/rf_scaler.pkl
  backend/models/   (directory created if absent)
"""

import os
import sys

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "CBC data_for_meandeley_csv.csv")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")

# ---------------------------------------------------------------------------
# Severity label constants
# ---------------------------------------------------------------------------
SEVERITY_NONE = 0
SEVERITY_MILD = 2
SEVERITY_MODERATE = 2
SEVERITY_SEVERE = 3

SEVERITY_LABELS = {0: "None", 1: "Mild", 2: "Moderate", 3: "Severe"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_dataset(path: str) -> pd.DataFrame:
    """Load the CBC CSV, skipping the second descriptive header row."""
    df = pd.read_csv(path, skiprows=[1])
    # Strip leading/trailing whitespace from column names
    df.columns = [c.strip() for c in df.columns]
    return df


def assign_anemia_detected(df: pd.DataFrame) -> pd.Series:
    """
    Return a Series of 0/1 anemia labels using sex-specific HGB thresholds.

    Sex encoding in this dataset:
      0 → male   (threshold: HGB < 13.0)
      1 → female (threshold: HGB < 12.0)

    Rows where Sex is NaN fall back to the female threshold (HGB < 12.0).
    """
    hgb = df["HGB"]

    if "Sex" not in df.columns:
        print("  [INFO] No 'Sex' column found — using single threshold HGB < 12.0")
        return (hgb < 12.0).astype(int)

    # Default: female threshold
    labels = (hgb < 12.0).astype(int)

    # Override for confirmed males (Sex == 0)
    male_mask = df["Sex"] == 0
    labels[male_mask] = (hgb[male_mask] < 13.0).astype(int)

    return labels


def assign_severity_label(hgb: pd.Series) -> pd.Series:
    """
    Map HGB values to WHO severity labels:
      0 = None     (HGB >= 12.0)
      1 = Mild     (10.0 <= HGB < 12.0)
      2 = Moderate (8.0  <= HGB < 10.0)
      3 = Severe   (HGB  < 8.0)
    """
    conditions = [
        hgb >= 12.0,
        (hgb >= 10.0) & (hgb < 12.0),
        (hgb >= 8.0) & (hgb < 10.0),
        hgb < 8.0,
    ]
    choices = [0, 1, 2, 3]
    return pd.Series(
        pd.cut(
            hgb,
            bins=[-float("inf"), 8.0, 10.0, 12.0, float("inf")],
            labels=[3, 2, 1, 0],
            right=False,
        ).astype(int),
        index=hgb.index,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Anemia Detection — Supervised Training Data Preparation")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load
    # ------------------------------------------------------------------
    print(f"\n[1] Loading dataset from:\n    {CSV_PATH}")
    df = load_dataset(CSV_PATH)
    print(f"    Raw shape: {df.shape}")

    # ------------------------------------------------------------------
    # 2. Drop rows with missing HGB (cannot label without it)
    # ------------------------------------------------------------------
    before = len(df)
    df = df.dropna(subset=["HGB"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"    Dropped {dropped} rows with missing HGB.")
    print(f"    Shape after dropping NaN HGB: {df.shape}")

    # ------------------------------------------------------------------
    # 3. Rename columns to canonical names used by the ML pipeline
    # ------------------------------------------------------------------
    rename_map = {
        "RBC": "RBC",
        "MCV": "MCV",
        "MCH": "MCH",
        "MCHC": "MCHC",
        "RDW": "RDW",
        "TLC": "TLC",
        "PLT /mm3": "PLT",
        "HGB": "HGB",
        "Sex": "Sex",
        "Age": "Age",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ------------------------------------------------------------------
    # 4. Label: anemia_detected
    # ------------------------------------------------------------------
    print("\n[2] Assigning anemia_detected labels …")
    df["anemia_detected"] = assign_anemia_detected(df)

    # ------------------------------------------------------------------
    # 5. Label: severity_label
    # ------------------------------------------------------------------
    print("[3] Assigning severity_label …")
    df["severity_label"] = assign_severity_label(df["HGB"])

    # ------------------------------------------------------------------
    # 6. Dataset info
    # ------------------------------------------------------------------
    print("\n[4] Dataset summary")
    print(f"    Total samples : {len(df)}")
    print(f"    Features      : RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB")

    print("\n    anemia_detected distribution:")
    ad_counts = df["anemia_detected"].value_counts().sort_index()
    for label, count in ad_counts.items():
        pct = 100 * count / len(df)
        name = "Anemia" if label == 1 else "No Anemia"
        print(f"      {label} ({name:10s}): {count:4d}  ({pct:.1f}%)")

    print("\n    severity_label distribution:")
    sl_counts = df["severity_label"].value_counts().sort_index()
    for label, count in sl_counts.items():
        pct = 100 * count / len(df)
        name = SEVERITY_LABELS.get(label, "?")
        print(f"      {label} ({name:8s}): {count:4d}  ({pct:.1f}%)")

    # ------------------------------------------------------------------
    # 7. Select feature columns + labels for the split
    # ------------------------------------------------------------------
    feature_cols = ["RBC", "MCV", "MCH", "MCHC", "RDW", "TLC", "PLT", "HGB"]
    extra_cols = [c for c in ["Age", "Sex"] if c in df.columns]
    label_cols = ["anemia_detected", "severity_label"]

    keep_cols = feature_cols + extra_cols + label_cols
    # Only keep columns that actually exist
    keep_cols = [c for c in keep_cols if c in df.columns]

    df_model = df[keep_cols].dropna(subset=feature_cols).reset_index(drop=True)
    dropped_feat = len(df) - len(df_model)
    if dropped_feat:
        print(f"\n    Dropped {dropped_feat} additional rows with missing feature values.")
    print(f"    Final usable samples: {len(df_model)}")

    # ------------------------------------------------------------------
    # 8. Train / test split (80/20, stratified on anemia_detected)
    # ------------------------------------------------------------------
    print("\n[5] Splitting 80/20 (random_state=42, stratify=anemia_detected) …")
    train_df, test_df = train_test_split(
        df_model,
        test_size=0.2,
        random_state=42,
        stratify=df_model["anemia_detected"],
    )
    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    print(f"    Train size : {len(train_df)}")
    print(f"    Test  size : {len(test_df)}")

    # ------------------------------------------------------------------
    # 9. Save splits
    # ------------------------------------------------------------------
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    train_path = os.path.join(DATA_DIR, "train.csv")
    test_path = os.path.join(DATA_DIR, "test.csv")

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"\n[6] Saved splits:")
    print(f"    {train_path}")
    print(f"    {test_path}")
    print(f"\n[7] Created directory (if new): {MODELS_DIR}")

    print("\n" + "=" * 60)
    print("Done. Ready for model training (task 0.2 / 0.3).")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Task 0.2 — Random Forest binary classifier for anemia detection
# ---------------------------------------------------------------------------

FEATURE_COLS = ["RBC", "MCV", "MCH", "MCHC", "RDW", "TLC", "PLT", "HGB"]
RF_MODEL_PATH = os.path.join(MODELS_DIR, "rf_anemia_classifier.pkl")
RF_SCALER_PATH = os.path.join(MODELS_DIR, "rf_scaler.pkl")


def train_rf_classifier():
    """
    Train a Random Forest binary classifier for anemia detection.

    - Loads train/test splits from backend/data/
    - Features: RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB
    - Target: anemia_detected (0/1)
    - Scales features with StandardScaler
    - Trains RandomForestClassifier(n_estimators=100, random_state=42)
    - Prints accuracy, precision, recall, F1 (weighted)
    - Saves model → backend/models/rf_anemia_classifier.pkl
    - Saves scaler → backend/models/rf_scaler.pkl
    """
    print("\n" + "=" * 60)
    print("Task 0.2 — Random Forest Anemia Classifier Training")
    print("=" * 60)

    train_path = os.path.join(DATA_DIR, "train.csv")
    test_path = os.path.join(DATA_DIR, "test.csv")

    # ------------------------------------------------------------------
    # 1. Load splits (run data prep first if files are missing)
    # ------------------------------------------------------------------
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print("\n[INFO] train.csv / test.csv not found — running data preparation …")
        main()

    print(f"\n[1] Loading training data from:\n    {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"    Train shape: {train_df.shape}")

    print(f"\n[2] Loading test data from:\n    {test_path}")
    test_df = pd.read_csv(test_path)
    print(f"    Test  shape: {test_df.shape}")

    # ------------------------------------------------------------------
    # 2. Prepare feature matrices and target vectors
    # ------------------------------------------------------------------
    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["anemia_detected"].values

    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["anemia_detected"].values

    print(f"\n[3] Features : {FEATURE_COLS}")
    print(f"    Target   : anemia_detected")
    print(f"    Train positives: {y_train.sum()} / {len(y_train)}")
    print(f"    Test  positives: {y_test.sum()} / {len(y_test)}")

    # ------------------------------------------------------------------
    # 3. Scale features
    # ------------------------------------------------------------------
    print("\n[4] Fitting StandardScaler on training data …")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ------------------------------------------------------------------
    # 4. Train Random Forest
    # ------------------------------------------------------------------
    print("\n[5] Training RandomForestClassifier(n_estimators=100, random_state=42) …")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train_scaled, y_train)
    print("    Training complete.")

    # ------------------------------------------------------------------
    # 5. Evaluate on test set
    # ------------------------------------------------------------------
    print("\n[6] Evaluating on test set …")
    y_pred = rf.predict(X_test_scaled)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"\n    Accuracy  : {acc:.4f}")
    print(f"    Precision : {prec:.4f}  (weighted)")
    print(f"    Recall    : {rec:.4f}  (weighted)")
    print(f"    F1 Score  : {f1:.4f}  (weighted)")

    # ------------------------------------------------------------------
    # 6. Save model and scaler
    # ------------------------------------------------------------------
    os.makedirs(MODELS_DIR, exist_ok=True)

    joblib.dump(rf, RF_MODEL_PATH)
    joblib.dump(scaler, RF_SCALER_PATH)

    print(f"\n[7] Saved model  → {RF_MODEL_PATH}")
    print(f"    Saved scaler → {RF_SCALER_PATH}")

    print("\n" + "=" * 60)
    print("Task 0.2 complete.")
    print("=" * 60)

    return rf, scaler


# ---------------------------------------------------------------------------
# Task 0.3 — Gradient Boosting multi-class classifier for severity
# ---------------------------------------------------------------------------

GB_MODEL_PATH = os.path.join(MODELS_DIR, "gb_severity_classifier.pkl")


def train_gb_severity_classifier():
    """
    Train a Gradient Boosting multi-class classifier for anemia severity.

    - Loads train/test splits from backend/data/
    - Features: RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB (all 8 CBC fields)
    - Target: severity_label (0=None, 1=Mild, 2=Moderate, 3=Severe)
    - Reuses the StandardScaler already saved at backend/models/rf_scaler.pkl
    - Trains GradientBoostingClassifier(n_estimators=100, random_state=42)
    - Prints sklearn classification_report
    - Saves model → backend/models/gb_severity_classifier.pkl
    """
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import classification_report

    print("\n" + "=" * 60)
    print("Task 0.3 — Gradient Boosting Severity Classifier Training")
    print("=" * 60)

    train_path = os.path.join(DATA_DIR, "train.csv")
    test_path = os.path.join(DATA_DIR, "test.csv")

    # ------------------------------------------------------------------
    # 1. Load splits (run data prep first if files are missing)
    # ------------------------------------------------------------------
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print("\n[INFO] train.csv / test.csv not found — running data preparation …")
        main()

    print(f"\n[1] Loading training data from:\n    {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"    Train shape: {train_df.shape}")

    print(f"\n[2] Loading test data from:\n    {test_path}")
    test_df = pd.read_csv(test_path)
    print(f"    Test  shape: {test_df.shape}")

    # ------------------------------------------------------------------
    # 2. Prepare feature matrices and target vectors
    # ------------------------------------------------------------------
    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["severity_label"].values

    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["severity_label"].values

    print(f"\n[3] Features : {FEATURE_COLS}")
    print(f"    Target   : severity_label")
    print(f"\n    Train severity distribution:")
    for label in sorted(set(y_train)):
        count = (y_train == label).sum()
        pct = 100 * count / len(y_train)
        name = SEVERITY_LABELS.get(label, "?")
        print(f"      {label} ({name:8s}): {count:4d}  ({pct:.1f}%)")

    # ------------------------------------------------------------------
    # 3. Load the existing scaler (fitted during RF training)
    # ------------------------------------------------------------------
    if not os.path.exists(RF_SCALER_PATH):
        print(f"\n[INFO] Scaler not found at {RF_SCALER_PATH} — running RF training first …")
        train_rf_classifier()

    print(f"\n[4] Loading scaler from:\n    {RF_SCALER_PATH}")
    scaler = joblib.load(RF_SCALER_PATH)

    X_train_scaled = scaler.transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ------------------------------------------------------------------
    # 4. Train Gradient Boosting classifier
    # ------------------------------------------------------------------
    print("\n[5] Training GradientBoostingClassifier(n_estimators=100, random_state=42) …")
    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    gb.fit(X_train_scaled, y_train)
    print("    Training complete.")

    # ------------------------------------------------------------------
    # 5. Evaluate on test set
    # ------------------------------------------------------------------
    print("\n[6] Evaluating on test set …")
    y_pred = gb.predict(X_test_scaled)

    target_names = ["None", "Mild", "Moderate", "Severe"]
    report = classification_report(y_test, y_pred, target_names=target_names, zero_division=0)
    print("\n    Classification Report:")
    print(report)

    # ------------------------------------------------------------------
    # 6. Save model
    # ------------------------------------------------------------------
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(gb, GB_MODEL_PATH)
    print(f"[7] Saved model → {GB_MODEL_PATH}")

    print("\n" + "=" * 60)
    print("Task 0.3 complete.")
    print("=" * 60)

    return gb


if __name__ == "__main__":
    main()
    train_rf_classifier()
    train_gb_severity_classifier()
