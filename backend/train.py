import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

print("1. Starting Step 1...")

try:
    # Attempt to load the data
    print("2. Attempting to find and load the CSV file...")
    df = pd.read_csv('CBC data_for_meandeley_csv.csv', skiprows=[1])
    print("3. CSV loaded successfully! Cleaning column names...")

    # Clean column names
    df.columns = [col.strip() for col in df.columns]

    # Select features
    features = ['RBC', 'MCV', 'MCH', 'MCHC', 'RDW', 'TLC', 'PLT /mm3', 'HGB']
    
    print("4. Converting columns to numeric...")
    for col in features:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print("5. Dropping empty rows...")
    df = df.dropna(subset=features)

    print("\n--- Step 1 Complete ---")
    print("Data loaded successfully.")
    print(f"Total valid patients: {len(df)}")

    # --- Step 2: Data Scaling ---
    print("\n--- Starting Step 2: Data Scaling ---")

    # Extract the 8 blood count features into X.
    # These are the only columns K-Means will use to calculate distances between patients.
    X = df[['RBC', 'MCV', 'MCH', 'MCHC', 'RDW', 'TLC', 'PLT /mm3', 'HGB']]

    # Scaling is STRICTLY NECESSARY for K-Means clustering.
    # K-Means groups patients by minimizing the Euclidean distance between data points.
    # Without scaling, features with large numeric ranges completely dominate the distance
    # calculation. For example:
    #   - PLT /mm3 (Platelet count) can range from ~50,000 to ~400,000
    #   - RBC count ranges from roughly 2.0 to 6.5
    # A small difference in PLT would outweigh any difference in RBC, making the
    # algorithm effectively ignore RBC, MCV, MCH, and other low-magnitude features.
    # StandardScaler fixes this by transforming every feature to have mean=0 and std=1,
    # so each feature contributes equally to the distance metric.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("Scaling complete.")
    print(f"X_scaled shape: {X_scaled.shape}  (rows=patients, cols=features)")
    print("\n--- Step 2 Complete ---")

    # --- Step 3: Model Training ---
    print("\n--- Starting Step 3: Model Training ---")

    # K-Means is an UNSUPERVISED LEARNING algorithm.
    # Unlike supervised models (e.g. logistic regression), it is never given labelled
    # examples of who has anemia and who does not. Instead, it discovers hidden structure
    # in the data entirely on its own by grouping patients based on the similarity of
    # their scaled blood parameters.
    #
    # Mathematically, fit_predict does the following:
    #   1. Randomly places 3 centroids (cluster centres) in the 8-dimensional feature space.
    #   2. Assigns every patient to the nearest centroid using Euclidean distance.
    #   3. Recalculates each centroid as the mean of all patients assigned to it.
    #   4. Repeats steps 2-3 until the centroids stop moving (convergence).
    # The result is 3 distinct patient groups whose members share similar CBC profiles,
    # which we will later interpret as Low, Moderate, and High anemia risk.
    #
    # n_clusters=3  : we want exactly 3 risk segments
    # random_state=42: fixes the initial centroid placement so results are reproducible
    kmeans = KMeans(n_clusters=3, random_state=42)

    # fit_predict trains the model on X_scaled and immediately returns the cluster label
    # (0, 1, or 2) assigned to each patient in a single step.
    df['Cluster'] = kmeans.fit_predict(X_scaled)

    print("✅ Model trained successfully.")
    print(f"Cluster distribution:\n{df['Cluster'].value_counts().sort_index()}")
    print("\n--- Step 3 Complete ---")

    # --- Step 4: Interpret Clusters (Risk Mapping) ---
    print("\n--- Starting Step 4: Cluster Interpretation ---")

    # Hemoglobin (HGB) is the primary clinical indicator of anemia.
    # Medically, a LOW HGB level directly signals that red blood cells are not carrying
    # enough oxygen — which is the definition of anemia. Therefore:
    #   - The cluster with the LOWEST mean HGB  → High Risk
    #   - The cluster with the MIDDLE  mean HGB  → Moderate Risk
    #   - The cluster with the HIGHEST mean HGB  → Low Risk
    # Using HGB averages per cluster gives us a medically grounded, data-driven way to
    # attach clinical meaning to the anonymous labels (0, 1, 2) that K-Means produced.
    hgb_means = df.groupby('Cluster')['HGB'].mean()

    # Sort clusters by their mean HGB ascending (lowest HGB first = highest risk first)
    # and assign risk labels accordingly.
    sorted_clusters = hgb_means.sort_values().index.tolist()
    risk_mapping = {
        sorted_clusters[0]: 'High Risk',
        sorted_clusters[1]: 'Moderate Risk',
        sorted_clusters[2]: 'Low Risk',
    }

    df['Risk_Category'] = df['Cluster'].map(risk_mapping)

    print("Cluster → Mean HGB → Risk Category:")
    for cluster, mean_hgb in hgb_means.sort_values().items():
        print(f"  Cluster {cluster}: Mean HGB = {mean_hgb:.2f}  →  {risk_mapping[cluster]}")
    print("\nSample verification (first 5 rows):")
    print(df[['HGB', 'Cluster', 'Risk_Category']].head())
    print("\n--- Step 4 Complete ---")

    # --- Step 5: Save the Assets ---
    print("\n--- Starting Step 5: Saving Assets ---")

    # Persist the three assets needed by the prediction app:
    #   kmeans_model.pkl : the trained model, used to assign a cluster to new patients
    #   scaler.pkl       : the fitted scaler, must be applied to new data before predicting
    #                      (new data must be scaled with the SAME mean/std learned here)
    #   risk_mapping.pkl : the dictionary that converts a raw cluster number to a
    #                      human-readable risk label
    with open('kmeans_model.pkl', 'wb') as f:
        pickle.dump(kmeans, f)

    with open('scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)

    with open('risk_mapping.pkl', 'wb') as f:
        pickle.dump(risk_mapping, f)

    print("\n✅ Machine Learning pipeline is complete and files are saved!")
    print("  kmeans_model.pkl, scaler.pkl, risk_mapping.pkl")
    print("\n--- Step 5 Complete ---")

except FileNotFoundError:
    print("\n❌ ERROR: I cannot find 'CBC data_for_meandeley_csv.csv'.")
    print("FIX: Please make sure the CSV file is saved in the EXACT SAME FOLDER as this Python file or Notebook.")
except Exception as e:
    print(f"\n❌ ERROR: Something else went wrong: {e}")