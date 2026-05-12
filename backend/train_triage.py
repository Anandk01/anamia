import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ─── Step 1: Load the dataset ─────────────────────────────────────────────────
df = pd.read_csv('synthetic_triage_data.csv')
print(f"Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")

# ─── Step 2: Separate features (X) and target (y) ────────────────────────────
# X contains the 8 patient symptoms and lifestyle factors the doctor observes
# BEFORE ordering a blood test (Age, Sex, Family History, Diet, Fatigue, etc.)
# y is the binary label: 1 = patient needs a CBC test, 0 = not needed.
X = df.drop(columns=['Needs_CBC_Test'])
y = df['Needs_CBC_Test']

print(f"Features : {X.columns.tolist()}")
print(f"Target   : Needs_CBC_Test  (0 = No, 1 = Yes)")

# ─── Step 3: Train / test split ───────────────────────────────────────────────
# 80% of records are used to train the model; 20% are held back to evaluate it
# on data it has never seen, giving an honest measure of real-world performance.
# random_state=42 makes the split reproducible across runs.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"\nTraining samples : {len(X_train)}")
print(f"Testing  samples : {len(X_test)}")

# ─── Step 4: Train the Random Forest model ───────────────────────────────────
# WHY RANDOM FOREST?
# A single Decision Tree memorises the training data too closely (overfitting),
# making it unreliable on new patients. A Random Forest fixes this by building
# many decision trees (n_estimators=100 by default), each trained on a random
# subset of the data and a random subset of the features. Every tree casts a
# "vote" on whether the patient needs a CBC test, and the majority vote wins.
# This ensemble approach means no single symptom or lifestyle factor dominates
# the decision — the model weighs ALL factors together, which is exactly how a
# doctor considers multiple symptoms before ordering a test.
# random_state=42 fixes the randomness so results are reproducible.
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)
print("\n[OK] Random Forest model trained successfully.")

# ─── Step 5: Evaluate on the held-out test set ───────────────────────────────
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print(f"\nTest Accuracy : {accuracy * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['No CBC Needed', 'CBC Needed']))

# ─── Step 6: Save the trained model ──────────────────────────────────────────
# The pkl file is loaded by the Flask backend at runtime so it can make
# triage predictions for new patients without re-training every time.
with open('triage_rf_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("[OK] Model saved to triage_rf_model.pkl")
