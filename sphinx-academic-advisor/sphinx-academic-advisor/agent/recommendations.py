"""Next-semester course recommendations.

Order of priority (highest first):
  1. Retake of a course the student attempted but did not pass.
  2. Courses in the categories that are fully mandatory for graduation (by level).
  3. Courses from categories that still need credits (for example electives).
Only courses that passed the eligibility rules (or still need verification) are considered.
"""

from dataclasses import dataclass, field
from typing import Optional

from agent import eligibility, graduation, rules
from agent.models import Decision, Status


@dataclass
class Recommendation:
    evaluation: eligibility.CourseEvaluation
    tier: int
    reason: str

    @property
    def course(self):
        return self.evaluation.course


@dataclass
class RecommendationResult:
    recommended: list = field(default_factory=list)  # list[Recommendation]
    deferred: list = field(default_factory=list)  # eligible, but not selected (reason inside)
    rejected: list = field(default_factory=list)  # list[CourseEvaluation] failing a rule
    completed: list = field(default_factory=list)  # codes already passed
    total_credits: float = 0.0
    credit_limit: Optional[float] = None
    limit_source: str = "none"  # "regulation" | "user" | "none"
    credit_decisions: list = field(default_factory=list)  # list[Decision]
    notes: list = field(default_factory=list)


def _classify(evaluation, ctx, required_cats, remaining):
    """Return (tier, reason, wanted). 'wanted' is False when the course is not needed."""
    course = evaluation.course
    failed_before = course.code in ctx.attempted and ctx.passed is not None and course.code not in ctx.passed
    if failed_before and (required_cats is None or course.category in required_cats):
        return 0, "Retake: the previous attempt did not reach the passing grade, and this course is mandatory.", True
    if required_cats is None:
        return 1, "Eligible, but the mandatory categories are not provided, so its importance cannot be verified.", True
    if course.category in required_cats:
        return 1, f"Mandatory '{course.category}' course whose prerequisites are satisfied.", True
    if course.category in remaining:
        if remaining[course.category] > 0:
            return 2, f"Counts toward the {remaining[course.category]:g} credits still needed in '{course.category}'.", True
        return 3, f"The '{course.category}' credit requirement is already met.", False
    return 3, f"The '{course.category}' category is not part of the listed graduation requirements.", False


def recommend_courses(dataset, user_credit_budget: Optional[float] = None) -> RecommendationResult:
    ctx = rules.build_context(dataset)
    regs = ctx.regulations
    evaluations = eligibility.evaluate_all(ctx)
    required_cats = regs.graduation_required_categories
    remaining = graduation.remaining_category_credits(ctx)

    result = RecommendationResult()
    candidates = []
    for evaluation in evaluations.values():
        if evaluation.already_completed:
            result.completed.append(evaluation.course.code)
        elif evaluation.status == Status.FAILED:
            result.rejected.append(evaluation)
        else:
            tier, reason, wanted = _classify(evaluation, ctx, required_cats, remaining)
            rec = Recommendation(evaluation, tier, reason)
            if wanted:
                candidates.append(rec)
            else:
                result.deferred.append(rec)

    candidates.sort(key=lambda r: (r.tier, r.course.level, r.course.code))

    # Which credit limit applies?
    if regs.max_credits_per_semester is not None:
        result.credit_limit, result.limit_source = regs.max_credits_per_semester, "regulation"
        if user_credit_budget and user_credit_budget > regs.max_credits_per_semester:
            result.notes.append(
                f"Your planning value ({user_credit_budget:g}) is above the official limit, so the official limit is used."
            )
    elif user_credit_budget:
        result.credit_limit, result.limit_source = float(user_credit_budget), "user"

    limit = result.credit_limit
    for rec in candidates:
        if limit is not None and result.total_credits + rec.course.credits > limit:
            rec.reason = f"Eligible and needed, but adding it would pass the {limit:g}-credit limit."
            result.deferred.append(rec)
            continue
        result.recommended.append(rec)
        result.total_credits += rec.course.credits

    result.credit_decisions.append(rules.rule_credit_load(result.total_credits, regs))
    if result.limit_source == "user":
        result.credit_decisions.append(
            Decision(
                "Planning credit limit (your own setting)",
                Status.PASSED,
                f"The list was trimmed to {limit:g} credits because you asked for that. It is not an official rule.",
            )
        )
    if ctx.passed is None:
        result.notes.append("The minimum passing grade is not provided, so no course can be fully verified.")
    return result
