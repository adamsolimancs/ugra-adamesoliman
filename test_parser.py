# test_parse_wiki_dump.py
# File to test parse_wiki_dump.py functionality
# Run with: python3 -m unittest test_parser.py

import json
import unittest
import tempfile
from pathlib import Path
from parser import parse_wiki_dump

def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class TestParseWikiDump(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def write_xml(self, content: str) -> str:
        xml_path = self.tmp_path / "input.xml"
        xml_path.write_text(content, encoding="utf-8")
        return str(xml_path)

    def output_path(self) -> str:
        return str(self.tmp_path / "out.jsonl")

    def test_basic_parsing_non_namespaced(self):
        # Non-namespaced minimal XML with two pages; only ns=0 should be included
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <title>Foo</title>
    <ns>0</ns>
    <revision>
      <text>Foo article content.</text>
    </revision>
  </page>
  <page>
    <title>User:Bar</title>
    <ns>2</ns>
    <revision>
      <text>User page content.</text>
    </revision>
  </page>
</mediawiki>
"""
        in_path = self.write_xml(xml)
        out_path = self.output_path()

        parse_wiki_dump(in_path, out_path)
        records = read_jsonl(out_path)

        self.assertEqual(len(records), 1, "Should only include ns=0 article pages")
        self.assertEqual(records[0]["title"], "Foo")
        self.assertEqual(records[0]["text"], "Foo article content.")

    def test_missing_text_field(self):
        # Page with ns=0 but missing <text>; current parser should write text=None
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <title>NoTextArticle</title>
    <ns>0</ns>
    <revision>
      <id>123</id>
      <!-- no text element -->
    </revision>
  </page>
</mediawiki>
"""
        in_path = self.write_xml(xml)
        out_path = self.output_path()

        parse_wiki_dump(in_path, out_path)
        records = read_jsonl(out_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "NoTextArticle")
        self.assertIsNone(records[0]["text"], "When <text> is missing, text should be None")

    def test_utf8_characters(self):
        # Ensure UTF-8 content is preserved
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <title>Emoji 🚀</title>
    <ns>0</ns>
    <revision>
      <text>Unicode snowman ☃ and emoji 👍</text>
    </revision>
  </page>
</mediawiki>
"""
        in_path = self.write_xml(xml)
        out_path = self.output_path()

        parse_wiki_dump(in_path, out_path)
        records = read_jsonl(out_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Emoji 🚀")
        self.assertEqual(records[0]["text"], "Unicode snowman ☃ and emoji 👍")

    def test_namespaced_dump_current_behavior(self):
        # Typical Wikipedia dumps use a default namespace; with the current parser
        # implementation (findtext('./ns')), no records will be found because child
        # elements are namespaced. This test documents current behavior.
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/">
  <page>
    <title>Namespaced Foo</title>
    <ns>0</ns>
    <revision>
      <text>Should not be captured with current parser due to namespaces.</text>
    </revision>
  </page>
  <page>
    <title>Namespaced Talk</title>
    <ns>1</ns>
    <revision>
      <text>Talk page</text>
    </revision>
  </page>
</mediawiki>
"""
        in_path = self.write_xml(xml)
        out_path = self.output_path()

        parse_wiki_dump(in_path, out_path)
        records = read_jsonl(out_path)

        # With the current code, findtext('./ns') returns None for namespaced elements,
        # so no article pages are emitted. If you later fix the parser to handle
        # namespaces, update this expectation accordingly.
        self.assertEqual(
            len(records), 0,
            "Current implementation does not handle namespaced dumps; expected 0 records."
        )

    def test_multiple_articles_non_namespaced(self):
        # Multiple ns=0 pages should all be emitted
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<mediawiki>
  <page>
    <title>A</title>
    <ns>0</ns>
    <revision><text>Content A</text></revision>
  </page>
  <page>
    <title>B</title>
    <ns>0</ns>
    <revision><text>Content B</text></revision>
  </page>
  <page>
    <title>Template:C</title>
    <ns>10</ns>
    <revision><text>Template C</text></revision>
  </page>
</mediawiki>
"""
        in_path = self.write_xml(xml)
        out_path = self.output_path()

        parse_wiki_dump(in_path, out_path)
        records = read_jsonl(out_path)

        self.assertEqual(len(records), 2)
        titles = [r["title"] for r in records]
        texts = [r["text"] for r in records]
        self.assertCountEqual(titles, ["A", "B"])
        self.assertCountEqual(texts, ["Content A", "Content B"])


if __name__ == "__main__":
    unittest.main()