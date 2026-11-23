from study_planner.cli import main


def test_plan_defaults_to_downloads_folder(tmp_path, monkeypatch, capsys):
    from study_planner import cli

    downloads = tmp_path / "Downloads"
    monkeypatch.setattr(cli, "_writable_downloads_dir", lambda: downloads)
    main([
        "plan",
        "--start-date", "2026-11-12",
        "--exam-date", "2026-11-14",
        "--diff1", "Hard",
        "--diff2", "Easy",
        "--diff3", "Hard",
        "--quiz", "Poor",
        "--stress", "Low",
    ])

    assert (downloads / "study-plan.ics").is_file()
    assert str(downloads / "study-plan.ics") in capsys.readouterr().out


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


def test_downloads_folder_uses_linux_xdg_setting(tmp_path, monkeypatch):
    from study_planner import cli

    home = tmp_path / "home"
    config = tmp_path / "config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text(
        'XDG_DOWNLOAD_DIR="$HOME/My Downloads"\n', encoding="utf-8"
    )
    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))

    assert cli.downloads_dir() == home / "My Downloads"


def test_downloads_folder_uses_windows_known_folder(tmp_path, monkeypatch):
    from study_planner import cli

    redirected_downloads = tmp_path / "OneDrive" / "Downloads"
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr(cli, "_windows_downloads_dir", lambda: redirected_downloads)

    assert cli.downloads_dir() == redirected_downloads


def test_demo_defaults_to_downloads_folder(tmp_path, monkeypatch):
    from study_planner import cli

    downloads = tmp_path / "Downloads"
    captured = []
    monkeypatch.setattr(cli, "_writable_downloads_dir", lambda: downloads)
    monkeypatch.setattr(cli, "demo", lambda out: captured.append(out))

    main(["demo"])

    assert captured == [str(downloads)]
