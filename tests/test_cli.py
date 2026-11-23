from study_planner.cli import main


def test_plan_command_accepts_user_inputs_and_writes_ics(tmp_path, capsys):
    output = tmp_path / "personal-plan.ics"
    main([
        "plan",
        "--start-date", "2026-11-12",
        "--exam-date", "2026-11-14",
        "--exam-name", "CS Exam",
        "--diff1", "Hard",
        "--diff2", "Easy",
        "--diff3", "Hard",
        "--quiz", "Poor",
        "--stress", "Low",
        "--out", str(output),
    ])

    text = output.read_text(encoding="utf-8")
    result = capsys.readouterr().out
    assert text.count("BEGIN:VEVENT") == 2
    assert "CS Exam" in text
    assert "expected utilities:" in result
    assert "2026-11-12" in result and "2026-11-13" in result
