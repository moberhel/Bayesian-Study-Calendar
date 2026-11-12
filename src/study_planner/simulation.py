"""Toy student simulator and the day-by-day planning loop.

The simulator's dynamics are only used to roll the demo forward; every decision is made by the
Bayes net in `decision.py`.
"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
import numpy as np
from .inference import BayesNet
from .decision import decide
from .calendars.base import CalendarBackend, apply_action

def days_bucket(n: int) -> str:
    return "Few" if n <= 2 else "Some" if n <= 6 else "Many"

def quiz_from_progress(p: float) -> str:
    return "Poor" if p < 0.35 else "OK" if p < 0.7 else "Good"

@dataclass
class Student:
    name: str
    concepts: dict[str, str]        # concept -> "Easy" | "Hard"
    progress: float                 # hidden true mastery in [0,1] -> drives simulated quiz result
    stress_pts: float               # 0..5, >=2.5 -> "High"
    # toy "environment" dynamics (used ONLY to roll the simulation forward day by day;
    # decisions are made by the Bayes net)
    PROG = {"Intense5h": 0.14, "Moderate3h": 0.085, "Light1h": 0.035, "Rest": 0.0}
    STR = {"Intense5h": +1.2, "Moderate3h": +0.4, "Light1h": -0.1, "Rest": -1.2}

    def evidence(self, days_left: int) -> dict[str, str]:
        ev = {f"Diff{i+1}": d for i, d in enumerate(self.concepts.values())}
        ev.update(Quiz=quiz_from_progress(self.progress), DaysLeft=days_bucket(days_left),
                  Stress="High" if self.stress_pts >= 2.5 else "Low")
        return ev

    def step(self, action: str):
        self.progress = min(1.0, self.progress + self.PROG[action])
        self.stress_pts = float(np.clip(self.stress_pts + self.STR[action], 0, 5))


def study_focus(student: Student) -> list[str]:
    """Concepts to put in the session title: Hard ones first."""
    hard = [c for c, d in student.concepts.items() if d == "Hard"]
    return hard or list(student.concepts)[:1]


def plan(student: Student, exam_name: str, exam_date: dt.date, today: dt.date,
         cal: CalendarBackend, bn: BayesNet, verbose=True):
    rows, day = [], today
    while day < exam_date:
        n = (exam_date - day).days
        ev = student.evidence(n)
        d = decide(bn, ev)
        why = (f"Evidence: {ev}. E[U]: " + ", ".join(f"{a}={u:.1f}" for a, u in d.eu.items()))
        apply_action(cal, day, d.best, study_focus(student), exam_name, why)
        rows.append((day, n, ev, d, student.progress, student.stress_pts))
        student.step(d.best)
        day += dt.timedelta(days=1)
    return rows
