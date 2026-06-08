# Preprocessing tweets for co-occurrence analysis and semantic networks.
# Requires Python 3.11 (last version fully compatible with spaCy).
# Run inside a virtualenv: .\venv\Scripts\python.exe 2.1-preprocesamiento_coocurrencias_red_tweets.py

import pandas as pd
import re
from langdetect import detect, LangDetectException
import spacy
from spacy.lang.es.stop_words import STOP_WORDS

# === CONFIG ===
INPUT_FILE = "tweets_scrapping_crudo.csv"
OUTPUT_FILE = "tweets_limpios_coocurrencias.csv"
TEXT_COLUMN = "texto"  # column with the original tweet text


def cargar_datos():
    """Reads the CSV and returns a DataFrame."""
    print(f"Reading: {INPUT_FILE}")
    df = pd.read_csv(
        INPUT_FILE,
        sep=";",
        engine="python"
    )

    if TEXT_COLUMN not in df.columns:
        raise ValueError(f"Column '{TEXT_COLUMN}' not found. Available: {list(df.columns)}")

    df = df.dropna(subset=[TEXT_COLUMN])
    df = df.reset_index(drop=True)
    print(f"Rows loaded: {len(df)}")
    return df


def limpiar_ruido(text):
    """
    Basic noise removal for tweets:
    - lowercase
    - strip newlines
    - remove URLs and mentions (@user)
    - strip hashtag symbol but keep the word text
    - remove RT prefix
    - replace non-alphanumeric chars with spaces
    """
    if not isinstance(text, str):
        text = str(text)

    text = text.lower()
    text = text.replace("\n", " ")
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"\brt\b", "", text)
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def detectar_idioma(text):
    """
    Returns a language code (e.g. 'es', 'en').
    Short texts are unreliable; returns 'unknown' for fewer than 3 chars.
    """
    if not isinstance(text, str) or len(text.strip()) < 3:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def procesar_con_spacy(df):
    """
    Runs spaCy on the 'clean' column to produce:
    - tokens (all words)
    - lemmas (base forms)
    - tokens_no_stop (lemmas without stopwords, alphabetic only)
    """
    print("Loading spaCy model (es_core_news_sm)...")
    nlp = spacy.load("es_core_news_sm")

    tokens_list = []
    lemmas_list = []
    tokens_no_stop_list = []

    print("Processing with spaCy (this may take a moment)...")

    for doc in nlp.pipe(df["clean"].tolist(), batch_size=50):
        tokens = []
        lemmas = []
        tokens_no_stop = []

        for token in doc:
            if token.is_space:
                continue

            tokens.append(token.text)
            lemmas.append(token.lemma_)

            # Keep only lemmas that are not stopwords and consist of letters
            if (not token.is_stop) and token.is_alpha:
                tokens_no_stop.append(token.lemma_.lower())

        tokens_list.append(tokens)
        lemmas_list.append(lemmas)
        tokens_no_stop_list.append(tokens_no_stop)

    df["tokens"] = tokens_list
    df["lemmas"] = lemmas_list
    df["tokens_no_stop"] = tokens_no_stop_list

    # Store as space-separated strings for CSV compatibility
    df["tokens_str"] = df["tokens"].apply(lambda toks: " ".join(toks))
    df["lemmas_str"] = df["lemmas"].apply(lambda toks: " ".join(toks))
    df["tokens_no_stop_str"] = df["tokens_no_stop"].apply(lambda toks: " ".join(toks))

    return df


def main():
    # 1. Load data
    df = cargar_datos()

    # 2. Clean noise
    print("Cleaning text...")
    df["clean"] = df[TEXT_COLUMN].apply(limpiar_ruido)

    # 3. Detect language
    print("Detecting language...")
    df["lang"] = df["clean"].apply(detectar_idioma)

    # 4. Keep only Spanish tweets
    antes = len(df)
    df = df[df["lang"] == "es"].reset_index(drop=True)
    print(f"Spanish tweets: {len(df)} (discarded {antes - len(df)})")

    # 5. Tokenize and lemmatize with spaCy
    df = procesar_con_spacy(df)

    # 6. Save
    columnas_a_guardar = [
        TEXT_COLUMN,
        "clean",
        "lang",
        "tokens_str",
        "lemmas_str",
        "tokens_no_stop_str"
    ]

    print(f"Saving to: {OUTPUT_FILE}")
    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
        columns=columnas_a_guardar,
        sep=";"
    )
    print("Done.")


if __name__ == "__main__":
    main()
