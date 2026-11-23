"""Google Calendar API v3 backend. Optional dependency: pip install ".[google]"."""
from __future__ import annotations
import datetime as dt
from zoneinfo import ZoneInfo
from .base import TAG, Event, CalendarBackend


class GoogleCalendar(CalendarBackend):
    """Real Google Calendar API v3 backend (requires: pip install google-api-python-client
    google-auth-oauthlib, plus an OAuth `credentials.json`).  NOT exercised in the offline
    demo; the interface is identical to LocalICSCalendar so the planner is backend-agnostic."""
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    def __init__(self, creds, calendar_id="primary", tz="America/Vancouver"):
        from googleapiclient.discovery import build
        self.svc, self.cal, self.tz = build("calendar", "v3", credentials=creds), calendar_id, ZoneInfo(tz)
    def list_events(self, day):
        t0 = dt.datetime.combine(day, dt.time.min, self.tz)
        t1 = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, self.tz)
        items = self.svc.events().list(calendarId=self.cal, timeMin=t0.isoformat(), timeMax=t1.isoformat(),
                                       singleEvents=True).execute().get("items", [])
        out = []
        for i in items:
            if "date" in i["start"]:
                start = dt.datetime.combine(dt.date.fromisoformat(i["start"]["date"]), dt.time.min)
                end = dt.datetime.combine(dt.date.fromisoformat(i["end"]["date"]), dt.time.min)
                all_day = True
            else:
                start = self._local_datetime(i["start"]["dateTime"])
                end = self._local_datetime(i["end"]["dateTime"])
                all_day = False
            out.append(Event(
                i.get("summary", ""), start, end,
                description=i.get("description", ""),
                all_day=all_day,
                system=i.get("extendedProperties", {}).get("private", {}).get("tag") == TAG,
                uid=i["id"],
            ))
        return out

    def _local_datetime(self, value):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self.tz)
        return parsed.astimezone(self.tz).replace(tzinfo=None)

    def insert(self, ev):
        body = {"summary": ev.summary, "description": ev.description,
                "extendedProperties": {"private": {"tag": TAG}}}
        if ev.all_day:
            body["start"], body["end"] = {"date": ev.start.date().isoformat()}, {"date": ev.end.date().isoformat()}
            body["transparency"] = "transparent"
        else:
            start = ev.start.replace(tzinfo=self.tz) if ev.start.tzinfo is None else ev.start.astimezone(self.tz)
            end = ev.end.replace(tzinfo=self.tz) if ev.end.tzinfo is None else ev.end.astimezone(self.tz)
            body["start"] = {"dateTime": start.isoformat(), "timeZone": str(self.tz)}
            body["end"] = {"dateTime": end.isoformat(), "timeZone": str(self.tz)}
        self.svc.events().insert(calendarId=self.cal, body=body).execute()
    def delete(self, ev): self.svc.events().delete(calendarId=self.cal, eventId=ev.uid).execute()
