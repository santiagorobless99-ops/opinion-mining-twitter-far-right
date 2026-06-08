"""
Reply extractor using Firefox (anti-detection mode).

Reads an existing scraped tweets CSV and fetches the replies
for each tweet by navigating to its thread page.
I use Firefox here because its webdriver is slightly harder to detect than Chrome's.

Usage:
    python extraer_respuestas_firefox.py
"""

import csv
import time
import random
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager


# === CONFIG ===

class Config:
    ARCHIVO_ENTRADA = "tweets_scrapping_crudo.csv"
    ARCHIVO_SALIDA = "tweets_con_respuestas.csv"
    MAX_RESPUESTAS_POR_TWEET = 20
    PAUSA_ENTRE_TWEETS = 3  # seconds


# === FUNCTIONS ===

def iniciar_firefox():
    """Launches Firefox with anti-detection settings."""
    print("\nStarting Firefox (anti-detection mode)...")

    options = Options()

    # Disable webdriver detection signals
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0")
    options.set_preference("privacy.trackingprotection.enabled", False)
    options.set_preference("network.http.referer.XOriginPolicy", 0)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("geo.enabled", False)

    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1280, 800)

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def esperar_login(driver):
    """Waits for manual login."""
    print("\n" + "="*60)
    print("MANUAL LOGIN REQUIRED")
    print("="*60)

    driver.get("https://twitter.com/login")

    print("""
    1. Log in to X in the Firefox window
    2. Once you're on the feed, come back here
    """)

    input("   >>> Press ENTER when login is complete... <<<")
    print("Continuing...")
    return True


def cargar_tweets_existentes():
    """Loads the tweets CSV."""
    print(f"\nLoading {Config.ARCHIVO_ENTRADA}...")
    df = pd.read_csv(Config.ARCHIVO_ENTRADA, sep=";")
    print(f"   -> {len(df)} tweets loaded")
    return df


def extraer_respuestas_tweet(driver, tweet_id, autor_original, query_original):
    """
    Navigates to a tweet's thread page and extracts replies.
    I skip the first element (the original tweet) and collect the rest.
    """
    respuestas = []
    fecha_descarga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        url = f"https://twitter.com/{autor_original}/status/{tweet_id}"
        driver.get(url)
        time.sleep(2)

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

        ids_vistos = {tweet_id}

        for i, tweet_el in enumerate(tweet_elements):
            if len(respuestas) >= Config.MAX_RESPUESTAS_POR_TWEET:
                break

            try:
                reply_data = extraer_datos_respuesta(tweet_el, query_original, tweet_id, fecha_descarga)
                if reply_data and reply_data["comment_id"] not in ids_vistos:
                    ids_vistos.add(reply_data["comment_id"])
                    respuestas.append(reply_data)
            except Exception:
                continue

    except Exception as e:
        print(f"      Error: {e}")

    return respuestas


def extraer_datos_respuesta(tweet_element, query_original, parent_id, fecha_descarga):
    """Parses a reply DOM element into a flat dict."""
    try:
        try:
            texto_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            texto = texto_el.text.replace('\n', ' ').replace('\r', ' ')
        except NoSuchElementException:
            return None

        try:
            autor_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
            autor = autor_el.get_attribute("href").split("/")[-1]
        except NoSuchElementException:
            autor = "unknown"

        try:
            link_el = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            href = link_el.get_attribute("href")
            reply_id = href.split("/status/")[-1].split("?")[0].split("/")[0]
        except NoSuchElementException:
            reply_id = str(hash(texto))[:15]

        if reply_id == parent_id:
            return None

        try:
            likes_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="like"] span')
            likes_text = likes_el.text.strip()
            if likes_text:
                likes = int(likes_text.replace(",", "").replace(".", "").replace("K", "000").replace("M", "000000"))
            else:
                likes = 0
        except (NoSuchElementException, ValueError):
            likes = 0

        try:
            time_el = tweet_element.find_element(By.TAG_NAME, 'time')
            fecha = time_el.get_attribute("datetime")
        except NoSuchElementException:
            fecha = ""

        return {
            "plataforma": "twitter",
            "video_id": query_original,
            "comment_id": reply_id,
            "parent_id": parent_id,
            "is_reply": 1,
            "autor": autor,
            "texto": texto,
            "likes": likes,
            "fecha": fecha,
            "fecha_descarga": fecha_descarga,
            "estado_video": "EXITO",
        }

    except Exception:
        return None


def guardar_csv(tweets, archivo):
    """Saves to semicolon-delimited CSV."""
    campos = [
        "plataforma", "video_id", "comment_id", "parent_id", "is_reply",
        "autor", "texto", "likes", "fecha", "fecha_descarga", "estado_video",
    ]

    with open(archivo, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        escritor.writeheader()
        escritor.writerows(tweets)


def main():
    print("\n" + "="*60)
    print("REPLY EXTRACTOR (FIREFOX)")
    print("="*60)

    df = cargar_tweets_existentes()
    driver = iniciar_firefox()

    try:
        esperar_login(driver)

        todos_los_tweets = df.to_dict('records')
        total_respuestas = 0

        print(f"\nFetching replies for {len(df)} tweets...")

        for i, row in enumerate(df.itertuples()):
            tweet_id = str(row.comment_id)
            autor = str(row.autor) if hasattr(row, 'autor') else "unknown"
            query = str(row.video_id) if hasattr(row, 'video_id') else ""

            print(f"\n[{i+1}/{len(df)}] Tweet {tweet_id}...")

            respuestas = extraer_respuestas_tweet(driver, tweet_id, autor, query)

            if respuestas:
                print(f"   -> {len(respuestas)} replies")
                todos_los_tweets.extend(respuestas)
                total_respuestas += len(respuestas)
            else:
                print(f"   -> No replies")

            time.sleep(Config.PAUSA_ENTRE_TWEETS + random.uniform(0, 2))

        guardar_csv(todos_los_tweets, Config.ARCHIVO_SALIDA)

        print("\n" + "="*60)
        print(f"Done. Original: {len(df)} | New replies: {total_respuestas} | Total: {len(todos_los_tweets)}")
        print(f"Saved to: {Config.ARCHIVO_SALIDA}")
        print("="*60)

    finally:
        print("\nClosing browser...")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
