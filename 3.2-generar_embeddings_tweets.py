"""
Generación de embeddings para tweets de X.

Entrada:
    - tweets_para_embeddings.csv
        (debe contener al menos la columna 'texto_clean')

Salida:
    - embeddings_tweets.npy
        -> matriz NumPy (n_tweets x dim_embedding)
    - tweets_index_embeddings.csv
        -> CSV con índices y metadatos para mapear cada fila de embeddings
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

# ========== CONFIGURACIÓN BÁSICA ==========

INPUT_FILE = "tweets_para_embeddings.csv"           # CSV preprocesado
TEXT_COLUMN = "texto_clean"                         # columna que usaremos para embedding
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

OUTPUT_EMBEDDINGS = "embeddings_tweets.npy"         # matriz de embeddings
OUTPUT_INDEX = "tweets_index_embeddings.csv"        # metadatos + índice


def cargar_corpus(path: str, text_col: str) -> pd.DataFrame:
    """
    Carga el CSV y comprueba que la columna de texto existe.
    Devuelve un DataFrame con un índice limpio (0..n-1).
    """
    print(f"Leyendo corpus desde: {path}")
    df = pd.read_csv(path, sep=";", encoding="utf-8", engine="python")

    if text_col not in df.columns:
        raise ValueError(
            f"La columna de texto '{text_col}' no está en el CSV. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Eliminamos filas con texto vacío por seguridad (debería haber 0)
    df = df.dropna(subset=[text_col])
    df[text_col] = df[text_col].astype(str).str.strip()
    df = df[df[text_col] != ""].copy()

    df = df.reset_index(drop=True)
    print(f"Número de tweets cargados: {len(df)}")
    return df


def cargar_modelo(model_name: str) -> SentenceTransformer:
    """
    Carga el modelo de sentence-transformers.
    Si es la primera vez, lo descargará de internet.
    """
    print(f"Cargando modelo de embeddings: {model_name}")
    model = SentenceTransformer(model_name)
    print("Modelo cargado correctamente.")
    return model


def generar_embeddings(model: SentenceTransformer, textos: list) -> np.ndarray:
    """
    Genera embeddings para una lista de textos.
    Devuelve una matriz NumPy de shape (n_textos, dim_embedding).
    """
    print(f"Generando embeddings para {len(textos)} textos...")
    embeddings = model.encode(
        textos,
        batch_size=64,           # puedes ajustar el tamaño de batch si quieres
        show_progress_bar=True,  # barra de progreso
        convert_to_numpy=True,
        normalize_embeddings=True  # normaliza a norma 1 (útil para similitud coseno)
    )
    print("Embeddings generados.")
    print(f"Shape de la matriz de embeddings: {embeddings.shape}")
    return embeddings


def guardar_resultados(df: pd.DataFrame, embeddings: np.ndarray,
                       path_embeddings: str, path_index: str):
    """
    Guarda:
    - la matriz de embeddings en .npy
    - un CSV con índice y metadatos para saber qué tweet corresponde a cada fila.
    """
    print(f"Guardando matriz de embeddings en: {path_embeddings}")
    np.save(path_embeddings, embeddings)

    # Creamos un DataFrame índice con metadatos útiles
    # (puedes añadir/quitar columnas según te interese)
    columnas_index = [
        "source_type",
        "source_query",
        "tweet_id",
        "conversation_id",
        "is_reply",
        "autor",
        "likes",
        "retweets",
        "replies",
        "fecha",
        "texto",
        "texto_clean",
        "lang",
    ]

    columnas_presentes = [c for c in columnas_index if c in df.columns]

    df_index = df[columnas_presentes].copy()
    df_index.insert(0, "embedding_idx", range(len(df_index)))

    print(f"Guardando índice de tweets en: {path_index}")
    df_index.to_csv(path_index, sep=";", encoding="utf-8", index=False)

    print("Resultados guardados correctamente.")
    print(f"- embeddings_tweets.npy -> shape {embeddings.shape}")
    print(f"- tweets_index_embeddings.csv -> {len(df_index)} filas")


def main():
    # 1. Cargar tweets preprocesados
    df = cargar_corpus(INPUT_FILE, TEXT_COLUMN)

    # 2. Cargar modelo de embeddings
    model = cargar_modelo(MODEL_NAME)

    # 3. Generar embeddings a partir de la columna de texto limpia
    textos = df[TEXT_COLUMN].tolist()
    embeddings = generar_embeddings(model, textos)

    # 4. Guardar resultados (matriz + índice)
    guardar_resultados(df, embeddings, OUTPUT_EMBEDDINGS, OUTPUT_INDEX)

    print("\n--- Proceso completado ---")
    print(f"Embeddings disponibles en: {OUTPUT_EMBEDDINGS}")
    print(f"Índice de tweets en: {OUTPUT_INDEX}")


if __name__ == "__main__":
    main()
