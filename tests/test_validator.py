from pathlib import Path

from src.validate import main as validate_main


def test_bad_fixtures_fail_validation(tmp_path, monkeypatch, capsys):
    fixture_dir = Path("tests/bad_examples")
    monkeypatch.setattr("sys.argv", ["validate.py", str(fixture_dir)])
    exit_code = validate_main()
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "VALIDATION FAILED" in captured.out
