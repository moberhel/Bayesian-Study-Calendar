"""Command-line demo:  study-planner demo [--out DIR]   (or: python -m study_planner demo)"""
from __future__ import annotations
import argparse
import datetime as dt
import itertools
import os
from pathlib import Path
import numpy as np

from .model import (STATES, MASTERY_BY_NUM_HARD, QUIZ_GIVEN_MASTERY)
from .inference import BayesNet
from .decision import decide
from .simulation import Student, plan
from .calendars import LocalICSCalendar, HOURS
from .scenarios import make_students, SNAPSHOTS, add_existing_commitments, TODAY, EXAM

BAR = "=" * 78


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from exc


def print_parameters(bn: BayesNet) -> None:
    print(BAR, "\nMODEL PARAMETERS (rationale in model.py / docs/model_parameters.md)\n" + BAR)
    print("P(Mastery[Low,Med,High] | #Hard concepts):")
    for k, v in MASTERY_BY_NUM_HARD.items():
        print(f"   {k} hard: {v}")
    print("P(Quiz[Poor,OK,Good] | Mastery):")
    for k, v in QUIZ_GIVEN_MASTERY.items():
        print(f"   {k:4s}: {v}")
    print("P(Grade[Low,Mid,High] | Mastery=Med, Action, DaysLeft):")
    for ai, a in enumerate(STATES["Action"]):
        print(f"   {a:11s}", {d: np.round(bn.cpt["Grade"][1, ai, i], 2).tolist()
                              for i, d in enumerate(STATES["DaysLeft"])})
    print("P(FutureStress=High | Stress=Low, Action, DaysLeft, Mastery=Med):")
    for ai, a in enumerate(STATES["Action"]):
        print(f"   {a:11s}", {d: round(float(bn.cpt["FutureStress"][0, ai, i, 1, 1]), 2)
                              for i, d in enumerate(STATES["DaysLeft"])})


def show_decision(label: str, ev: dict, d) -> None:
    print(f"\n{label}\n   evidence: {ev}")
    print(f"   posterior P(Mastery[Low,Med,High]) = {np.round(d.p_mastery, 2).tolist()}")
    print(f"   {'action':<11}{'E[score]':>9}{'P(HiStress)':>13}{'E[U]':>8}")
    for a in STATES["Action"]:
        star = "  <== BEST" if a == d.best else ""
        print(f"   {a:<11}{d.exp_score[a]:>9.1f}{d.p_stress[a]:>13.2f}{d.eu[a]:>8.1f}{star}")


def demo(out_dir: str) -> None:
    bn = BayesNet()
    print_parameters(bn)

    print("\n" + BAR + "\nA. DIFFICULTY SWEEP  (DaysLeft=Some, Quiz=OK, Stress=Low)\n" + BAR)
    print(f"{'Diff1':<6}{'Diff2':<6}{'Diff3':<6}{'P(Mastery=Low)':>15}{'  best action':>14}")
    for combo in itertools.product(["Easy", "Hard"], repeat=3):
        ev = dict(zip(["Diff1", "Diff2", "Diff3"], combo), Quiz="OK", DaysLeft="Some", Stress="Low")
        d = decide(bn, ev)
        print(f"{combo[0]:<6}{combo[1]:<6}{combo[2]:<6}{d.p_mastery[0]:>15.2f}{d.best:>14}")

    print("\n" + BAR + "\nB. ONE-DAY DECISIONS: full expected-utility tables\n" + BAR)
    for label, ev in SNAPSHOTS.items():
        show_decision(label, ev, decide(bn, ev))

    os.makedirs(out_dir, exist_ok=True)
    print("\n" + BAR + f"\nC. DYNAMIC PLANS  (today={TODAY}, exam={EXAM})\n" + BAR)
    summary = {}
    for name, student in make_students().items():
        cal = LocalICSCalendar()
        add_existing_commitments(cal)
        rows = plan(student, "CS Exam", EXAM, TODAY, cal, bn)
        path = os.path.join(out_dir, f"{name.split()[0].lower()}.ics")
        cal.export(path)
        print(f"\n--- {name}  (start progress={rows[0][4]:.2f}, stress={rows[0][5]:.1f})  -> {path} ---")
        print(f"{'date':<11}{'left':>5} {'days':<5}{'quiz':<5}{'stress':<7}{'ACTION':<12}{'calendar entry'}")
        for day, n, ev, d, _prog, _sp in rows:
            entries = [e for e in cal.list_events(day) if e.system]
            txt = ("all-day rest" if entries and entries[0].all_day else
                   "; ".join(f"{e.start:%H:%M}-{e.end:%H:%M}" for e in entries))
            print(f"{day:%a %b %d} {n:>4}  {ev['DaysLeft']:<5}{ev['Quiz']:<5}{ev['Stress']:<7}{d.best:<12}{txt}")
        summary[name] = [r[3].best for r in rows]

    print("\n" + BAR + "\nD. EFFECT OF lambda (stress weight) - same student, same day\n" + BAR)
    ev = dict(Diff1="Hard", Diff2="Easy", Diff3="Hard", Quiz="OK", DaysLeft="Some", Stress="Low")
    print(f"evidence: {ev}")
    for lam in (0, 10, 20, 30, 45, 60):
        d = decide(bn, ev, stress_weight=lam)
        print(f"   lambda={lam:<3} -> {d.best:<11} (E[score]={d.exp_score[d.best]:.1f}, P(HiStress)={d.p_stress[d.best]:.2f})")

    print("\n" + BAR + "\nSUMMARY: total scheduled study hours per scenario\n" + BAR)
    for k, acts in summary.items():
        print(f"{k:<28} {sum(HOURS.get(a, 0) for a in acts):>3} h   rest days: {acts.count('Rest')}   {acts}")


