# Tracking Famous People’s Residences from Wikipedia Dumps
## Overview

This project focuses on extracting and standardizing information about famous people’s residences over their lifetime.
Rather than web scraping live Wikipedia pages, it uses an offline Wikipedia dump (XML + bz2 format) to ensure efficiency, scalability, and respect for Wikipedia’s resources.

---
### Getting Started
#### Prerequisites
- Python 3.9+
- pip for installing packages

#### Installation
Clone the repository and install the required dependencies:
'''
bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
pip install -r requirements.txt
'''

#### Directory Setup (if not already existing)
- Place your compressed Wikipedia dump files (e.g., enwiki-latest-pages-articles.xml.bz2) inside a wiki_dumps/ directory in the project root.
- Create an output file in the root of the project for the parsing script: '''wiki_articles.jsonl'''

- Run the pipeline: python main.py

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
Parser '''parser.py'''
- Uses parallel, multiprocessing to parse the XML files within the wiki_dumps directory.
- Implemented using xml.etree.ElementTree, specifically the XMLPullParser() method. This method lets us process in parallel and avoid loading the
    entire Wiki dump into memory.
- Each process writes to a unique output file, stored in the '''/temp_parsed_output''' directory, but is combined into wiki_articles.jsonl during
    the main method process.


Extractor (TBD)



LLM Pipeline (TBD)



Main Method '''main.py'''
- Orchestrates the data pipeline, parsing, extracting, and then passing data to the LLM to output a .json file.