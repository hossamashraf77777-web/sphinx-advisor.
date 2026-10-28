"""Checks that the loaded data is consistent before the agent uses it.

An "error" means the data is broken (the app stops and shows it).
A "warning" means something is missing (the agent will say "needs verification").
"""

from dataclasses import dataclass

from agent.models import Regulations


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    message: str


def _find_cycle(courses: dict):
    """Return a course code that is part of a prerequisite cycle, or None."""
    state: dict = {}  # code -> 1 (visiting) / 2 (done)

    def visit(code):
        if state.get(code) == 2:
            return None
        if state.get(code) == 1:
            return code
        state[code] = 1
        for prereq in courses[code].prerequisites:
            if prereq in courses:
                found = visit(prereq)
                if found:
                    return found
        state[code] = 2
        return None

    for code in courses:
        found = visit(code)
        if found:
            return found
    return None


def validate_courses(courses: dict) -> list:
    issues = []
    for course in courses.values():
        if course.credits <= 0:
            issues.append(Issue("error", f"{course.code}: credit hours must be greater than 0."))
        for prereq in course.prerequisites:
            if prereq == course.code:
                issues.append(Issue("error", f"{course.code} lists itself as a prerequisite."))
            elif prereq not in courses:
                issues.append(Issue("error", f"{course.code}: prerequisite '{prereq}' is not in the course catalog."))
        if not course.prerequisites_known:
            issues.append(
                Issue("warning", f"{course.code}: prerequisites are marked UNKNOWN, so this course cannot be verified.")
            )
    cycle_code = _find_cycle(courses)
    if cycle_code:
        issues.append(Issue("error", f"Prerequisite cycle detected involving {cycle_code}."))
    return issues


def validate_students(students: list, courses: dict, regs: Regulations) -> list:
    issues = []
    for student in students:
        seen = set()
        repeated = False
        for record in student.records:
            if record.course_code not in courses:
                issues.append(
                    Issue("error", f"{student.student_id}: record for unknown course '{record.course_code}'.")
                )
            if regs.grade_scale and record.grade.strip().upper() not in regs.grade_scale:
                issues.append(
                    Issue(
                        "error",
                        f"{student.student_id}: grade '{record.grade}' in {record.course_code} is not in the grade scale.",
                    )
                )
            if record.course_code in seen:
                repeated = True
            seen.add(record.course_code)
        if repeated and regs.retake_policy is None:
            issues.append(
                Issue(
                    "warning",
                    f"{student.student_id}: a course was taken more than once but no retake policy is provided.",
                )
            )
    return issues


def validate_regulations(regs: Regulations) -> list:
    missing = {
        "Grade scale": bool(regs.grade_scale),
        "Minimum passing grade points": regs.min_passing_points is not None,
        "Retake policy": regs.retake_policy is not None,
        "Maximum credits per semester": regs.max_credits_per_semester is not None,
        "Minimum CGPA for good standing": regs.min_cgpa_good_standing is not None,
        "Total credits required to graduate": regs.graduation_total_credits is not None,
        "Required course categories": regs.graduation_required_categories is not None,
        "Category credit requirements": regs.graduation_category_credits is not None,
    }
    return [
        Issue("warning", f"Rule not provided: {name}. Decisions that depend on it will be marked 'needs verification'.")
        for name, provided in missing.items()
        if not provided
    ]


def validate_dataset(courses: dict, students: list, regs: Regulations) -> list:
    return validate_courses(courses) + validate_students(students, courses, regs) + validate_regulations(regs)
