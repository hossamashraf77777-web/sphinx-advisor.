"""High-level advising: academic standing, alerts, a text report, and the list of rules in use."""

from dataclasses import dataclass

from agent import eligibility, graduation, recommendations, rules
from agent.models import Decision, Status
from services import gpa_calculator as gpa


@dataclass(frozen=True)
class Alert:
    level: str  # "danger" | "warning" | "info"
    title: str
    message: str


def current_cgpa(dataset):
    """Cumulative GPA, or None if it cannot be calculated."""
    try:
        return gpa.calculate_gpa(dataset.student.records, dataset.courses, dataset.regulations).gpa
    except gpa.MissingRuleError:
        return None


def evaluate_standing(dataset) -> Decision:
    return rules.rule_good_standing(current_cgpa(dataset), dataset.regulations)


def build_alerts(dataset) -> list:
    ctx = rules.build_context(dataset)
    alerts = []

    standing = evaluate_standing(dataset)
    if standing.status == Status.FAILED:
        alerts.append(Alert("danger", "Academic standing", standing.explanation))
    elif standing.status == Status.NEEDS_VERIFICATION:
        alerts.append(Alert("info", "Academic standing cannot be verified", standing.explanation))

    if ctx.passed is not None:
        for code in sorted(ctx.attempted - ctx.passed):
            alerts.append(
                Alert(
                    "warning",
                    f"Failed course: {rules.label(ctx, code)}",
                    "This course has no passing attempt. See the Semester Recommendations page for retake advice.",
                )
            )

    for issue in dataset.issues:
        if issue.level == "warning":
            alerts.append(Alert("info", "Missing information", issue.message))

    order = {"danger": 0, "warning": 1, "info": 2}
    return sorted(alerts, key=lambda a: order[a.level])


def rules_in_use(regs) -> list:
    """Rows describing every regulation value and whether it was provided."""

    def row(name, value, provided):
        return {"Rule": name, "Value": value if provided else "-", "Provided": "Yes" if provided else "No"}

    grad_cats = regs.graduation_category_credits
    return [
        row("Grade scale", ", ".join(f"{g}={p:g}" for g, p in regs.grade_scale.items()), bool(regs.grade_scale)),
        row("Minimum passing grade points", regs.min_passing_points, regs.min_passing_points is not None),
        row("Retake policy", regs.retake_policy, regs.retake_policy is not None),
        row("Maximum credits per semester", regs.max_credits_per_semester, regs.max_credits_per_semester is not None),
        row("Minimum CGPA for good standing", regs.min_cgpa_good_standing, regs.min_cgpa_good_standing is not None),
        row("Total credits to graduate", regs.graduation_total_credits, regs.graduation_total_credits is not None),
        row(
            "Mandatory categories",
            ", ".join(regs.graduation_required_categories or []),
            regs.graduation_required_categories is not None,
        ),
        row(
            "Category credit requirements",
            ", ".join(f"{k}: {v:g}" for k, v in (grad_cats or {}).items()),
            grad_cats is not None,
        ),
    ]


def build_report(dataset, user_credit_budget=None) -> str:
    """A plain-text advising summary that can be downloaded. Always states the data source."""
    student = dataset.student
    lines = ["ACADEMIC ADVISING SUMMARY", "=" * 25]
    if dataset.is_demo:
        lines += ["WARNING: DEMONSTRATION DATA. This is NOT official university advice.", ""]
    lines += [f"Student: {student.name} ({student.student_id})", f"Program: {student.program}", ""]

    cgpa = current_cgpa(dataset)
    lines.append("CGPA: " + (f"{cgpa:.2f}" if cgpa is not None else "not available"))
    standing = evaluate_standing(dataset)
    lines.append(f"Standing check: {standing.status.value} - {standing.explanation}")

    progress = graduation.compute_progress(dataset)
    if progress.verified:
        lines.append(f"Credits earned: {progress.credits_earned:g} of {progress.total_required:g} required")
    else:
        lines.append("Graduation progress: cannot be verified (missing: " + "; ".join(progress.missing_rules) + ")")

    lines += ["", "RECOMMENDED COURSES"]
    result = recommendations.recommend_courses(dataset, user_credit_budget)
    if not result.recommended:
        lines.append("None.")
    for rec in result.recommended:
        lines.append(f"- {rec.course.code} {rec.course.title} ({rec.course.credits:g} cr) [{rec.evaluation.status.value}]")
        lines.append(f"    {rec.reason}")
    lines += ["", "CREDIT LOAD CHECKS"]
    lines += [f"- {d.rule}: {d.status.value} - {d.explanation}" for d in result.credit_decisions]
    lines += ["", "ALERTS"]
    alerts = build_alerts(dataset)
    lines += [f"- [{a.level}] {a.title}: {a.message}" for a in alerts] or ["None."]
    return "\n".join(lines) + "\n"
