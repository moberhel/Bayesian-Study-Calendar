"""Calendar-agnostic types and scheduling logic (finding free time, writing an action)."""
from __future__ import annotations
import datetime as dt
import uuid
from dataclasses import dataclass, field

TAG = "bayes-study-planner"      # marks events the planner created (safe to overwrite)

@dataclass
class Event:
    summary: str
    start: dt.datetime
    end: dt.datetime
    description: str = ""
    all_day: bool = False
    system: bool = False
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))


class CalendarBackend:
    def list_events(self, day: dt.date) -> list[Event]: raise NotImplementedError
    def insert(self, ev: Event) -> None: raise NotImplementedError
    def delete(self, ev: Event) -> None: raise NotImplementedError


DAY_START, DAY_END = 8, 22          # student's available hours
HOURS = {"Intense5h": 5, "Moderate3h": 3, "Light1h": 1}

def free_slots(cal: CalendarBackend, day: dt.date):
    """Return free (start,end) intervals within DAY_START..DAY_END, ignoring planner events."""
    busy = sorted((e.start, e.end) for e in cal.list_events(day) if not e.system and not e.all_day)
    cur, out = dt.datetime.combine(day, dt.time(DAY_START)), []
    end = dt.datetime.combine(day, dt.time(DAY_END))
    for s, e in busy:
        if s > cur: out.append((cur, min(s, end)))
        cur = max(cur, e)
    if cur < end: out.append((cur, end))
    return [(s, e) for s, e in out if e > s]


def apply_action(cal: CalendarBackend, day: dt.date, action: str, concepts: list[str],
                 exam_name: str, why: str) -> list[Event]:
    """Idempotently write the chosen action to the calendar for `day`."""
    for e in cal.list_events(day):                     # clear previous planner events
        if e.system: cal.delete(e)
    made = []
    if action == "Rest":
        ev = Event(f"REST DAY (protected) - {exam_name}", dt.datetime.combine(day, dt.time.min),
                   dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min),
                   description=why, all_day=True, system=True)
        cal.insert(ev); return [ev]
    need = timedelta_h(HOURS[action])
    label = {"Intense5h": "MANDATORY intense study", "Moderate3h": "Study block",
             "Light1h": "Light review"}[action]
    # greedily fill free time: longest slots first, split blocks if no single slot fits
    for s, e in sorted(free_slots(cal, day), key=lambda x: x[0] - x[1]):
        if need <= dt.timedelta(0): break
        take = min(need, e - s)
        if take < dt.timedelta(minutes=45) and need > take: continue
        ev = Event(f"{label}: {', '.join(concepts)} [{exam_name}]", s, s + take,
                   description=why, system=True)
        cal.insert(ev); made.append(ev); need -= take
    return made


def timedelta_h(h): return dt.timedelta(hours=h)
