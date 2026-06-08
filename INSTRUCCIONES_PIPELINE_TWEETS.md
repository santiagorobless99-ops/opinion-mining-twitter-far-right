# 📊 Pipeline de Opinion Mining para Tweets de X

## Descripción

Este pipeline permite analizar tweets de X (Twitter) mediante:
- **Scrapping**: Descarga de tweets por usuario o búsqueda
- **Preprocesamiento**: Limpieza y tokenización del texto
- **Coocurrencias**: Análisis de qué palabras aparecen juntas
- **Embeddings**: Vectorización para clustering y ML

---

## 🔧 Instalación (Paso a Paso)

### 1. Crear entorno virtual (recomendado)

```powershell
# Abrir PowerShell en la carpeta del proyecto
cd "C:\Users\Robles\Desktop\Opinion mining"

# Crear entorno virtual con Python 3.11
python -m venv venv

# Activar el entorno virtual
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
# Instalar todas las dependencias de una vez
pip install pandas tweepy langdetect spacy sentence-transformers numpy

# Descargar el modelo de español para spaCy
python -m spacy download es_core_news_sm
```

### 3. Obtener credenciales de la API de X

1. Ve a [developer.twitter.com](https://developer.twitter.com/)
2. Crea una cuenta de desarrollador (si no tienes)
3. Crea un nuevo proyecto y una app
4. Genera las credenciales → copia el **Bearer Token**

### 4. Configurar el script

Abre `pipeline_tweets_X.py` y edita la clase `Config`:

```python
class Config:
    # Pega aquí tu Bearer Token
    BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAxxxxx..."
    
    # Añade los usuarios que quieres analizar
    USERNAMES = [
        "usuario_ejemplo1",
        "usuario_ejemplo2",
    ]
    
    # Y/o términos de búsqueda
    SEARCH_QUERIES = [
        "universidad privada",
        "universidad pública",
    ]
```

---

## 🚀 Ejecución

### Opción A: Ejecutar todo el pipeline

```powershell
python pipeline_tweets_X.py --paso todo
```

### Opción B: Ejecutar pasos individuales

```powershell
# Paso 1: Descargar tweets
python pipeline_tweets_X.py --paso scrapping

# Paso 2: Preprocesar texto
python pipeline_tweets_X.py --paso preprocesar

# Paso 3: Calcular coocurrencias
python pipeline_tweets_X.py --paso coocurrencias

# Paso 4: Generar embeddings
python pipeline_tweets_X.py --paso embeddings
```

### Ver ayuda

```powershell
python pipeline_tweets_X.py --help
```

---

## 📁 Archivos Generados

| Archivo | Descripción |
|---------|-------------|
| `tweets_scrapping_crudo.csv` | Tweets descargados con metadatos |
| `tweets_limpios_coocurrencias.csv` | Texto tokenizado para redes semánticas |
| `tweets_para_embeddings.csv` | Texto limpio para vectorización |
| `coocurrencias_tweets.csv` | Tabla de coocurrencias por keyword |
| `embeddings_tweets.npy` | Matriz de embeddings (NumPy) |
| `tweets_index_embeddings.csv` | Índice que mapea embeddings a tweets |

---

## ⚙️ Configuración Avanzada

Puedes modificar estos parámetros en la clase `Config`:

```python
# Número máximo de tweets por usuario/búsqueda
MAX_TWEETS_POR_QUERY = 100

# Longitud mínima del texto para incluirlo
MIN_CHAR_LEN = 10
MIN_WORDS = 2

# Filtrar solo tweets en español
IDIOMA_OBJETIVO = "es"
USAR_FILTRO_IDIOMA = True

# Palabras clave para el análisis de coocurrencias
KEYWORDS = [
    "universidad",
    "carrera",
    "trabajo",
    # Añade las que necesites
]

# Modelo de embeddings (puedes cambiarlo)
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
```

---

## ❓ Solución de Problemas

### Error: "No module named 'tweepy'"
```powershell
pip install tweepy
```

### Error: "Can't find model 'es_core_news_sm'"
```powershell
python -m spacy download es_core_news_sm
```

### Error: "BEARER_TOKEN no configurado"
Edita el archivo y pega tu Bearer Token real en la línea correspondiente.

### Error: "El archivo no existe"
Ejecuta los pasos en orden: primero `scrapping`, luego `preprocesar`, etc.

---

## 📈 Uso de los Resultados

### Leer los embeddings en Python

```python
import numpy as np
import pandas as pd

# Cargar embeddings
embeddings = np.load("embeddings_tweets.npy")
print(f"Shape: {embeddings.shape}")  # (n_tweets, 384)

# Cargar índice
df_index = pd.read_csv("tweets_index_embeddings.csv", sep=";")

# Ahora embeddings[i] corresponde a df_index.iloc[i]
```

### Hacer clustering con los embeddings

```python
from sklearn.cluster import KMeans

# Agrupar en 5 clusters
kmeans = KMeans(n_clusters=5, random_state=42)
clusters = kmeans.fit_predict(embeddings)

# Añadir clusters al índice
df_index["cluster"] = clusters
```

### Visualizar con UMAP

```python
import umap
import matplotlib.pyplot as plt

# Reducir a 2D
reducer = umap.UMAP(n_components=2, random_state=42)
coords = reducer.fit_transform(embeddings)

# Graficar
plt.scatter(coords[:, 0], coords[:, 1], c=clusters, cmap="viridis", s=5)
plt.title("Clusters de tweets")
plt.show()
```

---

## 📞 Soporte

Si tienes problemas, verifica:
1. Que el entorno virtual esté activado
2. Que todas las dependencias estén instaladas
3. Que el Bearer Token sea válido
4. Que hayas ejecutado los pasos en orden
