"""Loads the dataset once, stops the page with a clear message if something is wrong,
and builds the sidebar. Every page starts with start_page()."""

import streamlit as st

import config
from services.data_loader import DataLoadError, load_dataset
from ui import components


@st.cache_resource(show_spinner=False)
def _load(mode: str, student_id):
    return load_dataset(mode, student_id)


def get_dataset():
    """Return the dataset, or show the problem and stop the page (never silently use other data)."""
    try:
        dataset = _load(config.DATA_MODE, st.session_state.get("student_id"))
    except DataLoadError as exc:
        components.page_header("Data could not be loaded", "The academic data files need attention.")
        st.error(str(exc))
        st.stop()
    errors = [i for i in dataset.issues if i.level == "error"]
    if errors:
        components.page_header("Data check failed", "The data files contain errors, so no advice can be given.")
        for issue in errors:
            st.error(issue.message)
        st.stop()
    return dataset


def start_page(title: str, subtitle: str):
    """Load data, draw the page header and the demo/official banner. Returns the dataset."""
    dataset = get_dataset()
    components.page_header(title, subtitle)
    components.data_source_banner(dataset)
    return dataset


def render_sidebar() -> None:
    """Data source info, student selector (only if the file has several students) and reload."""
    with st.sidebar:
        st.markdown("**Data source**")
        try:
            dataset = _load(config.DATA_MODE, st.session_state.get("student_id"))
        except DataLoadError:
            st.caption(f"Mode: {config.DATA_MODE} (not loaded)")
        else:
            st.caption("Demonstration data" if dataset.is_demo else "Official data")
            if len(dataset.students) > 1:
                st.selectbox(
                    "Student",
                    options=[s.student_id for s in dataset.students],
                    format_func=lambda sid: next(s.name for s in dataset.students if s.student_id == sid),
                    key="student_id",
                )
            else:
                st.caption(f"Student: {dataset.student.name}")
        if st.button("Reload data files", help="Re-read the files in the data folder after editing them."):
            _load.clear()
            st.rerun()
