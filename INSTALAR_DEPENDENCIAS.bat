@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  📦 Instalando dependencias del pipeline de tweets...
echo  ═══════════════════════════════════════════════════
echo.
echo  [1/3] Creando entorno virtual con Python 3.11...
py -3.11 -m venv venv
call venv\Scripts\activate.bat
echo.
echo  [2/3] Instalando librerias de Python...
pip install pandas tweepy langdetect spacy sentence-transformers numpy
echo.
echo  [3/3] Descargando modelo de espanol para spaCy...
python -m spacy download es_core_news_sm
echo.
echo  ════════════════════════════════════════════════════
echo  ✅ INSTALACION COMPLETADA
echo  ════════════════════════════════════════════════════
echo.
echo  Ahora puedes ejecutar EJECUTAR_PIPELINE.bat
echo.
pause
