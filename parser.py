# Parsing script to convert Wikipedia XML dump to JSONL format
import xml.etree.ElementTree as ET
import json
import bz2  # used for opening .bz2 compressed files

def find_namespace(dump_path):
    """
    Parses the beginning of an XML file to find the default namespace.
    """
    # We only need the 'start-ns' event to find the namespace
    parser = ET.XMLPullParser(['start-ns'])
    with bz2.open(dump_path, 'rb') as f:
        # Read a small chunk of the file (4KB is plenty)
        chunk = f.read(4096)
        parser.feed(chunk)
        for event, value in parser.read_events(): # type: ignore
            # 'start-ns' event provides a (prefix, uri) tuple
            if event == 'start-ns' and value[0] == '':  # type: ignore
                # The namespace URI is the second item in the tuple
                return value[1] # type: ignore
    
    raise ValueError("Could not find the default namespace in the XML file.")


def parse_wiki_dump(dump_path, output_jsonl_path):
    """_summary_

    Args:
        dump_path (String): file path to Wikipedia dump .bz2
        output_jsonl_path (String): file path to output .jsonl file
    """
    
    try:
        ns_uri = find_namespace(dump_path)
        NS = f'{{{ns_uri}}}'
        print(f"Namespace found: {NS}")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Open output .jsonl file for appending UTF-8 JSON records
    with open(output_jsonl_path, 'w', encoding='utf-8') as out_file:
        parser = ET.XMLPullParser(['end'])
        i = 0
        with bz2.open(dump_path, 'rb') as f:
            for chunk in f:
                parser.feed(chunk)
                # parser.read_events() will yield events as they are parsed from the chunk
                for event, elem in parser.read_events(): # type: ignore                    
                    if event == 'end' and elem.tag == f'{NS}page': # type: ignore # Find page elems
                        # Skip redirect pages
                        if elem.find(f'.//{NS}redirect') is not None: # type: ignore
                            elem.clear() # type: ignore
                            continue

                        # Find the articles <ns=0> using the NAMESPACE.
                        if elem.findtext(f'.//{NS}ns') == '0': # type: ignore
                            # Find title and text
                            title = elem.findtext(f'.//{NS}title') # type: ignore
                            text = elem.findtext(f'.//{NS}revision/{NS}text') # type: ignore

                            if title is not None and text is not None:
                                record = {
                                    'title': title,
                                    'text': text
                                }
                                out_file.write(json.dumps(record) + '\n')
                                
                                i += 1

                        elem.clear() # type: ignore # Clear the element from memory, keep memory usage low

        parser.close()
    
    print(f"Parsing complete: wrote {i} elements from {dump_path} to {output_jsonl_path}")
