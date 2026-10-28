"""Central settings for the whole project.

Everything that you might want to change without touching the logic lives here:
the data mode (demo / official), file locations, and chart colours.
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

APP_NAME = "Sphinx FCAI Academic Advisor"
FACULTY_NAME = "Faculty of Computers and Artificial Intelligence"
UNIVERSITY_NAME = "Sphinx University"

# "demo"     -> data/demo/      (placeholder data written by the team, NOT official)
# "official" -> data/official/  (real curriculum + regulations, added by the team)
# Change it by setting the environment variable SPHINX_DATA_MODE=official
DATA_MODE = os.environ.get("SPHINX_DATA_MODE", "demo").strip().lower()

DATA_DIRS = {
    "demo": ROOT_DIR / "data" / "demo",
    "official": ROOT_DIR / "data" / "official",
}

# Every data folder must contain these three files (see data/official/README.md).
REQUIRED_FILES = ("courses.csv", "student.json", "regulations.json")

CSS_FILE = ROOT_DIR / "styles" / "main.css"

# Colours used by Streamlit's built-in charts. Charts cannot read CSS variables,
# so keep these in sync with --secondary-color / --primary-color in main.css.
CHART_COLORS = ["#0F766E", "#14284B", "#9A6200"]
