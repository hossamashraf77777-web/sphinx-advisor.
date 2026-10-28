import pytest

from services import gpa_calculator as gpa
from tests.conftest import make_regs, rec


def test_gpa_is_credit_weighted(courses, regs):
    # T1 (3 cr) A=4.0 -> 12 ; E1 (3 cr) B=3.0 -> 9 ; 21 / 6 = 3.5
    result = gpa.calculate_gpa([rec("T1", "A"), rec("E1", "B")], courses, regs)
    assert result.gpa == pytest.approx(3.5)
    assert result.credits_attempted == 6
    assert result.credits_earned == 6


def test_failed_course_counts_in_gpa_but_not_in_earned_credits(courses, regs):
    result = gpa.calculate_gpa([rec("T1", "A"), rec("E1", "F")], courses, regs)
    assert result.gpa == pytest.approx(2.0)
    assert result.credits_earned == 3


def test_no_records_gives_no_gpa(courses, regs):
    result = gpa.calculate_gpa([], courses, regs)
    assert result.gpa is None


def test_retake_policy_latest_replaces_old_attempt(courses):
    regs = make_regs(retake_policy="latest")
    records = [rec("T1", "F", 1), rec("T1", "A", 2)]
    assert gpa.calculate_gpa(records, courses, regs).gpa == pytest.approx(4.0)


def test_retake_policy_all_counts_both_attempts(courses):
    regs = make_regs(retake_policy="all")
    records = [rec("T1", "F", 1), rec("T1", "A", 2)]
    assert gpa.calculate_gpa(records, courses, regs).gpa == pytest.approx(2.0)


def test_missing_retake_policy_is_flagged_not_guessed(courses):
    regs = make_regs(retake_policy=None)
    result = gpa.calculate_gpa([rec("T1", "F", 1), rec("T1", "A", 2)], courses, regs)
    assert result.retake_policy_verified is False


def test_missing_grade_scale_raises(courses):
    regs = make_regs(grade_scale={})
    with pytest.raises(gpa.MissingRuleError):
        gpa.calculate_gpa([rec("T1", "A")], courses, regs)


def test_missing_passing_grade_raises_for_pass_check():
    regs = make_regs(min_passing_points=None)
    with pytest.raises(gpa.MissingRuleError):
        gpa.is_passing("A", regs)


def test_passing_boundary(regs):
    assert gpa.is_passing("D", regs) is True  # 1.0 >= 1.0
    assert gpa.is_passing("F", regs) is False
    assert gpa.is_passing("Z", regs) is None  # not in the scale


def test_term_summaries_have_running_cumulative_gpa(courses, regs):
    records = [rec("T1", "A", 1), rec("E1", "B", 2)]
    terms = gpa.term_summaries(records, courses, regs)
    assert [t.term_order for t in terms] == [1, 2]
    assert terms[0].term_gpa == pytest.approx(4.0)
    assert terms[1].term_gpa == pytest.approx(3.0)
    assert terms[1].cumulative_gpa == pytest.approx(3.5)
    assert terms[1].cumulative_credits_earned == 6


def test_project_gpa_adds_a_future_term(courses, regs):
    records = [rec("T1", "A", 1)]
    projected = gpa.project_gpa(records, [("E1", "B")], courses, regs)
    assert projected.gpa == pytest.approx(3.5)


def test_project_gpa_rejects_bad_input(courses, regs):
    with pytest.raises(ValueError):
        gpa.project_gpa([], [("NOPE", "A")], courses, regs)
    with pytest.raises(ValueError):
        gpa.project_gpa([], [("T1", "Z")], courses, regs)
