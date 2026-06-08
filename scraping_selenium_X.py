"""
Selenium-based Twitter/X scraper.

I use this as a fallback when the API doesn't cover the time window I need
(e.g., tweets older than the 7-day free tier limit). Requires manual login.

Usage:
    python scraping_selenium_X.py
"""

import csv
import time
import random
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# === CONFIG ===

class Config:
    # Accounts I'm targeting
    USERNAMES = [
        "RobertoVaquero_",  # Roberto Vaquero
        "wallstwolverine",  # Wall Street Wolverine
        "juanrallo",        # Juan Ramón Rallo
        "navedelmisterio",  # Iker Jiménez
    ]

    # Keywords the tweets must contain
    KEYWORDS = [
        "Universidad",
        "Universidad pública",
        "Universidad privada",
    ]

    MAX_SCROLLS = 10           # scrolls per search query
    SCROLL_PAUSE = 2           # seconds between scrolls
    DELAY_ENTRE_BUSQUEDAS = 5  # seconds between search queries

    ARCHIVO_SALIDA = "tweets_scrapping_crudo.csv"

    TIEMPO_LOGIN = 300  # max seconds I'll wait for manual login


# === FUNCTIONS ===

def iniciar_navegador():
    """Launches Chrome with basic options."""
    print("\nStarting browser...")

    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--lang=es-ES")
    chrome_options.add_argument("--window-size=1280,800")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def esperar_login(driver):
    """Opens X login page and waits for manual login."""
    print("\n" + "="*60)
    print("MANUAL LOGIN REQUIRED")
    print("="*60)

    driver.get("https://twitter.com/login")

    print("""
    1. Log in to X in the browser window
    2. Complete any verification it asks for
    3. Once you're on the X feed, come back here
    """)

    input("   >>> Press ENTER when login is complete... <<<")

    time.sleep(2)
    try:
        driver.find_element(By.CSS_SELECTOR, '[data-testid="primaryColumn"]')
        print("Login verified.")
        return True
    except NoSuchElementException:
        print("Could not verify login, but continuing anyway...")
        return True


def buscar_tweets(driver, username, keyword):
    """Searches tweets from a user containing a keyword, then fetches replies."""
    tweets_encontrados = []
    tweet_urls = []

    query = f"from:{username} {keyword}"
    url = f"https://twitter.com/search?q={query.replace(' ', '%20')}&src=typed_query&f=live"

    print(f"\nSearching: {query}")
    driver.get(url)
    time.sleep(3)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
        )
    except TimeoutException:
        print("   -> No tweets found")
        return tweets_encontrados

    tweets_ids_vistos = set()

    for scroll_num in range(Config.MAX_SCROLLS):
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

        for tweet_el in tweet_elements:
            tweet_data = extraer_datos_tweet(tweet_el, username, keyword)
            if tweet_data and tweet_data["comment_id"] not in tweets_ids_vistos:
                tweets_ids_vistos.add(tweet_data["comment_id"])
                tweets_encontrados.append(tweet_data)

                try:
                    link_el = tweet_el.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                    tweet_url = link_el.get_attribute("href")
                    if "/status/" in tweet_url and tweet_url not in tweet_urls:
                        tweet_urls.append(tweet_url)
                except NoSuchElementException:
                    pass

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(Config.SCROLL_PAUSE + random.uniform(0.5, 1.5))

    print(f"   -> {len(tweets_encontrados)} original tweets")

    # Now fetch replies — I cap at 10 tweets to keep runtime reasonable
    if tweet_urls:
        print(f"   -> Fetching replies for {min(len(tweet_urls), 10)} tweets...")
        for tweet_url in tweet_urls[:10]:
            replies = extraer_respuestas(driver, tweet_url, username, keyword)
            for reply in replies:
                if reply["comment_id"] not in tweets_ids_vistos:
                    tweets_ids_vistos.add(reply["comment_id"])
                    tweets_encontrados.append(reply)
            time.sleep(1)

        print(f"   -> Total with replies: {len(tweets_encontrados)}")

    return tweets_encontrados


def extraer_respuestas(driver, tweet_url, username, keyword):
    """Extracts replies from a tweet's thread page."""
    respuestas = []

    try:
        driver.get(tweet_url)
        time.sleep(2)

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        # First element is the original tweet, rest are replies
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

        for i, tweet_el in enumerate(tweet_elements):
            if i == 0:
                continue
            reply_data = extraer_datos_tweet(tweet_el, username, keyword, is_reply=True)
            if reply_data:
                respuestas.append(reply_data)

    except Exception:
        pass

    return respuestas


def extraer_datos_tweet(tweet_element, username, keyword, is_reply=False):
    """Parses a tweet DOM element into a flat dict."""
    try:
        fecha_descarga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            texto_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            texto = texto_el.text.replace('\n', ' ').replace('\r', ' ')
        except NoSuchElementException:
            texto = ""

        try:
            autor_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
            autor = autor_el.get_attribute("href").split("/")[-1]
        except NoSuchElementException:
            autor = username

        try:
            link_el = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            href = link_el.get_attribute("href")
            tweet_id = href.split("/status/")[-1].split("?")[0].split("/")[0]
        except NoSuchElementException:
            tweet_id = str(hash(texto))[:15]

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
            "video_id": f"{username}:{keyword}",
            "comment_id": tweet_id,
            "parent_id": "",
            "is_reply": 1 if is_reply else 0,
            "autor": autor,
            "texto": texto,
            "likes": likes,
            "fecha": fecha,
            "fecha_descarga": fecha_descarga,
            "estado_video": "EXITO",
        }

    except Exception as e:
        print(f"      Error parsing tweet: {e}")
        return None


def guardar_csv(tweets, archivo):
    """Saves tweets to a semicolon-delimited CSV."""
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
    print("SELENIUM TWITTER SCRAPER")
    print("="*60)

    driver = iniciar_navegador()

    try:
        esperar_login(driver)

        todos_los_tweets = []
        total_busquedas = len(Config.USERNAMES) * len(Config.KEYWORDS)
        busqueda_actual = 0

        for username in Config.USERNAMES:
            for keyword in Config.KEYWORDS:
                busqueda_actual += 1
                print(f"\n[{busqueda_actual}/{total_busquedas}] ", end="")

                tweets = buscar_tweets(driver, username, keyword)
                todos_los_tweets.extend(tweets)

                if busqueda_actual < total_busquedas:
                    delay = Config.DELAY_ENTRE_BUSQUEDAS + random.uniform(1, 3)
                    print(f"   Waiting {delay:.1f}s...")
                    time.sleep(delay)

        # Deduplicate
        tweets_unicos = {}
        for tweet in todos_los_tweets:
            tweet_id = tweet.get("comment_id", "")
            if tweet_id and tweet_id not in tweets_unicos:
                tweets_unicos[tweet_id] = tweet

        todos_los_tweets = list(tweets_unicos.values())

        guardar_csv(todos_los_tweets, Config.ARCHIVO_SALIDA)

        print("\n" + "="*60)
        print(f"Done. {len(todos_los_tweets)} unique tweets saved to {Config.ARCHIVO_SALIDA}")
        print("="*60)

    finally:
        print("\nClosing browser...")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
