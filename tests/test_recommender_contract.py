"""
Contract tests for model.recommender (the thin adapter over model/engine.py).

Includes the Phase-1 regression proof: results for a fixed set of 10 titles are
identical (same movie order and scores) to the original engine called directly
via the backed-up original recommender.py (_backup_original/recommender.py).
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]          # .../WatchNext_Integration_Kit
WORKSPACE_ROOT = KIT_ROOT.parent                    # .../first_hackathon_practice
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from model.recommender import (  # noqa: E402
    load_model, search_movies, recommend_movies,
    is_model_ready,
    EmptyQueryError, InvalidFilterError, InvalidYearError,
    InvalidTopNError, InvalidGenreError, MovieNotFoundError,
)

REGRESSION_TITLES = [
    "Avatar", "The Dark Knight", "Interstellar", "Inception", "Titanic",
    "Iron Man", "The Avengers", "Pulp Fiction", "The Matrix", "Shrek",
]

SHARED_KEYS = {
    "movie_id", "title", "genres", "overview", "poster_path",
    "similarity_score", "reason",
}


def _load_backed_up_original():
    """Import the original recommender.py from ./_backup_original/ as a module.

    Its default artifact dir is ./artifacts next to itself, which does not exist,
    so point WATCHNEXT_ARTIFACT_DIR at the real kit artifacts first.
    """
    backup = WORKSPACE_ROOT / "_backup_original" / "recommender.py"
    if not backup.exists():
        backup = KIT_ROOT / "model" / "engine.py"
    os.environ["WATCHNEXT_ARTIFACT_DIR"] = str(KIT_ROOT / "model" / "artifacts")
    spec = importlib.util.spec_from_file_location("original_recommender", str(backup))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ORIGINAL = _load_backed_up_original()



# --------------------------------------------------------------------------- #
# 1. Import surface
# --------------------------------------------------------------------------- #
def test_imports_from_repo_root():
    # All contract names importable from model.recommender
    import model.recommender as mod  # noqa: F401
    for name in ["load_model", "search_movies", "recommend_movies",
                 "EmptyQueryError", "InvalidFilterError", "InvalidYearError",
                 "InvalidTopNError", "InvalidGenreError", "MovieNotFoundError"]:
        assert hasattr(mod, name), name


# --------------------------------------------------------------------------- #
# 2. load_model idempotency
# --------------------------------------------------------------------------- #
def test_load_model_idempotent():
    load_model()
    first = _get_recommender()
    load_model()
    load_model()
    second = _get_recommender()
    assert first is second
    assert is_model_ready() is True


def _get_recommender():
    import model.recommender as mod
    return mod.get_recommender()


# --------------------------------------------------------------------------- #
# 3. Exact key set + types (search and recommend)
# --------------------------------------------------------------------------- #
def test_search_result_schema():
    load_model()
    results = search_movies("batman", limit=4)
    assert len(results) <= 4
    for m in results:
        assert set(m.keys()) == SHARED_KEYS, m.keys()
        assert m["similarity_score"] is None
        assert m["reason"] is None
        assert isinstance(m["genres"], list)


def test_recommend_result_schema():
    load_model()
    results = recommend_movies("Avatar", top_n=5)
    assert len(results) == 5
    for m in results:
        assert set(m.keys()) == SHARED_KEYS, m.keys()
        assert isinstance(m["movie_id"], (int, str))
        assert isinstance(m["title"], str) and m["title"]
        assert isinstance(m["genres"], list) and all(isinstance(g, str) for g in m["genres"])
        assert isinstance(m["overview"], str)
        assert m["poster_path"] is None or isinstance(m["poster_path"], str)
        assert m["similarity_score"] is None or isinstance(m["similarity_score"], (int, float))


# --------------------------------------------------------------------------- #
# 4. Typed exceptions
# --------------------------------------------------------------------------- #
def test_error_hierarchy():
    assert issubclass(InvalidYearError, InvalidFilterError)
    assert issubclass(InvalidTopNError, InvalidFilterError)
    assert issubclass(InvalidGenreError, InvalidFilterError)
    assert issubclass(EmptyQueryError, ValueError)
    assert issubclass(MovieNotFoundError, LookupError)


def test_empty_title_errors():
    load_model()
    for bad in ["", "   "]:
        with pytest.raises(EmptyQueryError):
            recommend_movies(bad)
    with pytest.raises(EmptyQueryError):
        search_movies("")


def test_unknown_movie_errors():
    load_model()
    with pytest.raises(MovieNotFoundError) as excinfo:
        recommend_movies("ZzzqNotAMovie")
    assert isinstance(excinfo.value.suggestions, list)
    with pytest.raises(MovieNotFoundError) as excinfo2:
        recommend_movies("Avatr")
    assert "Avatar" in excinfo2.value.suggestions


def test_invalid_year_errors():
    load_model()
    for bad in ["abc", 2015.5, True, ""]:
        with pytest.raises(InvalidYearError):
            recommend_movies("Avatar", year=bad)
    # valid exact year works
    recommend_movies("The Dark Knight", year=2008)


def test_invalid_top_n_errors():
    load_model()
    for bad in [0, -3, 51, 100, "abc", True, 2.5]:
        with pytest.raises(InvalidTopNError):
            recommend_movies("Avatar", top_n=bad)
    recommend_movies("Avatar", top_n=5)
    recommend_movies("Avatar", top_n=50)


def test_unknown_genre_error():
    load_model()
    with pytest.raises(InvalidGenreError):
        recommend_movies("Avatar", genre="NopeGenre")
    # InvalidGenreError is catchable as InvalidFilterError too
    try:
        recommend_movies("Avatar", genre="NopeGenre")
    except InvalidFilterError:
        pass
    else:
        raise AssertionError("expected InvalidFilterError catchable")


# --------------------------------------------------------------------------- #
# 5. JSON serializability + no NaN
# --------------------------------------------------------------------------- #
def test_results_json_serializable_and_no_nan():
    load_model()
    for title in REGRESSION_TITLES:
        results = recommend_movies(title, top_n=5)
        search_results = search_movies(title[:4], limit=3)
        for payload in [results, search_results]:
            json.dumps(payload)  # must not raise
            _check_no_nan(payload)


# --------------------------------------------------------------------------- #
# 6. Regression proof vs the backed-up original engine (hard rule 1)
# --------------------------------------------------------------------------- #
def test_regression_identical_to_original_engine_on_10_titles():
    load_model()
    for title in REGRESSION_TITLES:
        adapter = recommend_movies(title, top_n=5)
        # original engine called directly: title->title, top_n->n
        original = ORIGINAL.recommend_movies(title=title, n=5)
        assert _score_tuple(adapter) == _score_tuple(original), (
            f"regression mismatch for {title!r}\n adapter: {_score_tuple(adapter)}\n"
            f" original: {_score_tuple(original)}"
        )
        for m in adapter:
            assert isinstance(m["reason"], str)


def test_recommend_never_returns_itself():
    load_model()
    titles = [m["title"] for m in recommend_movies("Avatar", top_n=10)]
    assert "Avatar" not in titles


def test_results_le_top_n():
    load_model()
    for n in [1, 2, 3, 10]:
        results = recommend_movies("Interstellar", top_n=n)
        assert len(results) <= n

def _score_tuple(results):
    """Order + score signature, used for the regression proof."""
    return [(r["title"], r["similarity_score"]) for r in results]


def _check_no_nan(value, path=""):
    if isinstance(value, float) and math.isnan(value):
        raise AssertionError(f"NaN at {path}")
    if isinstance(value, dict):
        for k, v in value.items():
            _check_no_nan(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _check_no_nan(v, f"{path}[{i}]")