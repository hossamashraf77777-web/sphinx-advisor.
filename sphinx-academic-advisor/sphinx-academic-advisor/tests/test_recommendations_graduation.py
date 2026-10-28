from agent import advisor, graduation, recommendations
from agent.models import Status
from tests.conftest import make_dataset, rec


def codes(items):
    return [r.course.code for r in items]


def test_recommendations_respect_prerequisites():
    result = recommendations.recommend_courses(make_dataset([]))
    recommended = codes(result.recommended)
    assert "T1" in recommended
    assert "T2" not in recommended and "T3" not in recommended
    assert {e.course.code for e in result.rejected} >= {"T2", "T3"}


def test_completed_courses_are_not_recommended():
    result = recommendations.recommend_courses(make_dataset([rec("T1", "A")]))
    assert "T1" not in codes(result.recommended)
    assert "T1" in result.completed
    assert "T2" in codes(result.recommended)


def test_failed_course_is_recommended_first_as_retake():
    result = recommendations.recommend_courses(make_dataset([rec("T1", "F")]))
    assert codes(result.recommended)[0] == "T1"
    assert result.recommended[0].tier == 0


def test_official_credit_limit_is_enforced():
    # limit is 6 in the test rules: only two 3-credit courses fit
    result = recommendations.recommend_courses(make_dataset([rec("T1", "A")]))
    assert result.total_credits <= 6
    assert result.limit_source == "regulation"
    assert result.deferred  # something eligible was left out


def test_user_budget_is_used_only_when_no_official_limit():
    ds = make_dataset([], max_credits_per_semester=None)
    result = recommendations.recommend_courses(ds, user_credit_budget=3)
    assert result.limit_source == "user"
    assert result.total_credits == 3
    statuses = [d.status for d in result.credit_decisions]
    assert Status.NEEDS_VERIFICATION in statuses  # official limit still unverified


def test_user_budget_cannot_exceed_official_limit():
    result = recommendations.recommend_courses(make_dataset([]), user_credit_budget=30)
    assert result.credit_limit == 6
    assert result.notes


def test_no_limit_anywhere_is_reported_as_unverified():
    ds = make_dataset([], max_credits_per_semester=None)
    result = recommendations.recommend_courses(ds)
    assert result.limit_source == "none"
    assert result.credit_decisions[0].status == Status.NEEDS_VERIFICATION


def test_elective_not_recommended_once_requirement_met():
    ds = make_dataset([rec("E1", "A")])
    result = recommendations.recommend_courses(ds)
    assert "U1" not in codes(result.recommended)
    assert "U1" in codes(result.deferred)


def test_progress_counts_only_passed_courses():
    ds = make_dataset([rec("T1", "A"), rec("T2", "F")])
    progress = graduation.compute_progress(ds)
    assert progress.verified
    assert progress.credits_earned == 3
    assert progress.remaining_credits == 9  # 12 required - 3 earned
    assert [c.code for c in progress.remaining_mandatory] == ["T2", "T3"]


def test_progress_not_verified_when_requirements_missing():
    ds = make_dataset([], graduation_total_credits=None)
    progress = graduation.compute_progress(ds)
    assert not progress.verified
    assert "Total credits required to graduate" in progress.missing_rules
    plan = graduation.build_plan(ds, 6)
    assert plan.terms == [] and plan.messages


def test_plan_needs_a_credit_limit():
    ds = make_dataset([], max_credits_per_semester=None)
    plan = graduation.build_plan(ds)
    assert plan.terms == []
    assert any("credit limit" in m for m in plan.messages)


def test_plan_orders_courses_by_prerequisites():
    ds = make_dataset([], max_credits_per_semester=None)
    plan = graduation.build_plan(ds, user_credit_limit=6)
    order = {c.code: t.number for t in plan.terms for c in t.courses}
    assert order["T1"] < order["T2"] < order["T3"]
    assert all(t.credits <= 6 for t in plan.terms)
    assert "E1" in order  # elective credits are scheduled too
    assert plan.complete
    assert plan.limit_source == "user"


def test_plan_reports_course_that_cannot_fit_the_limit():
    ds = make_dataset([], max_credits_per_semester=None)
    plan = graduation.build_plan(ds, user_credit_limit=2)
    assert plan.unscheduled
    assert not plan.complete


def test_alerts_include_failed_courses_and_missing_standing_rule():
    ds = make_dataset([rec("T1", "F")], min_cgpa_good_standing=None)
    titles = [a.title for a in advisor.build_alerts(ds)]
    assert any("Failed course" in t for t in titles)
    assert any("cannot be verified" in t for t in titles)


def test_low_cgpa_creates_danger_alert():
    ds = make_dataset([rec("T1", "F")])
    alerts = advisor.build_alerts(ds)
    assert alerts[0].level == "danger"


def test_report_states_demo_warning():
    assert "DEMONSTRATION DATA" in advisor.build_report(make_dataset([rec("T1", "A")]))
