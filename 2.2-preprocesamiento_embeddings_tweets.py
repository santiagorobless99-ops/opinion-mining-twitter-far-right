"""
Preprocesamiento de tweets de X optimizado para embeddings.

Supone como entrada el CSV generado por el script de scrapping, con al menos:
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

Salida: un CSV con los mismos metadatos + una columna 'texto_clean'
lista para usar con modelos de embeddings.
"""

import pandas as pd
import re
from langdetect import detect, LangDetectException

# ========= CONFIGURACIÓN BÁSICA =========

INPUT_FILE = "tweets_scrapping_crudo.csv"       # CSV del scrapping
OUTPUT_FILE = "tweets_para_embeddings.csv"       # CSV de salida

TEXT_COL = "texto"                  # columna con el tweet original
STATUS_COL = "estado_descarga"      # columna con el estado de la descarga

# Filtros de calidad para el texto a embedder
MIN_CHAR_LEN = 10                   # longitud mínima en caracteres
MIN_WORDS = 2                       # número mínimo de palabras

# Filtro de idioma (recomendado si solo quieres español)
USAR_FILTRO_IDIOMA = True
IDIOMA_OBJETIVO = "es"              # 'es' para castellano


# ========= FUNCIONES =========

def cargar_datos():
    """Lee el CSV original y devuelve un DataFrame."""
    print(f"Leyendo archivo de entrada: {INPUT_FILE}")
    df = pd.read_csv(
        INPUT_FILE,
        sep=";",
        encoding="utf-8",
        engine="python"
    )

    if TEXT_COL not in df.columns:
        raise ValueError(
            f"No se encuentra la columna de texto '{TEXT_COL}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    if STATUS_COL not in df.columns:
        raise ValueError(
            f"No se encuentra la columna de estado '{STATUS_COL}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    print(f"Filas totales cargadas: {len(df)}")
    return df


def limpiar_texto_para_embeddings(texto):
    """
    Limpieza mínima pensada para embeddings:
    - Asegura que es string.
    - Elimina saltos de línea.
    - Elimina URLs.
    - Elimina menciones (@usuario) - específico de Twitter.
    - Normaliza espacios.
    - Pasa a minúsculas.

    IMPORTANTE: NO eliminamos signos de puntuación ni emojis,
    porque pueden aportar información semántica útil a los embeddings.
    Conservamos hashtags sin el símbolo # porque aportan contexto.
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
    Detecta el idioma del texto usando langdetect.
    Si el texto es muy corto o hay error, devuelve 'unknown'.
    """
    if not isinstance(texto, str):
        return "unknown"
    texto = texto.strip()
    if len(texto) < 3:
        return "unknown"
    try:
        return detect(texto)
    except LangDetectException:
        return "unknown"
    except Exception:
        # Cualquier otro error lo tratamos igual
        return "unknown"


def aplicar_filtros_de_calidad(df):
    """
    Aplica filtros mínimos de calidad al DataFrame:
    - Filtra solo filas con estado de descarga exitoso.
    - Elimina filas con texto NaN o vacío.
    - Limpia el texto y lo guarda en 'texto_clean'.
    - Filtra por longitud mínima en caracteres y palabras.
    - (Opcional) Filtra por idioma.
    """
    # 1. Filtrar solo tweets descargados con éxito
    antes = len(df)
    df = df[df[STATUS_COL] == "EXITO"].copy()
    print(f"Filtrado por estado EXITO: {len(df)} filas (descartadas {antes - len(df)})")

    # 2. Eliminar filas con texto NaN
    df = df.dropna(subset=[TEXT_COL])
    df = df.reset_index(drop=True)
    print(f"Tras eliminar NaN en '{TEXT_COL}': {len(df)} filas")

    # 3. Limpiar texto para embeddings
    print("Limpiando texto para embeddings (columna 'texto_clean')...")
    df["texto_clean"] = df[TEXT_COL].apply(limpiar_texto_para_embeddings)

    # 4. Eliminar textos vacíos tras la limpieza
    antes = len(df)
    df = df[df["texto_clean"].str.strip() != ""].copy()
    print(f"Tras eliminar textos vacíos: {len(df)} filas (descartadas {antes - len(df)})")

    # 5. Añadir métricas de longitud
    df["n_chars"] = df["texto_clean"].str.len()
    df["n_words"] = df["texto_clean"].str.split().apply(len)

    # 6. Filtrar por longitud mínima
    antes = len(df)
    df = df[
        (df["n_chars"] >= MIN_CHAR_LEN) &
        (df["n_words"] >= MIN_WORDS)
    ].copy()
    print(f"Tras filtro de longitud: {len(df)} filas (descartadas {antes - len(df)})")

    # 7. Filtro de idioma (opcional)
    if USAR_FILTRO_IDIOMA:
        print("Detectando idioma y filtrando solo tweets en español...")
        df["lang"] = df["texto_clean"].apply(detectar_idioma_seguro)
        antes = len(df)
        df = df[df["lang"] == IDIOMA_OBJETIVO].copy()
        df = df.reset_index(drop=True)
        print(f"Tweets en '{IDIOMA_OBJETIVO}': {len(df)} (descartadas {antes - len(df)})")
    else:
        # Si no usamos filtro de idioma, ponemos 'lang' como 'unknown'
        df["lang"] = "unknown"

    return df


def seleccionar_columnas_salida(df):
    """
    Selecciona las columnas que queremos conservar en el CSV final
    para mantener trazabilidad + texto listo para embeddings.
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
    # 1. Cargar datos crudos
    df = cargar_datos()

    # 2. Aplicar filtros de calidad y generar 'texto_clean'
    df = aplicar_filtros_de_calidad(df)

    # 3. Seleccionar columnas útiles para embeddings
    df_salida = seleccionar_columnas_salida(df)

    # 4. Guardar resultado
    print(f"Guardando corpus preprocesado para embeddings en: {OUTPUT_FILE}")
    df_salida.to_csv(
        OUTPUT_FILE,
        sep=";",
        encoding="utf-8",
        index=False
    )
    print("¡Listo! Corpus de tweets optimizado para embeddings guardado.")


if __name__ == "__main__":
    main()
