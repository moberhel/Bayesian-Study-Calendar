import datetime as dt
from study_planner.calendars import LocalICSCalendar, Event, apply_action, HOURS
from study_planner.calendars.base import free_slots, DAY_START, DAY_END

DAY = dt.date(2026, 11, 12)
at = lambda h, m=0: dt.datetime.combine(DAY, dt.time(h, m))


def cal_with_commitments():
    cal = LocalICSCalendar()
    cal.insert(Event("Lecture", at(10), at(12)))
    cal.insert(Event("Job", at(15), at(17)))
    return cal


def planner_blocks(cal):
    return [e for e in cal.list_events(DAY) if e.system]


def test_free_slots_stay_in_window_and_avoid_busy_time():
    cal = cal_with_commitments()
    slots = free_slots(cal, DAY)
    assert slots[0][0] == at(DAY_START) and slots[-1][1] == at(DAY_END)
    for s, e in slots:
        assert not (s < at(12) and e > at(10)) and not (s < at(17) and e > at(15))


def test_study_blocks_never_overlap_existing_events():
    for action in ("Intense5h", "Moderate3h", "Light1h"):
        cal = cal_with_commitments()
        blocks = apply_action(cal, DAY, action, ["Inference"], "Exam", "why")
        busy = [(at(10), at(12)), (at(15), at(17))]
        for b in blocks:
            assert all(b.end <= s or b.start >= e for s, e in busy), action
            assert at(DAY_START) <= b.start and b.end <= at(DAY_END)


def test_block_lengths_match_the_action():
    for action, h in HOURS.items():
        cal = cal_with_commitments()
        blocks = apply_action(cal, DAY, action, ["x"], "Exam", "why")
        assert sum((b.end - b.start for b in blocks), dt.timedelta(0)) == dt.timedelta(hours=h)


def test_intense_block_splits_when_no_single_slot_fits():
    cal = LocalICSCalendar()
    for start, end in [(8, 11), (12, 15), (16, 19), (20, 22)]:   # leaves only 1-hour gaps
        cal.insert(Event("busy", at(start), at(end)))
    blocks = apply_action(cal, DAY, "Intense5h", ["x"], "Exam", "why")
    assert len(blocks) >= 2
    assert sum((b.end - b.start for b in blocks), dt.timedelta(0)) <= dt.timedelta(hours=3)  # can't over-schedule


def test_reapplying_is_idempotent_and_replaces_earlier_plan():
    cal = cal_with_commitments()
    apply_action(cal, DAY, "Intense5h", ["x"], "Exam", "first")
    apply_action(cal, DAY, "Light1h", ["x"], "Exam", "second")
    blocks = planner_blocks(cal)
    assert len(blocks) == 1 and blocks[0].description == "second"


def test_rest_day_clears_study_blocks_and_creates_all_day_event():
    cal = cal_with_commitments()
    apply_action(cal, DAY, "Intense5h", ["x"], "Exam", "study")
    apply_action(cal, DAY, "Rest", ["x"], "Exam", "rest")
    blocks = planner_blocks(cal)
    assert len(blocks) == 1 and blocks[0].all_day and "REST" in blocks[0].summary


def test_user_events_are_never_deleted():
    cal = cal_with_commitments()
    apply_action(cal, DAY, "Rest", ["x"], "Exam", "rest")
    apply_action(cal, DAY, "Moderate3h", ["x"], "Exam", "study")
    names = {e.summary for e in cal.list_events(DAY) if not e.system}
    assert names == {"Lecture", "Job"}


def test_ics_export_is_parseable(tmp_path):
    cal = cal_with_commitments()
    apply_action(cal, DAY, "Moderate3h", ["Inference"], "Exam", "because")
    path = tmp_path / "out.ics"
    cal.export(str(path))
    text = path.read_text()
    assert text.startswith("BEGIN:VCALENDAR") and text.rstrip().endswith("END:VCALENDAR")
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") == len(cal.events)
    assert "SUMMARY:Lecture" in text and "Study block: Inference [Exam]" in text


def test_google_calendar_reads_all_day_events_and_local_times(monkeypatch):
    from zoneinfo import ZoneInfo
    import sys
    import types
    from study_planner.calendars import google
    local_start = dt.datetime.combine(DAY, dt.time(17), ZoneInfo("America/Vancouver")).isoformat()
    local_end = dt.datetime.combine(DAY, dt.time(20), ZoneInfo("America/Vancouver")).isoformat()

    class Request:
        def execute(self):
            return {"items": [
                {"id": "rest", "summary": "REST", "start": {"date": DAY.isoformat()},
                 "end": {"date": (DAY + dt.timedelta(days=1)).isoformat()},
                 "extendedProperties": {"private": {"tag": google.TAG}}},
                {"id": "study", "summary": "Study", "start": {"dateTime": local_start},
                 "end": {"dateTime": local_end}},
            ]}

    class Events:
        def list(self, **kwargs):
            self.kwargs = kwargs
            return Request()

    class Service:
        def __init__(self):
            self.api = Events()
        def events(self):
            return self.api

    service = Service()
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda *args, **kwargs: service
    package = types.ModuleType("googleapiclient")
    package.discovery = discovery
    monkeypatch.setitem(sys.modules, "googleapiclient", package)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)

    cal = google.GoogleCalendar(object(), tz="America/Vancouver")
    events = cal.list_events(DAY)

    assert dt.datetime.fromisoformat(service.api.kwargs["timeMin"]).utcoffset() is not None
    assert service.api.kwargs["timeMax"].startswith("2026-11-13T00:00:00")
    assert events[0].all_day and events[0].system
    assert events[1].start == at(17) and events[1].end == at(20)
    utc_value = dt.datetime(2026, 11, 13, 1, tzinfo=dt.timezone.utc)
    assert cal._local_datetime("2026-11-13T01:00:00Z") == utc_value.astimezone(cal.tz).replace(tzinfo=None)


def test_google_calendar_inserts_all_day_events_and_deletes_by_id(monkeypatch):
    import sys
    import types
    from study_planner.calendars import google

    class Request:
        def execute(self):
            return {}

    class Events:
        def __init__(self):
            self.bodies = []
        def insert(self, **kwargs):
            self.bodies.append(kwargs["body"])
            return Request()
        def delete(self, **kwargs):
            self.delete_args = kwargs
            return Request()

    class Service:
        def __init__(self):
            self.api = Events()
        def events(self):
            return self.api

    service = Service()
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda *args, **kwargs: service
    package = types.ModuleType("googleapiclient")
    package.discovery = discovery
    monkeypatch.setitem(sys.modules, "googleapiclient", package)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)

    cal = google.GoogleCalendar(object(), calendar_id="primary")
    rest = Event("REST", at(0), at(0) + dt.timedelta(days=1), all_day=True, system=True)
    cal.insert(rest)
    study = Event("Study", at(17), at(18), system=True)
    cal.insert(study)
    cal.delete(Event("REST", rest.start, rest.end, uid="event-id"))

    rest_body, study_body = service.api.bodies
    assert rest_body["start"] == {"date": DAY.isoformat()}
    assert rest_body["end"] == {"date": (DAY + dt.timedelta(days=1)).isoformat()}
    assert study_body["start"]["dateTime"] == at(17).replace(tzinfo=cal.tz).isoformat()
    assert study_body["start"]["timeZone"] == "America/Vancouver"
    assert service.api.delete_args == {"calendarId": "primary", "eventId": "event-id"}
