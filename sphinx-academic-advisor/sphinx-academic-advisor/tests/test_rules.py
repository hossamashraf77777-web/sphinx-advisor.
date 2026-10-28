from agent import eligibility, rules
from agent.models import Status
from tests.conftest import make_dataset, rec


def ctx_for(records=(), **reg_overrides):
    return rules.build_context(make_dataset(records, **reg_overrides))


def test_prerequisite_not_met_is_rejected_with_explanation():
    ctx = ctx_for()
    decision = rules.rule_prerequisites(ctx.courses["T2"], ctx)
    assert decision.status == Status.FAILED
    assert "T1" in decision.explanation


def test_prerequisite_met_when_passed():
    ctx = ctx_for([rec("T1", "B")])
    assert rules.rule_prerequisites(ctx.courses["T2"], ctx).status == Status.PASSED


def test_failed_prerequisite_does_not_count():
    ctx = ctx_for([rec("T1", "F")])
    assert rules.rule_prerequisites(ctx.courses["T2"], ctx).status == Status.FAILED


def test_course_without_prerequisites_passes():
    ctx = ctx_for()
    assert rules.rule_prerequisites(ctx.courses["T1"], ctx).status == Status.PASSED


def test_unknown_prerequisites_need_verification():
    ctx = ctx_for()
    assert rules.rule_prerequisites(ctx.courses["U1"], ctx).status == Status.NEEDS_VERIFICATION


def test_missing_passing_grade_means_needs_verification_not_a_guess():
    ctx = ctx_for([rec("T1", "A")], min_passing_points=None)
    assert ctx.passed is None
    assert rules.rule_prerequisites(ctx.courses["T2"], ctx).status == Status.NEEDS_VERIFICATION


def test_already_passed_course_is_rejected():
    ctx = ctx_for([rec("T1", "B")])
    assert rules.rule_not_already_completed(ctx.courses["T1"], ctx).status == Status.FAILED


def test_failed_course_can_be_attempted_again_when_policy_known():
    ctx = ctx_for([rec("T1", "F")], retake_policy="latest")
    evaluation = eligibility.evaluate_course(ctx.courses["T1"], ctx)
    assert evaluation.status == Status.PASSED
    assert any(d.rule == rules.RULE_RETAKE for d in evaluation.decisions)


def test_retake_without_policy_needs_verification():
    ctx = ctx_for([rec("T1", "F")], retake_policy=None)
    assert eligibility.evaluate_course(ctx.courses["T1"], ctx).status == Status.NEEDS_VERIFICATION


def test_overall_status_failed_wins_over_needs_verification():
    ctx = ctx_for([rec("T1", "B")], retake_policy=None)
    # T1 already passed -> FAILED, even though other checks could be unverified
    assert eligibility.evaluate_course(ctx.courses["T1"], ctx).status == Status.FAILED


def test_credit_limit_rule():
    regs = ctx_for().regulations
    assert rules.rule_credit_load(6, regs).status == Status.PASSED
    assert rules.rule_credit_load(7, regs).status == Status.FAILED
    no_cap = ctx_for(max_credits_per_semester=None).regulations
    assert rules.rule_credit_load(6, no_cap).status == Status.NEEDS_VERIFICATION


def test_good_standing_rule():
    regs = ctx_for().regulations
    assert rules.rule_good_standing(2.5, regs).status == Status.PASSED
    assert rules.rule_good_standing(1.5, regs).status == Status.FAILED
    assert rules.rule_good_standing(None, regs).status == Status.NEEDS_VERIFICATION
    unknown = ctx_for(min_cgpa_good_standing=None).regulations
    assert rules.rule_good_standing(3.9, unknown).status == Status.NEEDS_VERIFICATION


def test_every_decision_has_rule_status_and_explanation():
    ctx = ctx_for([rec("T1", "F")])
    for evaluation in eligibility.evaluate_all(ctx).values():
        for d in evaluation.decisions:
            assert d.rule and d.explanation and isinstance(d.status, Status)
