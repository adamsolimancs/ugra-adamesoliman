# LLM processing script to normalize residence data
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from ollama import Client

LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "llama3.1:8b")
# LLM_SECONDARY_MODEL = os.getenv("LLM_SECONDARY_MODEL", "o3-mini")
# CONFIDENCE_THRESHOLD = int(os.getenv("LLM_CONFIDENCE_THRESHOLD", "75"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Professor server init
client = Client(host=OLLAMA_HOST)

# Regexes for basic quality control
_JSON_BLOCK_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)
_PLACE_TEXT_RE = re.compile(r"[A-Za-z]{2}")
_TIME_SPAN_RE = re.compile(
    r"(?ix)"
    r"("
    r"\b\d{3,4}(?:\s*[\-\u2013]\s*\d{2,4})?\b"  # 1990 or 1990-1995
    r"|"
    r"\b(?:early|mid|late)\s+\d{2}s\b"  # early 90s
    r"|"
    r"\b\d{1,2}(?:st|nd|rd|th)\s+century\b"
    r"|"
    r"\b(?:early|mid|late)\s+(?:life|career|childhood|adulthood)\b"
    r"|"
    r"\b(?:present|childhood|adulthood|youth)\b"
    r")"
)
_TEXT_CONTENT_RE = re.compile(r"[A-Za-z]{3}")
_NAME_TOKEN_RE = re.compile(r"[A-Za-z]{3,}")
_PRONOUN_RE = re.compile(r"\b(he|his|she|her|they|their|them|him|family)\b", re.IGNORECASE)
_CAP_NAME_RE = re.compile(r"\b[A-Z][a-z]+\b")
_NON_WORD_RE = re.compile(r"\W+")


# Helper function to build the prompt for the LLM
def _build_prompt(person: str, sentences: List[str]) -> str:
    evidence_block = "\n".join(f"- {s}" for s in sentences)
    return (
        "You will receive biographical sentences about a person. "
        "Extract every distinct residence mentioned for that person (ignore locations tied to other people that don't include the person). "
        "Respond ONLY with valid JSON shaped as a list of objects, each with keys "
        "'person', 'residence', 'time_span', and 'evidence' (person must equal the value given below). "
        "The 'evidence' must be a verbatim snippet from the provided sentences; if you cannot cite a snippet, omit the residence. "
        "You must include a non-empty time_span; if you cannot find one, reasonably infer from context or omit the record. "
        "time_span must be an exact year."
        f"Person: {person}\nSentences:\n{evidence_block}"
    )


def _extract_json_block(content: str) -> str:
    """Extract the first JSON-looking object/array from a longer response."""
    match = _JSON_BLOCK_RE.search(content)
    return match.group(0) if match else content


def _clean_json_payload(raw: str):
    """Attempt to load JSON; strip trailing commas if needed."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([\}\]])", r"\1", raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: try line-by-line objects
        objs = []
        for line in cleaned.splitlines():
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                objs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if objs:
            return objs
    return None


def _normalize_text(text: str) -> str:
    """Lowercase and strip punctuation/extra whitespace for fuzzy matching."""
    return _NON_WORD_RE.sub(" ", text).strip().lower()


def _normalize_residence_entry(
    item: Dict[str, str], person: str, sentences: List[str]
) -> Optional[Dict[str, str]]:
    """Drop obviously bad entries and blank out suspect fields using regex-based checks."""
    place = str(item.get("residence", item.get("place", ""))).strip()
    time_span_raw = str(item.get("time_span", "")).strip()
    time_span = time_span_raw
    evidence = str(item.get("evidence", "")).strip()
    person_val = str(item.get("person", person)).strip() or person
    person_tokens = [t.lower() for t in _NAME_TOKEN_RE.findall(person_val)]

    if not _PLACE_TEXT_RE.search(place):
        return None

    sentinel_time = {"", "none", "null", "n/a", "na", "unknown", "?"}
    if time_span.lower() in sentinel_time:
        return None
    if time_span and not _TIME_SPAN_RE.search(time_span):
        time_span = ""
    if not time_span:
        return None

    if evidence and not _TEXT_CONTENT_RE.search(evidence):
        evidence = ""
    if place and not evidence:
        return None

    # Evidence must be grounded in the provided sentences (loose match)
    evid_norm = _normalize_text(evidence)
    if evidence and evid_norm:
        sentence_norms = [_normalize_text(s) for s in sentences]
        found_in_source = any(evid_norm in s for s in sentence_norms)
        if not found_in_source:
            # Fallback: token overlap ≥ 60%
            evid_tokens = [t for t in evid_norm.split() if len(t) > 2]
            for s in sentence_norms:
                if not evid_tokens:
                    break
                overlap = sum(1 for t in evid_tokens if t in s.split())
                if overlap >= max(1, int(0.6 * len(evid_tokens))):
                    found_in_source = True
                    break
        if not found_in_source:
            return None

    # Require evidence to loosely refer to the target: name match OR pronoun hint.
    if evidence:
        has_person = any(tok in evid_norm for tok in person_tokens)
        has_pronoun = bool(_PRONOUN_RE.search(evidence))
        cap_names = [w.lower() for w in _CAP_NAME_RE.findall(evidence)]
        other_names = [w for w in cap_names if w not in person_tokens]
        if not has_person and not has_pronoun:
            return None
        # If the sentence only names other people and no person/pronoun, drop it.
        if other_names and not has_person and not has_pronoun:
            return None

    return {"person": person_val, "residence": place, "time_span": time_span, "evidence": evidence}


# Asynchronous function to call the LLM API
async def _call_llm(
    person: str,
    sentences: List[str],
    model_name: str,
) -> List[Dict[str, str]]:
    if not sentences:
        return []

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
        return []

    try:
        content = response["message"]["content"]
        content = _extract_json_block(content)
        parsed = _clean_json_payload(content)
        if parsed is None:
            return []
        residences_payload = []
        if isinstance(parsed, dict):
            # accept both plain list and keyed list
            if "residences" in parsed and isinstance(parsed["residences"], list):
                residences_payload = parsed["residences"]
            else:
                residences_payload = [parsed]
        elif isinstance(parsed, list):
            residences_payload = parsed
        normalized = []
        if isinstance(residences_payload, list):
            for item in residences_payload:
                cleaned = _normalize_residence_entry(item, person, sentences)
                if cleaned:
                    normalized.append(cleaned)
            return normalized
    except (KeyError, ValueError, json.JSONDecodeError):
        pass
    return []

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

            structured_residences = await _call_llm(person, sentences, LLM_PRIMARY_MODEL)

            if not structured_residences:
                continue

            for residence in structured_residences:
                outfile.write(json.dumps(residence) + "\n")


def main():
    asyncio.run(process_with_llm())


if __name__ == "__main__":
    main()
