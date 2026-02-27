import sys
from pathlib import Path

from ppt_local_translator import cli


def test_cli_parse(monkeypatch, tmp_path: Path):
    argv = [
        "prog",
        "--input",
        str(tmp_path / "a.pptx"),
        "--output-dir",
        str(tmp_path),
        "--model",
        "translategemma:4b",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    args = cli.parse_args()
    assert args.model == "translategemma:4b"
