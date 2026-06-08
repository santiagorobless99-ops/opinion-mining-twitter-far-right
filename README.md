# Opinion Mining: Far-Right Discourse on X/Twitter (Spain)

NLP pipeline for scraping and analyzing tweets from Spanish far-right influencers. Part of a doctoral research project on the platformization of far-right discourse. Designed to be methodologically comparable with the [YouTube pipeline](../).

## Research Context

This pipeline was developed for a PhD thesis (Universitat de València) examining how far-right online communities construct discourse around cultural and educational topics in Spain and Argentina.

**Sampled accounts:** @RobertoVaquero_, @wallstwolverine, @juanrallo, @navedelmisterio.

**Corpus focus:** tweets and reply threads containing keywords related to the public vs. private university debate.

## Pipeline

A unified pipeline (`pipeline_tweets_X.py`) with four sequential steps, runnable individually or end-to-end:

| Step | Flag | Description |
|---|---|---|
| 1. Scraping | `--paso scrapping` | Downloads tweets and reply threads via Tweepy (X API v2) |
| 2. Preprocessing | `--paso preprocesar` | Text cleaning, language detection, spaCy lemmatization (for co-occurrences) + light cleaning (for embeddings) |
| 3. Co-occurrences | `--paso coocurrencias` | Token co-occurrence frequency analysis per keyword |
| 4. Embeddings | `--paso embeddings` | Multilingual sentence embeddings via `sentence-transformers` |

Additional utilities: `scraping_selenium_X.py` (Selenium-based fallback), `extraer_respuestas_firefox.py` / `extraer_respuestas_remote.py` (reply extraction via browser automation), `verificar_y_validar.py` (corpus validation).

## Methods

**Scraping:** Tweepy v4 (X API v2). Targets specific user timelines filtered by keyword, then follows conversation threads to collect replies.

**Text preprocessing:** URL/mention/hashtag normalization, language detection (`langdetect`), lemmatization and stopword removal (spaCy `es_core_news_sm`). Two preprocessing branches: aggressive (for co-occurrence) and light (for embeddings).

**Co-occurrence analysis:** token-level frequencies and relative frequencies for configurable keywords. Output compatible with network analysis tools (Gephi, NetworkX).

**Semantic embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (384-d, normalized). Enables clustering and semantic mapping of the discourse corpus.

## Installation

```bash
pip install -r requirements.txt
python -m spacy download es_core_news_sm
```

**Configure credentials:**

```bash
cp .env.example .env
# Edit .env and add your X Bearer Token
# Get one at: https://developer.twitter.com/
```

## Usage

```bash
# Run individual steps
python pipeline_tweets_X.py --paso scrapping
python pipeline_tweets_X.py --paso preprocesar
python pipeline_tweets_X.py --paso coocurrencias
python pipeline_tweets_X.py --paso embeddings

# Or run the full pipeline
python pipeline_tweets_X.py --paso todo
```

Configure target accounts, keywords, and file paths in the `Config` class at the top of `pipeline_tweets_X.py`.

## Output Files

| File | Description |
|---|---|
| `tweets_final.csv` | Raw scraped tweets (ID, author, text, likes, date, reply flag, platform) |
| `tweets_limpios_coocurrencias.csv` | Lemmatized corpus (tokens, lemmas, filtered tokens) |
| `tweets_para_embeddings.csv` | Cleaned text with metadata for embedding |
| `coocurrencias_tweets.csv` | Co-occurrence matrix (keyword × token × freq) |
| `embeddings_tweets.npy` | NumPy array of sentence embeddings |
| `tweets_index_embeddings.csv` | Metadata index aligned with embedding array rows |

> Raw data files are excluded from this repository. Contact the author for access.

## Notes

- Requires X API v2 access (Basic tier or above for recent search endpoint). Free tier has significant rate limits.
- The Selenium-based scraper (`scraping_selenium_X.py`) is a fallback for cases where the API does not cover the required time window.
- Output schema is intentionally compatible with the YouTube pipeline to facilitate cross-platform analysis.

## Related

See the parent [`Opinion mining/`](../) folder for the equivalent YouTube pipeline.

## Author

Santiago Robles — PhD Candidate, Sociology, Universitat de València  
Contact: santiagorobless99@gmail.com
