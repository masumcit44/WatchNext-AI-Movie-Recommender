"""
Tests for the poster-first movie cards.

Spec:
  * all five results in one CSS grid with equal heights
  * poster box fixed at 2:3 with a placeholder layer and an absolutely
    positioned <img> on top, and NO onerror handler
  * TMDB image URL = https://image.tmdb.org/t/p/w342 + poster_path, only when
    poster_path is a non-empty string starting with "/"
  * html.escape applied to every API string
  * TMDB attribution in the footer
  * no star rating and no release year (the API provides neither)
"""
import re

import pytest


def _movie(**overrides):
    base = {
        "movie_id": 1,
        "title": "Interstellar",
        "genres": ["Adventure", "Drama", "Science Fiction", "Thriller"],
        "overview": "A team of explorers travels beyond this galaxy.",
        "poster_path": None,
        "similarity_score": 0.8123,
        "reason": "Shares genres: Science Fiction; keywords: space, time.",
    }
    base.update(overrides)
    return base


@pytest.fixture
def card():
    from frontend.app import render_movie_card_html

    return render_movie_card_html(_movie(), 1)


# ── Grid ────────────────────────────────────────────────────────────────────
def test_all_five_results_share_one_grid():
    from frontend.app import render_results_grid

    movies = [_movie(movie_id=i, title=f"Movie {i}") for i in range(5)]
    grid = render_results_grid(movies)

    assert grid.count('class="results-grid"') == 1
    assert grid.count('class="movie-card"') == 5
    assert grid.count("movie-poster-box") == 5


def test_grid_css_uses_equal_height_stretch():
    from frontend.app import render_results_grid  # noqa: F401  (ensures import works)
    import inspect

    import frontend.app as app_module

    source = inspect.getsource(app_module)
    grid_css = re.search(r"\.results-grid\s*\{([^}]*)\}", source)
    assert grid_css, "the .results-grid CSS rule must exist"
    assert "grid-template-columns" in grid_css.group(1)
    assert "align-items: stretch" in grid_css.group(1)


def test_poster_box_is_fixed_2_3_ratio():
    import inspect

    import frontend.app as app_module

    source = inspect.getsource(app_module)
    box_css = re.search(r"\.movie-poster-box\s*\{([^}]*)\}", source)
    assert box_css, "the .movie-poster-box CSS rule must exist"
    assert "aspect-ratio: 2 / 3" in box_css.group(1)
    assert "position: relative" in box_css.group(1)


def test_poster_img_is_absolutely_positioned_over_placeholder():
    import inspect

    import frontend.app as app_module

    source = inspect.getsource(app_module)
    img_css = re.search(r"\.movie-poster-img\s*\{([^}]*)\}", source)
    assert img_css, "the .movie-poster-img CSS rule must exist"
    assert "position: absolute" in img_css.group(1)
    assert "inset: 0" in img_css.group(1)


# ── Poster URL rules ────────────────────────────────────────────────────────
def test_poster_url_is_w342_plus_raw_path():
    from frontend.app import render_movie_card_html

    html = render_movie_card_html(_movie(poster_path="/abc123.jpg"), 1)
    assert "https://image.tmdb.org/t/p/w342/abc123.jpg" in html


@pytest.mark.parametrize("bad", [None, "", "   ", "abc.jpg", 123, True, [], {}])
def test_invalid_poster_path_yields_placeholder_only(bad):
    from frontend.app import render_movie_card_html

    html = render_movie_card_html(_movie(poster_path=bad), 1)
    assert "image.tmdb.org" not in html
    assert "<img" not in html
    assert "movie-poster-placeholder" in html


def test_poster_uses_only_w342_size():
    from frontend.app import render_movie_card_html

    html = render_movie_card_html(_movie(poster_path="/abc.jpg"), 1)
    urls = re.findall(r"https://image\.tmdb\.org/t/p/\w+", html)
    assert urls, "a TMDB image URL must be produced"
    assert all("/w342" in u for u in urls)


# ── No onerror ──────────────────────────────────────────────────────────────
def test_no_onerror_anywhere_in_card(card):
    assert "onerror" not in card.lower()


def test_placeholder_is_present_under_the_image():
    from frontend.app import render_movie_card_html

    html = render_movie_card_html(_movie(poster_path="/abc.jpg"), 1)
    # The placeholder div comes before the <img> in the DOM, so it sits
    # underneath the absolutely positioned image.
    assert html.index("movie-poster-placeholder") < html.index("<img")


# ── Escaping ────────────────────────────────────────────────────────────────
def test_every_api_string_is_escaped():
    from frontend.app import render_movie_card_html

    movie = _movie(
        title='<script>alert("xss")</script>',
        overview="Bad <b>html</b>",
        reason="Because <i>this</i>",
        genres=["Action & More"],
    )
    html = render_movie_card_html(movie, 1)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Bad &lt;b&gt;html&lt;/b&gt;" in html
    assert "Because &lt;i&gt;this&lt;/i&gt;" in html
    assert "Action &amp; More" in html


# ── No invented data ────────────────────────────────────────────────────────
def test_card_has_no_rating_or_year():
    from frontend.app import render_movie_card_html

    html = render_movie_card_html(_movie(), 1)
    assert "★" not in html
    assert "⭐" not in html
    assert "release_date" not in html
    assert "Release year" not in html
    assert "vote_average" not in html


# ── Footer attribution ──────────────────────────────────────────────────────
def test_footer_contains_tmdb_attribution():
    import inspect

    import frontend.app as app_module

    source = inspect.getsource(app_module)
    assert "courtesy of TMDB" in source
    assert "not endorsed or certified by TMDB" in source
