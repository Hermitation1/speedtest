"""Создаёт venv, ставит зависимости и запускает speedtest.

Использование:
    python run.py <url> [опции]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
DEPS = ("requests", "rich")


def _installed(python: Path, package: str) -> bool:
    result = subprocess.run(
        [str(python), "-c", f"import {package}"], check=False, capture_output=True
    )
    return result.returncode == 0


def _has_pip(python: Path) -> bool:
    result = subprocess.run(
        [str(python), "-m", "pip", "--version"], check=False, capture_output=True
    )
    return result.returncode == 0


def main() -> int:
    if not PYTHON.exists() or not _has_pip(PYTHON):
        print("Создаю окружение .venv ...", flush=True)
        shutil.rmtree(VENV, ignore_errors=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    if not all(_installed(PYTHON, dep) for dep in DEPS):
        print("Устанавливаю зависимости (requests, rich) ...", flush=True)
        subprocess.run(
            [
                str(PYTHON),
                "-m",
                "pip",
                "install",
                "-q",
                "--disable-pip-version-check",
                *DEPS,
            ],
            check=True,
        )
    return subprocess.run(
        [str(PYTHON), "-m", "speedtest", *sys.argv[1:]], check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
