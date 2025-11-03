import csv
import json
import random
import re
from pathlib import Path

import joblib
import mwparserfromhell

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9])')

# Lazy-loaded global model objects
_EMBEDDER = None
_CLF = None
_THRESHOLD = 0.5  # probability threshold for class=1, decision boundary
_MODEL_PATH = Path(__file__).resolve().parent / "residence_classifier.joblib"

def _load_model():
    """Load the (embedder, classifier) tuple saved by train_classifier.py."""
    global _EMBEDDER, _CLF
    if _EMBEDDER is not None and _CLF is not None:
        return
    try:
        print("⏳ Loading residence classifier model...")
        _EMBEDDER, _CLF = joblib.load(_MODEL_PATH)
    except Exception as e:
        print(f"Warning: unable to load model at {_MODEL_PATH}: {e}")
        _EMBEDDER, _CLF = None, None


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

    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(plain_text) if s.strip()]
    if not sentences:
        return []

    _load_model()
    if _EMBEDDER is None or _CLF is None:
        # Model not available; return no matches
        return []

    # Embed all sentences in a single batch for efficiency
    print("⏳ Embedding and classifying residence sentences...")
    X = _EMBEDDER.encode(sentences, show_progress_bar=False)
    probs = _CLF.predict_proba(X)[:, 1]

    matches = []
    seen = set()
    for sent, p in zip(sentences, probs):
        if p >= _THRESHOLD and sent not in seen:
            matches.append(sent)
            seen.add(sent)
    return matches


def process_pages(input_jsonl, output_jsonl, notable_csv):
    """Process JSONL wiki pages and extract residence sentences for notable people."""
    famous_titles = load_famous_name_map(notable_csv)

    # debug: print some sample names
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

            # fix for duplicate names
            if title not in famous_titles:
                continue

            residence_sentences = extract_residence_sentences(text)
            output_record = {
                'name': title,
                'residence_sentences': residence_sentences,
            }
            outfile.write(json.dumps(output_record) + '\n')
