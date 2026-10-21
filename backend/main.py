"""
WatchNext backend API (FastAPI).
API contract: see README.md. Run: uvicorn backend.main:app --reload

Owns: request validation, HTTP mapping of ML errors, lifespan model warm-up.
Does NOT: compute or alter similarity (delegated to model.recommender).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from model.recommender import (  # noqa: E402  (imported from repo root)
    load_model,
    search_movies,
    recommend_movies,
    EmptyQueryError,
    InvalidFilterError,
    InvalidYearError,
    InvalidTopNError,
    InvalidGenreError,
    MovieNotFoundError,
)

log = logging.getLogger("watchnext.api")

DEFAULT_LIMIT = 10
DEFAULT_TOP_N = 5

_MODEL_READY = False


class ModelNotReadyError(RuntimeError):
    """Raised by endpoints when the ML model has not been loaded yet."""


def _require_ready() -> None:
    if not _MODEL_READY:
        raise ModelNotReadyError(
            "Recommendation model is not ready. load_model() must be called "
            "at startup (backend lifespan); check WATCHNEXT_ARTIFACT_DIR."
        )


def _error(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
    )


def _parse_optional_int(param: str, value: Optional[str], default: Optional[int]) -> Optional[int]:
    """Parse a nullable integer query param without raising FastAPI 422."""
    if value is None:
        return default
    text = value.strip()
    if not text:
        if param == "year":
            raise InvalidYearError("year must be an integer (release year).")
        raise InvalidTopNError(f"{param} must be an integer between 1 and 50.")
    try:
        return int(text)
    except ValueError:
        if param == "year":
            raise InvalidYearError("year must be an integer (release year).")
        raise InvalidTopNError(f"{param} must be an integer between 1 and 50.")


# --------------------------------------------------------------------------- #
# Error -> HTTP mapping (contract error body: {"detail": {"code", "message"}})
# --------------------------------------------------------------------------- #
def _handler(code: str, status_code: int):
    def handle(_request: Request, exc: Exception) -> JSONResponse:
        return _error(code, str(exc), status_code)
    return handle


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(EmptyQueryError, _handler("EMPTY_QUERY", 400))
    app.add_exception_handler(InvalidYearError, _handler("INVALID_YEAR", 400))
    app.add_exception_handler(InvalidTopNError, _handler("INVALID_TOP_N", 400))
    app.add_exception_handler(InvalidGenreError, _handler("INVALID_FILTER", 400))
    app.add_exception_handler(InvalidFilterError, _handler("INVALID_FILTER", 400))
    app.add_exception_handler(MovieNotFoundError, _handler("MOVIE_NOT_FOUND", 404))
    app.add_exception_handler(ModelNotReadyError, _handler("MODEL_NOT_READY", 503))
    app.add_exception_handler(FileNotFoundError, _handler("MODEL_NOT_READY", 503))

    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # All query params are parsed manually, so 422 should not occur;
        # keep a contract-safe fallback anyway.
        return _error("INVALID_FILTER", "Invalid request parameters.", 400)

    app.add_exception_handler(RequestValidationError, _validation_error)

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unexpected error in WatchNext API")
        return _error("INTERNAL_ERROR", "Internal server error.", 500)


# --------------------------------------------------------------------------- #
# Application factory: lifespan warms the model once at startup
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _MODEL_READY
    try:
        load_model()  # idempotent; loads artifacts into memory once
        _MODEL_READY = True
    except Exception:  # noqa: BLE001 - stay up, report not-ready via /health and 503s
        log.exception("Failed to load recommendation model at startup")
        _MODEL_READY = False
    yield


app = FastAPI(title="WatchNext API", version="1.0.0", lifespan=lifespan)
install_error_handlers(app)

_cors_origins = os.environ.get("WATCHNEXT_CORS_ORIGINS", "").strip()
if _cors_origins:  # CORS off by default; opt in via comma-separated origin list
    origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log.info("CORS enabled for origins: %s", origins)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> Dict[str, Any]:
    """Health check including model readiness."""
    return {"status": "ok" if _MODEL_READY else "not ready", "model_ready": _MODEL_READY}


@app.get("/movies/search")
def search(q: Optional[str] = None, limit: Optional[str] = None) -> Dict[str, Any]:
    """Case-insensitive title search.

    Query params: q (required), limit (optional, default 10).
    """
    _require_ready()
    if not q or not q.strip():
        raise EmptyQueryError("Search query 'q' is required and must not be empty.")
    lim = _parse_optional_int("limit", limit, DEFAULT_LIMIT)
    results = search_movies(q.strip(), limit=lim)
    return {"query": q.strip(), "results": results}


@app.get("/recommend")
def recommend(
    title: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    top_n: Optional[str] = None,
) -> Dict[str, Any]:
    """Content-based recommendations for a movie title.

    Query params: title (required), genre (optional), year (optional, exact),
    top_n (optional, default 5, max 50).
    """
    _require_ready()
    if not title or not title.strip():
        raise EmptyQueryError("Recommendation 'title' is required and must not be empty.")
    top_n_i = _parse_optional_int("top_n", top_n, DEFAULT_TOP_N)
    year_i = _parse_optional_int("year", year, None)
    recommendations = recommend_movies(
        movie_title=title.strip(),
        genre=genre,
        year=year_i,
        top_n=top_n_i,
    )
    return {"query": title.strip(), "recommendations": recommendations}
