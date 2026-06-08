"""
Análisis de coocurrencias para tweets de X.

Este script calcula qué palabras aparecen juntas con frecuencia
en los tweets preprocesados, útil para crear redes semánticas.
"""

import pandas as pd
from collections import Counter

# ============================================
# CONFIGURACIÓN DEL SCRIPT
# ============================================

# Nombre del archivo de entrada: tu CSV ya preprocesado
INPUT_FILE = "tweets_limpios_coocurrencias.csv"

# Separador que usamos (ya lo fijamos a ';' en los otros scripts)
SEP = ";"

# Columna que contiene los lemas sin stopwords en forma de cadena
# Ejemplo de valor: "universidad público trabajo plan b"
TOKENS_COLUMN = "tokens_no_stop_str"

# Archivo de salida donde guardaremos las co-ocurrencias
OUTPUT_FILE = "coocurrencias_tweets.csv"

# Lista inicial de palabras clave para las que queremos estudiar co-ocurrencias.
# Puedes modificarla según tus intereses teóricos.
KEYWORDS = [
    "universidad",
    "carrera",
    "estudiar",
    "trabajo",
    "trabajar",
    "público",
    "privado",
    "plan",
    "b"
]

# Número de co-ocurrencias principales que mostraremos por pantalla para cada palabra clave
TOP_N = 20


def cargar_datos():
    """
    Lee el CSV preprocesado y devuelve un DataFrame de pandas.

    - Comprueba que la columna de tokens exista.
    - Rellena valores NaN con cadena vacía para evitar errores al hacer split.
    """
    print(f"Leyendo archivo: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, sep=SEP)

    # Comprobamos que la columna de tokens exista en el DataFrame
    if TOKENS_COLUMN not in df.columns:
        raise ValueError(
            f"La columna '{TOKENS_COLUMN}' no existe en el CSV. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Rellenamos posibles valores NaN con "" para poder aplicar .split() sin errores
    df[TOKENS_COLUMN] = df[TOKENS_COLUMN].fillna("")

    print(f"Filas cargadas: {len(df)}")
    return df


def construir_coocurrencias(df, keywords):
    """
    Construye las co-ocurrencias para cada palabra clave.

    Lógica:
    - Recorremos cada tweet.
    - Convertimos la cadena de lemas en una lista de tokens.
    - Para cada palabra clave:
        - Si está en el tweet, contamos co-ocurrencias con todos
          los demás tokens del mismo tweet (excluyendo la palabra clave).
    - Devolvemos un DataFrame con columnas:
        'keyword', 'token', 'cooc_freq', 'cooc_rel'
    """

    # Diccionario que mapeará cada palabra clave a un Counter:
    #   keyword -> Counter({token: frecuencia_de_coocurrencia})
    cooc_dict = {kw: Counter() for kw in keywords}

    print("Calculando co-ocurrencias...")

    # Recorremos cada fila del DataFrame
    for idx, tokens_str in enumerate(df[TOKENS_COLUMN]):
        # Convertimos la cadena "pal1 pal2 pal3" en una lista ["pal1", "pal2", "pal3"]
        tokens = str(tokens_str).split()

        # Si el tweet está vacío tras la limpieza, lo saltamos
        if not tokens:
            continue

        # Usamos un conjunto (set) para comprobar presencia/ausencia de cada keyword
        # de forma eficiente (O(1) en promedio).
        token_set = set(tokens)

        # Para cada palabra clave, vemos si aparece en este tweet
        for kw in keywords:
            if kw in token_set:
                # Si la palabra clave está en el tweet,
                # contamos co-ocurrencias con todos los demás tokens del tweet.
                for tok in tokens:
                    # Podemos excluir la propia palabra clave para no contar
                    # "universidad" co-ocurriendo con "universidad" en sí misma.
                    if tok == kw:
                        continue
                    # Sumamos 1 a la co-ocurrencia (kw, tok)
                    cooc_dict[kw][tok] += 1

        # (Opcional) Mostrar progreso cada X filas si el corpus fuera muy grande
        # if (idx + 1) % 1000 == 0:
        #     print(f"Procesadas {idx + 1} filas...")

    print("Co-ocurrencias calculadas. Construyendo DataFrame...")

    # Construimos una lista de diccionarios para transformar luego en DataFrame:
    # cada entrada será una fila con (keyword, token, cooc_freq, cooc_rel)
    rows = []

    for kw, counter in cooc_dict.items():
        # Frecuencia total de co-ocurrencias para esta palabra clave
        total_cooc = sum(counter.values())

        # Recorremos los tokens asociados a esta keyword, ordenados por frecuencia
        for tok, freq in counter.most_common():
            # Calculamos frecuencia relativa respecto al total de co-ocurrencias de la keyword
            rel = freq / total_cooc if total_cooc > 0 else 0.0

            rows.append({
                "keyword": kw,       # palabra clave (ej. "universidad")
                "token": tok,        # palabra que co-ocurre con la keyword
                "cooc_freq": freq,   # frecuencia absoluta de co-ocurrencia
                "cooc_rel": rel      # frecuencia relativa dentro de la keyword
            })

    # Creamos el DataFrame final
    cooc_df = pd.DataFrame(rows)

    # Ordenamos por keyword y luego por frecuencia descendente
    cooc_df = cooc_df.sort_values(
        by=["keyword", "cooc_freq"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return cooc_df


def guardar_resultados(cooc_df):
    """
    Guarda el DataFrame de co-ocurrencias en un CSV.
    """
    print(f"Guardando co-ocurrencias en: {OUTPUT_FILE}")
    cooc_df.to_csv(OUTPUT_FILE, index=False, sep=";", encoding="utf-8")
    print("Archivo de co-ocurrencias guardado correctamente.")


def mostrar_top_por_keyword(cooc_df, keywords, n=TOP_N):
    """
    Muestra por pantalla las n palabras más asociadas a cada keyword.
    """
    for kw in keywords:
        print(f"\n=== Palabra clave: '{kw}' ===")
        # Filtramos las filas de esa keyword
        sub = cooc_df[cooc_df["keyword"] == kw].head(n)
        if sub.empty:
            print("  (sin co-ocurrencias registradas)")
            continue

        for i, row in sub.iterrows():
            token = row["token"]
            freq = row["cooc_freq"]
            rel = row["cooc_rel"]
            print(f"  {token:<20} cooc_freq={freq:<4} cooc_rel={rel:.4f}")


def main():
    # 1) Cargar el DataFrame
    df = cargar_datos()

    # 2) Calcular las co-ocurrencias para las palabras clave
    cooc_df = construir_coocurrencias(df, KEYWORDS)

    # 3) Guardar los resultados en CSV
    guardar_resultados(cooc_df)

    # 4) Mostrar por pantalla las co-ocurrencias principales
    mostrar_top_por_keyword(cooc_df, KEYWORDS, n=TOP_N)


if __name__ == "__main__":
    main()
