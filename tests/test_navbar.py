"""
Tests for the fixed navigation bar.

The navbar is the single most fragile part of the Streamlit UI: Streamlit
renders a bare CSS string as paragraph *text*, which silently makes every
rule inert. These tests lock in the structure that prevents that.
"""
import re

import pytest


@pytest.fixture(scope="module")
def nav():
    """The rendered navigation bar HTML (CSS + markup)."""
    from frontend.app import build_nav

    return build_nav()


def test_nav_css_is_wrapped_in_style_tag(nav):
    """Regression: the stylesheet must be inside <style>...</style>.

    Without the wrapper Streamlit shows the CSS as literal text and the bar
    never becomes fixed.
    """
    assert "<style>" in nav
    assert "</style>" in nav
    # The CSS must not be rendered as body text.
    assert not nav.strip().startswith("html {")
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    assert "position: fixed" in style_body


def test_nav_has_exactly_one_header(nav):
    """Exactly one fixed header - no duplicate/stacked nav bars."""
    assert nav.count("<header") == 1
    assert nav.count("</header>") == 1
    assert nav.count('class="wn-nav"') == 1


def test_nav_is_fixed_with_blur_and_zindex(nav):
    """The bar is position:fixed, blurred and stacked above content."""
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    nav_rules = style_body.split("header.wn-nav {", 1)[1].split("}", 1)[0]
    assert "position: fixed" in nav_rules
    assert "backdrop-filter: blur" in nav_rules
    assert "-webkit-backdrop-filter: blur" in nav_rules
    assert "z-index: 900" in nav_rules


def test_nav_zindex_is_below_streamlit_popovers(nav):
    """The nav must not cover Streamlit's own dropdown popovers."""
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    zindexes = [int(m) for m in re.findall(r"z-index:\s*(\d+)", style_body)]
    assert zindexes, "nav stylesheet must declare a z-index"
    # BaseWeb popovers are rendered at z-index >= 1000.
    assert max(zindexes) < 1000


def test_container_padding_clears_nav_height(nav):
    """Page content must not slide under the fixed bar."""
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    match = re.search(r"\.block-container\s*\{[^}]*padding-top:\s*(\d+)px", style_body)
    assert match, "nav stylesheet must set .block-container padding-top"
    padding_top = int(match.group(1))
    nav_height = 64  # desktop height declared in the same stylesheet
    assert padding_top >= nav_height


def test_streamlit_header_is_hidden(nav):
    """Streamlit's own header must not overlap the fixed nav."""
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    assert '[data-testid="stHeader"]' in style_body


def test_brand_is_single_word_watchnext(nav):
    """The brand renders as the single word "WatchNext"."""
    assert "WatchNext" in nav
    brand = re.search(r'<span class="wn-brand-name">(.*?)</span>', nav)
    assert brand, "nav must contain a wn-brand-name span"
    assert brand.group(1).strip() == "WatchNext"
    # Not the old split "Watch" + "Next" two-span brand.
    assert 'class="wn-brand-word' not in nav


def test_nav_has_landmarks_and_accessible_labels(nav):
    """The bar uses banner/nav landmarks with an accessible name."""
    assert 'role="banner"' in nav
    assert "<nav" in nav
    assert 'aria-label="Primary"' in nav
    assert 'aria-label="WatchNext home"' in nav


def test_nav_links_have_real_targets(nav):
    """Every nav link points at an anchor that is actually rendered."""
    hrefs = re.findall(r'<a href="#([^"]+)">', nav)
    assert hrefs, "nav must contain anchor links"
    assert set(hrefs) == {"wn-search", "wn-results", "wn-about"}


def test_nav_anchor_targets_exist_in_page():
    """The page renders the anchors the nav links to."""
    from pathlib import Path

    import frontend.app as app_module

    source = Path(app_module.__file__).read_text(encoding="utf-8")
    for target in ("wn-search", "wn-results", "wn-about"):
        assert f'id="{target}"' in source, f"page must render anchor id={target}"


def test_nav_is_responsive(nav):
    """Media queries cover narrow (390px) and mid (700px) viewports."""
    style_body = nav.split("<style>", 1)[1].split("</style>", 1)[0]
    assert "@media (max-width: 700px)" in style_body
    assert "@media (max-width: 420px)" in style_body


def test_nav_no_onerror_handlers(nav):
    """The navbar must not carry inline error handlers."""
    assert "onerror" not in nav.lower()
