# Data extraction script to extract residence information from Wikipedia pages
import mwparserfromhell
import re
import json

# 
def extract_residence_from_wikitext(wikitext):
    # Parse wikitext with mwparserfromhell
    wikicode = mwparserfromhell.parse(wikitext)
    # Find infobox templates
    infoboxes = wikicode.filter_templates(matches='infobox .*')
    residences = []
    for tpl in infoboxes:
        if tpl.has("residence"):
            value = str(tpl.get("residence").value).strip()
            # Split multiple entries by comma or <br>, if needed
            residences.extend([v.strip() for v in re.split(r'<br\s*/?>|,', value) if v.strip()])
    # If no infobox residence, search text for cues
    if not residences:
        # Simple regex for sentences like "resides in City, Country"
        matches = re.findall(r'resid(?:e|ence|es) in ([A-Za-z ,\-]+)', wikitext, re.IGNORECASE)
        residences.extend(matches)
    return residences

#
def process_pages(input_jsonl, output_jsonl):    
    with open(input_jsonl, 'r', encoding='utf-8') as infile, \
         open(output_jsonl, 'w', encoding='utf-8') as outfile:
        for line in infile:
            page = json.loads(line)
            title = page['title']
            text = page['text'] or ""
            # Skip if title not in our list of famous people (not shown)
            # Extract residences
            places = extract_residence_from_wikitext(text)
            # Write out structured intermediate data
            output = {'title': title, 'residences_raw': places}
            outfile.write(json.dumps(output) + '\n')
