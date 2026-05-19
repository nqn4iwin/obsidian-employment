"""uv run crawl | convert | index 로 기존 스크립트를 실행합니다."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(relative: str) -> None:
    path = ROOT / relative
    args = sys.argv[1:]
    raise SystemExit(
        subprocess.call([sys.executable, str(path), *args], cwd=ROOT)
    )


def crawl() -> None:
    _run("crawler/saramin_crawler.py")


def convert() -> None:
    _run("converter/converter.py")


def build_index() -> None:
    _run("scripts/build_index.py")
