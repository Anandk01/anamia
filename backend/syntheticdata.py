import pandas as pd
import numpy as np
import random

# Number of virtual patients
num_patients = 2000
np.random.seed(42)

data = {
    'Age': np.random.randint(18, 80, num_patients),
    'Sex': np.random.choice([0, 1], num_patients), # 0 = Male, 1 = Female
    'Family_History_Anemia': np.random.choice([0, 1], num_patients, p=[0.8, 0.2]), # 20% have family history
    'Vegan_Diet': np.random.choice([0, 1], num_patients, p=[0.85, 0.15]), # 15% are vegan (higher risk of iron deficiency)
    'Fatigue': np.random.choice([0, 1], num_patients),
    'Dizziness': np.random.choice([0, 1], num_patients),
    'Breathlessness': np.random.choice([0, 1], num_patients),
    'Paleness': np.random.choice([0, 1], num_patients)
}

df = pd.DataFrame(data)

# --- The Logic: Define who actually has Anemia based on probability ---
def calculate_risk(row):
    score = 0
    # Symptoms weigh heavily
    score += row['Fatigue'] * 2
    score += row['Paleness'] * 2
    score += row['Dizziness'] * 1
    score += row['Breathlessness'] * 1
    
    # Lifestyle factors increase probability
    score += row['Family_History_Anemia'] * 1.5
    score += row['Vegan_Diet'] * 1
    
    # Females generally have a slightly higher baseline risk
    if row['Sex'] == 1:
        score += 0.5
        
    # If the combined score is high enough, flag them as 'Anemic' (1)
    if score >= 4.5:
        return 1
    else:
        return 0

# Apply the logic to create our Target column
df['Needs_CBC_Test'] = df.apply(calculate_risk, axis=1)

# Save to CSV
df.to_csv('synthetic_triage_data.csv', index=False)
print("Synthetic dataset 'synthetic_triage_data.csv' generated successfully with 2000 patients!")
print(df.head())