"""Combines the individual rules into one verdict per course."""

from dataclasses import dataclass, field

from agent import rules
from agent.models import Course, Decision, Status


@dataclass
class CourseEvaluation:
    course: Course
    decisions: list = field(default_factory=list)
    status: Status = Status.PASSED

    @property
    def already_completed(self) -> bool:
        return any(d.rule == rules.RULE_NOT_COMPLETED and d.status == Status.FAILED for d in self.decisions)

    @property
    def summary(self) -> str:
        if self.status == Status.PASSED:
            return "Eligible: every rule check passed."
        if self.status == Status.NEEDS_VERIFICATION:
            return "Possibly eligible: at least one check needs verification."
        return "Not eligible: " + " ".join(d.explanation for d in self.decisions if d.status == Status.FAILED)


def evaluate_course(course: Course, ctx: rules.Context) -> CourseEvaluation:
    decisions = [rules.rule_not_already_completed(course, ctx), rules.rule_prerequisites(course, ctx)]
    retake = rules.rule_retake(course, ctx)
    if retake is not None:
        decisions.append(retake)
    statuses = {d.status for d in decisions}
    if Status.FAILED in statuses:
        overall = Status.FAILED
    elif Status.NEEDS_VERIFICATION in statuses:
        overall = Status.NEEDS_VERIFICATION
    else:
        overall = Status.PASSED
    return CourseEvaluation(course=course, decisions=decisions, status=overall)


def evaluate_all(ctx: rules.Context) -> dict:
    """code -> CourseEvaluation for every course in the catalog."""
    return {code: evaluate_course(course, ctx) for code, course in ctx.courses.items()}


def decisions_as_rows(evaluation: CourseEvaluation) -> list:
    """Helper for tables/exports: plain dictionaries."""
    return [{"Rule": d.rule, "Result": d.status.value, "Explanation": d.explanation} for d in evaluation.decisions]
