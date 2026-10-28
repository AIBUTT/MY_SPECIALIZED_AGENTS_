"""Build datasets from raw inputs.

Usage:
    python -m {{module_name}}.dataset --input data/raw/<file> --output data/processed/<file>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from {{module_name}}.config import PROCESSED_DATA_DIR, RAW_DATA_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--output", type=Path, default=PROCESSED_DATA_DIR)
    parser.parse_args(argv)
    raise NotImplementedError("Define the dataset build in {{module_name}}/dataset.py.")


if __name__ == "__main__":
    raise SystemExit(main())
