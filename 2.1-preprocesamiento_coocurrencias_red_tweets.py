# Preprocesamiento de tweets para análisis de coocurrencias y redes semánticas.
#
# Antes de ejecutar esto es necesario instalar las dependencias en la terminal, usando en el entorno virtual con una versión...
# ... 3.11 de Python, pues es la última compatible con Spacy. Preguntar a la IA cómo usar el venv (entorno virtual).
# Una vez creado el entorno virtual, la ruta para ejecutar este script y que funcione es...
# ... ".\venv\Scripts\python.exe 2.1-preprocesamiento_coocurrencias_red_tweets.py"

import pandas as pd
import re
from langdetect import detect, LangDetectException
import spacy
from spacy.lang.es.stop_words import STOP_WORDS

# === CONFIGURACIÓN BÁSICA ===
INPUT_FILE = "tweets_scrapping_crudo.csv"      # nombre de tu CSV de entrada
OUTPUT_FILE = "tweets_limpios_coocurrencias.csv"  # nombre del CSV de salida
TEXT_COLUMN = "texto"                          # nombre de la columna que contiene el tweet original


def cargar_datos():
    """Lee el CSV y devuelve un DataFrame."""
    print(f"Leyendo archivo: {INPUT_FILE}")
    df = pd.read_csv(
        INPUT_FILE,
        sep=";",          # separador correcto
        engine="python"   # opcional, pero robusto
    )

    # Comprobamos que la columna de texto exista
    if TEXT_COLUMN not in df.columns:
        raise ValueError(f"La columna '{TEXT_COLUMN}' no existe en el CSV. "
                         f"Columnas disponibles: {list(df.columns)}")

    # Eliminamos filas donde el texto esté vacío o sea NaN
    df = df.dropna(subset=[TEXT_COLUMN])
    df = df.reset_index(drop=True)
    print(f"Filas cargadas: {len(df)}")
    return df


def limpiar_ruido(text):
    """
    Limpia ruido básico del tweet:
    - pasa a minúsculas
    - elimina saltos de línea
    - elimina URLs
    - elimina menciones (@usuario)
    - elimina hashtags (opcional: conserva el texto sin #)
    - sustituye símbolos raros por espacios
    """
    if not isinstance(text, str):
        text = str(text)

    # minúsculas
    text = text.lower()

    # quitar saltos de línea
    text = text.replace("\n", " ")

    # eliminar URLs
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    # eliminar menciones (@usuario)
    text = re.sub(r"@\w+", "", text)

    # eliminar hashtag pero conservar el texto (ej: #Universidad -> universidad)
    text = re.sub(r"#(\w+)", r"\1", text)

    # eliminar "RT" de retweets
    text = re.sub(r"\brt\b", "", text)

    # sustituir cualquier carácter que no sea letra, número o espacio por espacio
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)

    # colapsar espacios múltiples
    text = re.sub(r"\s+", " ", text).strip()

    return text


def detectar_idioma(text):
    """
    Devuelve el código de idioma (por ejemplo 'es', 'en', 'pt', etc.).
    NO traduce el texto, solo intenta adivinar el idioma.
    """
    # textos muy cortos son difíciles de detectar
    if not isinstance(text, str) or len(text.strip()) < 3:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def procesar_con_spacy(df):
    """
    Aplica spaCy a la columna 'clean' para obtener:
    - tokens (todas las palabras)
    - lemmas (formas base)
    - tokens_no_stop (lemmas sin stopwords, solo letras)
    """
    print("Cargando modelo de spaCy para español (es_core_news_sm)...")
    nlp = spacy.load("es_core_news_sm")

    tokens_list = []
    lemmas_list = []
    tokens_no_stop_list = []

    print("Procesando texto con spaCy (puede tardar un poco)...")

    for doc in nlp.pipe(df["clean"].tolist(), batch_size=50):
        tokens = []
        lemmas = []
        tokens_no_stop = []

        for token in doc:
            if token.is_space:
                continue

            tokens.append(token.text)
            lemmas.append(token.lemma_)

            # nos quedamos solo con lemmas, sin stopwords, solo letras
            if (not token.is_stop) and token.is_alpha:
                tokens_no_stop.append(token.lemma_.lower())

        tokens_list.append(tokens)
        lemmas_list.append(lemmas)
        tokens_no_stop_list.append(tokens_no_stop)

    df["tokens"] = tokens_list
    df["lemmas"] = lemmas_list
    df["tokens_no_stop"] = tokens_no_stop_list

    # Para guardar en CSV, convertimos las listas en cadenas separadas por espacios
    df["tokens_str"] = df["tokens"].apply(lambda toks: " ".join(toks))
    df["lemmas_str"] = df["lemmas"].apply(lambda toks: " ".join(toks))
    df["tokens_no_stop_str"] = df["tokens_no_stop"].apply(lambda toks: " ".join(toks))

    return df


def main():
    # 1. Cargar datos
    df = cargar_datos()

    # 2. Crear columna 'clean' con texto normalizado y sin ruido técnico
    print("Limpiando ruido del texto...")
    df["clean"] = df[TEXT_COLUMN].apply(limpiar_ruido)

    # 3. Detectar idioma
    print("Detectando idioma de los tweets...")
    df["lang"] = df["clean"].apply(detectar_idioma)

    # 4. Filtrar solo español
    antes = len(df)
    df = df[df["lang"] == "es"].reset_index(drop=True)
    despues = len(df)
    print(f"Tweets en español: {despues} (descartados {antes - despues})")

    # 5. Procesar con spaCy (tokenización, lematización, stopwords)
    df = procesar_con_spacy(df)

    # 6. Guardar resultado
    columnas_a_guardar = [
        TEXT_COLUMN,         # texto original
        "clean",             # texto limpio
        "lang",              # idioma detectado
        "tokens_str",        # tokens
        "lemmas_str",        # lemas
        "tokens_no_stop_str" # lemas sin stopwords
    ]

    print(f"Guardando CSV limpio en: {OUTPUT_FILE}")
    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
        columns=columnas_a_guardar,
        sep=";"
    )
    print("¡Listo! Corpus de tweets preprocesado guardado.")


if __name__ == "__main__":
    main()
