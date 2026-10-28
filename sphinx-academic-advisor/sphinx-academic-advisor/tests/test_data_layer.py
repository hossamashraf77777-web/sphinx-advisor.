import json

import pytest

from services import validation
from services.data_loader import DataLoadError, load_dataset
from tests.conftest import make_courses, make_dataset, make_regs, rec

GOOD_CSV = "code,title,credits,category,level,prerequisites,description\nA1,Alpha,3,core,1,,x\nA2,Beta,3,core,1,A1,x\n"
GOOD_STUDENT = {"students": [{"student_id": "S", "name": "N", "program": "P", "records": []}]}
GOOD_REGS = {"meta": {"is_demo": True, "label": "t"}, "grade_scale": {"A": 4.0}, "min_passing_points": 1.0}


def write_folder(tmp_path, csv=GOOD_CSV, student=GOOD_STUDENT, regs=GOOD_REGS):
    (tmp_path / "courses.csv").write_text(csv, encoding="utf-8")
    (tmp_path / "student.json").write_text(json.dumps(student), encoding="utf-8")
    (tmp_path / "regulations.json").write_text(json.dumps(regs), encoding="utf-8")
    return tmp_path


def test_shipped_demo_data_loads_without_errors():
    dataset = load_dataset("demo")
    assert dataset.is_demo
    assert not [i for i in dataset.issues if i.level == "error"]
    assert dataset.regulations.is_demo


def test_official_mode_without_files_fails_instead_of_using_demo():
    with pytest.raises(DataLoadError) as info:
        load_dataset("official")
    assert "demo" in str(info.value).lower()  # tells the user it will NOT fall back


def test_unknown_mode_is_rejected():
    with pytest.raises(DataLoadError):
        load_dataset("production")


def test_loads_a_valid_folder(tmp_path):
    dataset = load_dataset("demo", base_dir=write_folder(tmp_path))
    assert set(dataset.courses) == {"A1", "A2"}
    assert dataset.courses["A2"].prerequisites == ("A1",)


def test_duplicate_course_code_is_an_error(tmp_path):
    csv = GOOD_CSV + "A1,Again,3,core,1,,x\n"
    with pytest.raises(DataLoadError, match="duplicate"):
        load_dataset("demo", base_dir=write_folder(tmp_path, csv=csv))


def test_non_numeric_credits_is_an_error(tmp_path):
    csv = "code,title,credits,category,level,prerequisites\nA1,Alpha,three,core,1,\n"
    with pytest.raises(DataLoadError, match="numbers"):
        load_dataset("demo", base_dir=write_folder(tmp_path, csv=csv))


def test_missing_column_is_an_error(tmp_path):
    csv = "code,title,credits\nA1,Alpha,3\n"
    with pytest.raises(DataLoadError, match="missing columns"):
        load_dataset("demo", base_dir=write_folder(tmp_path, csv=csv))


def test_broken_json_is_reported_clearly(tmp_path):
    folder = write_folder(tmp_path)
    (folder / "regulations.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(DataLoadError, match="not valid JSON"):
        load_dataset("demo", base_dir=folder)


def test_bad_retake_policy_value_is_rejected(tmp_path):
    regs = dict(GOOD_REGS, retake_policy="sometimes")
    with pytest.raises(DataLoadError):
        load_dataset("demo", base_dir=write_folder(tmp_path, regs=regs))


def test_validation_finds_unknown_prerequisite_and_cycle():
    from agent.models import Course

    courses = {
        "A": Course("A", "A", 3, "core", 1, ("B",)),
        "B": Course("B", "B", 3, "core", 1, ("A",)),
        "C": Course("C", "C", 3, "core", 1, ("ZZZ",)),
    }
    messages = " ".join(i.message for i in validation.validate_courses(courses))
    assert "cycle" in messages
    assert "ZZZ" in messages


def test_validation_flags_unknown_course_and_grade_in_records():
    ds = make_dataset([rec("NOPE", "A"), rec("T1", "Z")])
    errors = [i.message for i in validation.validate_students(ds.students, ds.courses, ds.regulations)]
    assert any("NOPE" in m for m in errors)
    assert any("'Z'" in m for m in errors)


def test_validation_warns_about_each_missing_rule():
    regs = make_regs(retake_policy=None, max_credits_per_semester=None)
    messages = " ".join(i.message for i in validation.validate_regulations(regs))
    assert "Retake policy" in messages and "Maximum credits per semester" in messages


def test_validation_marks_unknown_prerequisites_as_warning():
    issues = validation.validate_courses(make_courses())
    assert any(i.level == "warning" and "U1" in i.message for i in issues)
