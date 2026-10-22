# WatchNext — Shared Integration Contract

This repository starter is for a 3-person, 3-hour hackathon team.

## Team ownership
- Member 1 (ML): `model/recommender.py`, data preparation and recommendation logic.
- Member 2 (Frontend): `frontend/app.py`, Streamlit UI.
- Member 3 (Backend): `backend/main.py`, API, validation, integration and tests.

## Non-negotiable shared contract
All members must use the exact file names, function names, API routes, and JSON keys below.

### ML interface — `model/recommender.py`
The ML developer must expose:
- `load_model()`
- `search_movies(query: str, limit: int = 10) -> list[dict]`
- `recommend_movies(movie_title: str, genre: str | None = None, year: int | None = None, top_n: int = 5) -> list[dict]`

Each movie dictionary must use these keys:
- `movie_id`: string or integer
- `title`: string
- `genres`: list of strings
- `overview`: string
- `poster_path`: string or null
- `similarity_score`: number or null
- `reason`: string

For search results, `similarity_score` and `reason` may be null. Do not fabricate movie metadata. `poster_path` may be null if no poster is available. `load_model()` must be safe to call once during backend startup; document whether it loads data/artifacts or prepares the recommender in memory.

### Backend API
Base URL locally: `http://127.0.0.1:8000`

- `GET /health`
- `GET /movies/search?q=inter&limit=10`
- `GET /recommend?title=Interstellar&genre=Adventure&year=2015&top_n=5`

Success response for recommendations:
```json
{
  "query": "Interstellar",
  "recommendations": [
    {
      "movie_id": "example-id",
      "title": "Example Movie",
      "genres": ["Science Fiction"],
      "overview": "Example overview.",
      "poster_path": null,
      "similarity_score": 0.82,
      "reason": "Shares a relevant genre and theme."
    }
  ]
}
```
This is a schema example only, not real recommendation data.

Search response:
```json
{
  "query": "inter",
  "results": [
    {
      "movie_id": "example-id",
      "title": "Example Movie",
      "genres": ["Science Fiction"],
      "overview": "Example overview.",
      "poster_path": null,
      "similarity_score": null,
      "reason": null
    }
  ]
}
```

Error response:
```json
{
  "detail": {
    "code": "MOVIE_NOT_FOUND",
    "message": "No matching movie was found."
  }
}
```

Use these error codes where relevant:
- `EMPTY_QUERY`
- `MOVIE_NOT_FOUND`
- `INVALID_YEAR`
- `INVALID_TOP_N`
- `MODEL_NOT_READY`
- `INTERNAL_ERROR`

HTTP status guidance:
- 400: empty/invalid query or invalid filters
- 404: movie not found
- 503: model not ready
- 500: unexpected server error (do not expose traceback or secrets)

### Frontend contract
Frontend must call the API over HTTP. It must not import or duplicate the ML recommendation algorithm.
Configure backend URL with `BACKEND_URL`; local default is `http://127.0.0.1:8000`.
Render the response keys exactly as documented.

### Important filter rule
The ML developer owns the recommendation algorithm and should apply `genre` and `year` consistently. The backend validates and passes those parameters through; it must not invent or recalculate similarity.

### Shared environment and dependencies
Use Python 3.10+.
Install with `pip install -r requirements.txt`.
Backend: `uvicorn backend.main:app --reload`
Frontend: `streamlit run frontend/app.py`
Swagger docs: `http://127.0.0.1:8000/docs`

## Working separately
Each person should work on their owned files and commit/push changes to the same Git repository. Avoid independently changing the shared contract. If any change is necessary, agree in the team chat first and update this document before changing code.

## Optional: Real movie posters
The backend serves `poster_path` from `model/artifacts/poster_paths.json` (mapping `movie_id` → TMDB poster path). If this file is absent, posters are placeholders.

To populate it from the local Kaggle `movies_metadata.csv` (no API key needed):
```powershell
# 1. Download movies_metadata.csv from https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata
# 2. Place it at `data/movies_metadata.csv`
# 3. Run the builder:
python scripts/build_poster_paths_from_csv.py
# 4. Restart the backend to load the new file
```

The builder is standard-library only. It exits with code `2` and prints download
instructions if `data/movies_metadata.csv` is missing.

Alternatively, with a TMDB API key (v4 bearer token in `.env` as `TMDB_READ_TOKEN`), you can use `scripts/build_poster_paths.py` (not committed).

---

## Frontend notes
* The Streamlit UI talks to the backend **over HTTP only** — it never imports `model/`.
* **Fixed navigation bar**: one `position: fixed` header with a translucent-blur
  background, `z-index: 900` (above page content, below Streamlit's own popovers).
  Streamlit's own header is hidden and the page container is padded so content
  never slides under the bar. The brand is the single word **WatchNext**.
  Responsive at 390 px, 700 px and 1920 px.
* **Poster-first cards**: all five results render in one CSS grid with equal-height
  cards. Each card has a fixed 2:3 poster box with a placeholder layer and an
  absolutely positioned `<img>` on top (no `onerror` handler — the placeholder is
  the natural fallback). The image URL is
  `https://image.tmdb.org/t/p/w342` + `poster_path`, used only when `poster_path`
  is a non-empty string starting with `/`. Every API string is HTML-escaped.
* The API returns no ratings and no release years, so the UI shows neither.
* TMDB attribution is displayed in the footer.

---

## Run locally (one command)
```powershell
.\run_local.ps1
```
This script:
1. Creates `.venv` in the repo root if missing
2. Installs `requirements.txt`
3. Copies `.env.example` to `.env` if missing
4. Starts `uvicorn backend.main:app` on `http://127.0.0.1:8000`
5. Starts `streamlit run frontend/app.py` on `http://localhost:8501`
6. Waits for `/health` to return `model_ready: true`
7. Prints the live URLs and keeps both servers running

To stop: press `Ctrl+C` in the PowerShell window, or run:
```powershell
Stop-Job -Id <backend_job_id>, <frontend_job_id> | Remove-Job
```

### Environment variables
`.env.example` documents every setting the app reads:

| Variable | Purpose | Default |
| --- | --- | --- |
| `BACKEND_URL` | Base URL the frontend calls | `http://127.0.0.1:8000` |
| `CORS_ALLOW_ORIGINS` | Comma-separated origins the backend accepts | `http://localhost:8501,http://127.0.0.1:8501` |

### Running the tests
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

