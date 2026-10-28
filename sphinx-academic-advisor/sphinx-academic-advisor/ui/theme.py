"""Loads styles/main.css once per run and injects it into the page."""

import streamlit as st

import config


def apply_theme() -> None:
    try:
        css = config.CSS_FILE.read_text(encoding="utf-8")
    except OSError:
        st.warning("The stylesheet styles/main.css could not be read. The app will use Streamlit's default look.")
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
