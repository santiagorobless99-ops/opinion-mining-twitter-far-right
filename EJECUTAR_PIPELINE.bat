"@echo off
chcp 65001 >nul
title Pipeline de Tweets - Menu Principal
color 0A

:menu
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║     📊 PIPELINE DE OPINION MINING PARA TWEETS DE X 📊       ║
echo  ╠══════════════════════════════════════════════════════════════╣
echo  ║                                                              ║
echo  ║   [1] Ejecutar TODO el pipeline                              ║
echo  ║   [2] Solo SCRAPPING (descargar tweets)                      ║
echo  ║   [3] Solo PREPROCESAR (limpiar texto)                       ║
echo  ║   [4] Solo COOCURRENCIAS (analizar palabras)                 ║
echo  ║   [5] Solo EMBEDDINGS (generar vectores)                     ║
echo  ║   [6] Instalar dependencias                                  ║
echo  ║   [7] Abrir instrucciones                                    ║
echo  ║   [0] Salir                                                  ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
set /p opcion="  Elige una opcion (0-7): "

if "%opcion%"=="1" goto todo
if "%opcion%"=="2" goto scrapping
if "%opcion%"=="3" goto preprocesar
if "%opcion%"=="4" goto coocurrencias
if "%opcion%"=="5" goto embeddings
if "%opcion%"=="6" goto instalar
if "%opcion%"=="7" goto instrucciones
if "%opcion%"=="0" goto salir
goto menu

:todo
cls
echo.
echo  🚀 Ejecutando pipeline completo...
echo  ══════════════════════════════════
echo.
call venv\Scripts\activate.bat 2>nul || echo ⚠️  Entorno virtual no encontrado, usando Python global
python pipeline_tweets_X.py --paso todo
echo.
pause
goto menu

:scrapping
cls
echo.
echo  📥 Descargando tweets...
echo  ════════════════════════
echo.
call venv\Scripts\activate.bat 2>nul
python pipeline_tweets_X.py --paso scrapping
echo.
pause
goto menu

:preprocesar
cls
echo.
echo  🔧 Preprocesando texto...
echo  ═════════════════════════
echo.
call venv\Scripts\activate.bat 2>nul
python pipeline_tweets_X.py --paso preprocesar
echo.
pause
goto menu

:coocurrencias
cls
echo.
echo  🔗 Calculando coocurrencias...
echo  ═══════════════════════════════
echo.
call venv\Scripts\activate.bat 2>nul
python pipeline_tweets_X.py --paso coocurrencias
echo.
pause
goto menu

:embeddings
cls
echo.
echo  🧠 Generando embeddings...
echo  ══════════════════════════
echo.
call venv\Scripts\activate.bat 2>nul
python pipeline_tweets_X.py --paso embeddings
echo.
pause
goto menu

:instalar
cls
echo.
echo  📦 Instalando dependencias...
echo  ═════════════════════════════
echo.
echo  Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate.bat
echo.
echo  Instalando librerias...
pip install pandas tweepy langdetect spacy sentence-transformers numpy
echo.
echo  Descargando modelo de espanol para spaCy...
python -m spacy download es_core_news_sm
echo.
echo  ✅ Instalacion completada!
echo.
pause
goto menu

:instrucciones
cls
start "" "INSTRUCCIONES_COMPLETAS.md"
goto menu

:salir
cls
echo.
echo  👋 ¡Hasta luego!
echo.
timeout /t 2 >nul
exit
