"""Graduation progress and a proposed path to graduation.

Requirements come only from regulations.json. If a requirement is missing, the result is
marked as not verified instead of being estimated.
"""

from dataclasses import dataclass, field
from typing import Optional

from agent import rules
from agent.models import Course

MAX_PLANNED_TERMS = 20


@dataclass
class GraduationProgress:
    verified: bool
    missing_rules: list
    total_required: Optional[float] = None
    credits_earned: Optional[float] = None
    remaining_credits: Optional[float] = None
    percent_complete: Optional[float] = None
    remaining_mandatory: list = field(default_factory=list)  # list[Course]
    category_rows: list = field(default_factory=list)  # list[dict]


@dataclass
class PlannedTerm:
    number: int
    courses: list
    credits: float


@dataclass
class GraduationPlan:
    progress: GraduationProgress
    terms: list = field(default_factory=list)
    unscheduled: list = field(default_factory=list)  # list[(Course, reason)]
    messages: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    credit_limit: Optional[float] = None
    limit_source: str = "none"  # "regulation" | "user" | "none"
    complete: bool = False


def _earned_in_category(ctx: rules.Context, category: str) -> float:
    return sum(c.credits for c in ctx.courses.values() if c.category == category and c.code in ctx.passed)


def remaining_category_credits(ctx: rules.Context) -> dict:
    """category -> credits still needed (only for categories with a credit requirement)."""
    required = ctx.regulations.graduation_category_credits
    if required is None or ctx.passed is None:
        return {}
    return {cat: max(0.0, need - _earned_in_category(ctx, cat)) for cat, need in required.items()}


def compute_progress(dataset) -> GraduationProgress:
    ctx = rules.build_context(dataset)
    regs = ctx.regulations
    missing = []
    if ctx.passed is None:
        missing.append("Minimum passing grade points")
    if regs.graduation_total_credits is None:
        missing.append("Total credits required to graduate")
    if regs.graduation_required_categories is None:
        missing.append("Required course categories")
    if regs.graduation_category_credits is None:
        missing.append("Category credit requirements")
    if missing:
        return GraduationProgress(verified=False, missing_rules=missing)

    required_cats = regs.graduation_required_categories
    mandatory = [c for c in ctx.courses.values() if c.category in required_cats]
    remaining_mandatory = sorted((c for c in mandatory if c.code not in ctx.passed), key=lambda c: (c.level, c.code))

    rows = []
    for cat in required_cats:
        cat_courses = [c for c in mandatory if c.category == cat]
        need = sum(c.credits for c in cat_courses)
        earned = sum(c.credits for c in cat_courses if c.code in ctx.passed)
        rows.append(
            {"Category": cat, "Requirement": "All courses in the category", "Required": need, "Earned": earned,
             "Remaining": need - earned}
        )
    for cat, need in regs.graduation_category_credits.items():
        earned = _earned_in_category(ctx, cat)
        rows.append(
            {"Category": cat, "Requirement": "Credits from the category", "Required": need,
             "Earned": min(earned, need) if need else earned, "Remaining": max(0.0, need - earned)}
        )

    total_required = regs.graduation_total_credits
    earned_total = _credits_earned_total(ctx)
    remaining = max(0.0, total_required - earned_total)
    percent = min(1.0, earned_total / total_required) if total_required else None
    return GraduationProgress(
        verified=True,
        missing_rules=[],
        total_required=total_required,
        credits_earned=earned_total,
        remaining_credits=remaining,
        percent_complete=percent,
        remaining_mandatory=remaining_mandatory,
        category_rows=rows,
    )


def _credits_earned_total(ctx: rules.Context) -> float:
    return sum(ctx.courses[code].credits for code in ctx.passed if code in ctx.courses)


def _ready(course: Course, passed: set) -> bool:
    return course.prerequisites_known and all(p in passed for p in course.prerequisites)


