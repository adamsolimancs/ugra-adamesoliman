"""Utility to time a full llm_processing run end-to-end."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from llm_processing import process_with_llm


def main() -> None:
    parser = argparse.ArgumentParser(description="Time the full llm_processing.py run.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("llm_output_residences.jsonl"),
        help="Input JSONL with residence_sentences (default: llm_output_residences.jsonl).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("structured_residences_2.jsonl"),
        help="Output JSONL for structured residences (default: structured_residences_2.jsonl).",
    )
    args = parser.parse_args()

    t0 = time.time()
    print(f"Running llm_processing: input={args.input}, output={args.output} ...")
    import asyncio

    asyncio.run(process_with_llm(str(args.input), str(args.output)))
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.2f}s. Output: {args.output}")


if __name__ == "__main__":
    main()
