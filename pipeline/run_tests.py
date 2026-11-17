#!/usr/bin/env python3
"""Runs every test in the repository.

    python3.14 pipeline/run_tests.py

Each folder's `*_test.py` files run in a fresh interpreter of their own, as
they always have (each sets up its own import path and some patch module
state), and the run fails when any of them fails.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("pipeline", "research", "curated")


def test_files() -> list[Path]:
    """Every test file, folder by folder, in name order."""
    return [
        path
        for folder in FOLDERS
        for path in sorted((ROOT / folder).glob("*_test.py"))
    ]


def main() -> int:
    failed = []
    for path in test_files():
        result = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True
        )
        outcome = (result.stderr.strip().splitlines() or ["(no output)"])[-1]
        print(f"{path.relative_to(ROOT)}: {outcome}")
        if result.returncode != 0:
            failed.append(path)
            print(result.stderr)
    print(f"\n{len(test_files()) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
