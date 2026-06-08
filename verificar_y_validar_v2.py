import numpy as np
import pandas as pd
import os
import sys

# Flush stdout immediately — useful when running this from a batch file
# or from an external process that pipes output.
sys.stdout.reconfigure(line_buffering=True)

base_path = r"c:\Users\Robles\Desktop\Opinion mining\TWITTER"
files = {
    "embeddings": "embeddings_tweets.npy",
    "final_csv": "tweets_final.csv",
    "limpios": "tweets_limpios_coocurrencias.csv",
    "index_embeddings": "tweets_index_embeddings.csv"
}

print("CHECK_START")
try:
    if os.path.exists(os.path.join(base_path, files["final_csv"])):
        df_final = pd.read_csv(os.path.join(base_path, files["final_csv"]), delimiter=";")
        print(f"Final_CSV_Rows: {len(df_final)}")
    else:
        print("Final_CSV: MISSING")

    if os.path.exists(os.path.join(base_path, files["limpios"])):
        df_limpios = pd.read_csv(os.path.join(base_path, files["limpios"]), delimiter=";")
        print(f"Limpios_CSV_Rows: {len(df_limpios)}")
    else:
        print("Limpios_CSV: MISSING")

    if os.path.exists(os.path.join(base_path, files["index_embeddings"])):
        df_index = pd.read_csv(os.path.join(base_path, files["index_embeddings"]), delimiter=";")
        print(f"Index_CSV_Rows: {len(df_index)}")
    else:
        print("Index_CSV: MISSING")

    if os.path.exists(os.path.join(base_path, files["embeddings"])):
        emb = np.load(os.path.join(base_path, files["embeddings"]))
        print(f"Embeddings_Shape: {emb.shape}")
    else:
        print("Embeddings_NPY: MISSING")

except Exception as e:
    print(f"ERROR: {e}")
print("CHECK_END")
