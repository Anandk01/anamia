"""Seed model_metrics table with sample data."""
import sys
sys.path.insert(0, '.')
from db import get_db

conn = get_db()

metrics = [
    ('Random Forest', 0.92, 0.89, 0.94, 0.91, 0.96, '[[145, 12], [8, 135]]', 'CBC_Mendeley_Dataset', 1421),
    ('Gradient Boosting', 0.90, 0.87, 0.92, 0.89, 0.94, '[[140, 17], [11, 132]]', 'CBC_Mendeley_Dataset', 1421),
    ('XGBoost', 0.93, 0.91, 0.95, 0.93, 0.97, '[[148, 9], [7, 136]]', 'CBC_Mendeley_Dataset', 1421),
    ('LightGBM', 0.91, 0.88, 0.93, 0.90, 0.95, '[[143, 14], [9, 134]]', 'CBC_Mendeley_Dataset', 1421),
]

for m in metrics:
    conn.execute(
        """INSERT INTO model_metrics 
           (model_name, accuracy, precision_score, recall, f1_score, auc_roc, confusion_matrix, dataset_name, dataset_size)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        m
    )

conn.commit()
conn.close()
print("Model metrics seeded successfully!")
print("  Random Forest:     92% accuracy, 0.96 AUC-ROC")
print("  Gradient Boosting: 90% accuracy, 0.94 AUC-ROC")
print("  XGBoost:           93% accuracy, 0.97 AUC-ROC")
print("  LightGBM:          91% accuracy, 0.95 AUC-ROC")
