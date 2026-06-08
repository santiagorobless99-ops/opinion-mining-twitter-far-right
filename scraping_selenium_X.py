"""
=============================================================================
SCRAPING DE TWEETS CON SELENIUM
=============================================================================

Este script usa Selenium para scrapear tweets de X (Twitter).
Permite obtener tweets más antiguos que la API gratuita.

Uso:
    python scraping_selenium_X.py

=============================================================================
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


# ==================== CONFIGURACIÓN ====================

class Config:
    """Configuración del scraping."""
    
    # Usuarios a buscar
    USERNAMES = [
        "RobertoVaquero_",  # Roberto Vaquero
        "wallstwolverine",  # Wall Street Wolverine
        "juanrallo",        # Juan Ramón Rallo
        "navedelmisterio",  # Iker Jiménez
    ]
    
    # Palabras clave que deben contener los tweets
    KEYWORDS = [
        "Universidad",
        "Universidad pública",
        "Universidad privada",
    ]
    
    # Configuración de scraping
    MAX_SCROLLS = 10          # Número de scrolls por búsqueda
    SCROLL_PAUSE = 2          # Segundos entre scrolls
    DELAY_ENTRE_BUSQUEDAS = 5 # Segundos entre búsquedas
    
    # Archivo de salida
    ARCHIVO_SALIDA = "tweets_scrapping_crudo.csv"
    
    # Tiempo de espera para login manual (segundos)
    TIEMPO_LOGIN = 300  # 5 minutos


# ==================== FUNCIONES ====================

def iniciar_navegador():
    """Inicia Chrome con Selenium."""
    print("\n🌐 Iniciando navegador...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--lang=es-ES")
    chrome_options.add_argument("--window-size=1280,800")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def esperar_login(driver):
    """Navega a X y espera a que el usuario haga login manualmente."""
    print("\n" + "="*60)
    print("🔐 INICIO DE SESIÓN MANUAL REQUERIDO")
    print("="*60)
    
    driver.get("https://twitter.com/login")
    
    print("""
    1. Inicia sesión en X con tu cuenta en la ventana del navegador
    2. Completa cualquier verificación que te pida
    3. Una vez que estés en el feed de X, vuelve aquí
    """)
    
    input("   >>> Presiona ENTER cuando hayas completado el login... <<<")
    
    # Verificar si el login fue exitoso
    time.sleep(2)
    try:
        driver.find_element(By.CSS_SELECTOR, '[data-testid="primaryColumn"]')
        print("✅ Login verificado!")
        return True
    except NoSuchElementException:
        print("⚠️  No se pudo verificar el login, pero continuaremos...")
        return True  # Continuar de todos modos


def buscar_tweets(driver, username, keyword):
    """Busca tweets de un usuario con una palabra clave Y sus respuestas."""
    tweets_encontrados = []
    tweet_urls = []  # Guardar URLs para luego extraer respuestas
    
    # Construir URL de búsqueda
    query = f"from:{username} {keyword}"
    url = f"https://twitter.com/search?q={query.replace(' ', '%20')}&src=typed_query&f=live"
    
    print(f"\n🔍 Buscando: {query}")
    driver.get(url)
    
    # Esperar a que cargue
    time.sleep(3)
    
    # Verificar si hay resultados
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
        )
    except TimeoutException:
        print("   → No se encontraron tweets")
        return tweets_encontrados
    
    # Hacer scroll y extraer tweets
    tweets_ids_vistos = set()
    
    for scroll_num in range(Config.MAX_SCROLLS):
        # Extraer tweets visibles
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        
        for tweet_el in tweet_elements:
            tweet_data = extraer_datos_tweet(tweet_el, username, keyword)
            if tweet_data and tweet_data["comment_id"] not in tweets_ids_vistos:
                tweets_ids_vistos.add(tweet_data["comment_id"])
                tweets_encontrados.append(tweet_data)
                
                # Guardar URL para extraer respuestas después
                try:
                    link_el = tweet_el.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                    tweet_url = link_el.get_attribute("href")
                    if "/status/" in tweet_url and tweet_url not in tweet_urls:
                        tweet_urls.append(tweet_url)
                except NoSuchElementException:
                    pass
        
        # Scroll hacia abajo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(Config.SCROLL_PAUSE + random.uniform(0.5, 1.5))
    
    print(f"   → {len(tweets_encontrados)} tweets originales")
    
    # Ahora extraer respuestas de cada tweet
    if tweet_urls:
        print(f"   → Extrayendo respuestas de {len(tweet_urls)} tweets...")
        for i, tweet_url in enumerate(tweet_urls[:10]):  # Limitar a 10 tweets para no tardar demasiado
            replies = extraer_respuestas(driver, tweet_url, username, keyword)
            for reply in replies:
                if reply["comment_id"] not in tweets_ids_vistos:
                    tweets_ids_vistos.add(reply["comment_id"])
                    tweets_encontrados.append(reply)
            time.sleep(1)  # Pausa entre tweets
        
        print(f"   → Total con respuestas: {len(tweets_encontrados)}")
    
    return tweets_encontrados


def extraer_respuestas(driver, tweet_url, username, keyword):
    """Extrae las respuestas de un tweet específico."""
    respuestas = []
    
    try:
        driver.get(tweet_url)
        time.sleep(2)
        
        # Hacer un par de scrolls para cargar respuestas
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # Buscar todos los tweets (el primero es el original, los demás son respuestas)
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        
        for i, tweet_el in enumerate(tweet_elements):
            if i == 0:  # Saltar el tweet original
                continue
            
            reply_data = extraer_datos_tweet(tweet_el, username, keyword, is_reply=True)
            if reply_data:
                respuestas.append(reply_data)
    
    except Exception as e:
        pass  # Ignorar errores
    
    return respuestas


def extraer_datos_tweet(tweet_element, username, keyword, is_reply=False):
    """Extrae los datos de un elemento de tweet."""
    try:
        fecha_descarga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extraer texto del tweet
        try:
            texto_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            texto = texto_el.text.replace('\n', ' ').replace('\r', ' ')
        except NoSuchElementException:
            texto = ""
        
        # Extraer autor
        try:
            autor_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
            autor = autor_el.get_attribute("href").split("/")[-1]
        except NoSuchElementException:
            autor = username
        
        # Extraer ID del tweet (desde el enlace)
        try:
            link_el = tweet_element.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
            href = link_el.get_attribute("href")
            tweet_id = href.split("/status/")[-1].split("?")[0].split("/")[0]
        except NoSuchElementException:
            tweet_id = str(hash(texto))[:15]
        
        # Extraer likes
        try:
            likes_el = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="like"] span')
            likes_text = likes_el.text.strip()
            if likes_text:
                likes = int(likes_text.replace(",", "").replace(".", "").replace("K", "000").replace("M", "000000"))
            else:
                likes = 0
        except (NoSuchElementException, ValueError):
            likes = 0
        
        # Extraer fecha
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
        print(f"      Error extrayendo tweet: {e}")
        return None


def guardar_csv(tweets, archivo):
    """Guarda los tweets en CSV."""
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
        escritor.writerows(tweets)


def main():
    """Función principal."""
    print("\n" + "="*60)
    print("🐦 SCRAPING DE TWEETS CON SELENIUM")
    print("="*60)
    
    # Iniciar navegador
    driver = iniciar_navegador()
    
    try:
        # Esperar login
        logged_in = esperar_login(driver)
        
        if not logged_in:
            print("\n⚠️  Continuando sin login (resultados limitados)")
        
        todos_los_tweets = []
        
        # Buscar por cada usuario + keyword
        total_busquedas = len(Config.USERNAMES) * len(Config.KEYWORDS)
        busqueda_actual = 0
        
        for username in Config.USERNAMES:
            for keyword in Config.KEYWORDS:
                busqueda_actual += 1
                print(f"\n[{busqueda_actual}/{total_busquedas}] ", end="")
                
                tweets = buscar_tweets(driver, username, keyword)
                todos_los_tweets.extend(tweets)
                
                # Pausa entre búsquedas
                if busqueda_actual < total_busquedas:
                    delay = Config.DELAY_ENTRE_BUSQUEDAS + random.uniform(1, 3)
                    print(f"   ⏱️  Esperando {delay:.1f}s...")
                    time.sleep(delay)
        
        # Eliminar duplicados
        tweets_unicos = {}
        for tweet in todos_los_tweets:
            tweet_id = tweet.get("comment_id", "")
            if tweet_id and tweet_id not in tweets_unicos:
                tweets_unicos[tweet_id] = tweet
        
        todos_los_tweets = list(tweets_unicos.values())
        
        # Guardar
        guardar_csv(todos_los_tweets, Config.ARCHIVO_SALIDA)
        
        print("\n" + "="*60)
        print(f"✅ SCRAPING COMPLETADO")
        print("="*60)
        print(f"   Total tweets únicos: {len(todos_los_tweets)}")
        print(f"   Guardado en: {Config.ARCHIVO_SALIDA}")
    
    finally:
        print("\n🔒 Cerrando navegador...")
        try:
            driver.quit()
        except Exception:
            pass  # Ignorar errores al cerrar


if __name__ == "__main__":
    main()
