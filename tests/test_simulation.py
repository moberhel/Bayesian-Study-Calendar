from study_planner.inference import BayesNet
from study_planner.simulation import plan, days_bucket, quiz_from_progress
from study_planner.calendars import LocalICSCalendar
from study_planner.scenarios import make_students, TODAY, EXAM


def test_days_bucket_boundaries():
    assert [days_bucket(n) for n in (1, 2, 3, 6, 7, 30)] == ["Few", "Few", "Some", "Some", "Many", "Many"]


def test_quiz_thresholds():
    assert [quiz_from_progress(p) for p in (0.0, 0.34, 0.35, 0.69, 0.7, 1.0)] == \
        ["Poor", "Poor", "OK", "OK", "Good", "Good"]


def test_one_decision_per_day_until_exam():
    rows = plan(make_students()["ADVANCED"], "Exam", EXAM, TODAY, LocalICSCalendar(), BayesNet())
    assert len(rows) == (EXAM - TODAY).days
    assert [r[1] for r in rows] == list(range((EXAM - TODAY).days, 0, -1))


def test_planning_is_deterministic():
    a = [r[3].best for r in plan(make_students()["MIXED (one hard concept)"], "E", EXAM, TODAY, LocalICSCalendar(), BayesNet())]
    b = [r[3].best for r in plan(make_students()["MIXED (one hard concept)"], "E", EXAM, TODAY, LocalICSCalendar(), BayesNet())]
    assert a == b
