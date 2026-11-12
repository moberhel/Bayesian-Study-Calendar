"""Bayesian network structure and handcrafted CPTs.

Ten variables: Diff1-3, Mastery, Quiz, DaysLeft, Stress, Action (decision), Grade, FutureStress.
Every parameter below is a named constant with a comment explaining what it means; see also
docs/model_parameters.md.
"""
from __future__ import annotations
import itertools
import math
import numpy as np

# =====================================================================
# 1. BAYESIAN NETWORK  (10 variables)
# =====================================================================
#
#   Diff1  Diff2  Diff3        DaysLeft     Stress(now)
#      \     |     /             |    \         |
#       v    v    v              |     \        |
#          Mastery ---> Quiz     |      \       |
#             |  \               |       \      |
#             |   \              v        v     v
#             |    +-----> Grade <--Action--> FutureStress
#             +---------------------------------^  (Mastery also -> FutureStress)
#
# Action is a DECISION node: we never infer it, we *set* it (do(Action=a)).
#
# State spaces
STATES = {
    "Diff1":        ["Easy", "Hard"],            # concept 1 difficulty (observed: syllabus/self-rating)
    "Diff2":        ["Easy", "Hard"],
    "Diff3":        ["Easy", "Hard"],
    "Mastery":      ["Low", "Med", "High"],      # LATENT true mastery of the material
    "Quiz":         ["Poor", "OK", "Good"],      # noisy observation of mastery (practice-quiz result)
    "DaysLeft":     ["Few", "Some", "Many"],     # <=2 days, 3-6 days, >=7 days to exam
    "Stress":       ["Low", "High"],             # current stress (observed: self-report / wearable)
    "Action":       ["Intense5h", "Moderate3h", "Light1h", "Rest"],
    "Grade":        ["Low", "Mid", "High"],      # exam outcome (<60, 60-85, >85)
    "FutureStress": ["Low", "High"],             # cramming/burnout stress carried into the exam window
}
PARENTS = {
    "Diff1": [], "Diff2": [], "Diff3": [], "DaysLeft": [], "Stress": [], "Action": [],
    "Mastery": ["Diff1", "Diff2", "Diff3"],
    "Quiz": ["Mastery"],
    "Grade": ["Mastery", "Action", "DaysLeft"],
    "FutureStress": ["Stress", "Action", "DaysLeft", "Mastery"],
}
ORDER = ["Diff1", "Diff2", "Diff3", "DaysLeft", "Stress", "Action",
         "Mastery", "Quiz", "Grade", "FutureStress"]


def sigmoid(x): return 1.0 / (1.0 + math.exp(-x))


# ---- Handcrafted parameters (every number here is explained) ----------------

# P(Mastery | #hard concepts).  Prior belief about how well a typical student has
# mastered the material before seeing any quiz data: harder content -> lower mastery.
# columns = [Low, Med, High]
MASTERY_BY_NUM_HARD = {
    0: [0.10, 0.30, 0.60],
    1: [0.20, 0.40, 0.40],
    2: [0.40, 0.40, 0.20],
    3: [0.60, 0.30, 0.10],
}
# P(Quiz | Mastery): a practice quiz is a noisy sensor (~70% diagnostic).
QUIZ_GIVEN_MASTERY = {
    "Low":  [0.70, 0.25, 0.05],
    "Med":  [0.25, 0.50, 0.25],
    "High": [0.05, 0.25, 0.70],
}
# Grade model: effective preparedness s = base(mastery) + gain(action) * urgency(days)
BASE = {"Low": 0.0, "Med": 1.2, "High": 2.6}          # starting preparedness (0-2 scale)
GAIN = {"Intense5h": 1.0, "Moderate3h": 0.6, "Light1h": 0.25, "Rest": 0.0}
# Marginal value of TODAY's session. Plenty of time left -> a skipped session can
# be made up later; few days left -> it can't.
URGENCY = {"Many": 0.8, "Some": 0.9, "Few": 1.0}
# Ordinal-logistic thresholds: P(Grade>=Mid)=sig((s-T_MID)/W), P(Grade=High)=sig((s-T_HIGH)/W)
T_MID, T_HIGH, W = 0.7, 1.9, 0.4

# FutureStress logit:
#   z = B0 + current_stress + action_fatigue + CRAM[mastery][days] * (1 - RELIEF * gain(action))
#   P(High) = sigmoid(z)
# The CRAM term is the "last-minute cramming" stress: being unprepared (low mastery) AND close to
# the deadline.  Studying today relieves it in proportion to how much it moves you forward, so
# putting work off is NOT free: it keeps a large cramming term alive for later.
S_B0 = -1.0
S_CURRENT = {"Low": 0.0, "High": 1.5}                  # stressed people stay stressed
S_FATIGUE = {"Intense5h": 1.0, "Moderate3h": 0.1, "Light1h": -0.2, "Rest": -0.6}   # direct fatigue / recovery
CRAM = {  # rows: mastery ; cols: Few, Some, Many
    "Low":  {"Few": 2.4, "Some": 1.6, "Many": 1.1},
    "Med":  {"Few": 1.2, "Some": 0.6, "Many": 0.2},
    "High": {"Few": -0.2, "Some": -0.4, "Many": -0.6},
}
RELIEF = 0.8
BURNOUT_AMP = 1.5   # when already High-stress, fatigue (and recovery) effects are 2.5x as strong


def build_cpts() -> dict[str, np.ndarray]:
    """Return CPTs as arrays shaped [parent1_states..., own_states]."""
    cpt: dict[str, np.ndarray] = {}
    cpt["Diff1"] = cpt["Diff2"] = cpt["Diff3"] = np.array([0.5, 0.5])
    cpt["DaysLeft"] = np.array([1/3, 1/3, 1/3])
    cpt["Stress"] = np.array([0.6, 0.4])
    cpt["Action"] = np.full(4, 0.25)                    # uniform; always overridden by do(.)

    m = np.zeros((2, 2, 2, 3))
    for i, j, k in itertools.product(range(2), repeat=3):
        m[i, j, k] = MASTERY_BY_NUM_HARD[i + j + k]
    cpt["Mastery"] = m

    cpt["Quiz"] = np.array([QUIZ_GIVEN_MASTERY[s] for s in STATES["Mastery"]])

    g = np.zeros((3, 4, 3, 3))                          # Mastery, Action, DaysLeft, Grade
    for mi, ms in enumerate(STATES["Mastery"]):
        for ai, a in enumerate(STATES["Action"]):
            for di, d in enumerate(STATES["DaysLeft"]):
                s = BASE[ms] + GAIN[a] * URGENCY[d]
                p_ge_mid, p_high = sigmoid((s - T_MID) / W), sigmoid((s - T_HIGH) / W)
                g[mi, ai, di] = [1 - p_ge_mid, p_ge_mid - p_high, p_high]
    cpt["Grade"] = g

    f = np.zeros((2, 4, 3, 3, 2))                       # Stress, Action, DaysLeft, Mastery, FS
    for si, st in enumerate(STATES["Stress"]):
        for ai, a in enumerate(STATES["Action"]):
            for di, d in enumerate(STATES["DaysLeft"]):
                for mi, ms in enumerate(STATES["Mastery"]):
                    z = (S_B0 + S_CURRENT[st] + S_FATIGUE[a] * (1 + BURNOUT_AMP * (st == "High"))
                         + CRAM[ms][d] * (1 - RELIEF * GAIN[a]))
                    f[si, ai, di, mi] = [1 - sigmoid(z), sigmoid(z)]
    cpt["FutureStress"] = f
    return cpt