def google_calendar(args):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from .calendars.google import GoogleCalendar

    token_path = Path(args.token)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    creds = Credentials.from_authorized_user_file(str(token_path), GoogleCalendar.SCOPES) if token_path.exists() else None
    if creds is not None and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if creds is None or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(args.credentials, GoogleCalendar.SCOPES)
        creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return GoogleCalendar(creds, calendar_id=args.calendar_id, tz=args.timezone)


def plan_for_user(args) -> None:
    start = args.start_date
    exam = args.exam_date
    if exam <= start:
        raise SystemExit("--exam-date must be later than --start-date")

    progress = {"Poor": 0.2, "OK": 0.5, "Good": 0.8}[args.quiz]
    stress_points = {"Low": 1.0, "High": 3.0}[args.stress]
    student = Student(
        "you",
        {"Concept 1": args.diff1, "Concept 2": args.diff2, "Concept 3": args.diff3},
        progress,
        stress_points,
    )
    cal = google_calendar(args) if args.calendar == "google" else LocalICSCalendar()
    rows = plan(student, args.exam_name, exam, start, cal, BayesNet())

    if args.calendar == "ics":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        cal.export(args.out)
        print(f"Calendar plan written to {args.out}")
    print(f"Study plan from {start} through {exam - dt.timedelta(days=1)}:")
    for day, _days_left, _evidence, decision, _progress, _stress in rows:
        utilities = ", ".join(f"{action}={value:.1f}" for action, value in decision.eu.items())
        print(f"  {day}: {decision.best} (expected utilities: {utilities})")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="study-planner", description="Bayesian study planner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="run the four student scenarios and write .ics files")
    d.add_argument("--out", default="calendars_out", help="directory for generated .ics files")
    p = sub.add_parser("plan", help="build a study plan for your exam and add it to a calendar")
    p.add_argument("--exam-date", required=True, type=parse_date, help="exam date in YYYY-MM-DD format")
    p.add_argument("--start-date", default=dt.date.today(), type=parse_date,
                   help="first day to plan (default: today), YYYY-MM-DD")
    p.add_argument("--exam-name", default="Exam")
    for index in range(1, 4):
        p.add_argument(f"--diff{index}", required=True, choices=("Easy", "Hard"),
                       help=f"difficulty of concept {index}")
    p.add_argument("--quiz", required=True, choices=("Poor", "OK", "Good"),
                   help="most recent practice quiz result")
    p.add_argument("--stress", required=True, choices=("Low", "High"),
                   help="current stress level")
    p.add_argument("--calendar", choices=("ics", "google"), default="ics")
    p.add_argument("--out", default="study-plan.ics", help="output path for --calendar ics")
    p.add_argument("--credentials", default="credentials.json",
                   help="Google OAuth client credentials JSON")
    p.add_argument("--token", default="token.json", help="path for the local OAuth token")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--timezone", default="America/Vancouver")
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        demo(args.out)
    elif args.cmd == "plan":
        plan_for_user(args)


if __name__ == "__main__":
    main()