def _why_unscheduled(course: Course, passed: set, limit: float) -> str:
    if not course.prerequisites_known:
        return "Its prerequisites are marked UNKNOWN in the curriculum data."
    if course.credits > limit:
        return f"Its {course.credits:g} credits exceed the per-term limit of {limit:g}."
    blocked = [p for p in course.prerequisites if p not in passed]
    if blocked:
        return "A prerequisite could not be scheduled: " + ", ".join(blocked) + "."
    return "No term had room for it."


def build_plan(dataset, user_credit_limit: Optional[float] = None) -> GraduationPlan:
    ctx = rules.build_context(dataset)
    regs = ctx.regulations
    progress = compute_progress(dataset)
    plan = GraduationPlan(progress=progress)

    if not progress.verified:
        plan.messages.append(
            "A verified graduation plan is not possible. Missing: " + "; ".join(progress.missing_rules) + "."
        )
        return plan

    if regs.max_credits_per_semester is not None:
        plan.credit_limit, plan.limit_source = regs.max_credits_per_semester, "regulation"
    elif user_credit_limit:
        plan.credit_limit, plan.limit_source = float(user_credit_limit), "user"
    else:
        plan.messages.append(
            "The official semester credit limit is not provided. Enter your own planning credit load to see a proposed path."
        )
        return plan

    limit = plan.credit_limit
    plan.assumptions = [
        "Every course is assumed to be offered every term: the offering schedule is not part of the data.",
        "Courses are placed as early as their prerequisites and the credit limit allow.",
        "Elective slots are filled in catalog order as placeholders. The student chooses the real electives.",
    ]
    if plan.limit_source == "user":
        plan.assumptions.append("The credit limit per term is your own planning value, not an official rule.")

    passed = set(ctx.passed)
    mandatory = {c.code: c for c in progress.remaining_mandatory}
    need = remaining_category_credits(ctx)
    pools = {
        cat: sorted(
            (c for c in ctx.courses.values() if c.category == cat and c.code not in passed and c.code not in mandatory),
            key=lambda c: (c.level, c.code),
        )
        for cat, remaining in need.items()
        if remaining > 0
    }
    scheduled: set = set()

    for number in range(1, MAX_PLANNED_TERMS + 1):
        picked, load = [], 0.0
        for course in sorted(mandatory.values(), key=lambda c: (c.level, c.code)):
            if course.code in scheduled or not _ready(course, passed):
                continue
            if load + course.credits <= limit:
                picked.append(course)
                load += course.credits
        for cat, pool in pools.items():
            for course in pool:
                if need[cat] <= 0:
                    break
                if course.code in scheduled or not _ready(course, passed):
                    continue
                if load + course.credits <= limit:
                    picked.append(course)
                    load += course.credits
                    need[cat] -= course.credits
        if not picked:
            break
        codes = {c.code for c in picked}
        scheduled |= codes
        passed |= codes
        plan.terms.append(PlannedTerm(number=number, courses=picked, credits=load))
        if all(code in scheduled for code in mandatory) and all(v <= 0 for v in need.values()):
            break

    for course in mandatory.values():
        if course.code not in scheduled:
            plan.unscheduled.append((course, _why_unscheduled(course, passed, limit)))
    for cat, remaining in need.items():
        if remaining > 0:
            plan.messages.append(
                f"{remaining:g} credits of '{cat}' could not be scheduled with the courses available in the catalog."
            )

    planned_credits = sum(t.credits for t in plan.terms)
    plan.complete = not plan.unscheduled and all(v <= 0 for v in need.values())
    if plan.complete and progress.credits_earned + planned_credits < progress.total_required:
        shortfall = progress.total_required - progress.credits_earned - planned_credits
        plan.messages.append(
            f"The listed requirements add up to fewer credits than the {progress.total_required:g} needed to graduate. "
            f"{shortfall:g} more credits are required, and the data does not say which courses they should come from."
        )
        plan.complete = False
    return plan
