import io
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout

from xml_reader import (
    display_xml_structure,
    get_all_elements,
    get_element_value,
    read_xml_file,
)


class TestXmlReader(unittest.TestCase):
    def _write_temp_xml(self, content):
        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_read_xml_file_returns_root_for_valid_xml(self):
        xml_path = self._write_temp_xml("<Root><Child>value</Child></Root>")

        root = read_xml_file(xml_path)

        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "Root")

    def test_read_xml_file_returns_none_for_missing_file(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = read_xml_file("/tmp/does-not-exist.xml")

        self.assertIsNone(result)
        self.assertIn("not found", buffer.getvalue())

    def test_read_xml_file_returns_none_for_parse_error(self):
        xml_path = self._write_temp_xml("<Root><Child></Root>")
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            result = read_xml_file(xml_path)

        self.assertIsNone(result)
        self.assertIn("Error parsing XML file", buffer.getvalue())

    def test_display_xml_structure_prints_nested_structure(self):
        root = ET.fromstring('<Root attr="x"> text <Child>v</Child></Root>')
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            display_xml_structure(root)

        output = buffer.getvalue()
        self.assertIn('<Root attr="x">', output)
        self.assertIn("text", output)
        self.assertIn("<Child>", output)
        self.assertIn("v", output)

    def test_get_element_value_and_get_all_elements(self):
        root = ET.fromstring("<Root><Item>a</Item><Group><Item>b</Item></Group></Root>")

        first_item = get_element_value(root, "Item")
        all_items = get_all_elements(root, "Item")

        self.assertEqual(first_item, "a")
        self.assertEqual(len(all_items), 2)
        self.assertEqual([elem.text for elem in all_items], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
