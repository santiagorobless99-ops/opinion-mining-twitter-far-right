"""
Reply extractor using remote Chrome debugging.

Connects to an already-running Chrome session via remote debugging port 9222,
so I don't need to log in again. Saves results incrementally to avoid losing
progress if something breaks mid-run.

To start Chrome with remote debugging:
    chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/chrome-debug"
"""

import csv
import time
import random
import os
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


# === CONFIG ===

ARCHIVO_ENTRADA = "tweets_scrapping_crudo.csv"
ARCHIVO_SALIDA = "tweets_con_respuestas.csv"
MAX_RESPUESTAS = 30
PAUSA = 3  # seconds between tweets


# === FUNCTIONS ===

def conectar_chrome():
    """Connects to an existing Chrome instance on port 9222."""
    print("\nConnecting to existing Chrome session...")

    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    driver = webdriver.Chrome(options=options)
    print("Connected.")
    return driver


def extraer_respuestas(driver, tweet_id, autor, query):
    """
    Navigates to a tweet's thread page and extracts replies.
    I include some debug output because X's DOM can be unpredictable.
    """
    respuestas = []
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        url = f"https://twitter.com/{autor}/status/{tweet_id}"
        driver.get(url)
        time.sleep(2)

        print(f"      [DEBUG] Title: {driver.title}")
        print(f"      [DEBUG] URL: {driver.current_url}")

        # Give the page extra time to render before scrolling
        time.sleep(4)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        print(f"      [DEBUG] 'tweet' elements found: {len(tweets)}")

        if len(tweets) == 0:
            # Extra diagnosis if nothing shows up — helps identify rendering issues
            articles = driver.find_elements(By.TAG_NAME, 'article')
            print(f"      [DEBUG] Generic 'article' elements: {len(articles)}")
            path_check = driver.find_elements(By.XPATH, "//*[contains(text(), 'Reply')]")
            print(f"      [DEBUG] Elements with 'Reply' text: {len(path_check)}")

        ids_vistos = {tweet_id}

        for tweet_el in tweets:
            if len(respuestas) >= MAX_RESPUESTAS:
                break

            try:
                texto_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                texto = texto_el.text.replace('\n', ' ')

                link = tweet_el.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                rid = link.get_attribute("href").split("/status/")[-1].split("?")[0].split("/")[0]

                if rid in ids_vistos or rid == tweet_id:
                    continue
                ids_vistos.add(rid)

                try:
                    a_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
                    r_autor = a_el.get_attribute("href").split("/")[-1]
                except:
                    r_autor = "unknown"

                try:
                    l_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="like"] span')
                    likes = int(l_el.text.replace(",", "").replace("K", "000").replace("M", "000000") or 0)
                except:
                    likes = 0

                respuestas.append({
                    "plataforma": "twitter",
                    "video_id": query,
                    "comment_id": rid,
                    "parent_id": tweet_id,
                    "is_reply": 1,
                    "autor": r_autor,
                    "texto": texto,
                    "likes": likes,
                    "fecha": "",
                    "fecha_descarga": fecha,
                    "estado_video": "EXITO",
                })
            except:
                continue
    except Exception as e:
        print(f"   Error: {e}")

    return respuestas


def cargar_progreso():
    """
    Loads parent IDs already processed from the output file.
    This lets me resume a run without reprocessing everything.
    """
    procesados = set()
    if os.path.exists(ARCHIVO_SALIDA):
        try:
            df_out = pd.read_csv(ARCHIVO_SALIDA, sep=";")
            if "parent_id" in df_out.columns:
                procesados = set(df_out["parent_id"].astype(str).unique())
        except Exception:
            pass
    return procesados


def guardar_incremental(datos, archivo, modo='a'):
    """
    Appends rows to the output CSV.
    I write incrementally so partial results survive interruptions.
    """
    campos = ["plataforma", "video_id", "comment_id", "parent_id", "is_reply",
              "autor", "texto", "likes", "fecha", "fecha_descarga", "estado_video"]

    archivo_existe = os.path.exists(archivo)

    with open(archivo, modo, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        if not archivo_existe or modo == 'w':
            w.writeheader()
        w.writerows(datos)


def main():
    print("\n" + "="*60)
    print("REPLY EXTRACTOR (REMOTE CHROME, INCREMENTAL)")
    print("="*60)

    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"Input file not found: {ARCHIVO_ENTRADA}")
        return

    df = pd.read_csv(ARCHIVO_ENTRADA, sep=";")
    print(f"   {len(df)} tweets to process")

    procesados = cargar_progreso()
    print(f"   {len(procesados)} already processed (will skip)")

    try:
        driver = conectar_chrome()
    except Exception as e:
        print(f"Could not connect to Chrome: {e}")
        return

    total_resp = 0

    for i, row in enumerate(df.itertuples()):
        tid = str(row.comment_id)

        if tid in procesados:
            continue

        autor = str(row.autor) if hasattr(row, 'autor') else "x"
        query = str(row.video_id) if hasattr(row, 'video_id') else ""

        print(f"\n[{i+1}/{len(df)}] Tweet {tid[:10]}...")

        resp = extraer_respuestas(driver, tid, autor, query)

        if resp:
            print(f"   -> {len(resp)} replies — saving...")
            guardar_incremental(resp, ARCHIVO_SALIDA)
            total_resp += len(resp)
            procesados.add(tid)
        else:
            print(f"   -> 0 replies")

        time.sleep(PAUSA + random.uniform(0, 2))

    print("\n" + "="*60)
    print(f"Done. New replies this session: {total_resp}")
    print(f"Output file: {ARCHIVO_SALIDA}")
    print("="*60)


if __name__ == "__main__":
    main()
