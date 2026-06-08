"""
Scraping tweets from X (Twitter).

Requires X (Twitter) API credentials.
Get them at: https://developer.twitter.com/

Output: CSV with tweets and metadata compatible with the YouTube scraping schema.
"""

import tweepy
import csv
from datetime import datetime

# === API CREDENTIALS ===
# Load X_BEARER_TOKEN from a .env file in this directory.
# Get one at: https://developer.twitter.com/

BEARER_TOKEN = "YOUR_BEARER_TOKEN_HERE"

# Accounts to download tweets from
USERNAMES = [
    # "username1",
    # "username2",
]

# Search queries (alternative to user-based retrieval)
SEARCH_QUERIES = [
    # "universidad privada",
    # "universidad pública",
]

OUTPUT_FILE = "tweets_scrapping_crudo.csv"
FECHA_DESCARGA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Maximum tweets to download per user or search query
MAX_TWEETS_POR_QUERY = 100


def crear_cliente():
    """Creates a Tweepy client using Bearer Token (OAuth 2.0 App-Only)."""
    cliente = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)
    return cliente


def descargar_tweets_usuario(cliente, username: str):
    """
    Downloads tweets from a specific user.
    Returns a tuple: (list of dicts, download_status).
    """
    tweets = []
    estado_descarga = "EXITO"

    try:
        user = cliente.get_user(username=username)
        if user.data is None:
            estado_descarga = "ERROR_USUARIO_NO_ENCONTRADO"
            return tweets, estado_descarga

        user_id = user.data.id

        respuesta = cliente.get_users_tweets(
            id=user_id,
            max_results=MAX_TWEETS_POR_QUERY,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
            expansions=["author_id"],
        )

        if respuesta.data is None:
            estado_descarga = "SIN_TWEETS"
            return tweets, estado_descarga

        for tweet in respuesta.data:
            metrics = tweet.public_metrics or {}
            is_reply = 1 if tweet.in_reply_to_user_id else 0

            tweets.append({
                "source_type": "user",
                "source_query": username,
                "tweet_id": tweet.id,
                "conversation_id": tweet.conversation_id,
                "is_reply": is_reply,
                "autor": username,
                "texto": tweet.text,
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "fecha": tweet.created_at.isoformat() if tweet.created_at else "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado_descarga,
            })

    except tweepy.errors.TweepyException as e:
        estado_descarga = f"ERROR_API_{type(e).__name__}"
        print(f"  -> {estado_descarga}: Error al procesar @{username}. Detalle: {e}")

    except Exception as e:
        estado_descarga = "ERROR_OTRO"
        print(f"  -> {estado_descarga}: Error inesperado en @{username}. Detalle: {e}")

    return tweets, estado_descarga


def descargar_tweets_busqueda(cliente, query: str):
    """
    Downloads tweets matching a search query.
    Returns a tuple: (list of dicts, download_status).
    """
    tweets = []
    estado_descarga = "EXITO"

    try:
        respuesta = cliente.search_recent_tweets(
            query=query,
            max_results=MAX_TWEETS_POR_QUERY,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )

        if respuesta.data is None:
            estado_descarga = "SIN_RESULTADOS"
            return tweets, estado_descarga

        users_map = {}
        if respuesta.includes and "users" in respuesta.includes:
            for user in respuesta.includes["users"]:
                users_map[user.id] = user.username

        for tweet in respuesta.data:
            metrics = tweet.public_metrics or {}
            is_reply = 1 if tweet.in_reply_to_user_id else 0
            autor = users_map.get(tweet.author_id, str(tweet.author_id))

            tweets.append({
                "source_type": "search",
                "source_query": query,
                "tweet_id": tweet.id,
                "conversation_id": tweet.conversation_id,
                "is_reply": is_reply,
                "autor": autor,
                "texto": tweet.text,
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "fecha": tweet.created_at.isoformat() if tweet.created_at else "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado_descarga,
            })

    except tweepy.errors.TweepyException as e:
        estado_descarga = f"ERROR_API_{type(e).__name__}"
        print(f"  -> {estado_descarga}: Error en búsqueda '{query}'. Detalle: {e}")

    except Exception as e:
        estado_descarga = "ERROR_OTRO"
        print(f"  -> {estado_descarga}: Error inesperado en búsqueda '{query}'. Detalle: {e}")

    return tweets, estado_descarga


def guardar_csv(datos, archivo):
    """Saves the list of dicts to a semicolon-delimited CSV."""
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        campos = [
            "source_type",
            "source_query",
            "tweet_id",
            "conversation_id",
            "is_reply",
            "autor",
            "texto",
            "likes",
            "retweets",
            "replies",
            "fecha",
            "fecha_descarga",
            "estado_descarga",
        ]
        escritor = csv.DictWriter(
            f,
            fieldnames=campos,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL
        )
        escritor.writeheader()
        for fila in datos:
            # Asegurarse de que el campo "texto" se maneje correctamente
            fila['texto'] = fila['texto'].replace('\n', ' ').replace('\r', ' ')
            escritor.writerow(fila)


if __name__ == "__main__":
    todos_los_tweets = []

    cliente = crear_cliente()

    # Download by user
    for username in USERNAMES:
        print(f"Downloading tweets from @{username}...")
        tweets, estado = descargar_tweets_usuario(cliente, username)
        print(f"  -> {len(tweets)} tweets processed. Status: {estado}")

        if estado != "EXITO" and not tweets:
            todos_los_tweets.append({
                "source_type": "user",
                "source_query": username,
                "tweet_id": "", "conversation_id": "", "is_reply": "",
                "autor": "", "texto": f"DOWNLOAD FAILED - {estado}",
                "likes": 0, "retweets": 0, "replies": 0, "fecha": "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado,
            })
        else:
            todos_los_tweets.extend(tweets)

    # Download by search query
    for query in SEARCH_QUERIES:
        print(f"Searching tweets: '{query}'...")
        tweets, estado = descargar_tweets_busqueda(cliente, query)
        print(f"  -> {len(tweets)} tweets processed. Status: {estado}")

        if estado != "EXITO" and not tweets:
            todos_los_tweets.append({
                "source_type": "search",
                "source_query": query,
                "tweet_id": "", "conversation_id": "", "is_reply": "",
                "autor": "", "texto": f"DOWNLOAD FAILED - {estado}",
                "likes": 0, "retweets": 0, "replies": 0, "fecha": "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado,
            })
        else:
            todos_los_tweets.extend(tweets)

    print(f"\n--- Execution summary ---")
    print(f"Total tweets: {len(todos_los_tweets)}")
    guardar_csv(todos_los_tweets, OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")
