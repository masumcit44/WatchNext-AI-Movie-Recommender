
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# --------------------------------------------------
# ML MODEL INTEGRATION
# --------------------------------------------------

recommender = None
MODEL_READY = False
MODEL_ERROR = None


def initialize_model():
    """Load the ML recommender when the backend starts."""
    global recommender, MODEL_READY, MODEL_ERROR

    try:
        recommender = import_module("model.recommender")
        recommender.load_model()

        MODEL_READY = True
        MODEL_ERROR = None
        print("Movie recommendation model loaded successfully.")

    except Exception as exc:
        MODEL_READY = False
        MODEL_ERROR = str(exc)
        print(f"Model is not ready: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_model()
    yield


app = FastAPI(
    title="WatchNext API",
    description="AI-powered movie recommendation backend.",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# ERROR RESPONSE HELPER
# --------------------------------------------------

def error_response(
    status_code: int,
    code: str,
    message: str,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "code": code,
                "message": message,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return error_response(
        400,
        "INVALID_PARAMETERS",
        "One or more request parameters are invalid.",
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "WatchNext API",
        "model_ready": MODEL_READY,
    }


# --------------------------------------------------
# MOVIE SEARCH
# --------------------------------------------------

@app.get("/movies/search")
def search_movies(
    q: str = Query(..., description="Movie title to search"),
    limit: int = Query(10, ge=1, le=50),
):
    query = q.strip()

    if not query:
        return error_response(
            400,
            "EMPTY_QUERY",
            "Search query cannot be empty.",
        )

    if not MODEL_READY or recommender is None:
        return error_response(
            503,
            "MODEL_NOT_READY",
            "The movie recommendation model is not ready.",
        )

    try:
        results = recommender.search_movies(
            query=query,
            limit=limit,
        )

        return {
            "query": query,
            "results": results,
        }

    except Exception:
        return error_response(
            500,
            "INTERNAL_ERROR",
            "An unexpected error occurred while searching movies.",
        )


# --------------------------------------------------
# MOVIE RECOMMENDATIONS
# --------------------------------------------------

@app.get("/recommend")
def recommend_movies(
    title: str = Query(..., description="Selected movie title"),
    genre: str | None = Query(None),
    year: int | None = Query(None, ge=1888, le=2100),
    top_n: int = Query(5, ge=1, le=20),
):
    movie_title = title.strip()

    if not movie_title:
        return error_response(
            400,
            "EMPTY_QUERY",
            "Movie title cannot be empty.",
        )

    if not MODEL_READY or recommender is None:
        return error_response(
            503,
            "MODEL_NOT_READY",
            "The movie recommendation model is not ready.",
        )

    try:
        recommendations = recommender.recommend_movies(
            movie_title=movie_title,
            genre=genre,
            year=year,
            top_n=top_n,
        )

        if not recommendations:
            return error_response(
                404,
                "MOVIE_NOT_FOUND",
                "No matching movie was found.",
            )

        return {
            "query": movie_title,
                
            "recommendations": recommendations,
        }

    except ValueError:
        return error_response(
            404,
            "MOVIE_NOT_FOUND",
            "No matching movie was found.",
        )

    except Exception:
        return error_response(
            500,
            "INTERNAL_ERROR",
            "An unexpected error occurred while generating recommendations.",
        )
        