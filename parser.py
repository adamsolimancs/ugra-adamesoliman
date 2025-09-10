# Parsing script to convert Wikipedia XML dump to JSONL format
import xml.etree.ElementTree as ET
import json

def parse_wiki_dump(dump_path, output_jsonl_path):
    # Open output .jsonl file for appending UTF-8 JSON records
    with open(output_jsonl_path, 'w', encoding='utf-8') as out_file:
        context = ET.iterparse(dump_path)
        for event, elem in context:
            print(f"parse_wiki_dump [event, elem]:\t [{event}, {elem}]")
            # Only process <page> elements
            if elem.tag.endswith('page'):
                # Check namespace = 0 (article pages only)
                ns = elem.findtext('./ns')
                if ns != '0':
                    elem.clear(); continue
                
                # Build record dictionary and write as JSON line
                title = elem.findtext('./title')
                text = elem.findtext('.//text')
                record = {'title': title, 'text': text}
                out_file.write(json.dumps(record) + '\n')
                # Free memory by clearing processed element
                elem.clear()
