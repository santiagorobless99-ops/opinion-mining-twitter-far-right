import numpy as np
import pandas as pd
import os

# Quick sanity check — I run this after the pipeline to verify
# that the output files exist and their shapes are consistent.

base_path = r"c:\Users\Robles\Desktop\Opinion mining\TWITTER"
files = {
    "embeddings": "embeddings_tweets.npy",
    "final_csv": "tweets_final.csv",
    "index_embeddings": "tweets_index_embeddings.csv"
}

try:
    print("--- Data verification ---")
    emb_path = os.path.join(base_path, files["embeddings"])
    if os.path.exists(emb_path):
        emb = np.load(emb_path)
        print(f"Embeddings shape: {emb.shape}")
    else:
        print(f"Embeddings file not found at {emb_path}")

    csv_path = os.path.join(base_path, files["final_csv"])
    if os.path.exists(csv_path):
        df_final = pd.read_csv(csv_path, delimiter=";")
        print(f"Tweets final rows: {len(df_final)}")
    else:
        print(f"Final CSV not found at {csv_path}")

    index_path = os.path.join(base_path, files["index_embeddings"])
    if os.path.exists(index_path):
        df_index = pd.read_csv(index_path, delimiter=";")
        print(f"Index embeddings rows: {len(df_index)}")
    else:
        print(f"Index embeddings not found at {index_path}")

except Exception as e:
    print(f"Error: {e}")
