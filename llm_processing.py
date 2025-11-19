# LLM processing script to normalize residence data
from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List, Tuple

from ollama import Client

LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "llama3.1:8b")
# LLM_SECONDARY_MODEL = os.getenv("LLM_SECONDARY_MODEL", "o3-mini")
# CONFIDENCE_THRESHOLD = int(os.getenv("LLM_CONFIDENCE_THRESHOLD", "75"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Professor server init
client = Client(host=OLLAMA_HOST)

# Helper function to build the prompt for the LLM
def _build_prompt(person: str, sentences: List[str]) -> str:
    evidence_block = "\n".join(f"- {s}" for s in sentences)
    return (
        "You will receive biographical sentences about a person. "
        "Extract every distinct residence mentioned for that person. "
        "Respond ONLY with valid JSON representing an object with keys 'confidence' and 'residences'. "
        "'confidence' must be an integer from 0 to 100 describing how certain you are. "
        "'residences' must be a list of objects with keys 'place', 'time_span', and 'evidence'. "
        "If information is missing, use an empty string.\n\n"
        f"Person: {person}\nSentences:\n{evidence_block}"
    )

# Asynchronous function to call the LLM API
async def _call_llm(
    person: str,
    sentences: List[str],
    model_name: str,
) -> Tuple[List[Dict[str, str]], int]:
    if not sentences:
        return [], 0

    try:
        response = await asyncio.to_thread(
            lambda: client.chat(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise information extraction assistant.",
                    },
                    {
                        "role": "user",
                        "content": _build_prompt(person, sentences),
                    },
                ],
                options={"temperature": 0},
            )
        )
    except Exception:
        return [], 0

    try:
        content = response["message"]["content"]
        parsed = json.loads(content)
        confidence = 0
        if isinstance(parsed, dict):
            confidence = int(parsed.get("confidence", 0))
            parsed = parsed.get("residences", [])
        normalized = []
        if isinstance(parsed, list):
            for item in parsed:
                normalized.append(
                    {
                        "place": item.get("place", ""),
                        "time_span": item.get("time_span", ""),
                        "evidence": item.get("evidence", ""),
                    }
                )
            return normalized, confidence
    except (KeyError, ValueError, json.JSONDecodeError):
        pass
    return [], 0

# Main processing function
async def process_with_llm(
    input_jsonl: str = "llm_output_residences.jsonl",
    output_jsonl: str = "structured_residences.jsonl",
) -> None:
    with open(input_jsonl, "r", encoding="utf-8") as infile, open(
        output_jsonl, "w", encoding="utf-8"
    ) as outfile:
        for line in infile:
            record = json.loads(line)
            person = record.get("name") or record.get("title") or ""
            sentences = record.get("residence_sentences", [])
            if not sentences or sentences[0] == "":
                # No residence sentences found
                continue

            structured_residences, confidence = await _call_llm(
                person, sentences, LLM_PRIMARY_MODEL
            )

            # if confidence < CONFIDENCE_THRESHOLD or not structured_residences:
            #     print(
            #         f"[LLM] Confidence {confidence}% for {person} using {LLM_PRIMARY_MODEL}. "
            #         f"Escalating to {LLM_SECONDARY_MODEL}."
            #     )
            #     structured_residences, confidence = await _call_llm(
            #         person, sentences, LLM_SECONDARY_MODEL
            #     )

            if not structured_residences:
                outfile.write(
                    json.dumps(
                        {
                            "person": person,
                            "residence": {
                                "place": "",
                                "time_span": "",
                                "evidence": "",
                            },
                        }
                    )
                    + "\n"
                )
                continue

            for residence in structured_residences:
                outfile.write(
                    json.dumps(
                        {
                            "person": person,
                            "residence": residence,
                        }
                    )
                    + "\n"
                )


def main():
    asyncio.run(process_with_llm())


if __name__ == "__main__":
    main()
