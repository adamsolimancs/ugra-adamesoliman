# Main orchestration script to process Wikipedia dump and extract structured residence data
import os
import time
import subprocess
import multiprocessing
from pathlib import Path
from parser import parse_wiki_dump
from extractor import process_pages

def combine_files(source_files, destination_file):
    """Concatenates multiple files into a single destination file."""
    print(f"\nCombining {len(source_files)} files into {destination_file}...")
    with open(destination_file, 'wb') as outfile:
        for filepath in source_files:
            with open(filepath, 'rb') as infile:
                outfile.write(infile.read())
            
            os.remove(filepath) # remove the partial file after it has been merged

if __name__ == "__main__":
    start_time = time.time()
    
    final_parsed_jsonl = "wiki_articles.jsonl"
    extracted_jsonl = "raw_residences.jsonl"
    structured_jsonl = "final_residences.jsonl"
    
    input_dir = Path('./wiki_dumps')
    
    # --- PREPARE TASKS FOR PARALLEL PROCESSING ---
    temp_output_dir = Path('./temp_parsed_output') # temporary directory for the output of each process
    temp_output_dir.mkdir(exist_ok=True)
    
    # Find all .bz2 files in the input directory
    dump_paths = list(input_dir.glob('*.bz2'))
    if not dump_paths:
        print(f"Error: No .bz2 files found in the directory '{input_dir}'.")
        exit()
        
    print(f"Found {len(dump_paths)} dump files to process.")

    # Create a list of (input_path, unique_output_path) tuples
    tasks = []
    for dump_path in dump_paths:
        # Create a unique name for the output file based on the input file's name
        # e.g., 'wiki-dump1.bz2' -> 'temp_parsed_output/wiki-dump1.xml.jsonl'
        output_path = temp_output_dir / f"{dump_path.stem}.jsonl"
        tasks.append((str(dump_path), str(output_path)))


    # --- RUN PARSING IN PARALLEL ---
    # Use a process pool to execute parse_wiki_dump for each task
    # It automatically uses the number of available CPU cores
    print(f"Starting parallel parsing with {multiprocessing.cpu_count()} cores...")
    with multiprocessing.Pool() as pool:
        pool.starmap(parse_wiki_dump, tasks)

    print("\nAll individual dump files have been parsed.")

    # --- COMBINE RESULTS ---
    # Get the list of all temporary files created by the processes
    temp_files = sorted(list(temp_output_dir.glob('*.jsonl')))
    if temp_files:
        combine_files(temp_files, final_parsed_jsonl)
    else:
        print("Warning: No temporary files were created. The final output will be empty.")
    
    parsing_end_time = time.time()
    print(f"✔ Total parsing and combining finished in {parsing_end_time - start_time:.2f} seconds.")
    
    
    # --- 5. EXTRACT IMPORTANT DATA ---
    # NOTE: hardcoded path to the notable humans CSV
    # NOTE: The model must be trained first by running train_classifier.py
    process_pages(final_parsed_jsonl, extracted_jsonl, 'notable_humans/result.csv')

    # --- 6. LLM USAGE ---
    llm_start_time = time.time()
    try:
        subprocess.run(["python3", "llm_processing.py"], check=True)
    finally:
        elapsed = time.time() - llm_start_time
        print(f"✔ LLM post-processing finished in {elapsed:.2f} seconds.")
    
