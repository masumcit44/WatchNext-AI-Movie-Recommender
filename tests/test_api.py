
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "WatchNext API"


def test_search_requires_query():
    response = client.get("/movies/search")

    assert response.status_code == 400


def test_search_rejects_empty_query():
    response = client.get("/movies/search?q=%20%20")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "EMPTY_QUERY"


def test_search_rejects_invalid_limit():
    response = client.get("/movies/search?q=Avatar&limit=0")

    assert response.status_code == 400


def test_recommend_requires_title():
    response = client.get("/recommend")

    assert response.status_code == 400


def test_recommend_rejects_invalid_top_n():
    response = client.get("/recommend?title=Avatar&top_n=0")

    assert response.status_code == 400


def test_recommend_rejects_invalid_year():
    response = client.get("/recommend?title=Avatar&year=1800")

    assert response.status_code == 400



def test_search_returns_model_not_ready():
    from backend import main

    if main.MODEL_READY:
        return

    response = client.get("/movies/search?q=Avatar")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_NOT_READY"


def test_recommend_returns_model_not_ready():
    from backend import main

    if main.MODEL_READY:
        return

    response = client.get("/recommend?title=Avatar")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_NOT_READY"
