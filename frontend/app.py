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

# ─── Custom CSS (unchanged visual design) ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --bg:#090711; --panel:#131020; --purple:#a855f7; --lav:#d5a8ff; --muted:#aaa0bc; }
html, body, [data-testid="stAppViewContainer"] { background:var(--bg); color:#f8f5ff; font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(9,7,17,.88); }
[data-testid="stAppViewContainer"] > .main { background:radial-gradient(ellipse at 80% 0%,rgba(113,48,173,.15),transparent 35%),var(--bg); }
.block-container { max-width:1420px; padding-top:1.1rem; padding-bottom:3rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.04em; color:#fff; }
a { color:#d5a8ff !important; }
.brandbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.35rem 0 1rem; border-bottom:1px solid rgba(205,173,255,.14); margin-bottom:1.3rem; }
.brand { display:flex; align-items:baseline; flex-wrap:wrap; gap:.55rem; min-width:0; font-family:'Space Grotesk',sans-serif; font-size:1.55rem; font-weight:700; letter-spacing:-.06em; line-height:1.4; }
.brand-name-accent { color:#c084fc; text-shadow:0 0 20px rgba(168,85,247,.5); }
.brand-subtitle { display:inline-block; color:#a99eb8; font-family:'DM Sans',sans-serif; font-size:.65rem; font-weight:500; letter-spacing:0; white-space:normal; }
.brand-tag { display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; max-width:100%; box-sizing:border-box; font-size:.72rem; line-height:1.45; color:#e3d6f3; border:1px solid rgba(192,132,252,.3); background:rgba(168,85,247,.08); padding:.55rem .85rem; border-radius:99px; white-space:normal; text-align:center; }
.hero { position:relative; overflow:hidden; border:1px solid rgba(196,148,255,.22); border-radius:22px; padding:clamp(1.4rem,4vw,3.4rem); margin-bottom:1.7rem;
background:linear-gradient(100deg,rgba(12,9,22,.98) 0%,rgba(17,10,30,.93) 53%,rgba(39,16,62,.67) 100%),radial-gradient(circle at 83% 35%,rgba(168,85,247,.5),transparent 36%); box-shadow:0 18px 70px rgba(0,0,0,.18); }
.hero:after { content:"✦"; position:absolute; right:8%; top:3%; font-size:clamp(7rem,20vw,16rem); line-height:1; color:rgba(196,132,252,.08); pointer-events:none; }
.eyebrow { color:#c084fc; text-transform:uppercase; letter-spacing:.18em; font-size:.68rem; font-weight:700; }
.hero h1 { font-size:clamp(2.3rem,5vw,4.4rem); line-height:1.02; margin:.7rem 0 1rem; max-width:800px; }
.hero h1 span { color:#c084fc; }
.hero p { color:#c6bdd5; max-width:610px; font-size:1rem; line-height:1.75; }
.stat-row { display:flex; gap:2rem; flex-wrap:wrap; margin-top:1.5rem; }
.stat { border-left:2px solid #a855f7; padding-left:.75rem; }
.stat strong { display:block; font-size:1.15rem; color:#fff; }
.stat small { color:#a99eb8; font-size:.72rem; }
.panel { background:linear-gradient(145deg,rgba(25,19,40,.94),rgba(14,11,24,.96)); border:1px solid rgba(201,163,255,.16); border-radius:16px; padding:1rem; height:100%; }
.panel-title { font-family:'Space Grotesk',sans-serif; font-size:1.1rem; font-weight:700; margin-bottom:.25rem; }
.panel-subtitle { color:#a99eb8; font-size:.8rem; margin-bottom:1rem; }
.section-head { display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:1.8rem 0 1rem; }
.section-head h2 { margin:0; font-size:1.55rem; }
.section-head p { margin:.3rem 0 0; color:#a99eb8; font-size:.82rem; }
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] > div, div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div { background:#0d0a17 !important; color:#f8f5ff !important; border-color:rgba(197,156,255,.28) !important; border-radius:10px !important; }
div[data-testid="stTextInput"] input:focus { box-shadow:0 0 0 1px #a855f7 !important; }
.stButton > button { border-radius:10px; border:1px solid rgba(192,132,252,.35); background:linear-gradient(110deg,#963ee5,#7131c9); color:white; font-weight:700; min-height:2.65rem; transition:all .15s ease; }
.stButton > button:hover { border-color:#d4a4ff; box-shadow:0 0 22px rgba(168,85,247,.25); color:#fff; transform:translateY(-1px); }
.stButton > button[kind="secondary"] { background:rgba(255,255,255,.035); border-color:rgba(201,163,255,.2); color:#e9ddf7; }
.movie-card { overflow:hidden; height:100%; border:1px solid rgba(200,165,255,.16); border-radius:14px; background:#131020; box-shadow:0 10px 25px rgba(0,0,0,.12); }
.movie-poster { width:100%; aspect-ratio:2/2.8; object-fit:cover; display:block; background:linear-gradient(145deg,#291743,#100c1c); }
.poster-placeholder { width:100%; aspect-ratio:2/2.8; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:.7rem; padding:1rem; text-align:center; color:#c9a5ef; background:radial-gradient(circle at 50% 25%,#42205e,#171022 70%); }
.poster-placeholder span { font-size:.8rem; font-weight:700; }
.movie-info { padding:.85rem; }
.movie-title { font-family:'Space Grotesk',sans-serif; color:#fff; font-size:1rem; font-weight:700; line-height:1.3; margin-bottom:.45rem; }
.movie-meta { display:flex; flex-wrap:wrap; gap:.4rem; color:#b2a6c2; font-size:.72rem; margin-bottom:.7rem; }
.pill { display:inline-block; border:1px solid rgba(192,132,252,.25); background:rgba(168,85,247,.1); color:#d8b8ff; padding:.2rem .48rem; border-radius:99px; font-size:.66rem; margin:0 .22rem .25rem 0; }
.movie-overview { color:#bdb3cc; font-size:.78rem; line-height:1.6; min-height:5rem; }
.why-box { border-top:1px solid rgba(201,163,255,.13); margin-top:.7rem; padding-top:.65rem; color:#d9c7ef; font-size:.74rem; line-height:1.5; }
.why-label { color:#c084fc; font-size:.64rem; letter-spacing:.1em; text-transform:uppercase; font-weight:700; margin-bottom:.25rem; }
.match { display:inline-block; color:#b7f4d2; background:rgba(52,211,153,.09); border:1px solid rgba(52,211,153,.2); border-radius:6px; padding:.2rem .4rem; font-size:.68rem; }
.helper { color:#a99eb8; font-size:.76rem; }
div[data-testid="stAlert"] { border-radius:10px; }
hr { border-color:rgba(201,163,255,.12) !important; }
footer { visibility:hidden; }
@media(max-width:700px) {
 .block-container { padding-left:1rem; padding-right:1rem; }
 .brandbar { align-items:flex-start; flex-direction:column; gap:.45rem; }
 .hero { border-radius:16px; padding:1.3rem; }
 .hero h1 { font-size:2.35rem; }
 .stat-row { gap:1rem; }
 .section-head { align-items:flex-start; flex-direction:column; }
 .movie-overview { min-height:0; }
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


def render_movie_card_html(movie: dict, index: int) -> str:
    """Build a single complete HTML string for one movie card."""
    title = html.escape(movie.get("title", ""))
    genres = movie.get("genres", [])
    overview = html.escape(movie.get("overview", "") or "")
    reason = html.escape(movie.get("reason", "") or "")
    similarity = movie.get("similarity_score")
    poster_path = movie.get("poster_path")

    # Genres as pills
    genre_html = "".join(f'<span class="pill">{html.escape(g)}</span>' for g in genres)

    # Poster
    if poster_path and isinstance(poster_path, str) and poster_path.strip():
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        poster_html = f'<img class="movie-poster" src="{poster_url}" alt="{title} poster" loading="lazy">'
    else:
        poster_html = f'<div class="poster-placeholder"><span>🎬</span><span>{title}</span><small>Poster unavailable</small></div>'

    # Similarity score display
    sim_html = ""
    if similarity is not None:
        sim_html = f'<div style="margin-top:.7rem"><span class="match">Similarity score {similarity:.2f}</span></div>'

    return f"""
<div class="movie-card">
    {poster_html}
    <div class="movie-info">
        <div class="movie-title">{title}</div>
        <div class="movie-meta"><span>#{index}</span></div>
        {genre_html}
        <div class="movie-overview">{overview}</div>
        <div class="why-box"><div class="why-label">✦ Why this match</div>{reason}</div>
        {sim_html}
    </div>
</div>
"""


# ─── Header ───
st.markdown("""
<div class="brandbar">
  <div class="brand"><span style="color:#f8f5ff;text-shadow:none">Watch</span><span class="brand-name-accent">Next</span><span class="brand-subtitle">AI MOVIE DISCOVERY</span></div>
  <div class="brand-tag">✦ Find your next favorite movie</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<section class="hero">
  <div class="eyebrow">YOUR PERSONAL CINEMA · AI / ML HACKATHON</div>
  <h1>Less scrolling.<br><span>More great stories.</span></h1>
  <p>Tell WatchNext one movie you love. We'll find five movies with similar genres, themes, and storytelling — and explain why each one made the list.</p>
  <div class="stat-row">
    <div class="stat"><strong>5 picks</strong><small>Focused recommendations</small></div>
    <div class="stat"><strong>Explainable</strong><small>See why each movie fits</small></div>
    <div class="stat"><strong>Free demo</strong><small>No paid API required</small></div>
  </div>
</section>
""", unsafe_allow_html=True)

# ─── Search and filter controls ───
st.markdown('<div class="section-head"><div><div class="eyebrow">START WITH A FAVORITE</div><h2>What did you enjoy watching?</h2><p>Search the TMDB 5000 catalog or type a title directly.</p></div></div>', unsafe_allow_html=True)

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
with c2:
    st.markdown('<div class="panel"><div class="panel-title">Fine-tune your picks</div><div class="panel-subtitle">Optional filters apply to the recommended results.</div>', unsafe_allow_html=True)
    genre_filter = st.selectbox("Genre", GENRES, index=0)
    # Exact year input (backend supports exact match only)
    st.markdown('<div class="helper">Backend matches exact release year only. Leave empty for any year.</div>', unsafe_allow_html=True)
    year_input = st.number_input("Release year (exact)", min_value=1900, max_value=2030, value=None, step=1, format="%d")
    st.markdown('</div>', unsafe_allow_html=True)

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

# ─── Action handlers ───
def handle_find():
    # Determine the title: typed text takes priority, then selection
    title = ""
    if typed_title and typed_title.strip():
        title = typed_title.strip()
    elif selected_label != "— Choose a match —":
        # Extract title from "Title (Genre1, Genre2)" format
        title = selected_label.split(" (")[0]
    else:
        st.warning("Please enter or select a movie first.")
        return

    with st.spinner("Finding movies with similar genres and themes..."):
        try:
            data = recommend_movies_api(title, genre_filter if genre_filter != "All genres" else None, year_input if year_input else None, 5)
            st.session_state.source_title = data.get("query", title)
            st.session_state.results = data.get("recommendations", [])
            st.session_state.source_movie = None  # we don't have the source movie details from API
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

# ─── Results display ───
if st.session_state.results is not None and st.session_state.source_title:
    source_title = st.session_state.source_title
    results = st.session_state.results
    st.markdown("---")
    st.markdown(
        f'<div class="section-head"><div><div class="eyebrow">PERSONALIZED RESULTS</div><h2>Because you liked <span style="color:#c084fc">{html.escape(source_title)}</span></h2><p>Ranked by content-based TF-IDF cosine similarity on the TMDB 5000 dataset.</p></div><div class="match">✓ Recommendation run complete</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="panel" style="margin-bottom:1rem"><div class="panel-title">Why these recommendations?</div><div class="panel-subtitle" style="margin:0">Recommendations use content-based TF-IDF + cosine similarity on genres, keywords, cast, and director. The reason highlights shared genres, keywords, and cast members.</div></div>',
        unsafe_allow_html=True,
    )
    if results:
        cols = st.columns(5 if len(results) == 5 else min(5, len(results)), gap="medium")
        for i, movie in enumerate(results):
            with cols[i % len(cols)]:
                st.markdown(render_movie_card_html(movie, i + 1), unsafe_allow_html=True)
    else:
        st.warning("No recommendations are available with the selected filters. Widen the filter range and try again.")

st.markdown("---")
st.markdown("""
<div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap;color:#82778f;font-size:.72rem">
  <span><strong style="color:#c9b6df">WatchNext</strong> · Content-based movie recommender (TMDB 5000, TF-IDF + cosine similarity)</span>
  <span>Poster images from TMDB where available · Exact-year filter only · No personalization</span>
</div>
""", unsafe_allow_html=True)