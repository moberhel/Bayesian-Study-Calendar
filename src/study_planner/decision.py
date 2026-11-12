"""Utility function and expected-utility maximisation over the four study actions."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .model import STATES
from .inference import BayesNet

# =====================================================================
# 3. UTILITY FUNCTION + DECISION
# =====================================================================
GRADE_VALUE = {"Low": 50.0, "Mid": 75.0, "High": 95.0}   # % score represented by each state
STRESS_COST = 30.0       # lambda: utility points lost if the student ends up High-stress

def utility(p_grade: np.ndarray, p_stress_high: float, stress_weight=STRESS_COST) -> float:
    """U(a) = E[exam score | a]  -  lambda * P(FutureStress=High | a)"""
    exp_score = sum(p * GRADE_VALUE[g] for p, g in zip(p_grade, STATES["Grade"]))
    return exp_score - stress_weight * p_stress_high


@dataclass
class Decision:
    best: str
    eu: dict[str, float]
    exp_score: dict[str, float]
    p_stress: dict[str, float]
    p_mastery: np.ndarray


def decide(bn: BayesNet, evidence: dict[str, str], stress_weight=STRESS_COST) -> Decision:
    """
    INFERENCE TASK: for each action a, compute (with Action=a as evidence)
        P(Grade | e, do(a))            and        P(FutureStress | e, do(a))
    where e = {Diff1..3, Quiz, DaysLeft, Stress}.  Then pick argmax_a U(a).
    """
    eu, es, ps = {}, {}, {}
    for a in STATES["Action"]:
        ev = {**evidence, "Action": a}
        pg = bn.query(["Grade"], ev).table
        pf = bn.query(["FutureStress"], ev).table
        es[a] = float(sum(p * GRADE_VALUE[g] for p, g in zip(pg, STATES["Grade"])))
        ps[a] = float(pf[1])
        eu[a] = float(utility(pg, ps[a], stress_weight))
    pm = bn.query(["Mastery"], evidence).table
    return Decision(max(eu, key=eu.get), eu, es, ps, pm)
