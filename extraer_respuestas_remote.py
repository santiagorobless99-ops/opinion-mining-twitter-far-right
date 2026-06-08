"""
EXTRAER RESPUESTAS - CONECTAR A CHROME EXISTENTE
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


# ==================== CONFIGURACIÓN ====================

ARCHIVO_ENTRADA = "tweets_scrapping_crudo.csv"
ARCHIVO_SALIDA = "tweets_con_respuestas.csv"
MAX_RESPUESTAS = 30
PAUSA = 3


# ==================== FUNCIONES ====================

def conectar_chrome():
    """Conecta a Chrome existente con remote debugging."""
    print("\n🔗 Conectando a Chrome existente...")
    
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    driver = webdriver.Chrome(options=options)
    print("✅ Conectado!")
    return driver


def extraer_respuestas(driver, tweet_id, autor, query):
    """Extrae respuestas de un tweet."""
    respuestas = []
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        url = f"https://twitter.com/{autor}/status/{tweet_id}"
        driver.get(url)
        time.sleep(2)
        
        print(f"      [DEBUG] Título: {driver.title}")
        print(f"      [DEBUG] URL: {driver.current_url}")
        
        # Scroll para cargar respuestas
        time.sleep(4)  # Esperar más tiempo inicial
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Buscar tweets
        tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        print(f"      [DEBUG] Elementos 'tweet' encontrados: {len(tweets)}")
        
        if len(tweets) == 0:
            # Diagnóstico extra si no encuentra nada
            articles = driver.find_elements(By.TAG_NAME, 'article')
            print(f"      [DEBUG] Elementos 'article' genéricos: {len(articles)}")
            path_check = driver.find_elements(By.XPATH, "//*[contains(text(), 'Responder')]")
            print(f"      [DEBUG] Elementos con texto 'Responder': {len(path_check)}")
        ids_vistos = {tweet_id}
        
        for tweet_el in tweets:
            if len(respuestas) >= MAX_RESPUESTAS:
                break
            
            try:
                # texto
                texto_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                texto = texto_el.text.replace('\n', ' ')
                
                # id
                link = tweet_el.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                rid = link.get_attribute("href").split("/status/")[-1].split("?")[0].split("/")[0]
                
                if rid in ids_vistos or rid == tweet_id:
                    continue
                ids_vistos.add(rid)
                
                # autor
                try:
                    a_el = tweet_el.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
                    r_autor = a_el.get_attribute("href").split("/")[-1]
                except:
                    r_autor = "unknown"
                
                # likes
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
    """Carga los IDs de los tweets padres ya procesados."""
    procesados = set()
    if os.path.exists(ARCHIVO_SALIDA):
        try:
            df_out = pd.read_csv(ARCHIVO_SALIDA, sep=";")
            if "parent_id" in df_out.columns:
                # Convertir a string para asegurar consistencia
                procesados = set(df_out["parent_id"].astype(str).unique())
            
            # También añadir los que están en el archivo pero marcados como "SIN_RESPUESTAS" o similar si implementáramos eso
            # Por ahora, simplemente confiamos en que si hay algo con ese parent_id, ya se intentó.
        except Exception:
            pass
    return procesados

def guardar_incremental(datos, archivo, modo='a'):
    """Guarda datos incrementalmente."""
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
    print("📥 EXTRACCIÓN DE RESPUESTAS (REMOTO + INCREMENTAL)")
    print("="*60)
    
    # Cargar tweets entrada
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"❌ No se encuentra {ARCHIVO_ENTRADA}")
        return

    df = pd.read_csv(ARCHIVO_ENTRADA, sep=";")
    print(f"   {len(df)} tweets cargados para procesar")
    
    # Cargar progreso
    procesados = cargar_progreso()
    print(f"   {len(procesados)} tweets ya procesados anteriormente")
    
    # Conectar a Chrome
    try:
        driver = conectar_chrome()
    except Exception as e:
        print(f"❌ Error al conectar a Chrome: {e}")
        return
    
    total_resp = 0
    
    for i, row in enumerate(df.itertuples()):
        tid = str(row.comment_id)
        
        # Saltar si ya está procesado
        if tid in procesados:
            continue
            
        autor = str(row.autor) if hasattr(row, 'autor') else "x"
        query = str(row.video_id) if hasattr(row, 'video_id') else ""
        
        print(f"\n[{i+1}/{len(df)}] Tweet {tid[:10]}...")
        
        resp = extraer_respuestas(driver, tid, autor, query)
        
        # Si no hay respuestas, al menos registrar que se procesó (opcional, pero ayuda a no reintentar infinitamente)
        # Para simplificar, si no hay respuestas, no guardamos nada en el CSV de salida, 
        # pero el riesgo es re-procesar siempre los vacíos.
        # Mejor estrategia: Guardar todo lo encontrado. Si está vacío, quizás deberíamos tener un log aparte.
        # Por ahora, asumimos que re-procesar los vacíos es aceptable o que el usuario interrumpirá.
        # ALTERNATIVA: Guardar un registro "dummy" o simplemente confiar en que el CSV crece.
        
        if resp:
            print(f"   → {len(resp)} respuestas - Guardando...")
            guardar_incremental(resp, ARCHIVO_SALIDA)
            total_resp += len(resp)
            procesados.add(tid)
        else:
            print(f"   → 0 respuestas")
            # Podríamos guardarlo en un set en memoria para esta ejecución
        
        time.sleep(PAUSA + random.uniform(0, 2))
    
    print("\n" + "="*60)
    print(f"✅ FINALIZADO")
    print(f"   Respuestas nuevas en esta sesión: {total_resp}")
    print(f"   Archivo: {ARCHIVO_SALIDA}")
    print("="*60)


if __name__ == "__main__":
    main()
