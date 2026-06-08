"""
Scrapping de tweets de X (Twitter).

NOTA: Este script requiere credenciales de la API de X (Twitter).
Para obtenerlas, visita: https://developer.twitter.com/

Salida: CSV con tweets y metadatos similares al scrapping de YouTube.
"""

import tweepy
import csv
from datetime import datetime

# === CONFIGURA AQUÍ TUS CREDENCIALES DE LA API DE X ===
# NOTA CIENTÍFICA: En un entorno de producción o publicación,
# estas credenciales deberían cargarse desde variables de entorno (.env) o un archivo seguro.

# Credenciales para OAuth 2.0 (App-Only)
BEARER_TOKEN = "TU_BEARER_TOKEN_AQUI"

# Lista de usuarios de los que queremos obtener tweets
# O bien, términos de búsqueda para buscar tweets
USERNAMES = [
    # Añade aquí los usernames de las cuentas que quieras analizar
    # "usuario1",
    # "usuario2",
]

# Términos de búsqueda (alternativa a buscar por usuario)
SEARCH_QUERIES = [
    # "universidad privada",
    # "universidad pública",
]

# Archivo de salida
OUTPUT_FILE = "tweets_scrapping_crudo.csv"
FECHA_DESCARGA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Número máximo de tweets a descargar por usuario o búsqueda
MAX_TWEETS_POR_QUERY = 100


def crear_cliente():
    """
    Crea el cliente de Tweepy usando Bearer Token (OAuth 2.0 App-Only).
    """
    cliente = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)
    return cliente


def descargar_tweets_usuario(cliente, username: str):
    """
    Descarga tweets de un usuario específico.
    Devuelve una tupla: (lista de diccionarios, estado_descarga).
    """
    tweets = []
    estado_descarga = "EXITO"

    try:
        # Primero obtenemos el ID del usuario
        user = cliente.get_user(username=username)
        if user.data is None:
            estado_descarga = "ERROR_USUARIO_NO_ENCONTRADO"
            return tweets, estado_descarga

        user_id = user.data.id

        # Obtenemos los tweets del usuario
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
    Descarga tweets que coincidan con una búsqueda.
    Devuelve una tupla: (lista de diccionarios, estado_descarga).
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

        # Mapear author_id a username
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
    """
    Guarda la lista de diccionarios en un CSV con separador ';'.
    """
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

    # Creamos el cliente de la API
    cliente = crear_cliente()

    # Descargar tweets por usuario
    for username in USERNAMES:
        print(f"Descargando tweets de @{username}...")
        tweets, estado = descargar_tweets_usuario(cliente, username)
        print(f"  -> {len(tweets)} tweets procesados. Estado: {estado}")

        if estado != "EXITO" and not tweets:
            todos_los_tweets.append({
                "source_type": "user",
                "source_query": username,
                "tweet_id": "", "conversation_id": "", "is_reply": "",
                "autor": "", "texto": f"NO SE PUDO DESCARGAR - {estado}",
                "likes": 0, "retweets": 0, "replies": 0, "fecha": "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado,
            })
        else:
            todos_los_tweets.extend(tweets)

    # Descargar tweets por búsqueda
    for query in SEARCH_QUERIES:
        print(f"Buscando tweets con '{query}'...")
        tweets, estado = descargar_tweets_busqueda(cliente, query)
        print(f"  -> {len(tweets)} tweets procesados. Estado: {estado}")

        if estado != "EXITO" and not tweets:
            todos_los_tweets.append({
                "source_type": "search",
                "source_query": query,
                "tweet_id": "", "conversation_id": "", "is_reply": "",
                "autor": "", "texto": f"NO SE PUDO DESCARGAR - {estado}",
                "likes": 0, "retweets": 0, "replies": 0, "fecha": "",
                "fecha_descarga": FECHA_DESCARGA,
                "estado_descarga": estado,
            })
        else:
            todos_los_tweets.extend(tweets)

    print(f"\n--- Resumen de la Ejecución ---")
    print(f"Total tweets finales: {len(todos_los_tweets)}")
    guardar_csv(todos_los_tweets, OUTPUT_FILE)
    print(f"Guardado en {OUTPUT_FILE}")
