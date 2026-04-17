"""Tests for main.py CLI — argument parsing & helper functions."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestCheckApiKey:
    def test_returns_false_without_key(self):
        from main import _check_api_key
        with patch.dict("os.environ", {}, clear=True):
            assert _check_api_key() is False

    def test_returns_true_with_key(self):
        from main import _check_api_key
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}):
            assert _check_api_key() is True


class TestPrintTurns:
    def test_prints_agent_info(self, capsys):
        from main import _print_turns
        turns = [
            {
                "emoji": "📊",
                "name": "CFO",
                "label": "재무총괄",
                "text": "테스트 응답입니다.",
            }
        ]
        _print_turns(turns)
        out = capsys.readouterr().out
        assert "CFO" in out
        assert "재무총괄" in out
        assert "테스트 응답" in out


class TestLoadFiles:
    def test_loads_xlsx(self, tmp_path, capsys):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["매물명", "가격"])
        ws.append(["테스트A", 40000])
        path = tmp_path / "test.xlsx"
        wb.save(path)

        from main import _load_files
        result = _load_files([str(path)])
        assert "매물명" in result
        assert "테스트A" in result
        out = capsys.readouterr().out
        assert "파싱 완료" in out

    def test_nonexistent_file(self, capsys):
        from main import _load_files
        result = _load_files(["/nonexistent/file.xlsx"])
        assert result == ""
        out = capsys.readouterr().out
        assert "실패" in out


class TestArgParser:
    def test_demo_flag(self):
        import argparse
        from main import main
        with patch("sys.argv", ["main.py", "--list-sessions"]):
            main()

    def test_no_api_key_exits(self):
        import pytest
        from main import main
        with patch("sys.argv", ["main.py"]), \
             patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestSessionList:
    def test_prints_no_sessions(self, capsys):
        from main import _print_session_list
        _print_session_list()
        out = capsys.readouterr().out
        assert "세션" in out
