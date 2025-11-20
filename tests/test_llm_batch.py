# Utility script to fire a limited number of LLM requests through the llm_processing pipeline.
# It stops after the requested count so you can quickly inspect regex QC behavior.
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import time
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from llm_processing import LLM_PRIMARY_MODEL, _call_llm


def _default_output_path() -> Path:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    return ROOT / f"llm_test_{stamp}.jsonl"


def _abs(path: Path) -> Path:
    """Return a repo-rooted absolute path for relative inputs."""
    return path if path.is_absolute() else ROOT / path


def _load_cases(input_path: Path, count: int) -> List[Tuple[str, List[str]]]:
    """Load up to `count` cases from a JSONL shaped like llm_output_residences.jsonl."""
    cases: List[Tuple[str, List[str]]] = []
    with input_path.open("r", encoding="utf-8") as infile:
        for line in infile:
            record = json.loads(line)
            person = record.get("name") or record.get("title") or ""
            sentences = record.get("residence_sentences") or []
            if not sentences or sentences[0] == "":
                continue
            cases.append((person, sentences))
            if len(cases) >= count:
                break
    return cases


async def _run_single(person: str, sentences: List[str], model_name: str) -> Tuple[str, List[dict]]:
    residences = await _call_llm(person, sentences, model_name)
    return person, residences


async def run_batch(
    input_path: Path,
    count: int,
    output_path: Path,
    model_name: str,
    concurrency: int = 5,
) -> None:
    """Send up to `count` LLM requests from the provided input file and persist JSONL output."""
    cases = _load_cases(input_path, count)
    if not cases:
        print(f"No cases found in {input_path} to process.")
        return

    semaphore = asyncio.Semaphore(concurrency)

    async def bound_call(person: str, sentences: List[str]):
        async with semaphore:
            return await _run_single(person, sentences, model_name)

    tasks = [asyncio.create_task(bound_call(person, sentences)) for person, sentences in cases]
    results = await asyncio.gather(*tasks)

    with output_path.open("w", encoding="utf-8") as outfile:
        for person, residences in results:
            if residences:
                for residence in residences:
                    outfile.write(json.dumps(residence) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a limited number of LLM normalization calls (from llm_processing) to test regex QC."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "llm_output_residences.jsonl",
        help="Input JSONL with residence_sentences (default: repo_root/llm_output_residences.jsonl).",
    )
    parser.add_argument("--count", type=int, default=10, help="Max number of input records to process (default: 25).")
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_path(),
        help="Where to write the structured JSONL output (default: repo_root/llm_test_<timestamp>.jsonl).",
    )
    parser.add_argument(
        "--model",
        default=LLM_PRIMARY_MODEL,
        help="Model name to use (default: value of LLM_PRIMARY_MODEL).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent requests to the LLM (default: 5).",
    )
    args = parser.parse_args()

    input_path = _abs(args.input)
    output_path = _abs(args.output)

    print(
        f"Starting up to {args.count} requests from {input_path} "
        f"-> {output_path} using model '{args.model}' (concurrency={args.concurrency})..."
    )
    t0 = time.time()
    asyncio.run(run_batch(input_path, args.count, output_path, args.model, args.concurrency))
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()
