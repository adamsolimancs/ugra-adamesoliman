# Tracking Famous People’s Residences from Wikipedia Dumps
## Overview

This project focuses on extracting and standardizing information about famous people’s residences over their lifetime.
Rather than web scraping live Wikipedia pages, it uses an offline Wikipedia dump (XML + bz2 format) to ensure efficiency, scalability, and respect for Wikipedia’s resources.

---
### Getting Started
#### Prerequisites
- Python 3+
- pip for installing packages

#### Installation
Clone the repository (SSH method below) and install the required dependencies:

```bash
git clone git@github.com:adamsolimancs/ugra-adamesoliman.git
cd ugra-adamesoliman
pip install -r requirements.txt
```

#### Directory Setup (if not already existing)
- Place your compressed Wikipedia dump files (e.g., enwiki-latest-pages-articles.xml.bz2) inside a wiki_dumps/ directory in the project root.
- Have a CSV of notable humans located at ./notable_humans/result.csv 
- Run the pipeline: `python main.py`

---
### Pipeline

The ***data pipeline*** is designed to:
- Parse massive XML dumps.
- Extract relevant data (primarily residence information).
- Clean and structure the data.
- Use tiers of LLMs to resolve ambiguous text into structured formats.
- Simple requests → handled by a lightweight local LLM.
- Complex requests → escalated to a more costly online LLM (e.g., Mistral, Gemini, GPT).
- This system must scale to millions of API calls, requiring careful design in parallelization, data storage, and LLM selection.


#### Components
Parser `parser.py`
- Uses parallel, multiprocessing to parse the XML files within the wiki_dumps directory.
- Implemented using xml.etree.ElementTree, specifically the XMLPullParser() method. This method lets us process in parallel and avoid loading the
    entire Wiki dump into memory.
- Each process writes to a unique output file, stored in the `/temp_parsed_output` directory, but is combined into `wiki_articles.jsonl` during
    the main method process.


Extractor `extractor.py`
- Loads the SentenceTransformer embedder (`all-MiniLM-L6-v2`) and the logistic-regression classifier trained by `train_classifier.py`.
- Embeds every sentence in each article, applies the classifier, and keeps the ones with a residence probability ≥ 0.5.
- Outputs JSON lines shaped as `{"name": ..., "residence_sentences": [...]}`. Empty arrays mean the person was processed but no residence sentence was found.

Classifier Training `train_classifier.py`
- Reads `train_data.jsonl`, encodes text with the same SentenceTransformer, and fits a logistic regression model.
- Saves both the embedder and classifier together at `residence_classifier.joblib` for the extractor to reuse.



LLM Pipeline (TBD)



Main Method '''main.py'''
- Orchestrates the data pipeline, parsing, extracting, and then passing data to the LLM to output a .json file.

---
### Instructions for Running the Pipeline

1. Prepare assets
   - Place dump files (e.g., `enwiki-latest-pages-articles.xml.bz2`) in `wiki_dumps/`.
   - Confirm `notable_humans/result.csv` includes the target people.
   - Refresh `train_data.jsonl` with labeled residence examples.
2. Parse Wikipedia dumps
   - For a single dump: `python - <<'PY'` snippet in the dialog above to emit `wiki_articles.jsonl`.
   - For all dumps: `python main.py` orchestrates parsing, combining, and yields `wiki_articles.jsonl` automatically.
3. Train classifier
   - Run `python train_classifier.py` to fit the logistic regression on SentenceTransformer embeddings and save `residence_classifier.joblib`.
4. Run extractor
   - Execute `python test_llm.py` (or import `process_pages`) to score sentences and write `llm_output_residences.jsonl`.
5. Review outputs
   - Inspect JSONL records; empty `residence_sentences` arrays signal no matches for that person.
   - Apply any filtering or downstream formatting before handing off results.

Re-run steps 3–4 whenever you update the training data or model configuration so predictions stay in sync.

