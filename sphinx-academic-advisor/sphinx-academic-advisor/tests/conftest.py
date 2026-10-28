"""Small hand-made datasets for the tests.

They are tiny on purpose: the tests check the RULES, not the demo data.
Codes like T1, T2 are test fixtures only.
"""

import pytest

from agent.models import Course, CourseRecord, Dataset, Regulations, Student


def make_regs(**overrides) -> Regulations:
    base = dict(
        is_demo=True,
        label="test rules",
        grade_scale={"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0},
        min_passing_points=1.0,
        retake_policy="latest",
        max_credits_per_semester=6.0,
        min_cgpa_good_standing=2.0,
        graduation_total_credits=12.0,
        graduation_required_categories=["core"],
        graduation_category_credits={"elective": 3.0},
    )
    base.update(overrides)
    return Regulations(**base)


def make_courses() -> dict:
    items = [
        Course("T1", "Test One", 3, "core", 1),
        Course("T2", "Test Two", 3, "core", 1, ("T1",)),
        Course("T3", "Test Three", 3, "core", 2, ("T2",)),
        Course("E1", "Test Elective", 3, "elective", 1),
        Course("U1", "Test Unknown Prereq", 3, "elective", 1, (), False),
    ]
    return {c.code: c for c in items}


def make_dataset(records=(), **reg_overrides) -> Dataset:
    student = Student("S1", "Test Student", "Test Program", "Term 1", list(records))
    return Dataset(
        courses=make_courses(),
        students=[student],
        student=student,
        regulations=make_regs(**reg_overrides),
        is_demo=True,
        source_dir="tests",
    )


def rec(code, grade, order=1):
    return CourseRecord(code, grade, f"Term {order}", order)


@pytest.fixture
def courses():
    return make_courses()


@pytest.fixture
def regs():
    return make_regs()
