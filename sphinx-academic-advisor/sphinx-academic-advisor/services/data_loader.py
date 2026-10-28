"""Reads the three data files (courses.csv, student.json, regulations.json).

This is the ONLY module that touches the files. To move to a database later, only this
file needs to change.
"""

import csv
import json
from pathlib import Path
from typing import Optional

import config
from agent.models import Course, CourseRecord, Dataset, Regulations, Student
from services import validation


class DataLoadError(Exception):
    """The data files are missing or badly formatted. The message is safe to show to the user."""


_COURSE_COLUMNS = {"code", "title", "credits", "category", "level", "prerequisites"}


def _read_json(path: Path):
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"{path.name} is not valid JSON (line {exc.lineno}): {exc.msg}") from exc


def load_courses(path: Path) -> dict:
    courses: dict = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = {name.strip() for name in (reader.fieldnames or [])}
        missing = _COURSE_COLUMNS - header
        if missing:
            raise DataLoadError(f"courses.csv is missing columns: {', '.join(sorted(missing))}.")
        for line_no, raw in enumerate(reader, start=2):
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k and isinstance(v, (str, type(None)))}
            if not any(row.values()):
                continue
            code = row.get("code", "")
            if not code:
                raise DataLoadError(f"courses.csv line {line_no}: the course code is empty.")
            if code in courses:
                raise DataLoadError(f"courses.csv line {line_no}: duplicate course code '{code}'.")
            try:
                credits = float(row["credits"])
                level = int(row["level"])
            except ValueError as exc:
                raise DataLoadError(
                    f"courses.csv line {line_no}: 'credits' and 'level' must be numbers (course {code})."
                ) from exc
            prereq_text = row["prerequisites"]
            known = prereq_text.upper() != "UNKNOWN"
            prereqs = tuple(p.strip() for p in prereq_text.split(";") if p.strip()) if known else ()
            courses[code] = Course(
                code=code,
                title=row["title"],
                credits=credits,
                category=row["category"].lower(),
                level=level,
                prerequisites=prereqs,
                prerequisites_known=known,
                description=row.get("description", ""),
            )
    if not courses:
        raise DataLoadError("courses.csv contains no courses.")
    return courses


def load_students(path: Path) -> list:
    data = _read_json(path)
    raw_students = data.get("students") if isinstance(data, dict) else None
    if not raw_students:
        raise DataLoadError("student.json must contain a non-empty 'students' list.")
    students = []
    for raw in raw_students:
        try:
            records = [
                CourseRecord(
                    course_code=str(r["course_code"]).strip(),
                    grade=str(r["grade"]).strip(),
                    term=str(r["term"]).strip(),
                    term_order=int(r["term_order"]),
                )
                for r in raw.get("records", [])
            ]
            students.append(
                Student(
                    student_id=str(raw["student_id"]),
                    name=str(raw["name"]),
                    program=str(raw.get("program", "")),
                    admission_term=str(raw.get("admission_term", "")),
                    records=records,
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise DataLoadError(f"student.json has a badly formatted student or record: {exc!r}") from exc
    return students


def load_regulations(path: Path) -> Regulations:
    data = _read_json(path)
    try:
        return Regulations.from_dict(data)
    except (ValueError, TypeError, AttributeError) as exc:
        raise DataLoadError(f"regulations.json has a badly formatted value: {exc}") from exc


def load_dataset(mode: str, student_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Dataset:
    """Load, cross-check and return everything for the chosen mode ("demo" or "official")."""
    if mode not in config.DATA_DIRS:
        raise DataLoadError(f"Unknown data mode '{mode}'. Use 'demo' or 'official'.")
    folder = Path(base_dir) if base_dir else config.DATA_DIRS[mode]
    missing = [name for name in config.REQUIRED_FILES if not (folder / name).is_file()]
    if missing:
        hint = (
            " The app will not fall back to demo data. See data/official/README.md for the expected format."
            if mode == "official"
            else ""
        )
        raise DataLoadError(f"Missing data file(s) in {folder}: {', '.join(missing)}.{hint}")

    courses = load_courses(folder / "courses.csv")
    students = load_students(folder / "student.json")
    regulations = load_regulations(folder / "regulations.json")

    if student_id is None:
        student = students[0]
    else:
        matches = [s for s in students if s.student_id == student_id]
        if not matches:
            raise DataLoadError(f"Student '{student_id}' was not found in student.json.")
        student = matches[0]

    return Dataset(
        courses=courses,
        students=students,
        student=student,
        regulations=regulations,
        is_demo=(mode == "demo") or regulations.is_demo,
        source_dir=str(folder),
        issues=validation.validate_dataset(courses, students, regulations),
    )
