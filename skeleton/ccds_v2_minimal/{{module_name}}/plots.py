"""Produce figures from accepted outputs.

Usage:
    python -m {{module_name}}.plots --input runs/<run_id>/<file> --output reports/figures/<run_id>/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from {{module_name}}.config import FIGURES_DIR, RUNS_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=RUNS_DIR)
    parser.add_argument("--output", type=Path, default=FIGURES_DIR)
    parser.parse_args(argv)
    raise NotImplementedError("Define figures in {{module_name}}/plots.py.")


if __name__ == "__main__":
    raise SystemExit(main())
