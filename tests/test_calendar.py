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
