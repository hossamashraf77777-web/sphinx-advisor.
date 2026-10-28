"""Reusable pieces of interface. Pages call these instead of writing HTML themselves.

All text is escaped with html.escape so data from files can never break the page.
The look of each piece is defined by the .sx-* classes in styles/main.css.
"""

import html

import streamlit as st

import config
from agent.models import Decision, Status

_STATUS_STYLE = {
    Status.PASSED: ("Rule met", "success"),
    Status.FAILED: ("Rule not met", "danger"),
    Status.NEEDS_VERIFICATION: ("Needs verification", "warning"),
}

_COURSE_STATUS_STYLE = {
    Status.PASSED: ("Eligible", "success"),
    Status.FAILED: ("Not eligible", "danger"),
    Status.NEEDS_VERIFICATION: ("Needs verification", "warning"),
}


def _e(text) -> str:
    return html.escape(str(text))


def badge(text: str, kind: str = "neutral") -> str:
    """Return the HTML of a small coloured label. kind: success | warning | danger | info | neutral."""
    return f'<span class="sx-badge sx-badge--{kind}">{_e(text)}</span>'


def status_badge(status: Status, course_level: bool = False) -> str:
    text, kind = (_COURSE_STATUS_STYLE if course_level else _STATUS_STYLE)[status]
    return badge(text, kind)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="sx-page-header"><p class="sx-eyebrow">{_e(config.FACULTY_NAME)} &middot; {_e(config.UNIVERSITY_NAME)}</p>'
        f"<h1>{_e(title)}</h1><p class=\"sx-subtitle\">{_e(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


def notice(kind: str, title: str, text: str) -> None:
    """A highlighted message box. kind: info | success | warning | danger."""
    st.markdown(
        f'<div class="sx-notice sx-notice--{kind}"><strong>{_e(title)}</strong><span>{_e(text)}</span></div>',
        unsafe_allow_html=True,
    )


def data_source_banner(dataset) -> None:
    """Shown on every page, so demo data can never be mistaken for official data."""
    if dataset.is_demo:
        notice(
            "warning",
            "Demonstration data - not official university advice",
            "Courses, credit hours, prerequisites, grading rules and graduation requirements on this page are "
            "placeholders written for testing. Do not use them for real registration decisions.",
        )
    else:
        notice(
            "info",
            "Official data files loaded",
            f"Source: {dataset.regulations.label or dataset.source_dir}. Always confirm important decisions "
            "with the academic office.",
        )


def decision_card(decision: Decision) -> None:
    text, kind = _STATUS_STYLE[decision.status]
    st.markdown(
        f'<div class="sx-decision sx-decision--{kind}"><div class="sx-decision__head">'
        f"<span>{_e(decision.rule)}</span>{badge(text, kind)}</div><p>{_e(decision.explanation)}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, text: str) -> None:
    st.markdown(f'<div class="sx-empty"><strong>{_e(title)}</strong><p>{_e(text)}</p></div>', unsafe_allow_html=True)


def facts(items: list) -> None:
    """Show label/value pairs in a responsive grid. items = [(label, value), ...]"""
    cells = "".join(
        f'<div><div class="sx-fact__label">{_e(label)}</div><div class="sx-fact__value">{_e(value)}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="sx-facts">{cells}</div>', unsafe_allow_html=True)


def format_gpa(value) -> str:
    return f"{value:.2f}" if value is not None else "Not available"
