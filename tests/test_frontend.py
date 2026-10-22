"""
Frontend tests using streamlit.testing.v1.AppTest with mocked requests.
"""
import json
from unittest.mock import patch, Mock
import pytest

# Test data matching the API contract
SAMPLE_SEARCH_RESULTS = [
    {
        "movie_id": 157336,
        "title": "Interstellar",
        "genres": ["Adventure", "Drama", "Science Fiction"],
        "overview": "A team of explorers travels beyond this galaxy...",
        "poster_path": None,
        "similarity_score": None,
        "reason": None,
    },
    {
        "movie_id": 27203,
        "title": "Inception",
        "genres": ["Action", "Science Fiction", "Thriller"],
        "overview": "A skilled thief enters dreams to steal secrets...",
        "poster_path": None,
        "similarity_score": None,
        "reason": None,
    },
]

SAMPLE_RECOMMENDATIONS = [
    {
        "movie_id": 27203,
        "title": "Inception",
        "genres": ["Action", "Science Fiction", "Thriller"],
        "overview": "A skilled thief enters dreams to steal secrets...",
        "poster_path": "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
        "similarity_score": 0.8234,
        "reason": "Shares genres: Science Fiction, Thriller; keywords: dreams, mind; cast: Leonardo DiCaprio.",
    },
    {
        "movie_id": 157336,
        "title": "Interstellar",
        "genres": ["Adventure", "Drama", "Science Fiction"],
        "overview": "A team of explorers travels beyond this galaxy...",
        "poster_path": None,
        "similarity_score": 0.7562,
        "reason": "Shares genres: Adventure, Science Fiction; keywords: space, time; cast: Matthew McConaughey.",
    },
    {
        "movie_id": 12345,
        "title": "The Martian",
        "genres": ["Adventure", "Drama", "Science Fiction"],
        "overview": "An astronaut stranded on Mars...",
        "poster_path": "/5aGhaIH3OnhX4CfewX6b9YQnLY7.jpg",
        "similarity_score": 0.6891,
        "reason": "Shares genres: Adventure, Science Fiction; keywords: space, survival; cast: Matt Damon.",
    },
    {
        "movie_id": 67890,
        "title": "Gravity",
        "genres": ["Drama", "Science Fiction", "Thriller"],
        "overview": "Two astronauts stranded in space...",
        "poster_path": None,
        "similarity_score": 0.6234,
        "reason": "Shares genres: Science Fiction, Thriller; keywords: space, survival; cast: Sandra Bullock.",
    },
    {
        "movie_id": 11111,
        "title": "Ad Astra",
        "genres": ["Adventure", "Mystery", "Science Fiction"],
        "overview": "An astronaut travels to the edge of the solar system...",
        "poster_path": None,
        "similarity_score": 0.5876,
        "reason": "Shares genres: Adventure, Science Fiction; keywords: space, father; cast: Brad Pitt.",
    },
]


def make_mock_response(data, status_code=200):
    """Create a mock response object."""
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = Mock()
    if status_code >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock


def test_render_movie_card_html_builder():
    """Pure function test for the card HTML builder."""
    from frontend.app import render_movie_card_html

    movie = {
        "movie_id": 123,
        "title": "Test Movie",
        "genres": ["Action", "Sci-Fi"],
        "overview": "A test overview.",
        "poster_path": "/test.jpg",
        "similarity_score": 0.75,
        "reason": "Shares Action and Sci-Fi genres.",
    }

    html = render_movie_card_html(movie, 1)

    # Check all expected elements
    assert "movie-card" in html
    assert "Test Movie" in html
    assert "Action" in html
    assert "Sci-Fi" in html
    assert "A test overview." in html
    assert "Shares Action and Sci-Fi genres." in html
    assert "Similarity score 0.75" in html
    assert "#1" in html
    # Poster URL uses the TMDB w342 size
    assert "https://image.tmdb.org/t/p/w342/test.jpg" in html
    # New structure: poster box with layered placeholder + image
    assert "movie-poster-box" in html
    assert "movie-poster-img" in html
    assert "movie-poster-placeholder" in html  # Layered placeholder + image

    # The spec forbids an onerror handler: the placeholder layer is the fallback
    assert "onerror" not in html.lower()

    # Test with null poster
    movie_no_poster = {**movie, "poster_path": None}
    html_no_poster = render_movie_card_html(movie_no_poster, 2)
    assert "movie-poster-box" in html_no_poster
    assert "movie-poster-placeholder" in html_no_poster
    assert "movie-poster-img" not in html_no_poster
    assert "https://image.tmdb.org/t/p/w342" not in html_no_poster

    # Test with empty string poster
    movie_empty_poster = {**movie, "poster_path": ""}
    html_empty_poster = render_movie_card_html(movie_empty_poster, 3)
    assert "movie-poster-placeholder" in html_empty_poster
    assert "movie-poster-img" not in html_empty_poster

    # A poster_path without a leading "/" is not a valid TMDB path
    movie_bad_poster = {**movie, "poster_path": "test.jpg"}
    html_bad_poster = render_movie_card_html(movie_bad_poster, 4)
    assert "image.tmdb.org" not in html_bad_poster
    assert "movie-poster-placeholder" in html_bad_poster

    # Test escaping - HTML should be escaped in output
    movie_xss = {**movie, "title": "<script>alert(1)</script>", "overview": "<b>bold</b>"}
    html_xss = render_movie_card_html(movie_xss, 4)
    # The HTML should contain escaped versions (html.escape converts < to < etc.)
    # Raw HTML tags should NOT appear
    assert "<script>" not in html_xss
    assert "<b>" not in html_xss


