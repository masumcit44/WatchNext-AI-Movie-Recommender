import os
import random
import html
import requests
import streamlit as st
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 10.0

st.set_page_config(
    page_title="WatchNext | AI Movie Discovery",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Static genre list matching the TMDB 5000 dataset ───
GENRES = [
    "All genres",
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Family", "Fantasy", "Foreign",
    "History", "Horror", "Music", "Mystery", "Romance",
    "Science Fiction", "TV Movie", "Thriller", "War", "Western",
]

# ─── Seed words for "Surprise Me" ───
SURPRISE_SEEDS = ["the", "star", "love", "man", "war", "night", "city", "dark"]

# ─── Fixed navigation bar ───
# The stylesheet MUST be wrapped in a <style> tag: Streamlit renders bare CSS
# as paragraph text, which silently makes every rule inert.
NAV_CSS = """
<style>
html { scroll-behavior: smooth; }
body { overflow-x: hidden; }

/* One fixed, translucent-blur header. z-index 900 keeps it above page content
   but below Streamlit's own popovers (BaseWeb renders those far higher). */
header.wn-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 64px;
  z-index: 900;
  background: rgba(9, 7, 17, 0.82);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(205, 173, 255, 0.14);
}
header.wn-nav .wn-nav-inner {
  max-width: 1420px;
  margin: 0 auto;
  height: 100%;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Brand is the single word "WatchNext" (accent on the trailing letters) */
header.wn-nav .wn-brand {
  display: flex;
  align-items: baseline;
  gap: .55rem;
  text-decoration: none;
  color: #f8f5ff;
  min-width: 0;
}
header.wn-nav .wn-brand-name {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: -0.04em;
  line-height: 1.2;
  white-space: nowrap;
  background: linear-gradient(92deg, #f8f5ff 0%, #f8f5ff 52%, #c084fc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
header.wn-nav .wn-brand-sub {
  font-family: 'DM Sans', sans-serif;
  font-size: .58rem;
  font-weight: 500;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: #a99eb8;
  white-space: nowrap;
}

header.wn-nav .wn-nav-links {
  display: flex;
  gap: 1rem;
  list-style: none;
  margin: 0 0 0 auto;
  padding: 0;
  min-width: 0;
}
header.wn-nav .wn-nav-links a {
  color: #d9c8f5;
  text-decoration: none;
  font-family: 'DM Sans', sans-serif;
  font-size: .82rem;
  font-weight: 500;
  padding-bottom: .15rem;
  border-bottom: 2px solid transparent;
  transition: color .15s ease, border-color .15s ease;
  white-space: nowrap;
}
header.wn-nav .wn-nav-links a:hover {
  color: #f0e6ff;
  border-bottom-color: #a78bfa;
}
header.wn-nav .wn-nav-links a:focus-visible {
  outline: 2px solid #a78bfa;
  outline-offset: 2px;
}

header.wn-nav .wn-nav-tag {
  background: rgba(168, 85, 247, .12);
  border: 1px solid rgba(192, 132, 252, .3);
  color: #e3d6f3;
  font-size: .68rem;
  font-weight: 600;
  padding: .3rem .75rem;
  border-radius: 99px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Page content clears the fixed bar */
.block-container { padding-top: 88px !important; }
html { scroll-padding-top: 80px; }
#wn-search, #wn-results, #wn-about { scroll-margin-top: 80px; }

/* Hide Streamlit's own header/toolbar so nothing overlaps the fixed nav */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 0; min-height: 0;
  visibility: hidden;
  overflow: hidden;
  z-index: 899;
}

@media (max-width: 700px) {
  header.wn-nav { height: 56px; }
  header.wn-nav .wn-nav-inner { gap: .6rem; padding: 0 .75rem; }
  header.wn-nav .wn-brand-sub,
  header.wn-nav .wn-nav-tag { display: none; }
  header.wn-nav .wn-nav-links {
    gap: .65rem;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }
  header.wn-nav .wn-nav-links::-webkit-scrollbar { display: none; }
  header.wn-nav .wn-nav-links a { font-size: .76rem; }
}
@media (max-width: 420px) {
  header.wn-nav .wn-nav-inner { padding: 0 .6rem; }
  header.wn-nav .wn-brand-name { font-size: 1.02rem; }
  header.wn-nav .wn-nav-links { gap: .55rem; }
  header.wn-nav .wn-nav-links a { font-size: .72rem; }
}
</style>
"""


def build_nav() -> str:
    """Return the fixed navigation bar: stylesheet + markup, served together.

    CSS and HTML are emitted in a single st.markdown call so the bar can never
    appear without the rules that position it.
    """
    # NOTE: build the link list as a LIST. Adjacent f-strings would be
    # concatenated into one string and " ".join() would split it per character.
    links = " ".join(
        [
            '<li><a href="#wn-search">Search</a></li>',
            '<li><a href="#wn-results">Results</a></li>',
            '<li><a href="#wn-about">About</a></li>',
        ]
    )
    return NAV_CSS + f"""
<header role="banner" class="wn-nav">
  <nav class="wn-nav-inner" aria-label="Primary">
    <a class="wn-brand" href="#wn-search" aria-label="WatchNext home">
      <span class="wn-brand-name">WatchNext</span>
      <span class="wn-brand-sub">AI MOVIE DISCOVERY</span>
    </a>
    <ul class="wn-nav-links">
      {links}
    </ul>
    <div class="wn-nav-tag">Find your next favorite movie</div>
  </nav>
</header>
"""


# ─── Custom CSS - poster-first cards ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { 
    --bg:#090711; 
    --panel:#131020; 
    --purple:#a855f7; 
    --lav:#d5a8ff; 
    --muted:#aaa0bc; 
    --text:#f8f5ff;
    --label:#cbbfe0;
    --card-bg:#131020;
    --border:#c8a5ff;
}
html, body, [data-testid="stAppViewContainer"] { 
    background:var(--bg); 
    color:var(--text); 
    font-family:'DM Sans',sans-serif; 
}
[data-testid="stHeader"] { 
    background:rgba(9,7,17,.88); 
}
[data-testid="stAppViewContainer"] > .main { 
    background:radial-gradient(ellipse at 80% 0%,rgba(113,48,173,.15),transparent 35%),var(--bg); 
}
.block-container { 
    max-width:1420px; 
    padding-top:3.5rem; 
    padding-bottom:3rem; 
}
h1,h2,h3 { 
    font-family:'Space Grotesk',sans-serif !important; 
    letter-spacing:-.04em; 
    color:#fff; 
}
a { color:#d5a8ff !important; }

/* Hero */
.hero { 
    position:relative; 
    overflow:hidden; 
    border:1px solid rgba(196,148,255,.22); 
    border-radius:22px; 
    padding:clamp(1.4rem,4vw,3.4rem); 
    margin-bottom:1.7rem;
    background:linear-gradient(100deg,rgba(12,9,22,.98) 0%,rgba(17,10,30,.93) 53%,rgba(39,16,62,.67) 100%),radial-gradient(circle at 83% 35%,rgba(168,85,247,.5),transparent 36%); 
    box-shadow:0 18px 70px rgba(0,0,0,.18); 
}
.hero:after { 
    content:"✦"; 
    position:absolute; 
    right:8%; 
    top:3%; 
    font-size:clamp(7rem,20vw,16rem); 
    line-height:1; 
    color:rgba(196,132,252,.08); 
    pointer-events:none; 
}
.eyebrow { 
    color:#c084fc; 
    text-transform:uppercase; 
    letter-spacing:.18em; 
    font-size:.68rem; 
    font-weight:700; 
}
.hero h1 { 
    font-size:clamp(2.3rem,5vw,4.4rem); 
    line-height:1.02; 
    margin:.7rem 0 1rem; 
    max-width:800px; 
}
.hero h1 span { color:#c084fc; }
.hero p { color:#c6bdd5; max-width:610px; font-size:1rem; line-height:1.75; }
.stat-row { display:flex; gap:2rem; flex-wrap:wrap; margin-top:1.5rem; }
.stat { border-left:2px solid #a855f7; padding-left:.75rem; }
.stat strong { display:block; font-size:1.15rem; color:#fff; }
.stat small { color:#a99eb8; font-size:.72rem; }

/* Panel / filter container */
.filter-panel { 
    background:linear-gradient(145deg,rgba(25,19,40,.94),rgba(14,11,24,.96)); 
    border:1px solid rgba(201,163,255,.16); 
    border-radius:16px; 
    padding:1rem; 
    height:100%; 
}
.panel-title { 
    font-family:'Space Grotesk',sans-serif; 
    font-size:1.1rem; 
    font-weight:700; 
    margin-bottom:.25rem; 
}
.panel-subtitle { 
    color:#a99eb8; 
    font-size:.8rem; 
    margin-bottom:1rem; 
}

/* Section head */
.section-head { 
    display:flex; 
    align-items:end; 
    justify-content:space-between; 
    gap:1rem; 
    margin:1.8rem 0 1rem; 
}
.section-head h2 { margin:0; font-size:1.55rem; }
.section-head p { margin:.3rem 0 0; color:#a99eb8; font-size:.82rem; }

/* Input styling - dark theme */
div[data-testid="stTextInput"] input, 
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div, 
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
div[data-testid="stNumberInput"] input { 
    background:#0d0a17 !important; 
    color:#f8f5ff !important; 
    border-color:rgba(197,156,255,.28) !important; 
    border-radius:10px !important; 
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus { 
    box-shadow:0 0 0 1px #a855f7 !important; 
    outline: none;
}
/* Number input buttons */
div[data-testid="stNumberInput"] button { 
    background:#0d0a17 !important; 
    color:#f8f5ff !important; 
    border-color:rgba(197,156,255,.28) !important; 
}
div[data-testid="stNumberInput"] button:hover { 
    background:#1a1528 !important; 
    border-color:#a855f7 !important; 
}

/* Label contrast */
label[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] > div {
    color: var(--label) !important;
    font-size: .78rem !important;
    font-weight: 500 !important;
}

/* Buttons */
.stButton > button { 
    border-radius:10px; 
    border:1px solid rgba(192,132,252,.35); 
    background:linear-gradient(110deg,#963ee5,#7131c9); 
    color:white; 
    font-weight:700; 
    min-height:2.65rem; 
    transition:all .15s ease; 
}
.stButton > button:hover { 
    border-color:#d4a4ff; 
    box-shadow:0 0 22px rgba(168,85,247,.25); 
    color:#fff; 
    transform:translateY(-1px); 
}
.stButton > button[kind="secondary"] { 
    background:rgba(255,255,255,.035); 
    border-color:rgba(201,163,255,.2); 
    color:#e9ddf7; 
}
.stButton > button[kind="secondary"]:hover {
    border-color:#d4a4ff;
    background:rgba(168,85,247,.15);
    color:#fff;
}

/* Active filter pills in results header */
.active-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.75rem;
    margin-bottom: 1rem;
}
.active-filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.75rem;
    background: rgba(168,85,247,.15);
    border: 1px solid rgba(192,132,252,.3);
    border-radius: 99px;
    font-size: 0.72rem;
    color: var(--lav);
    font-weight: 500;
}
.active-filter-pill button {
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 0;
    font-size: 0.9em;
    line-height: 1;
    opacity: 0.7;
}
.active-filter-pill button:hover {
    opacity: 1;
    color: #ff6b6b;
}
.clear-filters-btn {
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(192,132,252,.2) !important;
    color: var(--lav) !important;
    font-size: 0.72rem !important;
    padding: 0.25rem 0.75rem !important;
    border-radius: 99px !important;
    min-height: auto !important;
    font-weight: 500 !important;
}
.clear-filters-btn:hover {
    background: rgba(168,85,247,.15) !important;
    border-color: rgba(192,132,252,.4) !important;
    color: #fff !important;
}

/* Results grid */
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1.2rem;
    align-items: stretch;
}

/* Poster-first movie card */
.movie-card {
    display: flex;
    flex-direction: column;
    background: var(--card-bg);
    border: 1px solid rgba(200,165,255,.16);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 10px 25px rgba(0,0,0,.12);
    height: 100%;
    min-height: 0;
}

/* Poster box - always 2:3 ratio */
.movie-poster-box {
    position: relative;
    width: 100%;
    aspect-ratio: 2 / 3;
    border-radius: 14px 14px 0 0;
    overflow: hidden;
    background: radial-gradient(circle at 50% 25%, #42205e, #171022 70%);
    flex-shrink: 0;
}
.movie-poster-img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    loading: lazy;
    opacity: 0;
    transition: opacity 0.3s ease;
}
.movie-poster-img.loaded {
    opacity: 1;
}
.movie-poster-placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    text-align: center;
    color: #c9a5ef;
    z-index: 1;
}
.movie-poster-placeholder .icon {
    font-size: 2.5rem;
    opacity: 0.6;
}
.movie-poster-placeholder .title {
    font-size: 0.7rem;
    font-weight: 600;
    max-width: 80%;
    line-height: 1.3;
    color: #d8c8f0;
}

/* Card content */
.movie-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    padding: 0.85rem;
    min-height: 0;
}
.movie-title-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
.movie-title {
    font-family: 'Space Grotesk', sans-serif;
    color: #fff;
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.3;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.movie-rank {
    color: #a99eb8;
    font-size: 0.72rem;
    font-weight: 500;
    white-space: nowrap;
    flex-shrink: 0;
}
.movie-genres {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.5rem;
}
.pill {
    display: inline-block;
    border: 1px solid rgba(192,132,252,.25);
    background: rgba(168,85,247,.1);
    color: #d8b8ff;
    padding: 0.18rem 0.5rem;
    border-radius: 99px;
    font-size: 0.62rem;
    font-weight: 500;
    white-space: nowrap;
}
.movie-overview {
    color: #bdb3cc;
    font-size: 0.75rem;
    line-height: 1.5;
    flex: 1;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 0.6rem;
}
.why-box {
    border-top: 1px solid rgba(201,163,255,.13);
    padding-top: 0.6rem;
    margin-top: auto;
    flex-shrink: 0;
}
.why-label {
    color: #c084fc;
    font-size: 0.6rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.why-text {
    color: #d9c7ef;
    font-size: 0.72rem;
    line-height: 1.5;
}
.match-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.75rem;
    padding: 0.2rem 0.5rem;
    background: rgba(52,211,153,.09);
    border: 1px solid rgba(52,211,153,.2);
    border-radius: 6px;
    font-size: 0.65rem;
    color: #b7f4d2;
    font-weight: 600;
    align-self: flex-start;
}

/* Helper text */
.helper {
    color: #a99eb8;
    font-size: 0.78rem;
}

/* Alerts */
div[data-testid="stAlert"] { 
    border-radius: 10px; 
}

/* Suggestion buttons */
.suggestions-box {
    margin-top: 1rem;
    padding: 1rem;
    background: rgba(168,85,247,.05);
    border: 1px solid rgba(192,132,252,.2);
    border-radius: 12px;
}
.suggestions-title {
    color: #c084fc;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.75rem;
}
.suggestion-btn {
    display: inline-block;
    margin: 0.25rem 0.5rem 0.25rem 0;
    padding: 0.4rem 0.85rem;
    background: rgba(168,85,247,.1);
    border: 1px solid rgba(192,132,252,.25);
    border-radius: 99px;
    color: #d8b8ff;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
}
.suggestion-btn:hover {
    background: rgba(168,85,247,.25);
    border-color: #d4a4ff;
    color: #fff;
    transform: translateY(-1px);
}

/* Footer */
footer { visibility: hidden; }
hr { border-color: rgba(201,163,255,.12) !important; }

@media(max-width:700px) {
    .block-container { padding-left:1rem; padding-right:1rem; }
    .brandbar { align-items:flex-start; flex-direction:column; gap:.45rem; }
    .hero { border-radius:16px; padding:1.3rem; }
    .hero h1 { font-size:2.35rem; }
    .stat-row { gap:1rem; }
    .section-head { align-items:flex-start; flex-direction:column; }
    .results-grid { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.9rem; }
}
</style>
""", unsafe_allow_html=True)


# ─── API helpers ───
def _api_get(endpoint: str, params: dict) -> dict:
    """Call backend API with timeout and friendly error handling."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot reach the WatchNext API at {BACKEND_URL}. Start it with `uvicorn backend.main:app --reload`.")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request to {BACKEND_URL} timed out after {REQUEST_TIMEOUT}s.")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", {}).get("message", str(e))
        except Exception:
            detail = str(e)
        raise RuntimeError(detail)
    except ValueError:
        raise RuntimeError(f"Invalid JSON response from {BACKEND_URL}.")


@st.cache_data(ttl=60, show_spinner=False)
def search_movies_cached(query: str, limit: int = 10) -> list[dict]:
    """Cached search for autocomplete."""
    if not query or not query.strip():
        return []
    data = _api_get("/movies/search", {"q": query.strip(), "limit": limit})
    return data.get("results", [])


def recommend_movies_api(title: str, genre: str | None = None, year: int | None = None, top_n: int = 5) -> dict:
    """Call /recommend endpoint."""
    params = {"title": title.strip(), "top_n": top_n}
    if genre and genre != "All genres":
        params["genre"] = genre
    if year is not None:
        params["year"] = year
    return _api_get("/recommend", params)


def render_results_grid(movies: list[dict]) -> str:
    """Render all movie cards as a single CSS grid HTML string."""
    cards_html = []
    for i, movie in enumerate(movies):
        cards_html.append(render_movie_card_html(movie, i + 1))
    return f'<div class="results-grid">{"".join(cards_html)}</div>'


def render_movie_card_html(movie: dict, index: int) -> str:
    """Build a single complete HTML string for one poster-first movie card."""
    title = html.escape(movie.get("title", ""))
    genres = movie.get("genres", [])
    overview = html.escape(movie.get("overview", "") or "")
    reason = html.escape(movie.get("reason", "") or "")
    similarity = movie.get("similarity_score")
    poster_path = movie.get("poster_path")

    # Genres as pills - show up to 3, then "+N"
    visible_genres = genres[:3]
    extra_count = len(genres) - 3
    genre_html = "".join(f'<span class="pill">{html.escape(g)}</span>' for g in visible_genres)
    if extra_count > 0:
        genre_html += f'<span class="pill">+{extra_count}</span>'

    # Poster box with layered placeholder + image.
    # The <img> is absolutely positioned ON TOP of the placeholder layer and
    # starts at opacity 0; the onload handler fades it in. If the image fails
    # to load, onload never fires, so the placeholder stays visible - no
    # onerror handler is needed (and none is used).
    if isinstance(poster_path, str) and poster_path.startswith("/"):
        poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
        poster_box = f"""
<div class="movie-poster-box">
    <div class="movie-poster-placeholder">
        <span class="icon">🎬</span>
        <span class="title">{title}</span>
    </div>
    <img class="movie-poster-img"
         src="{html.escape(poster_url, quote=True)}"
         alt="{title}"
         loading="lazy"
         onload="this.classList.add('loaded');">
</div>"""
    else:
        poster_box = f"""
<div class="movie-poster-box">
    <div class="movie-poster-placeholder" style="display:flex;">
        <span class="icon">🎬</span>
        <span class="title">{title}</span>
    </div>
</div>"""

    # Similarity score pill
    sim_html = ""
    if similarity is not None:
        sim_html = f'<div class="match-pill">Similarity score {similarity:.2f}</div>'

    return f"""
<div class="movie-card">
    {poster_box}
    <div class="movie-content">
        <div class="movie-title-row">
            <div class="movie-title" title="{title}">{title}</div>
            <div class="movie-rank">#{index}</div>
        </div>
        <div class="movie-genres">{genre_html}</div>
        <div class="movie-overview" title="{overview}">{overview}</div>
        <div class="why-box">
            <div class="why-label">✦ Why this match</div>
            <div class="why-text">{reason}</div>
        </div>
        {sim_html}
    </div>
</div>
"""


# ─── Fixed navigation bar ───
st.markdown(build_nav(), unsafe_allow_html=True)

st.markdown("""
<section class="hero">
  <div class="eyebrow">YOUR PERSONAL CINEMA · AI / ML HACKATHON</div>
  <h1>Less scrolling.<br><span>More great stories.</span></h1>
  <p>Tell WatchNext one movie you love. We'll find five movies with similar genres, themes, and storytelling — and explain why each one made the list.</p>
  <div class="stat-row">
    <div class="stat"><strong>5 picks</strong><small>Focused recommendations</small></div>
    <div class="stat"><strong>Explainable</strong><small>See why each movie fits</small></div>
    <div class="stat"><strong>TMDB 5000</strong><small>Real movie catalog</small></div>
  </div>
</section>
""", unsafe_allow_html=True)

# ─── Search and filter controls ───
st.markdown('<div id="wn-search" class="section-head"><div><div class="eyebrow">START WITH A FAVORITE</div><h2>What did you enjoy watching?</h2><p>Search the TMDB 5000 catalog or type a title directly.</p></div></div>', unsafe_allow_html=True)

c1, c2 = st.columns([2.3, 1], gap="large")
with c1:
    typed_title = st.text_input(
        "Movie title",
        placeholder="e.g. Interstellar",
        key="movie_search",
        help="Enter a movie title. As you type, matches from the TMDB 5000 catalog will appear below.",
    )
    # Autocomplete selectbox populated from cached search
    search_results = search_movies_cached(typed_title, limit=10) if typed_title else []
    select_options = ["— Choose a match —"] + [f'{m["title"]} ({", ".join(m.get("genres", [])[:3])})' for m in search_results]
    selected_label = st.selectbox("Or pick a match", select_options, index=0)
    st.caption("Type a title and press Enter to see matches")
with c2:
    with st.container(border=True):
        st.markdown('<div class="panel-title">Fine-tune your picks</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-subtitle">Optional filters apply to the recommended results.</div>', unsafe_allow_html=True)
        genre_filter = st.selectbox("Genre", GENRES, index=0)
        st.markdown('<div class="helper">Backend matches exact release year only. Leave empty for any year.</div>', unsafe_allow_html=True)
        year_input = st.number_input("Release year (exact)", min_value=1900, max_value=2030, value=None, step=1, format="%d")

b1, b2, spacer = st.columns([1.6, 1, 4])
with b1:
    find_clicked = st.button("✦  Find Similar Movies", type="primary", use_container_width=True)
with b2:
    surprise_clicked = st.button("🎲  Surprise Me", type="secondary", use_container_width=True)

# ─── Session state ───
if "results" not in st.session_state:
    st.session_state.results = None
if "source_title" not in st.session_state:
    st.session_state.source_title = None
if "source_movie" not in st.session_state:
    st.session_state.source_movie = None
if "active_filters" not in st.session_state:
    st.session_state.active_filters = {}
if "suggestions" not in st.session_state:
    st.session_state.suggestions = None

# ─── Helper functions ───
def normalize(text: str) -> str:
    """Normalize title for comparison."""
    import re
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

def clear_results():
    st.session_state.results = None
    st.session_state.source_title = None
    st.session_state.source_movie = None
    st.session_state.suggestions = None

def get_active_filter_pills() -> str:
    """Generate HTML for active filter pills with clear button."""
    pills = []
    if st.session_state.active_filters.get("genre") and st.session_state.active_filters["genre"] != "All genres":
        pills.append(f'<div class="active-filter-pill">Genre: {html.escape(st.session_state.active_filters["genre"])}<button onclick="this.parentElement.remove(); window.parent.postMessage({{type:\'clear_genre\'}}, \'*\');">×</button></div>')
    if st.session_state.active_filters.get("year"):
        pills.append(f'<div class="active-filter-pill">Year: {html.escape(str(st.session_state.active_filters["year"]))}<button onclick="this.parentElement.remove(); window.parent.postMessage({{type:\'clear_year\'}}, \'*\');">×</button></div>')
    if not pills:
        return ""
    return f'<div class="active-filters">{"".join(pills)}<button class="clear-filters-btn" onclick="window.parent.postMessage({{type:\'clear_all\'}}, \'*\');">Clear all filters</button></div>'


# ─── Action handlers ───
def handle_find():
    # Determine the title: dropdown selection takes priority, then typed text
    title = ""
    source = "dropdown" if selected_label != "— Choose a match —" else "typed"
    
    if selected_label != "— Choose a match —":
        # Extract title from "Title (Genre1, Genre2)" format
        title = selected_label.split(" (")[0]
    elif typed_title and typed_title.strip():
        title = typed_title.strip()
    else:
        st.warning("Please enter or select a movie first.")
        return

    # Track active filters
    active = {}
    if genre_filter != "All genres":
        active["genre"] = genre_filter
    if year_input is not None:
        active["year"] = year_input
    st.session_state.active_filters = active

    with st.spinner("Finding movies with similar genres and themes..."):
        try:
            data = recommend_movies_api(
                title, 
                genre_filter if genre_filter != "All genres" else None, 
                year_input if year_input else None, 
                5
            )
            st.session_state.source_title = data.get("query", title)
            st.session_state.results = data.get("recommendations", [])
            st.session_state.source_movie = None
            st.session_state.suggestions = None
            clear_results.__annotations__ = {}  # suppress warning
            if len(st.session_state.results) < 5 and st.session_state.results:
                st.info(f"Only {len(st.session_state.results)} recommendations match these filters. Widen the genre filter or remove the year filter to see more results.")
            elif not st.session_state.results:
                st.warning("No recommendations match the current filters. Try a wider filter range.")
        except RuntimeError as e:
            error_msg = str(e)
            st.session_state.results = None
            st.session_state.source_title = None
            st.session_state.suggestions = None
            
            # If 404 MOVIE_NOT_FOUND, get suggestions from search
            if "MOVIE_NOT_FOUND" in error_msg and "Did you mean" in error_msg:
                # Extract suggestions from error message or call search
                try:
                    search_data = _api_get("/movies/search", {"q": title, "limit": 10})
                    st.session_state.suggestions = search_data.get("results", [])[:5]
                except Exception:
                    pass
            
            st.error(error_msg)


def handle_suggestion_click(suggestion_title: str):
    """Handle click on a suggestion button."""
    st.session_state.active_filters = {}
    genre_filter = "All genres"  # reset genre
    year_input = None  # reset year
    
    with st.spinner("Finding movies with similar genres and themes..."):
        try:
            data = recommend_movies_api(suggestion_title, None, None, 5)
            st.session_state.source_title = data.get("query", suggestion_title)
            st.session_state.results = data.get("recommendations", [])
            st.session_state.source_movie = None
            st.session_state.suggestions = None
            if len(st.session_state.results) < 5 and st.session_state.results:
                st.info(f"Only {len(st.session_state.results)} recommendations match these filters. Widen the genre filter or remove the year filter to see more results.")
            elif not st.session_state.results:
                st.warning("No recommendations match the current filters. Try a wider filter range.")
        except RuntimeError as e:
            st.session_state.results = None
            st.session_state.source_title = None
            st.error(str(e))


def handle_surprise():
    with st.spinner("Picking a surprise movie..."):
        seed = random.choice(SURPRISE_SEEDS)
        try:
            search_data = _api_get("/movies/search", {"q": seed, "limit": 10})
            candidates = search_data.get("results", [])
            if not candidates:
                st.warning("Could not find a surprise movie. Try again.")
                return
            pick = random.choice(candidates)
            title = pick["title"]
            data = recommend_movies_api(title, genre_filter if genre_filter != "All genres" else None, year_input if year_input else None, 5)
            st.session_state.source_title = data.get("query", title)
            st.session_state.results = data.get("recommendations", [])
            st.session_state.source_movie = pick
            st.session_state.suggestions = None
            active = {}
            if genre_filter != "All genres":
                active["genre"] = genre_filter
            if year_input is not None:
                active["year"] = year_input
            st.session_state.active_filters = active
            if len(st.session_state.results) < 5 and st.session_state.results:
                st.info(f"Only {len(st.session_state.results)} recommendations match these filters. Widen the genre filter or remove the year filter to see more results.")
            elif not st.session_state.results:
                st.warning("No recommendations match the current filters. Try a wider filter range.")
        except RuntimeError as e:
            st.session_state.results = None
            st.session_state.source_title = None
            st.error(str(e))


if find_clicked:
    handle_find()
if surprise_clicked:
    handle_surprise()

# Handle suggestion clicks via query params (Streamlit workaround)
# Check for suggestion click in URL
if "suggestion_click" in st.query_params:
    suggestion_title = st.query_params["suggestion_click"]
    st.query_params.clear()
    handle_suggestion_click(suggestion_title)

# ─── Results display ───
if st.session_state.results is not None and st.session_state.source_title:
    source_title = st.session_state.source_title
    results = st.session_state.results
    st.markdown("---")
    st.markdown(
        f'<div id="wn-results" class="section-head"><div><div class="eyebrow">PERSONALIZED RESULTS</div><h2>Because you liked <span style="color:#c084fc">{html.escape(source_title)}</span></h2><p>Ranked by content-based TF-IDF cosine similarity on the TMDB 5000 dataset.</p></div><div class="match">✓ Recommendation run complete</div></div>',
        unsafe_allow_html=True,
    )
    
    # Active filters display
    filter_html = get_active_filter_pills()
    if filter_html:
        st.markdown(filter_html, unsafe_allow_html=True)
    
    st.markdown(
        f'<div class="panel" style="margin-bottom:1rem"><div class="panel-title">Why these recommendations?</div><div class="panel-subtitle" style="margin:0">Recommendations use content-based TF-IDF + cosine similarity on genres, keywords, cast, and director. The reason highlights shared genres, keywords, and cast members.</div></div>',
        unsafe_allow_html=True,
    )
    if results:
        st.markdown(render_results_grid(results), unsafe_allow_html=True)
    else:
        st.warning("No recommendations are available with the selected filters. Widen the filter range and try again.")

# ─── Suggestions display (for 404 or no exact match) ───
if st.session_state.suggestions:
    st.markdown("---")
    st.markdown(
        f'<div class="suggestions-box"><div class="suggestions-title">No exact match for “{html.escape(st.session_state.source_title or "")}”. Did you mean:</div>',
        unsafe_allow_html=True,
    )
    suggestion_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        with suggestion_cols[i]:
            title = sugg.get("title", "")
            genres = sugg.get("genres", [])
            if st.button(f"{title} ({', '.join(genres[:2])})", key=f"sugg_{i}", use_container_width=True):
                handle_suggestion_click(title)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div id="wn-about" style="display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap;color:#82778f;font-size:.72rem">
  <span><strong style="color:#c9b6df">WatchNext</strong> · Content-based movie recommender (TMDB 5000, TF-IDF + cosine similarity)</span>
  <span>Poster images courtesy of TMDB. This product uses TMDB data but is not endorsed or certified by TMDB. · Exact-year filter only · No personalization</span>
</div>
""", unsafe_allow_html=True)