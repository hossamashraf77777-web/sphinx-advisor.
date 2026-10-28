"""The individual academic rules.

Each rule is a small function that returns a Decision (rule name + status + explanation).
Rules never guess: when the data or regulation they need is missing, they return
Status.NEEDS_VERIFICATION and say exactly what is missing.
"""

from dataclasses import dataclass
from typing import Optional

from agent.models import Course, Decision, Regulations, Status
from services import gpa_calculator as gpa

RULE_NOT_COMPLETED = "Course not already completed"
RULE_PREREQUISITES = "Prerequisites completed"
RULE_RETAKE = "Retake of a failed course"
RULE_CREDIT_LOAD = "Semester credit limit"
RULE_STANDING = "Academic standing (CGPA)"


@dataclass
class Context:
    """The student's situation, prepared once and shared by all rules."""

    courses: dict
    regulations: Regulations
    records: list
    passed: Optional[set]  # None when the minimum passing grade is not provided
    attempted: set


def build_context(dataset) -> Context:
    records = dataset.student.records
    try:
        passed = gpa.passed_codes(records, dataset.regulations)
    except gpa.MissingRuleError:
        passed = None
    return Context(
        courses=dataset.courses,
        regulations=dataset.regulations,
        records=records,
        passed=passed,
        attempted={r.course_code for r in records},
    )


def label(ctx: Context, code: str) -> str:
    course = ctx.courses.get(code)
    return f"{code} - {course.title}" if course else code


def rule_not_already_completed(course: Course, ctx: Context) -> Decision:
    if course.code not in ctx.attempted:
        return Decision(RULE_NOT_COMPLETED, Status.PASSED, "There is no attempt of this course on the student's record.")
    if ctx.passed is None:
        return Decision(
            RULE_NOT_COMPLETED,
            Status.NEEDS_VERIFICATION,
            "The course was attempted, but the minimum passing grade is not provided, so we cannot tell whether it was passed.",
        )
    if course.code in ctx.passed:
        return Decision(RULE_NOT_COMPLETED, Status.FAILED, "The student has already passed this course.")
    return Decision(
        RULE_NOT_COMPLETED, Status.PASSED, "The student attempted this course but did not reach the passing grade."
    )


def rule_prerequisites(course: Course, ctx: Context) -> Decision:
    if not course.prerequisites_known:
        return Decision(
            RULE_PREREQUISITES,
            Status.NEEDS_VERIFICATION,
            "The curriculum data marks this course's prerequisites as UNKNOWN. Check the official curriculum.",
        )
    if not course.prerequisites:
        return Decision(RULE_PREREQUISITES, Status.PASSED, "The curriculum lists no prerequisites for this course.")
    if ctx.passed is None:
        return Decision(
            RULE_PREREQUISITES,
            Status.NEEDS_VERIFICATION,
            "The minimum passing grade is not provided, so we cannot tell which prerequisites were passed.",
        )
    missing = [p for p in course.prerequisites if p not in ctx.passed]
    if missing:
        names = ", ".join(label(ctx, p) for p in missing)
        return Decision(RULE_PREREQUISITES, Status.FAILED, f"Not yet passed: {names}.")
    return Decision(
        RULE_PREREQUISITES, Status.PASSED, f"All prerequisites are passed ({', '.join(course.prerequisites)})."
    )


def rule_retake(course: Course, ctx: Context) -> Optional[Decision]:
    """Only applies when the student already has a failing attempt. None = rule not applicable."""
    if ctx.passed is None or course.code not in ctx.attempted or course.code in ctx.passed:
        return None
    policy = ctx.regulations.retake_policy
    if policy is None:
        return Decision(
            RULE_RETAKE,
            Status.NEEDS_VERIFICATION,
            "The student has a failed attempt of this course, but the retake policy is not provided. "
            "Confirm the retake rules with the academic office.",
        )
    return Decision(
        RULE_RETAKE, Status.PASSED, f"Retaking a failed course is allowed; the GPA counts attempts with policy '{policy}'."
    )


def rule_credit_load(total_credits: float, regs: Regulations) -> Decision:
    cap = regs.max_credits_per_semester
    if cap is None:
        return Decision(
            RULE_CREDIT_LOAD,
            Status.NEEDS_VERIFICATION,
            f"The semester credit limit is not provided, so {total_credits:g} credits cannot be verified.",
        )
    if total_credits > cap:
        return Decision(RULE_CREDIT_LOAD, Status.FAILED, f"{total_credits:g} credits exceeds the limit of {cap:g}.")
    return Decision(RULE_CREDIT_LOAD, Status.PASSED, f"{total_credits:g} credits is within the limit of {cap:g}.")


def rule_good_standing(cgpa: Optional[float], regs: Regulations) -> Decision:
    threshold = regs.min_cgpa_good_standing
    if threshold is None:
        return Decision(
            RULE_STANDING,
            Status.NEEDS_VERIFICATION,
            "The minimum CGPA for good standing is not provided, so the standing cannot be verified.",
        )
    if cgpa is None:
        return Decision(RULE_STANDING, Status.NEEDS_VERIFICATION, "There are no graded courses to calculate a CGPA from.")
    if cgpa >= threshold:
        return Decision(RULE_STANDING, Status.PASSED, f"CGPA {cgpa:.2f} meets the minimum of {threshold:g}.")
    return Decision(RULE_STANDING, Status.FAILED, f"CGPA {cgpa:.2f} is below the minimum of {threshold:g}.")
