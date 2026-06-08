"""
=============================================================================
PIPELINE COMPLETO DE OPINION MINING PARA TWEETS DE X (TWITTER)
=============================================================================

Este script unificado permite:
1. Descargar tweets de X (requiere API)
2. Preprocesar el texto para análisis
3. Calcular coocurrencias de palabras clave
4. Generar embeddings con sentence-transformers

Uso:
    python pipeline_tweets_X.py --help
    python pipeline_tweets_X.py --paso scrapping
    python pipeline_tweets_X.py --paso preprocesar
    python pipeline_tweets_X.py --paso coocurrencias
    python pipeline_tweets_X.py --paso embeddings
    python pipeline_tweets_X.py --paso todo

=============================================================================
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ==================== DEPENDENCIAS OPCIONALES ====================
# Se importan según el paso que se ejecute

def importar_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError:
        print("ERROR: Necesitas instalar pandas. Ejecuta: pip install pandas")
        sys.exit(1)

def importar_tweepy():
    try:
        import tweepy
        return tweepy
    except ImportError:
        print("ERROR: Necesitas instalar tweepy. Ejecuta: pip install tweepy")
        sys.exit(1)

def importar_langdetect():
    try:
        from langdetect import detect, LangDetectException
        return detect, LangDetectException
    except ImportError:
        print("ERROR: Necesitas instalar langdetect. Ejecuta: pip install langdetect")
        sys.exit(1)

def importar_spacy():
    try:
        import spacy
        return spacy
    except ImportError:
        print("ERROR: Necesitas instalar spacy. Ejecuta: pip install spacy")
        print("       Luego instala el modelo: python -m spacy download es_core_news_sm")
        sys.exit(1)

def importar_sentence_transformers():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer
    except ImportError:
        print("ERROR: Necesitas instalar sentence-transformers.")
        print("       Ejecuta: pip install sentence-transformers")
        sys.exit(1)

def importar_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        print("ERROR: Necesitas instalar numpy. Ejecuta: pip install numpy")
        sys.exit(1)


# ==================== CONFIGURACIÓN GLOBAL ====================

class Config:
    """Configuración centralizada del pipeline."""

    # === CREDENCIALES API DE X ===
    # Crea un archivo .env en esta carpeta con el contenido:
    #   X_BEARER_TOKEN=tu_token_aqui
    # Obtén tu Bearer Token en: https://developer.twitter.com/
    BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
    
    # === FUENTES DE DATOS ===
    # Lista de usuarios de los que descargar tweets
    USERNAMES = [
        "RobertoVaquero_",  # Roberto Vaquero
        "wallstwolverine",  # Wall Street Wolverine
        "juanrallo",        # Juan Ramón Rallo
        "navedelmisterio",  # Iker Jiménez
    ]
    
    # Palabras clave que deben contener los tweets
    KEYWORDS_FILTRO = [
        "Universidad",
        "Universidad pública",
        "Universidad privada",
    ]
    
    # Términos de búsqueda adicionales (búsqueda general, sin filtrar por usuario)
    SEARCH_QUERIES = [
        # Desactivado - solo buscamos en los usuarios específicos
    ]
    
    # === ARCHIVOS ===
    ARCHIVO_SCRAPPING = "tweets_final.csv"
    ARCHIVO_PREPROCESADO_COOC = "tweets_limpios_coocurrencias.csv"
    ARCHIVO_PREPROCESADO_EMB = "tweets_para_embeddings.csv"
    ARCHIVO_COOCURRENCIAS = "coocurrencias_tweets.csv"
    ARCHIVO_EMBEDDINGS = "embeddings_tweets.npy"
    ARCHIVO_INDEX_EMB = "tweets_index_embeddings.csv"
    
    # === PARÁMETROS DE SCRAPPING ===
    MAX_TWEETS_POR_QUERY = 100
    
    # === PARÁMETROS DE PREPROCESAMIENTO ===
    MIN_CHAR_LEN = 10
    MIN_WORDS = 2
    IDIOMA_OBJETIVO = "es"
    USAR_FILTRO_IDIOMA = True
    
    # === PALABRAS CLAVE PARA COOCURRENCIAS ===
    KEYWORDS = [
        "universidad",
        "carrera",
        "estudiar",
        "trabajo",
        "trabajar",
        "público",
        "privado",
        "plan",
    ]
    TOP_N_COOC = 20
    
    # === MODELO DE EMBEDDINGS ===
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


# ==================== PASO 1: SCRAPPING ====================

def ejecutar_scrapping():
    """Descarga tweets de X usando la API."""
    tweepy = importar_tweepy()
    
    print("\n" + "="*60)
    print("PASO 1: SCRAPPING DE TWEETS")
    print("="*60)
    
    if Config.BEARER_TOKEN == "TU_BEARER_TOKEN_AQUI":
        print("\n⚠️  ERROR: Debes configurar tu BEARER_TOKEN en la clase Config.")
        print("   Obtén uno en: https://developer.twitter.com/")
        return False
    
    if not Config.USERNAMES and not Config.SEARCH_QUERIES:
        print("\n⚠️  ERROR: Debes añadir usuarios o términos de búsqueda en Config.")
        return False
    
    fecha_descarga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cliente = tweepy.Client(bearer_token=Config.BEARER_TOKEN, wait_on_rate_limit=True)
    todos_los_tweets = []
    
    # Descargar tweets de usuarios que contengan las palabras clave
    if Config.USERNAMES and Config.KEYWORDS_FILTRO:
        for username in Config.USERNAMES:
            for keyword in Config.KEYWORDS_FILTRO:
                print(f"\n📥 Buscando tweets de @{username} con '{keyword}'...")
                tweets, estado = _descargar_tweets_usuario_keyword(cliente, username, keyword, fecha_descarga, tweepy)
                print(f"   → {len(tweets)} tweets + respuestas. Estado: {estado}")
                
                if tweets:
                    todos_los_tweets.extend(tweets)
    
    # Descargar por búsqueda general (si hay queries adicionales)
    for query in Config.SEARCH_QUERIES:
        print(f"\n🔍 Buscando '{query}'...")
        tweets, estado = _descargar_tweets_busqueda(cliente, query, fecha_descarga, tweepy)
        print(f"   → {len(tweets)} tweets. Estado: {estado}")
        
        if not tweets and estado != "EXITO":
            todos_los_tweets.append(_crear_fila_error("search", query, estado, fecha_descarga))
        else:
            todos_los_tweets.extend(tweets)
    
    # Eliminar duplicados por tweet_id
    tweets_unicos = {}
    for tweet in todos_los_tweets:
        tweet_id = tweet.get("comment_id", "")
        if tweet_id and tweet_id not in tweets_unicos:
            tweets_unicos[tweet_id] = tweet
        elif not tweet_id:
            tweets_unicos[id(tweet)] = tweet
    
    todos_los_tweets = list(tweets_unicos.values())
    
    # Guardar
    _guardar_csv_scrapping(todos_los_tweets, Config.ARCHIVO_SCRAPPING)
    print(f"\n✅ Guardado: {Config.ARCHIVO_SCRAPPING} ({len(todos_los_tweets)} tweets únicos)")
    return True


def _descargar_tweets_usuario_keyword(cliente, username, keyword, fecha_descarga, tweepy):
    """Descarga tweets de un usuario que contengan una palabra clave + respuestas."""
    tweets = []
    estado = "EXITO"
    
    try:
        # Buscar tweets del usuario que contengan la keyword
        query = f"from:{username} {keyword} -is:retweet"
        
        respuesta = cliente.search_recent_tweets(
            query=query,
            max_results=Config.MAX_TWEETS_POR_QUERY,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        
        if respuesta.data is None:
            return tweets, "SIN_RESULTADOS"
        
        users_map = {}
        if respuesta.includes and "users" in respuesta.includes:
            for user in respuesta.includes["users"]:
                users_map[user.id] = user.username
        
        conversation_ids = set()
        
        # Añadir tweets originales
        for tweet in respuesta.data:
            autor = users_map.get(tweet.author_id, username)
            tweets.append(_crear_fila_tweet(tweet, "user", f"{username}:{keyword}", autor, fecha_descarga, estado))
            
            if tweet.conversation_id:
                conversation_ids.add(tweet.conversation_id)
        
        # Buscar respuestas a cada tweet
        total_replies = 0
        for conv_id in conversation_ids:
            replies = _descargar_replies(cliente, conv_id, f"{username}:{keyword}", fecha_descarga, tweepy)
            tweets.extend(replies)
            total_replies += len(replies)
        
        if total_replies > 0:
            print(f"      + {total_replies} respuestas")
    
    except tweepy.errors.TweepyException as e:
        estado = f"ERROR_API_{type(e).__name__}"
    except Exception as e:
        estado = "ERROR_OTRO"
    
    return tweets, estado


def _descargar_tweets_usuario(cliente, username, fecha_descarga, tweepy):
    """Descarga tweets de un usuario."""
    tweets = []
    estado = "EXITO"
    
    try:
        user = cliente.get_user(username=username)
        if user.data is None:
            return tweets, "ERROR_USUARIO_NO_ENCONTRADO"
        
        respuesta = cliente.get_users_tweets(
            id=user.data.id,
            max_results=Config.MAX_TWEETS_POR_QUERY,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
        )
        
        if respuesta.data is None:
            return tweets, "SIN_TWEETS"
        
        for tweet in respuesta.data:
            tweets.append(_crear_fila_tweet(tweet, "user", username, username, fecha_descarga, estado))
    
    except tweepy.errors.TweepyException as e:
        estado = f"ERROR_API_{type(e).__name__}"
    except Exception as e:
        estado = "ERROR_OTRO"
    
    return tweets, estado


def _descargar_tweets_busqueda(cliente, query, fecha_descarga, tweepy):
    """Descarga tweets por búsqueda Y sus respuestas."""
    tweets = []
    estado = "EXITO"
    
    try:
        # Buscar tweets que coincidan con la query
        respuesta = cliente.search_recent_tweets(
            query=f"{query} -is:retweet",  # Excluir retweets
            max_results=Config.MAX_TWEETS_POR_QUERY,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        
        if respuesta.data is None:
            return tweets, "SIN_RESULTADOS"
        
        users_map = {}
        if respuesta.includes and "users" in respuesta.includes:
            for user in respuesta.includes["users"]:
                users_map[user.id] = user.username
        
        conversation_ids = set()
        
        # Primero añadimos los tweets originales
        for tweet in respuesta.data:
            autor = users_map.get(tweet.author_id, str(tweet.author_id))
            tweets.append(_crear_fila_tweet(tweet, "search", query, autor, fecha_descarga, estado))
            
            # Guardamos el conversation_id para buscar respuestas
            if tweet.conversation_id:
                conversation_ids.add(tweet.conversation_id)
        
        print(f"   → {len(tweets)} tweets originales encontrados")
        
        # Ahora buscamos las respuestas a cada conversación
        total_replies = 0
        for conv_id in conversation_ids:
            replies = _descargar_replies(cliente, conv_id, query, fecha_descarga, tweepy)
            tweets.extend(replies)
            total_replies += len(replies)
        
        if total_replies > 0:
            print(f"   → {total_replies} respuestas encontradas")
    
    except tweepy.errors.TweepyException as e:
        estado = f"ERROR_API_{type(e).__name__}"
    except Exception as e:
        estado = "ERROR_OTRO"
    
    return tweets, estado


def _descargar_replies(cliente, conversation_id, query_original, fecha_descarga, tweepy):
    """Descarga las respuestas a un tweet usando su conversation_id."""
    replies = []
    
    try:
        # Buscar respuestas en la conversación
        respuesta = cliente.search_recent_tweets(
            query=f"conversation_id:{conversation_id} is:reply",
            max_results=100,
            tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id", "in_reply_to_user_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        
        if respuesta.data is None:
            return replies
        
        users_map = {}
        if respuesta.includes and "users" in respuesta.includes:
            for user in respuesta.includes["users"]:
                users_map[user.id] = user.username
        
        for tweet in respuesta.data:
            autor = users_map.get(tweet.author_id, str(tweet.author_id))
            replies.append(_crear_fila_tweet(tweet, "reply", query_original, autor, fecha_descarga, "EXITO"))
    
    except Exception:
        pass  # Ignoramos errores en replies individuales
    
    return replies


def _crear_fila_tweet(tweet, source_type, source_query, autor, fecha_descarga, estado):
    """Crea un diccionario con los datos del tweet (formato compatible con YouTube)."""
    metrics = tweet.public_metrics or {}
    return {
        "plataforma": "twitter",  # Para identificar fuente al combinar con YouTube
        "video_id": source_query,  # Equivale a video_id en YouTube
        "comment_id": str(tweet.id),  # Equivale a comment_id
        "parent_id": str(tweet.conversation_id) if tweet.conversation_id else "",  # Equivale a parent_id
        "is_reply": 1 if tweet.in_reply_to_user_id else 0,
        "autor": autor,
        "texto": tweet.text.replace('\n', ' ').replace('\r', ' '),
        "likes": metrics.get("like_count", 0),
        "fecha": tweet.created_at.isoformat() if tweet.created_at else "",
        "fecha_descarga": fecha_descarga,
        "estado_video": estado,  # Equivale a estado_video
    }


def _crear_fila_error(source_type, source_query, estado, fecha_descarga):
    """Crea una fila de error (formato compatible con YouTube)."""
    return {
        "plataforma": "twitter",
        "video_id": source_query,
        "comment_id": "", "parent_id": "", "is_reply": "",
        "autor": "", "texto": f"NO SE PUDO DESCARGAR - {estado}",
        "likes": 0, "fecha": "",
        "fecha_descarga": fecha_descarga,
        "estado_video": estado,
    }


def _guardar_csv_scrapping(datos, archivo):
    """Guarda los tweets en CSV (formato compatible con YouTube)."""
    campos = [
        "plataforma",
        "video_id",
        "comment_id",
        "parent_id",
        "is_reply",
        "autor",
        "texto",
        "likes",
        "fecha",
        "fecha_descarga",
        "estado_video",
    ]
    
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        escritor.writeheader()
        escritor.writerows(datos)


# ==================== PASO 2: PREPROCESAMIENTO ====================

def ejecutar_preprocesamiento():
    """Preprocesa los tweets para análisis."""
    pd = importar_pandas()
    detect, LangDetectException = importar_langdetect()
    spacy = importar_spacy()
    
    print("\n" + "="*60)
    print("PASO 2: PREPROCESAMIENTO DE TWEETS")
    print("="*60)
    
    # Verificar archivo de entrada
    if not Path(Config.ARCHIVO_SCRAPPING).exists():
        print(f"\n⚠️  ERROR: No existe el archivo {Config.ARCHIVO_SCRAPPING}")
        print("   Ejecuta primero: python pipeline_tweets_X.py --paso scrapping")
        return False
    
    # Cargar datos
    print(f"\n📂 Cargando {Config.ARCHIVO_SCRAPPING}...")
    df = pd.read_csv(Config.ARCHIVO_SCRAPPING, sep=";", engine="python")
    print(f"   → {len(df)} filas cargadas")
    
    # Filtrar solo exitosos
    df = df[df["estado_video"] == "EXITO"].copy()
    df = df.dropna(subset=["texto"]).reset_index(drop=True)
    print(f"   → {len(df)} tweets válidos")
    
    # === PREPROCESAMIENTO PARA COOCURRENCIAS ===
    print("\n🔧 Preprocesando para coocurrencias...")
    df_cooc = df.copy()
    df_cooc["clean"] = df_cooc["texto"].apply(_limpiar_texto_coocurrencias)
    df_cooc["lang"] = df_cooc["clean"].apply(lambda x: _detectar_idioma(x, detect, LangDetectException))
    
    antes = len(df_cooc)
    df_cooc = df_cooc[df_cooc["lang"] == Config.IDIOMA_OBJETIVO].reset_index(drop=True)
    print(f"   → {len(df_cooc)} tweets en español (descartados {antes - len(df_cooc)})")
    
    # Procesar con spaCy
    print("   → Tokenizando con spaCy...")
    df_cooc = _procesar_con_spacy(df_cooc, spacy)
    
    # Guardar
    cols_cooc = ["texto", "clean", "lang", "tokens_str", "lemmas_str", "tokens_no_stop_str"]
    df_cooc[cols_cooc].to_csv(Config.ARCHIVO_PREPROCESADO_COOC, sep=";", index=False, encoding="utf-8")
    print(f"   ✅ Guardado: {Config.ARCHIVO_PREPROCESADO_COOC}")
    
    # === PREPROCESAMIENTO PARA EMBEDDINGS ===
    print("\n🔧 Preprocesando para embeddings...")
    df_emb = df.copy()
    df_emb["texto_clean"] = df_emb["texto"].apply(_limpiar_texto_embeddings)
    df_emb = df_emb[df_emb["texto_clean"].str.strip() != ""].copy()
    
    df_emb["n_chars"] = df_emb["texto_clean"].str.len()
    df_emb["n_words"] = df_emb["texto_clean"].str.split().apply(len)
    df_emb = df_emb[(df_emb["n_chars"] >= Config.MIN_CHAR_LEN) & (df_emb["n_words"] >= Config.MIN_WORDS)].copy()
    
    if Config.USAR_FILTRO_IDIOMA:
        df_emb["lang"] = df_emb["texto_clean"].apply(lambda x: _detectar_idioma(x, detect, LangDetectException))
        df_emb = df_emb[df_emb["lang"] == Config.IDIOMA_OBJETIVO].reset_index(drop=True)
    
    print(f"   → {len(df_emb)} tweets listos para embeddings")
    
    # Guardar
    cols_emb = ["video_id", "comment_id", "parent_id", "is_reply", "autor", "likes", "fecha",
                "texto", "texto_clean", "n_chars", "n_words", "lang"]
    cols_presentes = [c for c in cols_emb if c in df_emb.columns]
    df_emb[cols_presentes].to_csv(Config.ARCHIVO_PREPROCESADO_EMB, sep=";", index=False, encoding="utf-8")
    print(f"   ✅ Guardado: {Config.ARCHIVO_PREPROCESADO_EMB}")
    
    return True


def _limpiar_texto_coocurrencias(text):
    """Limpieza agresiva para coocurrencias."""
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    text = text.replace("\n", " ")
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"\brt\b", "", text)
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _limpiar_texto_embeddings(text):
    """Limpieza ligera para embeddings (conserva emojis/puntuación)."""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"\bRT\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def _detectar_idioma(text, detect, LangDetectException):
    """Detecta el idioma del texto."""
    if not isinstance(text, str) or len(text.strip()) < 3:
        return "unknown"
    try:
        return detect(text)
    except (LangDetectException, Exception):
        return "unknown"


def _procesar_con_spacy(df, spacy):
    """Tokeniza y lematiza con spaCy."""
    nlp = spacy.load("es_core_news_sm")
    
    tokens_list, lemmas_list, tokens_no_stop_list = [], [], []
    
    for doc in nlp.pipe(df["clean"].tolist(), batch_size=50):
        tokens, lemmas, tokens_no_stop = [], [], []
        for token in doc:
            if token.is_space:
                continue
            tokens.append(token.text)
            lemmas.append(token.lemma_)
            if not token.is_stop and token.is_alpha:
                tokens_no_stop.append(token.lemma_.lower())
        
        tokens_list.append(tokens)
        lemmas_list.append(lemmas)
        tokens_no_stop_list.append(tokens_no_stop)
    
    df["tokens_str"] = [" ".join(t) for t in tokens_list]
    df["lemmas_str"] = [" ".join(t) for t in lemmas_list]
    df["tokens_no_stop_str"] = [" ".join(t) for t in tokens_no_stop_list]
    
    return df


# ==================== PASO 3: COOCURRENCIAS ====================

def ejecutar_coocurrencias():
    """Calcula coocurrencias de palabras clave."""
    pd = importar_pandas()
    
    print("\n" + "="*60)
    print("PASO 3: ANÁLISIS DE COOCURRENCIAS")
    print("="*60)
    
    if not Path(Config.ARCHIVO_PREPROCESADO_COOC).exists():
        print(f"\n⚠️  ERROR: No existe {Config.ARCHIVO_PREPROCESADO_COOC}")
        print("   Ejecuta primero: python pipeline_tweets_X.py --paso preprocesar")
        return False
    
    print(f"\n📂 Cargando {Config.ARCHIVO_PREPROCESADO_COOC}...")
    df = pd.read_csv(Config.ARCHIVO_PREPROCESADO_COOC, sep=";")
    df["tokens_no_stop_str"] = df["tokens_no_stop_str"].fillna("")
    print(f"   → {len(df)} tweets cargados")
    
    print("\n🔗 Calculando coocurrencias...")
    cooc_dict = {kw: Counter() for kw in Config.KEYWORDS}
    
    for tokens_str in df["tokens_no_stop_str"]:
        tokens = str(tokens_str).split()
        if not tokens:
            continue
        token_set = set(tokens)
        
        for kw in Config.KEYWORDS:
            if kw in token_set:
                for tok in tokens:
                    if tok != kw:
                        cooc_dict[kw][tok] += 1
    
    # Construir DataFrame
    rows = []
    for kw, counter in cooc_dict.items():
        total = sum(counter.values())
        for tok, freq in counter.most_common():
            rows.append({
                "keyword": kw,
                "token": tok,
                "cooc_freq": freq,
                "cooc_rel": freq / total if total > 0 else 0.0
            })
    
    cooc_df = pd.DataFrame(rows)
    cooc_df = cooc_df.sort_values(by=["keyword", "cooc_freq"], ascending=[True, False])
    cooc_df.to_csv(Config.ARCHIVO_COOCURRENCIAS, sep=";", index=False, encoding="utf-8")
    
    print(f"   ✅ Guardado: {Config.ARCHIVO_COOCURRENCIAS}")
    
    # Mostrar resultados
    print("\n📊 TOP COOCURRENCIAS:")
    for kw in Config.KEYWORDS:
        sub = cooc_df[cooc_df["keyword"] == kw].head(Config.TOP_N_COOC)
        if sub.empty:
            continue
        print(f"\n   '{kw}':")
        for _, row in sub.head(5).iterrows():
            print(f"      {row['token']:<15} freq={row['cooc_freq']:<4} rel={row['cooc_rel']:.3f}")
    
    return True


# ==================== PASO 4: EMBEDDINGS ====================

def ejecutar_embeddings():
    """Genera embeddings con sentence-transformers."""
    pd = importar_pandas()
    np = importar_numpy()
    SentenceTransformer = importar_sentence_transformers()
    
    print("\n" + "="*60)
    print("PASO 4: GENERACIÓN DE EMBEDDINGS")
    print("="*60)
    
    if not Path(Config.ARCHIVO_PREPROCESADO_EMB).exists():
        print(f"\n⚠️  ERROR: No existe {Config.ARCHIVO_PREPROCESADO_EMB}")
        print("   Ejecuta primero: python pipeline_tweets_X.py --paso preprocesar")
        return False
    
    print(f"\n📂 Cargando {Config.ARCHIVO_PREPROCESADO_EMB}...")
    df = pd.read_csv(Config.ARCHIVO_PREPROCESADO_EMB, sep=";", engine="python")
    df = df.dropna(subset=["texto_clean"]).reset_index(drop=True)
    print(f"   → {len(df)} tweets cargados")
    
    print(f"\n🧠 Cargando modelo: {Config.MODEL_NAME}")
    print("   (puede tardar en la primera ejecución)")
    model = SentenceTransformer(Config.MODEL_NAME)
    
    print(f"\n⚡ Generando embeddings para {len(df)} tweets...")
    textos = df["texto_clean"].tolist()
    embeddings = model.encode(
        textos,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    
    print(f"   → Shape: {embeddings.shape}")
    
    # Guardar embeddings
    np.save(Config.ARCHIVO_EMBEDDINGS, embeddings)
    print(f"   ✅ Guardado: {Config.ARCHIVO_EMBEDDINGS}")
    
    # Guardar índice
    df.insert(0, "embedding_idx", range(len(df)))
    df.to_csv(Config.ARCHIVO_INDEX_EMB, sep=";", index=False, encoding="utf-8")
    print(f"   ✅ Guardado: {Config.ARCHIVO_INDEX_EMB}")
    
    return True


# ==================== EJECUCIÓN COMPLETA ====================

def ejecutar_todo():
    """Ejecuta todo el pipeline."""
    print("\n" + "="*60)
    print("PIPELINE COMPLETO DE OPINION MINING")
    print("="*60)
    
    pasos = [
        ("Scrapping", ejecutar_scrapping),
        ("Preprocesamiento", ejecutar_preprocesamiento),
        ("Coocurrencias", ejecutar_coocurrencias),
        ("Embeddings", ejecutar_embeddings),
    ]
    
    for nombre, funcion in pasos:
        if not funcion():
            print(f"\n❌ El pipeline se detuvo en: {nombre}")
            return False
    
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    print("="*60)
    print("\nArchivos generados:")
    print(f"  📄 {Config.ARCHIVO_SCRAPPING}")
    print(f"  📄 {Config.ARCHIVO_PREPROCESADO_COOC}")
    print(f"  📄 {Config.ARCHIVO_PREPROCESADO_EMB}")
    print(f"  📄 {Config.ARCHIVO_COOCURRENCIAS}")
    print(f"  📄 {Config.ARCHIVO_EMBEDDINGS}")
    print(f"  📄 {Config.ARCHIVO_INDEX_EMB}")
    
    return True


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de Opinion Mining para tweets de X",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python pipeline_tweets_X.py --paso scrapping     # Descargar tweets
  python pipeline_tweets_X.py --paso preprocesar   # Limpiar texto
  python pipeline_tweets_X.py --paso coocurrencias # Analizar coocurrencias
  python pipeline_tweets_X.py --paso embeddings    # Generar embeddings
  python pipeline_tweets_X.py --paso todo          # Ejecutar todo
        """
    )
    
    parser.add_argument(
        "--paso", "-p",
        choices=["scrapping", "preprocesar", "coocurrencias", "embeddings", "todo"],
        required=True,
        help="Paso del pipeline a ejecutar"
    )
    
    args = parser.parse_args()
    
    pasos = {
        "scrapping": ejecutar_scrapping,
        "preprocesar": ejecutar_preprocesamiento,
        "coocurrencias": ejecutar_coocurrencias,
        "embeddings": ejecutar_embeddings,
        "todo": ejecutar_todo,
    }
    
    exito = pasos[args.paso]()
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()
