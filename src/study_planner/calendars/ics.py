"""Offline calendar backend that exports RFC-5545 .ics files."""
from __future__ import annotations
import datetime as dt
from .base import TAG, Event, CalendarBackend


class LocalICSCalendar(CalendarBackend):
    """Offline backend: in-memory calendar that exports RFC-5545 .ics (importable
    into Google/Apple/Outlook calendars)."""
    def __init__(self): self.events: list[Event] = []
    def list_events(self, day):
        return [e for e in self.events if e.start.date() <= day <= (e.end - dt.timedelta(seconds=1)).date()]
    def insert(self, ev): self.events.append(ev)
    def delete(self, ev): self.events = [e for e in self.events if e.uid != ev.uid]
    def export(self, path):
        f = lambda d: d.strftime("%Y%m%dT%H%M%S")
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{TAG}//EN"]
        for e in sorted(self.events, key=lambda e: e.start):
            lines += ["BEGIN:VEVENT", f"UID:{e.uid}@{TAG}", f"DTSTAMP:{f(dt.datetime.now())}"]
            if e.all_day:
                lines += [f"DTSTART;VALUE=DATE:{e.start:%Y%m%d}", f"DTEND;VALUE=DATE:{(e.end):%Y%m%d}"]
            else:
                lines += [f"DTSTART:{f(e.start)}", f"DTEND:{f(e.end)}"]
            lines += [f"SUMMARY:{e.summary}", f"DESCRIPTION:{e.description.replace(chr(10), ' / ')}",
                      "END:VEVENT"]
        lines.append("END:VCALENDAR")
        open(path, "w").write("\r\n".join(lines))
