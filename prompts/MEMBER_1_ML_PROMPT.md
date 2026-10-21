# Prompt — Member 1: Dataset, Feature Engineering & Recommendation Model

You are the ML engineer for WatchNext, a 3-hour hackathon project. Read the repository `README.md` first and follow its Shared Integration Contract exactly.

## Own these files
- `model/recommender.py`
- Optional preprocessing/model artifacts under `model/`
- Optional dataset exploration scripts if needed

## Task
Use the TMDB 5000 Movies and Credits dataset to build a fast content-based movie recommender. Inspect columns, missing values, duplicates, and data types. Clean metadata, then build useful text features from genres, overview, keywords, and optionally cast. Use TF-IDF and cosine similarity as a practical baseline.

## Required exact interface
Implement these public functions in `model/recommender.py`:
- `load_model()`
- `search_movies(query: str, limit: int = 10) -> list[dict]`
- `recommend_movies(movie_title: str, genre: str | None = None, year: int | None = None, top_n: int = 5) -> list[dict]`

Every result dictionary must contain exactly these shared keys:
`movie_id`, `title`, `genres`, `overview`, `poster_path`, `similarity_score`, `reason`.
`genres` must be a list of strings. Use null/None for unavailable poster paths and scores; use an empty string/list for missing metadata. Do not fabricate movie information.

## Behavior
- Search is case-insensitive and returns dataset-backed matches.
- Recommendation excludes the selected movie itself.
- Return up to `top_n` recommendations, normally 5.
- Apply optional genre and year filters consistently; document the year field used.
- Each recommendation reason must be grounded in available metadata.
- Handle unknown movie titles and missing metadata safely.
- Load/prepare artifacts once; avoid rebuilding vectors on every request.
- Keep memory and latency reasonable for a 3-hour hackathon.

## Handoff
- Make sure the module can be imported from the repository root as `from model.recommender import load_model, search_movies, recommend_movies`.
- Document dataset filenames and configuration in README.
- Test at least 10 input movies and report known limitations.
- Do not build FastAPI or Streamlit.
- Do not change the shared schema or function signatures without team agreement.
