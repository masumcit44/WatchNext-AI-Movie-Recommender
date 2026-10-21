import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

"""
Backend API tests for WatchNext (FastAPI TestClient).

Covers: /health, /movies/search, /recommend, empty/unknown/invalid inputs,
missing metadata, model-not-ready (503 via monkeypatching), and real-artifact
integration tests (Avatar, The Dark Knight, Interstellar, typo "Avatr", unknown title).
"""
from fastapi.testclient import TestClient

import backend.main as main_app
import model.recommender as ml

client = TestClient(main_app.app)
client.__enter__()

EXACT_KEYS = {
    "movie_id", "title", "genres", "overview", "poster_path",
    "similarity_score", "reason",
}


def _assert_movie_shape(movie):
    assert set(movie.keys()) == EXACT_KEYS, movie.keys()
    assert isinstance(movie["movie_id"], (int, str))
    assert isinstance(movie["title"], str) and movie["title"]
    assert isinstance(movie["genres"], list) and all(isinstance(g, str) for g in movie["genres"])
    assert isinstance(movie["overview"], str)
    assert movie["poster_path"] is None or isinstance(movie["poster_path"], str)
    assert movie["similarity_score"] is None or isinstance(movie["similarity_score"], (int, float))
    assert movie["reason"] is None or isinstance(movie["reason"], str)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
