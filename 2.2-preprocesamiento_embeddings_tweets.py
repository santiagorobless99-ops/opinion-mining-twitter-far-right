"""
Preprocessing tweets from X for sentence embeddings.

Expects the CSV produced by the scraping script, with at least:
- source_type
- source_query
- tweet_id
- conversation_id
- is_reply
- autor
- texto
- likes
- retweets
- replies
- fecha
- fecha_descarga
- estado_descarga

Output: same metadata + a 'texto_clean' column ready for embedding models.
"""

import pandas as pd
import re
from langdetect import detect, LangDetectException

# ========= CONFIG =========

INPUT_FILE = "tweets_scrapping_crudo.csv"       # input CSV from scraping step
OUTPUT_FILE = "tweets_para_embeddings.csv"       # output CSV

TEXT_COL = "texto"                  # column with the original tweet text
STATUS_COL = "estado_descarga"      # column with download status

# Quality filters for the text to embed
MIN_CHAR_LEN = 10                   # minimum character length
MIN_WORDS = 2                       # minimum word count

# Language filter — set to False for multilingual corpora
USAR_FILTRO_IDIOMA = True
IDIOMA_OBJETIVO = "es"              # 'es' for Spanish


# ========= FUNCTIONS =========

def cargar_datos():
    """Reads the raw CSV and returns a DataFrame."""
    print(f"Reading: {INPUT_FILE}")
    df = pd.read_csv(
        INPUT_FILE,
        sep=";",
        encoding="utf-8",
        engine="python"
    )

    if TEXT_COL not in df.columns:
        raise ValueError(
            f"Text column '{TEXT_COL}' not found. "
            f"Available: {list(df.columns)}"
        )

    if STATUS_COL not in df.columns:
        raise ValueError(
            f"Status column '{STATUS_COL}' not found. "
            f"Available: {list(df.columns)}"
        )

    print(f"Rows loaded: {len(df)}")
    return df


def limpiar_texto_para_embeddings(texto):
    """
    Minimal cleaning for embeddings:
    - Ensures input is a string.
    - Removes line breaks, URLs, and mentions (@user).
    - Normalizes whitespace and lowercases.

    Punctuation and emojis are kept — they carry semantic information.
    Hashtag symbols are stripped but the text is preserved for context.
    """
    if not isinstance(texto, str):
        texto = str(texto)

    # Strip básico
    texto = texto.strip()

    # Sustituir saltos de línea por espacio
    texto = texto.replace("\n", " ").replace("\r", " ")

    # Eliminar URLs
    texto = re.sub(r"http\S+|www\.\S+", "", texto)

    # Eliminar menciones (@usuario)
    texto = re.sub(r"@\w+", "", texto)

    # Conservar texto de hashtags sin el símbolo #
    texto = re.sub(r"#(\w+)", r"\1", texto)

    # Eliminar "RT" de retweets
    texto = re.sub(r"\bRT\b", "", texto, flags=re.IGNORECASE)

    # Colapsar espacios múltiples
    texto = re.sub(r"\s+", " ", texto)

    # Minúsculas
    texto = texto.lower().strip()

    return texto


def detectar_idioma_seguro(texto):
    """
    Detects language with langdetect.
    Returns 'unknown' for short or unparseable input.
    """
    if not isinstance(texto, str):
        return "unknown"
    texto = texto.strip()
    if len(texto) < 3:
        return "unknown"
    try:
        return detect(texto)
    except (LangDetectException, Exception):
        return "unknown"


def aplicar_filtros_de_calidad(df):
    """
    Applies quality filters in sequence:
    1. Keep only successfully downloaded rows
    2. Drop NaN text
    3. Clean text -> 'texto_clean'
    4. Drop empty texts after cleaning
    5. Filter by minimum length (chars and words)
    6. Optionally filter by language
    """
    # 1. Keep only successful downloads
    antes = len(df)
    df = df[df[STATUS_COL] == "EXITO"].copy()
    print(f"After status filter: {len(df)} rows (dropped {antes - len(df)})")

    # 2. Drop NaN
    df = df.dropna(subset=[TEXT_COL])
    df = df.reset_index(drop=True)
    print(f"After dropping NaN: {len(df)} rows")

    # 3. Clean
    print("Cleaning text for embeddings...")
    df["texto_clean"] = df[TEXT_COL].apply(limpiar_texto_para_embeddings)

    # 4. Drop empties
    antes = len(df)
    df = df[df["texto_clean"].str.strip() != ""].copy()
    print(f"After dropping empty texts: {len(df)} rows (dropped {antes - len(df)})")

    # 5. Length filters
    df["n_chars"] = df["texto_clean"].str.len()
    df["n_words"] = df["texto_clean"].str.split().apply(len)

    antes = len(df)
    df = df[
        (df["n_chars"] >= MIN_CHAR_LEN) &
        (df["n_words"] >= MIN_WORDS)
    ].copy()
    print(f"After length filter: {len(df)} rows (dropped {antes - len(df)})")

    # 6. Language filter
    if USAR_FILTRO_IDIOMA:
        print("Detecting language...")
        df["lang"] = df["texto_clean"].apply(detectar_idioma_seguro)
        antes = len(df)
        df = df[df["lang"] == IDIOMA_OBJETIVO].copy().reset_index(drop=True)
        print(f"Spanish only: {len(df)} (dropped {antes - len(df)})")
    else:
        df["lang"] = "unknown"

    return df


def seleccionar_columnas_salida(df):
    """
    Selects the columns to keep: traceability metadata + cleaned text.
    Only includes columns that actually exist in the DataFrame.
    """
    columnas_basicas = [
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
        "fecha_descarga",
        STATUS_COL,
        TEXT_COL,
        "texto_clean",
        "n_chars",
        "n_words",
        "lang",
    ]

    # Algunas columnas podrían no existir si el CSV original es distinto;
    # filtramos solo las que estén presentes.
    columnas_presentes = [c for c in columnas_basicas if c in df.columns]

    df_salida = df[columnas_presentes].copy()
    return df_salida


def main():
    # 1. Load raw data
    df = cargar_datos()

    # 2. Filter and clean
    df = aplicar_filtros_de_calidad(df)

    # 3. Select output columns
    df_salida = seleccionar_columnas_salida(df)

    # 4. Save
    print(f"Saving to: {OUTPUT_FILE}")
    df_salida.to_csv(
        OUTPUT_FILE,
        sep=";",
        encoding="utf-8",
        index=False
    )
    print("Done.")


if __name__ == "__main__":
    main()
