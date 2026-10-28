"""GPA and credit calculations.

Every number here comes from the regulations file. If a needed rule is missing the
functions raise MissingRuleError instead of guessing.
"""

from dataclasses import dataclass
from typing import Optional

from agent.models import Course, CourseRecord, Regulations


class MissingRuleError(Exception):
    """A rule needed for this calculation was not provided in regulations.json."""

    def __init__(self, rule_name: str):
        self.rule_name = rule_name
        super().__init__(f"The rule '{rule_name}' is not provided in the regulations file.")


@dataclass
class GpaResult:
    gpa: Optional[float]  # None when there is nothing to average
    quality_points: float
    credits_attempted: float
    credits_earned: Optional[float]  # None when the passing grade is not provided
    skipped_records: int  # records ignored (unknown course or unrecognised grade)
    retake_policy_verified: bool  # False when the student repeated a course but no policy exists


@dataclass
class TermSummary:
    term: str
    term_order: int
    term_gpa: Optional[float]
    cumulative_gpa: Optional[float]
    credits_attempted: float
    credits_earned: Optional[float]
    cumulative_credits_earned: Optional[float]


def _normalise(grade: str) -> str:
    return str(grade).strip().upper()


def grade_points(grade: str, regs: Regulations) -> Optional[float]:
    """Grade points for a letter grade, or None if the grade is not in the scale."""
    if not regs.grade_scale:
        raise MissingRuleError("grade_scale")
    return regs.grade_scale.get(_normalise(grade))


def is_passing(grade: str, regs: Regulations) -> Optional[bool]:
    """True/False, or None if the grade is not in the scale."""
    if regs.min_passing_points is None:
        raise MissingRuleError("min_passing_points")
    points = grade_points(grade, regs)
    if points is None:
        return None
    return points >= regs.min_passing_points


def passed_codes(records: list, regs: Regulations) -> set:
    """Codes of courses with at least one passing attempt."""
    return {r.course_code for r in records if is_passing(r.grade, regs)}


def credits_earned(records: list, courses: dict, regs: Regulations) -> float:
    return sum(courses[code].credits for code in passed_codes(records, regs) if code in courses)


def select_attempts(records: list, regs: Regulations) -> list:
    """Apply the retake policy: which attempts count towards the GPA."""
    policy = regs.retake_policy
    if policy in (None, "all"):
        return list(records)
    by_course: dict = {}
    for record in sorted(records, key=lambda r: r.term_order):
        by_course.setdefault(record.course_code, []).append(record)
    chosen = []
    for attempts in by_course.values():
        if policy == "latest":
            chosen.append(attempts[-1])
        else:  # "best"
            chosen.append(max(attempts, key=lambda r: grade_points(r.grade, regs) or 0.0))
    return chosen


def _average(used: list, courses: dict, regs: Regulations):
    quality = attempted = 0.0
    skipped = 0
    for record in used:
        course = courses.get(record.course_code)
        points = grade_points(record.grade, regs)
        if course is None or points is None:
            skipped += 1
            continue
        quality += points * course.credits
        attempted += course.credits
    gpa = quality / attempted if attempted else None
    return gpa, quality, attempted, skipped


def calculate_gpa(records: list, courses: dict, regs: Regulations) -> GpaResult:
    used = select_attempts(records, regs)
    gpa, quality, attempted, skipped = _average(used, courses, regs)
    codes = [r.course_code for r in records]
    has_repeats = len(codes) != len(set(codes))
    earned = credits_earned(records, courses, regs) if regs.min_passing_points is not None else None
    return GpaResult(
        gpa=gpa,
        quality_points=quality,
        credits_attempted=attempted,
        credits_earned=earned,
        skipped_records=skipped,
        retake_policy_verified=(regs.retake_policy is not None) or not has_repeats,
    )


def term_summaries(records: list, courses: dict, regs: Regulations) -> list:
    """One row per term, with the term GPA and the cumulative GPA up to that term."""
    terms = sorted({(r.term_order, r.term) for r in records})
    summaries = []
    for order, name in terms:
        in_term = [r for r in records if r.term_order == order]
        up_to_now = [r for r in records if r.term_order <= order]
        term_gpa, _, attempted, _ = _average(in_term, courses, regs)
        cumulative = calculate_gpa(up_to_now, courses, regs)
        if regs.min_passing_points is not None:
            earned_here = sum(
                courses[r.course_code].credits
                for r in in_term
                if r.course_code in courses and is_passing(r.grade, regs)
            )
        else:
            earned_here = None
        summaries.append(
            TermSummary(
                term=name,
                term_order=order,
                term_gpa=term_gpa,
                cumulative_gpa=cumulative.gpa,
                credits_attempted=attempted,
                credits_earned=earned_here,
                cumulative_credits_earned=cumulative.credits_earned,
            )
        )
    return summaries


def project_gpa(records: list, planned: list, courses: dict, regs: Regulations) -> GpaResult:
    """What-if: add planned (course_code, grade) pairs as a future term and recompute."""
    next_order = max((r.term_order for r in records), default=0) + 1
    extra = []
    for code, grade in planned:
        if code not in courses:
            raise ValueError(f"Unknown course code: {code}")
        if grade_points(grade, regs) is None:
            raise ValueError(f"Grade '{grade}' is not in the grade scale.")
        extra.append(CourseRecord(code, _normalise(grade), "Projected term", next_order))
    return calculate_gpa(list(records) + extra, courses, regs)


def grade_distribution(records: list) -> dict:
    """How many times each grade appears (for the bar chart)."""
    counts: dict = {}
    for record in records:
        key = _normalise(record.grade)
        counts[key] = counts.get(key, 0) + 1
    return counts
