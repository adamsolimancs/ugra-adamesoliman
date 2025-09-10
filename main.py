# Main orchestration script to process Wikipedia dump and extract structured residence data
from parser import parse_wiki_dump
# import subprocess    parallel processing, review later

if __name__ == "__main__":
    # File paths (consider moving to ENV)
    dump_paths = ['wiki-dump1.bz2']
    parsed_jsonl = "wiki_articles.jsonl"
    extracted_jsonl = "raw_residences.jsonl"
    structured_jsonl = "final_residences.jsonl"

    # 1. Run parsing script on each dump
    for path in dump_paths:
        parse_wiki_dump(path, parsed_jsonl)
        
    # 2. Extract raw residences

    # 3. Call LLM for normalization
