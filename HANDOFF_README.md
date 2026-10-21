# WatchNext ML Recommender — Backend Handoff Guide

## 1. Purpose
This package provides the Machine Learning recommendation module for **WatchNext**, an explainable content-based movie recommendation system built on the TMDB 5000 Movies & Credits dataset. It is packaged to integrate directly into the FastAPI backend service.

---

## 2. Folder Layout
```
WatchNext_Integration_Kit/
├── requirements.txt            # Runtime dependencies (numpy, scipy, fastapi, uvicorn, etc.)
├── requirements-dev.txt        # Optional training/dev dependencies (pandas, scikit-learn)
├── HANDOFF_README.md           # This backend handoff document
├── README.md                   # Shared integration contract
├── .env.example                # Example environment variables
├── backend/
│   ├── __init__.py
│   └── main.py                 # FastAPI service implementing the HTTP contract
├── model/
│   ├── __init__.py
│   ├── recommender.py          # Public contract adapter (import from here)
│   ├── engine.py               # Core TF-IDF similarity engine (numpy/scipy)
│   └── artifacts/
│       ├── config.json         # Feature block weights and metadata
│       ├── features.npz        # Compressed sparse feature matrix (25,456 features)
│       └── movies.json         # Movie catalog metadata (4,803 titles)
└── tests/
    ├── __init__.py
    ├── test_api.py             # API route and status code tests
    └── test_recommender_contract.py # Contract validation & regression tests
```

---

## 3. Installation
Ensure Python 3.10+ (tested on Python 3.14.3) is active:
```bash
pip install -r requirements.txt
```
*Note: The runtime engine depends only on standard library, `numpy`, and `scipy`. `pandas` and `scikit-learn` are not required at runtime.*

---

## 4. How Artifacts Are Located & Overrides
By default, the engine loads its 3 required artifact files (`config.json`, `features.npz`, `movies.json`) from `model/artifacts/` located adjacent to `model/engine.py`.

To override the artifact directory at runtime (e.g. in staging, containerized, or testing environments), set the environment variable:
```bash
export WATCHNEXT_ARTIFACT_DIR="/custom/path/to/artifacts"
```
Or in Windows PowerShell:
```powershell
$env:WATCHNEXT_ARTIFACT_DIR="C:\custom\path\to\artifacts"
```
If the directory or any of the three artifacts are missing or unreadable, `load_model()` raises `FileNotFoundError`, which the backend maps to `503 MODEL_NOT_READY`.

---

## 5. Public API (`model.recommender`)

Import the adapter functions and exceptions from `model.recommender`:
```python
from model.recommender import (
    load_model,
    search_movies,
    recommend_movies,
    is_model_ready,
    EmptyQueryError,
    InvalidFilterError,
    InvalidYearError,
    InvalidTopNError,
    InvalidGenreError,
    MovieNotFoundError,
)
```

### 5.1 `load_model()`
* **Signature:** `load_model() -> None`
* **Behavior:** Idempotent. Loads artifacts into memory on first call; subsequent calls return immediately. Safe to call repeatedly. Call once during backend startup in lifespan.

### 5.2 `is_model_ready()`
* **Signature:** `is_model_ready() -> bool`
* **Behavior:** Returns `True` if `load_model()` completed successfully, `False` otherwise.

### 5.3 `search_movies(query: str, limit: int = 10) -> list[dict]`
* **Parameters:**
  * `query`: Search string (case-insensitive substring match against movie titles). Empty string raises `EmptyQueryError`.
  * `limit`: Maximum number of search results to return (integer between 1 and 50, default: 10).
* **Return Schema:** List of movie dictionaries conforming to the exact 7-key shared contract. For search results, `similarity_score` and `reason` are `None`.

### 5.4 `recommend_movies(movie_title: str, genre: str | None = None, year: int | None = None, top_n: int = 5) -> list[dict]`
* **Parameters:**
  * `movie_title`: Exact or fuzzy title of the reference movie. Empty string raises `EmptyQueryError`.
  * `genre`: Optional genre filter (case-insensitive string). If non-matching to catalog, raises `InvalidGenreError`.
  * `year`: Optional exact release year (integer). Non-integer raises `InvalidYearError`.
  * `top_n`: Number of recommendations (integer between 1 and 50, default: 5). Non-integer or out-of-range raises `InvalidTopNError`.
