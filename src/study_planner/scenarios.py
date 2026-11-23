"""Student scenarios and one-day snapshots used by the demo and the tests."""
from __future__ import annotations
import datetime as dt
from .simulation import Student
from .calendars.base import Event, CalendarBackend

TODAY = dt.date.today()
EXAM = TODAY + dt.timedelta(days=8)


def make_students() -> dict[str, Student]:
    """Fresh (mutable) Student objects, one per scenario."""
    return {
        "STRUGGLING": Student("struggling", {"Bayes nets": "Hard", "Inference": "Hard", "Utility": "Hard"}, 0.10, 1.0),
        "ADVANCED": Student("advanced", {"Bayes nets": "Easy", "Inference": "Easy", "Utility": "Easy"}, 0.80, 0.5),
        "MIXED (one hard concept)": Student("mixed", {"Bayes nets": "Easy", "Inference": "Hard", "Utility": "Easy"}, 0.45, 1.5),
        "ANXIOUS ADVANCED": Student("anxious", {"Bayes nets": "Easy", "Inference": "Easy", "Utility": "Hard"}, 0.65, 3.5),
    }


SNAPSHOTS = {
    "Struggling student, 2 days to exam":
        dict(Diff1="Hard", Diff2="Hard", Diff3="Hard", Quiz="Poor", DaysLeft="Few", Stress="Low"),
    "Struggling student, 8 days to exam":
        dict(Diff1="Hard", Diff2="Hard", Diff3="Hard", Quiz="Poor", DaysLeft="Many", Stress="Low"),
    "Advanced student, 8 days to exam":
        dict(Diff1="Easy", Diff2="Easy", Diff3="Easy", Quiz="Good", DaysLeft="Many", Stress="Low"),
    "Advanced but burnt out, 4 days to exam":
        dict(Diff1="Easy", Diff2="Easy", Diff3="Easy", Quiz="Good", DaysLeft="Some", Stress="High"),
}


def add_existing_commitments(cal: CalendarBackend, start: dt.date = TODAY, end: dt.date = EXAM) -> None:
    """A lecture (10-12) and a part-time job (15-17) every day, so the scheduler must work around them."""
    for i in range((end - start).days):
        day = start + dt.timedelta(days=i)
        at = lambda h: dt.datetime.combine(day, dt.time(h))
        cal.insert(Event("Lecture", at(10), at(12)))
        cal.insert(Event("Part-time job", at(15), at(17)))
