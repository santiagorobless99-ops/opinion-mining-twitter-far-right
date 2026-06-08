# 📊 GUÍA COMPLETA: Pipeline de Opinion Mining para Tweets de X

---

## 📋 ¿QUÉ HACE ESTE SCRIPT?

**Sí, este script realiza el scrapping (descarga) de tweets automáticamente** usando la API oficial de X (Twitter). El pipeline completo incluye:

1. **SCRAPPING** → Descarga tweets desde X
2. **PREPROCESAMIENTO** → Limpia y tokeniza el texto
3. **COOCURRENCIAS** → Analiza qué palabras aparecen juntas
4. **EMBEDDINGS** → Convierte tweets en vectores para ML

---

## 🚀 INSTRUCCIONES PASO A PASO

### PASO 1: Obtener credenciales de la API de X (OBLIGATORIO)

> ⚠️ **Sin este paso, el scrapping NO funcionará**

1. **Ir a** [developer.twitter.com](https://developer.twitter.com/)

2. **Crear cuenta de desarrollador:**
   - Haz clic en "Sign up" o "Apply"
   - Inicia sesión con tu cuenta de X (Twitter)
   - Completa el formulario describiendo tu uso (ej: "Academic research on public opinion")
   - Acepta los términos y condiciones

3. **Crear un proyecto y app:**
   - Ve a "Projects & Apps" → "Overview"
   - Clic en "Create Project"
   - Nombre: `opinion_mining` (o el que quieras)
   - Crea una App dentro del proyecto

4. **Generar Bearer Token:**
   - En la configuración de tu App, ve a "Keys and Tokens"
   - En la sección "Bearer Token", haz clic en "Generate"
   - **COPIA EL TOKEN** (solo se muestra una vez)

---

### PASO 2: Preparar el entorno de Python

Abre **PowerShell** o **Terminal** en la carpeta del proyecto:

```powershell
# Ir a la carpeta TWITTER
cd "C:\Users\Robles\Desktop\Opinion mining\TWITTER"

# Crear entorno virtual (solo la primera vez)
python -m venv venv

# Activar el entorno virtual
.\venv\Scripts\Activate.ps1
```

> 💡 Sabrás que está activado si ves `(venv)` al inicio de la línea

---

### PASO 3: Instalar dependencias (solo la primera vez)

```powershell
# Instalar todas las librerías necesarias
pip install pandas tweepy langdetect spacy sentence-transformers numpy

# Descargar el modelo de español para spaCy
python -m spacy download es_core_news_sm
```

---

### PASO 4: Configurar el script

1. **Abre el archivo** `pipeline_tweets_X.py` con un editor de texto (Notepad, VSCode, etc.)

2. **Busca la clase `Config`** (alrededor de la línea 70) y modifica:

```python
class Config:
    # === PEGA AQUÍ TU BEARER TOKEN ===
    BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAMxxxxxxxxxxxxx..."
    
    # === USUARIOS A ANALIZAR ===
    # Añade los nombres de usuario SIN la @
    USERNAMES = [
        "PabloIglesias",    # Ejemplo
        "saborido_r",       # Ejemplo
        # Añade más usuarios...
    ]
    
    # === TÉRMINOS DE BÚSQUEDA ===
    # El script buscará tweets que contengan estas palabras
    SEARCH_QUERIES = [
        "universidad privada",
        "universidad pública",
        # Añade más búsquedas...
    ]
    
    # === PALABRAS CLAVE PARA COOCURRENCIAS ===
    KEYWORDS = [
        "universidad",
        "carrera",
        "trabajo",
        # Añade las que te interesen...
    ]
```

3. **Guarda el archivo**

---

### PASO 5: Ejecutar el pipeline

#### Opción A: Ejecutar TODO de una vez

```powershell
python pipeline_tweets_X.py --paso todo
```

#### Opción B: Ejecutar paso por paso

```powershell
# 1. Descargar tweets (SCRAPPING)
python pipeline_tweets_X.py --paso scrapping

# 2. Preprocesar el texto
python pipeline_tweets_X.py --paso preprocesar

# 3. Calcular coocurrencias
python pipeline_tweets_X.py --paso coocurrencias

# 4. Generar embeddings
python pipeline_tweets_X.py --paso embeddings
```

---

## 📁 ARCHIVOS QUE SE GENERAN

Después de ejecutar el pipeline, encontrarás estos archivos en la carpeta TWITTER:

| Archivo | Descripción |
|---------|-------------|
| `tweets_scrapping_crudo.csv` | ✅ Todos los tweets descargados con metadatos |
| `tweets_limpios_coocurrencias.csv` | Texto tokenizado y lematizado |
| `tweets_para_embeddings.csv` | Texto limpio para ML |
| `coocurrencias_tweets.csv` | Tabla de palabras que aparecen juntas |
| `embeddings_tweets.npy` | Matriz de vectores (para clustering) |
| `tweets_index_embeddings.csv` | Índice que conecta vectores con tweets |

---

## ❓ SOLUCIÓN DE PROBLEMAS

### "ModuleNotFoundError: No module named 'tweepy'"
```powershell
pip install tweepy
```

### "OSError: Can't find model 'es_core_news_sm'"
```powershell
python -m spacy download es_core_news_sm
```

### "ERROR: Debes configurar tu BEARER_TOKEN"
Abre `pipeline_tweets_X.py` y pega tu Bearer Token real (ver Paso 1).

### "ERROR: No existe el archivo tweets_scrapping_crudo.csv"
Ejecuta primero el paso de scrapping:
```powershell
python pipeline_tweets_X.py --paso scrapping
```

### "401 Unauthorized" o "403 Forbidden"
Tu Bearer Token no es válido o tu app no tiene permisos. Genera uno nuevo en developer.twitter.com.

### "429 Too Many Requests"
Has alcanzado el límite de la API. Espera 15 minutos e intenta de nuevo.

---

## 💡 CONSEJOS

1. **Empieza con pocos usuarios/búsquedas** para probar que todo funciona
2. **La API gratuita tiene límites**: ~10,000 tweets/mes
3. **Los embeddings tardan** la primera vez porque descarga el modelo (~500MB)
4. **Guarda tu Bearer Token** en un lugar seguro, no lo compartas

---

## 🔄 EJEMPLO DE USO COMPLETO

```powershell
# 1. Abrir PowerShell e ir a la carpeta
cd "C:\Users\Robles\Desktop\Opinion mining\TWITTER"

# 2. Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 3. Ejecutar todo el pipeline
python pipeline_tweets_X.py --paso todo

# 4. Ver los resultados
dir *.csv
```

---

## 📞 ARCHIVOS INCLUIDOS

```
TWITTER/
├── pipeline_tweets_X.py              ← Script principal (USAR ESTE)
├── INSTRUCCIONES_COMPLETAS.md        ← Este archivo
├── INSTRUCCIONES_PIPELINE_TWEETS.md  ← Instrucciones adicionales
├── 1-scrapping_X_tweets.py           ← Script individual de scrapping
├── 2.1-preprocesamiento_coocurrencias_red_tweets.py
├── 2.2-preprocesamiento_embeddings_tweets.py
├── 3.1-analisis_coocurrencias_tweets.py
└── 3.2-generar_embeddings_tweets.py
```

> 💡 **Recomendación**: Usa solo `pipeline_tweets_X.py`, los demás son para referencia.
