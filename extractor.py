import mwparserfromhell
import re
import json
import csv

# Extract residence information from Wikipedia page wikitext
def extract_residence_from_wikitext(wikitext):
    """Parse the wikitext and extract residence information."""
    wikicode = mwparserfromhell.parse(wikitext)
    # Find any infobox templates in the text
    infoboxes = wikicode.filter_templates(matches='infobox', recursive=True)
    residences = []
    for tpl in infoboxes:
        # Some infobox template names are like 'Infobox person', 'Infobox scientist', etc.
        # Using matches='infobox' catches any template with 'infobox' in the name.
        if tpl.has("residence"):
            # Get the raw value of the residence parameter
            value = str(tpl.get("residence").value).strip()
            # Split multiple residences by <br> or commas
            parts = re.split(r'<br\s*/?>|,', value)
            for part in parts:
                part = part.strip()
                if part:
                    residences.append(part)
    # If no residence found in infobox, search the plain text for "resides in ..."
    if not residences:
        matches = re.findall(r'resid(?:e|ence|es) in ([A-Za-z ,\-]+)', wikitext, re.IGNORECASE)
        # Add each found location (already a string) to residences list
        for loc in matches:
            loc = loc.strip()
            if loc:
                residences.append(loc)
    return residences

# Main function to process pages and extract residences for notable humans
def process_pages(input_jsonl, output_jsonl, notable_csv):
    # Load the set of notable names from the CSV
    famous_names = set()
    with open(notable_csv, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get('name')
            if name:
                famous_names.add(name.strip().replace('_', ' '))
    
    print(f"Here are 15 random famous people loaded from the CSV:")
    for name in list(famous_names)[:15]:
        print(f"Notable person: {name}")

    # Open input and output files
    with open(input_jsonl, 'r', encoding='utf-8') as infile, \
         open(output_jsonl, 'w', encoding='utf-8') as outfile:
        for line in infile:
            page = json.loads(line)
            title = page.get('title')
            text = page.get('text') or ""
            # Skip pages that are not in our famous people list
            if title not in famous_names:
                continue
            # Extract residence information from the page text
            residences = extract_residence_from_wikitext(text)
            # Prepare the output record
            output_record = {'title': title, 'residences_raw': residences}
            # Write it as a JSON line
            outfile.write(json.dumps(output_record) + '\n')