* **Return Schema:** List of up to `top_n` movie dictionaries. The input movie itself is never included in recommendations.

### 5.5 Result Schema (Exact 7 Keys)
Every movie item in recommendations and search results contains exactly these keys:
```json
{
  "movie_id": 19995,
  "title": "Avatar",
  "genres": ["Action", "Adventure", "Fantasy", "Science Fiction"],
  "overview": "In the 22nd century, a paraplegic Marine...",
  "poster_path": null,
  "similarity_score": 0.2847,
  "reason": "Shares genres: Action, Adventure, Science Fiction; keywords: futuristic, space, alien; cast: Zoe Saldana."
}
```

---

## 6. Error-to-HTTP Status & Code Mapping Table

The backend maps all raised exceptions to the uniform JSON format `{"detail": {"code": "<CODE>", "message": "<MESSAGE>"}}`:

| Exception Raised | HTTP Status | JSON `detail.code` | Cause / Meaning |
| :--- | :---: | :--- | :--- |
| `EmptyQueryError` | **400** | `EMPTY_QUERY` | Search `q` or recommend `title` is missing/empty string |
| `InvalidYearError` | **400** | `INVALID_YEAR` | `year` filter is not an integer |
| `InvalidTopNError` | **400** | `INVALID_TOP_N` | `top_n` or `limit` is not an integer in `[1, 50]` |
| `InvalidGenreError` | **400** | `INVALID_FILTER` | Specified genre not found in catalog (Available listed in message) |
| `InvalidFilterError`| **400** | `INVALID_FILTER` | Generic filter validation failure |
| `MovieNotFoundError`| **404** | `MOVIE_NOT_FOUND` | Movie title unknown (close typo suggestions in `.suggestions`) |
| `ModelNotReadyError` / `FileNotFoundError` | **503** | `MODEL_NOT_READY` | Model artifacts missing, unreadable, or startup incomplete |
| Unhandled `Exception`| **500** | `INTERNAL_ERROR` | Unexpected server crash (traceback suppressed from client) |

---

## 7. Model Warm-Up at Startup (FastAPI Lifespan)
Warm up the model during application lifespan so requests never block on initial disk I/O:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from model.recommender import load_model

_MODEL_READY = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _MODEL_READY
    try:
        load_model()
        _MODEL_READY = True
    except Exception:
        _MODEL_READY = False
    yield

app = FastAPI(lifespan=lifespan)
```

---

## 8. Optional `poster_paths.json` Documented Format
The base TMDB 5000 CSV dataset does not include poster paths. Therefore, `poster_path` defaults to `null`.

If a poster mapping file is provided, place it at `model/artifacts/poster_paths.json` (or inside the directory designated by `WATCHNEXT_ARTIFACT_DIR`). The format must be a JSON object mapping string or integer `movie_id` to the relative or absolute poster URL path:
```json
{
  "19995": "/kyeqWdyUXW608qlYkRqosgPjhpH.jpg",
  "272": "/7C921eWK06n12c1miRXsD2POQ9a.jpg",
  "157336": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"
}
```
*Note: Do not generate mock poster URLs; if no file is present, leave `poster_path` as `null`.*

---

## 9. Known Limitations
1. **Title Lookup Only:** Recommendations are retrieved by matching a known title from the dataset catalog.
2. **Posters:** `poster_path` is `null` unless an external `poster_paths.json` is supplied.
3. **Exact Year Matching:** The `year` filter in the adapter enforces an exact release year match (`release_year == year`).
4. **Duplicate Title Resolution:** If multiple movies share the exact same title in TMDB 5000, the system deterministically resolves to the entry with the highest `vote_count`.
5. **No Personalization:** The model is content-based and metadata-driven; it does not track user history or user ratings.

