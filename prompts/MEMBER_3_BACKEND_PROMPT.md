# Prompt — Member 3: Backend Developer & Integration Engineer

You are the backend developer for WatchNext. Read the repository `README.md` first and follow its Shared Integration Contract exactly.

## Own these files
- `backend/main.py`
- `tests/test_api.py`
- Backend-specific documentation additions

## Task
Build a lightweight FastAPI REST API that connects the ML module to the Streamlit frontend. Do not implement or duplicate the ML algorithm.

## ML imports
Import from repository root:
`from model.recommender import load_model, search_movies, recommend_movies`

Required ML signatures:
- `load_model()`
- `search_movies(query: str, limit: int = 10) -> list[dict]`
- `recommend_movies(movie_title: str, genre: str | None = None, year: int | None = None, top_n: int = 5) -> list[dict]`

## Exact endpoints
- `GET /health`
- `GET /movies/search?q=...&limit=10`
- `GET /recommend?title=...&genre=...&year=...&top_n=5`
- FastAPI automatic docs at `/docs`

## Exact response schemas
Search:
`{"query": "...", "results": [movie_objects]}`

Recommendations:
`{"query": "...", "recommendations": [movie_objects]}`

Each movie object must contain:
`movie_id`, `title`, `genres`, `overview`, `poster_path`, `similarity_score`, `reason`.

Expected error body:
`{"detail": {"code": "MOVIE_NOT_FOUND", "message": "No matching movie was found."}}`

Use appropriate HTTP status codes: 400 for empty/invalid input, 404 for unknown movies, 503 when the model is not ready, and 500 for unexpected errors. Never expose tracebacks or secrets.

## Implementation requirements
- Load model/data once at application startup using FastAPI lifespan or an equivalent safe pattern.
- Do not load model artifacts on every request.
- Validate `q`, `title`, `limit`, `top_n`, and `year`.
- Keep filters as parameters passed to the ML module; do not calculate similarity in backend.
- Ensure missing metadata does not crash the API.
- Add tests for health, search, recommendation, empty input, unknown movie, invalid filters, and missing metadata. Use test doubles/monkeypatching rather than requiring the full dataset in every test.
- Add CORS only if the actual deployment requires it.
- Run with `uvicorn backend.main:app --reload`.
- Do not change shared contract without agreement from both teammates.
