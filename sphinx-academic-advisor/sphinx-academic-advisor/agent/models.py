"""Plain data shapes shared by every layer (no Streamlit in here).

Keeping them in one file makes it easy to see what a "course" or a "decision" is.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    """Result of one rule check."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_VERIFICATION = "needs_verification"


@dataclass(frozen=True)
class Decision:
    """One rule check: which rule, what happened, and why (in plain English)."""

    rule: str
    status: Status
    explanation: str


@dataclass(frozen=True)
class Course:
    code: str
    title: str
    credits: float
    category: str
    level: int
    prerequisites: tuple = ()
    prerequisites_known: bool = True  # False when the data says UNKNOWN
    description: str = ""


@dataclass(frozen=True)
class CourseRecord:
    """One attempt of one course by the student."""

    course_code: str
    grade: str
    term: str
    term_order: int


@dataclass
class Student:
    student_id: str
    name: str
    program: str
    admission_term: str
    records: list = field(default_factory=list)


def _number(value) -> Optional[float]:
    return None if value is None else float(value)


@dataclass
class Regulations:
    """The academic rules. A value of None means "not provided" (never guessed)."""

    is_demo: bool
    label: str
    grade_scale: dict  # grade -> grade points ({} if not provided)
    min_passing_points: Optional[float]
    retake_policy: Optional[str]  # "all" | "latest" | "best" | None
    max_credits_per_semester: Optional[float]
    min_cgpa_good_standing: Optional[float]
    graduation_total_credits: Optional[float]
    graduation_required_categories: Optional[list]
    graduation_category_credits: Optional[dict]

    @classmethod
    def from_dict(cls, raw: dict) -> "Regulations":
        meta = raw.get("meta") or {}
        grad = raw.get("graduation") or {}
        scale = {str(k).strip().upper(): float(v) for k, v in (raw.get("grade_scale") or {}).items()}
        cat_credits = grad.get("category_credits")
        policy = raw.get("retake_policy")
        if policy is not None and policy not in ("all", "latest", "best"):
            raise ValueError("retake_policy must be 'all', 'latest', 'best' or null")
        required = grad.get("required_categories")
        return cls(
            is_demo=bool(meta.get("is_demo", False)),
            label=str(meta.get("label", "")),
            grade_scale=scale,
            min_passing_points=_number(raw.get("min_passing_points")),
            retake_policy=policy,
            max_credits_per_semester=_number(raw.get("max_credits_per_semester")),
            min_cgpa_good_standing=_number(raw.get("min_cgpa_good_standing")),
            graduation_total_credits=_number(grad.get("total_credits")),
            graduation_required_categories=list(required) if required is not None else None,
            graduation_category_credits=(
                {str(k): float(v) for k, v in cat_credits.items()} if cat_credits is not None else None
            ),
        )


@dataclass
class Dataset:
    """Everything the agent needs, already loaded and checked."""

    courses: dict  # code -> Course
    students: list
    student: Student  # the student currently selected
    regulations: Regulations
    is_demo: bool
    source_dir: str
    issues: list = field(default_factory=list)  # validation.Issue objects