def test_health_ready():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_ready"] is True
    assert body["status"] == "ok"
    # CORS is enabled by default for localhost:8501
    assert "access-control-allow-origin" not in resp.headers  # No Origin header sent


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
def test_search_success():
    resp = client.get("/movies/search", params={"q": "inter", "limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "inter"
    assert len(body["results"]) <= 3
    for movie in body["results"]:
        _assert_movie_shape(movie)
        assert movie["similarity_score"] is None
        assert movie["reason"] is None


def test_search_respects_limit():
    resp = client.get("/movies/search", params={"q": "batm", "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2


def test_search_empty_query():
    resp = client.get("/movies/search", params={"q": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMPTY_QUERY"


def test_search_missing_query():
    resp = client.get("/movies/search")
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMPTY_QUERY"


def test_search_invalid_limit():
    resp = client.get("/movies/search", params={"q": "Avatar", "limit": 0})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_TOP_N"


def test_search_invalid_limit_non_integer():
    resp = client.get("/movies/search", params={"q": "Avatar", "limit": "abc"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_TOP_N"


# --------------------------------------------------------------------------- #
# Recommendations
# --------------------------------------------------------------------------- #
def test_recommend_success_avatar():
    resp = client.get("/recommend", params={"title": "Avatar"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "Avatar"
    recs = body["recommendations"]
    assert len(recs) == 5
    titles = [m["title"] for m in recs]
    assert "Avatar" not in titles  # never recommends itself
    for m in recs:
        _assert_movie_shape(m)
        assert isinstance(m["similarity_score"], float)


def test_recommend_default_top_n_is_five():
    resp = client.get("/recommend", params={"title": "Interstellar"})
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) == 5


def test_recommend_top_n_respected():
    resp = client.get("/recommend", params={"title": "Avatar", "top_n": 2})
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) == 2


def test_recommend_genre_and_year_filters():
    resp = client.get("/recommend", params={"title": "The Dark Knight", "genre": "Action", "year": 2008})
    assert resp.status_code == 200
    for m in resp.json()["recommendations"]:
        assert "action" in [g.lower() for g in m["genres"]]


def test_recommend_empty_title():
    resp = client.get("/recommend", params={"title": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMPTY_QUERY"


def test_recommend_missing_title():
    resp = client.get("/recommend")
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMPTY_QUERY"


def test_recommend_unknown_movie():
    resp = client.get("/recommend", params={"title": "ZzzqUnknownTitle"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "MOVIE_NOT_FOUND"
    assert "ZzzqUnknownTitle" in body["detail"]["message"]


def test_recommend_typo_suggestions():
    resp = client.get("/recommend", params={"title": "Avatr"})
    assert resp.status_code == 404
    assert "Avatar" in resp.json()["detail"]["message"]


def test_recommend_invalid_year():
    resp = client.get("/recommend", params={"title": "Avatar", "year": "abc"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_YEAR"


def test_recommend_invalid_top_n_zero():
    resp = client.get("/recommend", params={"title": "Avatar", "top_n": 0})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_TOP_N"


def test_recommend_invalid_top_n_non_integer():
    resp = client.get("/recommend", params={"title": "Avatar", "top_n": "abc"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_TOP_N"


def test_recommend_invalid_top_n_above_cap():
    resp = client.get("/recommend", params={"title": "Avatar", "top_n": 51})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_TOP_N"


def test_recommend_unknown_genre():
    resp = client.get("/recommend", params={"title": "Avatar", "genre": "Nope"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILTER"
    assert "nope" in resp.json()["detail"]["message"].lower()


# --------------------------------------------------------------------------- #
# Missing metadata (monkeypatched ML layer - no dataset dependency)
# --------------------------------------------------------------------------- #
def test_missing_metadata_does_not_crash(monkeypatch):
    fake = [{
        "movie_id": 1,
        "title": "Missing Meta",
        "genres": [],
        "overview": "",
        "poster_path": None,
        "similarity_score": 0.5,
        "reason": "",
    }]
    monkeypatch.setattr(main_app, "recommend_movies", lambda *a, **k: fake)
    resp = client.get("/recommend", params={"title": "Whatever"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["recommendations"]) == 1
    _assert_movie_shape(body["recommendations"][0])


# --------------------------------------------------------------------------- #
# Model not ready (503) via monkeypatching
# --------------------------------------------------------------------------- #
def test_model_not_ready(monkeypatch):
    monkeypatch.setattr(main_app, "_MODEL_READY", False)
    resp = client.get("/recommend", params={"title": "Avatar"})
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "MODEL_NOT_READY"
    assert "traceback" not in resp.text.lower()
    health = client.get("/health")
    assert health.json()["model_ready"] is False


# --------------------------------------------------------------------------- #
# Real-artifact integration tests
# --------------------------------------------------------------------------- #
def test_integration_real_titles():
    for title in ["Avatar", "The Dark Knight", "Interstellar"]:
        resp = client.get("/recommend", params={"title": title, "top_n": 5})
        assert resp.status_code == 200, title
        recs = resp.json()["recommendations"]
        assert 1 <= len(recs) <= 5
        for m in recs:
            _assert_movie_shape(m)
            assert m["title"] != title
    resp = client.get("/recommend", params={"title": "Avatr"})
    assert resp.status_code == 404
    assert "Avatar" in resp.json()["detail"]["message"]


# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #
def test_cors_enabled_for_localhost():
    resp = client.get("/health", headers={"Origin": "http://localhost:8501"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:8501"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_enabled_for_127():
    resp = client.get("/health", headers={"Origin": "http://127.0.0.1:8501"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:8501"


# --------------------------------------------------------------------------- #
# Regression: API results match engine directly
# --------------------------------------------------------------------------- #
REGRESSION_TITLES = [
    "Avatar", "The Dark Knight", "Interstellar", "Inception", "Titanic",
    "Iron Man", "The Avengers", "Pulp Fiction", "The Matrix", "Shrek",
]


def _engine_score_tuple(title: str):
    from model.engine import recommend_movies
    results = recommend_movies(title=title, n=5)
    return [(r["title"], round(r["similarity_score"], 4)) for r in results]


def test_regression_api_matches_engine_on_10_titles():
    """Confirm /recommend returns same movie order and scores as model/engine.py directly."""
    for title in REGRESSION_TITLES:
        resp = client.get("/recommend", params={"title": title, "top_n": 5})
        assert resp.status_code == 200, title
        api_results = resp.json()["recommendations"]
        api_tuple = [(r["title"], r["similarity_score"]) for r in api_results]
        engine_tuple = _engine_score_tuple(title)
        assert api_tuple == engine_tuple, (
            f"regression mismatch for {title!r}\n API: {api_tuple}\n engine: {engine_tuple}"
        )