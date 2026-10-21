# Prompt — Member 2: Streamlit Frontend Developer

You are the frontend engineer for WatchNext. Read the repository `README.md` first and follow its Shared Integration Contract exactly.

## Own this file
- `frontend/app.py`

## Task
Build a clean, responsive Streamlit app for a movie recommendation prototype. Users should search/select a movie, optionally choose genre and release year, and view five similar movies with explanations.

## Backend URL
Read `BACKEND_URL` from environment variables using `python-dotenv`; default to `http://127.0.0.1:8000`.
Do not import the ML module or duplicate the recommendation algorithm.

## Exact endpoints
- `GET {BACKEND_URL}/health`
- `GET {BACKEND_URL}/movies/search?q=<query>&limit=10`
- `GET {BACKEND_URL}/recommend?title=<title>&genre=<optional>&year=<optional>&top_n=5`

## Expected JSON keys
Recommendation response:
`{"query": "...", "recommendations": [...]}`

Each movie object:
`movie_id`, `title`, `genres`, `overview`, `poster_path`, `similarity_score`, `reason`.

Search response:
`{"query": "...", "results": [...]}`

Use these keys exactly. Do not assume a poster exists. For a null/missing poster path, show a placeholder. Do not invent recommendations if the API fails.

## Required UI
- Title and brief explanation.
- Search/select movie interface using the backend search endpoint.
- Find Similar Movies button.
- Cards showing title, poster/placeholder, genres, overview, and reason.
- Genre and year filters.
- Empty input, no result, loading, timeout, and backend error handling.
- Optional Surprise Me only after required features work.

## Handoff
- Keep API URL configurable.
- Use requests with a timeout.
- Make error messages user-friendly.
- Test against the real backend, not just mock data.
- Do not change API routes, JSON keys, or shared files without team agreement.
- Run using `streamlit run frontend/app.py`.
