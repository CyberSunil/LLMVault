"""Regression tests: player names must be XML-escaped in the completion card SVG.

/api/setname stores the name as-is (up to 14 chars). card_svg.render() is what
must encode <, >, &, and quotes so they cannot inject markup into /card.svg.
"""
import html
import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import card_svg  # noqa: E402

# The player name is the only <text> that uses filter url(#softglow) without a
# variant suffix. If markup were injected, this group would not be a single
# text node (or would not equal html.escape of the truncated name).
_NAME_TEXT = re.compile(r'filter="url\(#softglow\)">([^<]*)</text>')


def _render(name):
    return card_svg.render(
        "beginner",
        "BEGINNER",
        name,
        10,
        100,
        "desc",
        ["Prompt Injection"],
        "Jan 1, 2026",
        "example.com/repo",
        "Author",
        "LLMVault",
    )


def _shown(name):
    """The card draws at most 10 characters (see card_svg._name_lines)."""
    return (name or "Player").strip()[:10]


def _name_in_svg(svg):
    match = _NAME_TEXT.search(svg)
    assert match, "player-name <text> node missing from SVG"
    return match.group(1)


def test_plain_name_appears_in_svg():
    assert _name_in_svg(_render("Alice")) == "Alice"


def test_empty_name_falls_back_to_player():
    assert _name_in_svg(_render("")) == "Player"
    assert _name_in_svg(_render(None)) == "Player"


@pytest.mark.parametrize(
    "name",
    [
        "A&B<C>",
        '<x>&"\'',
        "</text>",
        "<script>",
        "</svg>",
        '"><img',
        "Tom & Jery",
        "x > y < z",
    ],
)
def test_player_name_is_xml_escaped_in_svg(name):
    svg = _render(name)
    shown = _shown(name)
    escaped = html.escape(shown, quote=True)

    assert _name_in_svg(svg) == escaped
    # The raw payload must not appear as markup; only as escaped text.
    assert escaped in svg


def test_fourteen_char_name_is_truncated_then_escaped():
    # /api/setname allows 14 chars; the card still only draws 10.
    name = "<script>alert!"
    assert len(name) == 14
    svg = _render(name)
    shown = _shown(name)
    assert shown == "<script>al"
    assert _name_in_svg(svg) == html.escape(shown, quote=True)
    assert "<script>" not in svg


def test_script_tag_is_not_raw_markup():
    svg = _render("<script>")
    assert "<script>" not in svg
    assert _name_in_svg(svg) == "&lt;script&gt;"
