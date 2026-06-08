"""
Co-occurrence analysis for tweets from X.

Calculates which words appear together with target keywords in preprocessed tweets,
useful for building semantic networks.
"""

import pandas as pd
from collections import Counter

# ============================================
# CONFIG
# ============================================

INPUT_FILE = "tweets_limpios_coocurrencias.csv"
SEP = ";"
TOKENS_COLUMN = "tokens_no_stop_str"  # space-separated lemmas without stopwords
OUTPUT_FILE = "coocurrencias_tweets.csv"

# Theoretically motivated keywords — I'm interested in how these terms
# co-occur with others in discourse about public vs. private university.
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

TOP_N = 20


def cargar_datos():
    """
    Reads the preprocessed CSV and returns a DataFrame.
    Checks that the token column exists and fills NaN so .split() doesn't break.
    """
    print(f"Reading: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, sep=SEP)

    if TOKENS_COLUMN not in df.columns:
        raise ValueError(
            f"Column '{TOKENS_COLUMN}' not found. Available: {list(df.columns)}"
        )

    df[TOKENS_COLUMN] = df[TOKENS_COLUMN].fillna("")

    print(f"Rows loaded: {len(df)}")
    return df


def construir_coocurrencias(df, keywords):
    """
    Builds co-occurrence counts for each keyword.

    Logic: for each tweet, if a keyword appears in it, I count every other
    token in that tweet as a co-occurrence. A set is used for O(1) keyword
    lookups per tweet.

    Returns a DataFrame with columns: keyword, token, cooc_freq, cooc_rel.
    """
    cooc_dict = {kw: Counter() for kw in keywords}

    print("Calculating co-occurrences...")

    for tokens_str in df[TOKENS_COLUMN]:
        tokens = str(tokens_str).split()

        if not tokens:
            continue

        token_set = set(tokens)

        for kw in keywords:
            if kw in token_set:
                for tok in tokens:
                    if tok == kw:
                        continue
                    cooc_dict[kw][tok] += 1

    print("Building DataFrame...")

    rows = []
    for kw, counter in cooc_dict.items():
        total_cooc = sum(counter.values())

        for tok, freq in counter.most_common():
            rel = freq / total_cooc if total_cooc > 0 else 0.0
            rows.append({
                "keyword": kw,
                "token": tok,
                "cooc_freq": freq,
                "cooc_rel": rel
            })

    cooc_df = pd.DataFrame(rows)
    cooc_df = cooc_df.sort_values(
        by=["keyword", "cooc_freq"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return cooc_df


def guardar_resultados(cooc_df):
    """Saves the co-occurrence DataFrame to CSV."""
    print(f"Saving to: {OUTPUT_FILE}")
    cooc_df.to_csv(OUTPUT_FILE, index=False, sep=";", encoding="utf-8")
    print("Saved.")


def mostrar_top_por_keyword(cooc_df, keywords, n=TOP_N):
    """Prints the top n co-occurring tokens per keyword."""
    for kw in keywords:
        print(f"\n=== '{kw}' ===")
        sub = cooc_df[cooc_df["keyword"] == kw].head(n)
        if sub.empty:
            print("  (no co-occurrences)")
            continue

        for i, row in sub.iterrows():
            print(f"  {row['token']:<20} cooc_freq={row['cooc_freq']:<4} cooc_rel={row['cooc_rel']:.4f}")


def main():
    df = cargar_datos()
    cooc_df = construir_coocurrencias(df, KEYWORDS)
    guardar_resultados(cooc_df)
    mostrar_top_por_keyword(cooc_df, KEYWORDS, n=TOP_N)


if __name__ == "__main__":
    main()
