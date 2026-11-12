import itertools
from study_planner.inference import BayesNet
from study_planner.decision import decide, utility
from study_planner.simulation import plan
from study_planner.calendars import LocalICSCalendar, HOURS
from study_planner.scenarios import make_students, add_existing_commitments, TODAY, EXAM

bn = BayesNet()


def hours(action):
    return HOURS.get(action, 0)


def ev(d1, d2, d3, quiz="OK", days="Some", stress="Low"):
    return dict(Diff1=d1, Diff2=d2, Diff3=d3, Quiz=quiz, DaysLeft=days, Stress=stress)


def run_plan(name):
    student = make_students()[name]
    cal = LocalICSCalendar()
    add_existing_commitments(cal)
    return [r[3].best for r in plan(student, "Exam", EXAM, TODAY, cal, bn)]


def test_best_action_is_argmax_of_expected_utility():
    d = decide(bn, ev("Hard", "Easy", "Hard"))
    assert d.eu[d.best] == max(d.eu.values())


def test_utility_trades_score_against_stress():
    import numpy as np
    p = np.array([0.1, 0.4, 0.5])
    assert utility(p, 0.0) > utility(p, 0.5)          # more stress -> lower utility
    assert utility(p, 0.3, stress_weight=0) > utility(p, 0.3, stress_weight=30)


def test_struggling_student_gets_more_study_than_advanced():
    struggling = sum(hours(a) for a in run_plan("STRUGGLING"))
    advanced = sum(hours(a) for a in run_plan("ADVANCED"))
    assert struggling > advanced


def test_system_uses_at_least_three_distinct_actions_across_scenarios():
    used = set()
    for name in make_students():
        used |= set(run_plan(name))
    assert len(used) >= 3


def test_more_hard_concepts_never_lowers_intensity():
    """Fixed quiz/days/stress: study hours are non-decreasing in the number of Hard concepts."""
    by_count = {}
    for combo in itertools.product(["Easy", "Hard"], repeat=3):
        by_count.setdefault(combo.count("Hard"), []).append(hours(decide(bn, ev(*combo)).best))
    levels = [max(by_count[k]) for k in sorted(by_count)]
    assert levels == sorted(levels)
    assert hours(decide(bn, ev("Hard", "Hard", "Hard")).best) > hours(decide(bn, ev("Easy", "Easy", "Easy")).best)


def test_high_stress_never_increases_intensity():
    """Same everything except Stress: High stress never yields MORE study hours than Low."""
    for combo in itertools.product(["Easy", "Hard"], repeat=3):
        for quiz in ["Poor", "OK", "Good"]:
            for days in ["Few", "Some", "Many"]:
                low = hours(decide(bn, ev(*combo, quiz, days, "Low")).best)
                high = hours(decide(bn, ev(*combo, quiz, days, "High")).best)
                assert high <= low, (combo, quiz, days, low, high)


def test_higher_stress_weight_never_increases_intensity():
    for combo in itertools.product(["Easy", "Hard"], repeat=3):
        e = ev(*combo)
        h = [hours(decide(bn, e, stress_weight=lam).best) for lam in (0, 15, 30, 60, 120)]
        assert h == sorted(h, reverse=True), (combo, h)


def test_burnt_out_advanced_student_rests():
    d = decide(bn, ev("Easy", "Easy", "Easy", "Good", "Some", "High"))
    assert d.best == "Rest"


def test_unprepared_student_close_to_exam_studies_hard():
    d = decide(bn, ev("Hard", "Hard", "Hard", "Poor", "Few", "Low"))
    assert d.best == "Intense5h"
