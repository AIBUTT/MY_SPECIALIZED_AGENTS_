"""Run inference with a trained model.

Usage:
    python -m {{module_name}}.modeling.predict --features data/processed/<file> --model-dir models/<run_id>/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from {{module_name}}.config import MODELS_DIR, PROCESSED_DATA_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--features", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument("--model-dir", type=Path, default=MODELS_DIR)
    parser.parse_args(argv)
    raise NotImplementedError("Define inference in {{module_name}}/modeling/predict.py.")


if __name__ == "__main__":
    raise SystemExit(main())
