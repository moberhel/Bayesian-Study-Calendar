import numpy as np
from study_planner.inference import BayesNet

EVIDENCE_SETS = [
    {},
    {"Quiz": "Poor"},
    {"Diff1": "Hard", "Diff2": "Easy", "Diff3": "Hard", "Quiz": "OK", "DaysLeft": "Few",
     "Stress": "High", "Action": "Rest"},
    {"Diff1": "Easy", "Diff2": "Easy", "Diff3": "Easy", "Quiz": "Good", "DaysLeft": "Many",
     "Stress": "Low", "Action": "Intense5h"},
    {"Mastery": "Med", "Action": "Light1h", "DaysLeft": "Some"},
]


def test_variable_elimination_matches_bruteforce():
    bn = BayesNet()
    for ev in EVIDENCE_SETS:
        for target in ["Grade", "FutureStress", "Mastery", "Quiz"]:
            if target in ev:
                continue
            ve = bn.query([target], ev).table
            bf = bn.query_bruteforce(target, ev)
            assert np.allclose(ve, bf), (target, ev)


def test_posteriors_are_distributions():
    bn = BayesNet()
    for ev in EVIDENCE_SETS:
        t = bn.query(["Grade"], ev).table
        assert np.isclose(t.sum(), 1.0) and (t >= 0).all()


def test_joint_query_marginalizes_correctly():
    bn = BayesNet()
    ev = {"Quiz": "Poor", "DaysLeft": "Few"}
    joint = bn.query(["Grade", "FutureStress"], ev).table
    assert joint.shape == (3, 2)
    assert np.allclose(joint.sum(axis=1), bn.query(["Grade"], ev).table)
    assert np.allclose(joint.sum(axis=0), bn.query(["FutureStress"], ev).table)


def test_quiz_evidence_moves_mastery_in_the_right_direction():
    bn = BayesNet()
    poor = bn.query(["Mastery"], {"Quiz": "Poor"}).table
    good = bn.query(["Mastery"], {"Quiz": "Good"}).table
    assert poor[0] > good[0] and good[2] > poor[2]