@patch("frontend.app.requests.get")
def test_search_movies_cached(mock_get):
    """Test the cached search function directly."""
    from frontend.app import search_movies_cached

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": SAMPLE_SEARCH_RESULTS}
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    results = search_movies_cached("interstellar", limit=10)
    assert len(results) == 2
    assert results[0]["title"] == "Interstellar"
    assert results[1]["title"] == "Inception"

    # Second call should use cache
    results2 = search_movies_cached("interstellar", limit=10)
    assert results2 == results
    # But mock should only be called once due to cache
    assert mock_get.call_count == 1


@patch("frontend.app.requests.get")
def test_recommend_movies_api(mock_get):
    """Test the recommend API function directly."""
    from frontend.app import recommend_movies_api

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"query": "Interstellar", "recommendations": SAMPLE_RECOMMENDATIONS}
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    data = recommend_movies_api("Interstellar", genre="Action", year=2014, top_n=5)
    assert data["query"] == "Interstellar"
    assert len(data["recommendations"]) == 5

    # Check params passed correctly
    call_args = mock_get.call_args
    params = call_args[1]["params"]
    assert params["title"] == "Interstellar"
    assert params["genre"] == "Action"
    assert params["year"] == 2014
    assert params["top_n"] == 5


@patch("frontend.app.requests.get")
def test_recommend_movies_api_no_genre_filter(mock_get):
    """Test recommend API without genre filter."""
    from frontend.app import recommend_movies_api

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"query": "Avatar", "recommendations": SAMPLE_RECOMMENDATIONS}
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    data = recommend_movies_api("Avatar", genre="All genres", year=None, top_n=5)
    assert data["query"] == "Avatar"

    call_args = mock_get.call_args
    params = call_args[1]["params"]
    assert "genre" not in params
    assert "year" not in params


@patch("frontend.app.requests.get")
def test_api_connection_error(mock_get):
    """Test connection error handling."""
    import requests
    from frontend.app import _api_get

    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with pytest.raises(RuntimeError) as excinfo:
        _api_get("/test", {})
    assert "Cannot reach the WatchNext API" in str(excinfo.value)


@patch("frontend.app.requests.get")
def test_api_timeout(mock_get):
    """Test timeout handling."""
    import requests
    from frontend.app import _api_get

    mock_get.side_effect = requests.exceptions.Timeout("Timeout")

    with pytest.raises(RuntimeError) as excinfo:
        _api_get("/test", {})
    assert "timed out" in str(excinfo.value)


@patch("frontend.app.requests.get")
def test_api_http_error(mock_get):
    """Test HTTP error handling with JSON response."""
    import requests
    from frontend.app import _api_get

    mock_resp = Mock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"detail": {"code": "MOVIE_NOT_FOUND", "message": "Movie not found: 'Zzzq'. Did you mean: Avatar?"}}
    mock_get.return_value = mock_resp

    http_error = requests.exceptions.HTTPError("404")
    http_error.response = mock_resp
    mock_resp.raise_for_status.side_effect = http_error

    with pytest.raises(RuntimeError) as excinfo:
        _api_get("/test", {})
    assert "Did you mean: Avatar" in str(excinfo.value)


@patch("frontend.app.requests.get")
def test_api_invalid_json(mock_get):
    """Test invalid JSON response."""
    from frontend.app import _api_get

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError) as excinfo:
        _api_get("/test", {})
    assert "Invalid JSON response" in str(excinfo.value)


@patch("frontend.app.requests.get")
def test_search_movies_cached_empty_query(mock_get):
    """Test search with empty query returns empty list without calling API."""
    from frontend.app import search_movies_cached

    results = search_movies_cached("", limit=10)
    assert results == []
    mock_get.assert_not_called()

    results = search_movies_cached("   ", limit=10)
    assert results == []
    mock_get.assert_not_called()