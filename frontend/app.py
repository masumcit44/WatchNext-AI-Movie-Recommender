"""
Frontend developer owns this module.
Run: streamlit run frontend/app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="WatchNext", page_icon="🎬", layout="wide")
st.title("🎬 WatchNext")
st.write("Find your next movie from a movie you already like.")

# TODO (frontend developer):
# 1. Search/select a movie through GET /movies/search.
# 2. Call GET /recommend with title and optional genre/year.
# 3. Render title, genres, overview, poster_path, similarity_score, reason.
# 4. Handle loading, empty input, API errors, and missing posters.
# 5. Do not fabricate recommendation results.
st.caption(f"Backend URL: {BACKEND_URL}")
