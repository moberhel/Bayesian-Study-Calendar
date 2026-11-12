"""Google Calendar API v3 backend. Optional dependency: pip install ".[google]"."""
from __future__ import annotations
import datetime as dt
from .base import TAG, Event, CalendarBackend


class GoogleCalendar(CalendarBackend):
    """Real Google Calendar API v3 backend (requires: pip install google-api-python-client
    google-auth-oauthlib, plus an OAuth `credentials.json`).  NOT exercised in the offline
    demo; the interface is identical to LocalICSCalendar so the planner is backend-agnostic."""
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    def __init__(self, creds, calendar_id="primary", tz="America/Vancouver"):
        from googleapiclient.discovery import build
        self.svc, self.cal, self.tz = build("calendar", "v3", credentials=creds), calendar_id, tz
    def list_events(self, day):
        t0 = dt.datetime.combine(day, dt.time.min).isoformat() + "Z"
        t1 = dt.datetime.combine(day, dt.time.max).isoformat() + "Z"
        items = self.svc.events().list(calendarId=self.cal, timeMin=t0, timeMax=t1,
                                       singleEvents=True).execute().get("items", [])
        out = []
        for i in items:
            if "dateTime" not in i["start"]: continue
            out.append(Event(i.get("summary", ""), dt.datetime.fromisoformat(i["start"]["dateTime"]).replace(tzinfo=None),
                             dt.datetime.fromisoformat(i["end"]["dateTime"]).replace(tzinfo=None),
                             system=i.get("extendedProperties", {}).get("private", {}).get("tag") == TAG,
                             uid=i["id"]))
        return out
    def insert(self, ev):
        body = {"summary": ev.summary, "description": ev.description,
                "extendedProperties": {"private": {"tag": TAG}}}
        if ev.all_day:
            body["start"], body["end"] = {"date": ev.start.date().isoformat()}, {"date": ev.end.date().isoformat()}
            body["transparency"] = "transparent"
        else:
            body["start"] = {"dateTime": ev.start.isoformat(), "timeZone": self.tz}
            body["end"] = {"dateTime": ev.end.isoformat(), "timeZone": self.tz}
        self.svc.events().insert(calendarId=self.cal, body=body).execute()
    def delete(self, ev): self.svc.events().delete(calendarId=self.cal, eventId=ev.uid).execute()
