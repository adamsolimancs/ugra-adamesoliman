import csv
import json
import random
import re

import mwparserfromhell

# Precompile expressions used for sentence parsing and residence detection
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9])')
RESIDENCE_HINT_RE = re.compile(
    r'\b(resides?|residing|residence|lives?|living|based|settled|moved)\b',
    re.IGNORECASE,
)


def load_famous_name_map(notable_csv):
    """Return a mapping of article titles to their raw CSV tokens."""
    title_map = {}
    with open(notable_csv, 'r', encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile):
            raw_name = row.get('name')
            if not raw_name:
                continue
            pretty_title = raw_name.strip().replace('_', ' ')
            title_map[pretty_title] = raw_name.strip()
    return title_map


def extract_residence_sentences(wikitext):
    """Return sentences from the article text that refer to residences."""
    plain_text = mwparserfromhell.parse(wikitext).strip_code()
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    if not plain_text:
        return []

    sentences = SENTENCE_SPLIT_RE.split(plain_text)
    matches = []
    seen = set()
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        if RESIDENCE_HINT_RE.search(candidate):
            # Deduplicate exact sentence repeats
            if candidate not in seen:
                matches.append(candidate)
                seen.add(candidate)
    return matches


def process_pages(input_jsonl, output_jsonl, notable_csv):
    """Process JSONL wiki pages and extract residence sentences for notable people."""
    famous_titles = load_famous_name_map(notable_csv)

    sample_titles = random.sample(
        list(famous_titles.keys()),
        k=min(15, len(famous_titles)),
    ) if famous_titles else []
    if sample_titles:
        print(f"Here are {len(sample_titles)} random famous people loaded from the CSV:")
        for name in sample_titles:
            print(f"Notable person: {name}")

    with open(input_jsonl, 'r', encoding='utf-8') as infile, \
            open(output_jsonl, 'w', encoding='utf-8') as outfile:
        for line in infile:
            page = json.loads(line)
            title = page.get('title', '')
            text = page.get('text') or ''

            if title not in famous_titles:
                continue

            residence_sentences = extract_residence_sentences(text)
            output_record = {
                'name': title,
                'residence_sentences': residence_sentences,
            }
            outfile.write(json.dumps(output_record) + '\n')
