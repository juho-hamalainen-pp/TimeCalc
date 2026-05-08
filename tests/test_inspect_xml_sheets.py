import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from inspect_xml_sheets import inspect_xml_file


class TestInspectXmlSheets(unittest.TestCase):
    def _write_temp_xml(self, content):
        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_reports_missing_sheets_container(self):
        xml_path = self._write_temp_xml("<Root><Main /></Root>")
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            inspect_xml_file(xml_path)

        self.assertIn("No <Sheets> container found", buffer.getvalue())

    def test_reports_no_sheet_elements_inside_sheets(self):
        xml_path = self._write_temp_xml("<Root><Sheets><Other /></Sheets></Root>")
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            inspect_xml_file(xml_path)

        output = buffer.getvalue()
        self.assertIn("Found 0 Sheet element(s)", output)
        self.assertIn("No <Sheet> elements found inside <Sheets>!", output)

    def test_reports_sheet_details_and_time_samples(self):
        xml_path = self._write_temp_xml(
            """
            <Root Name="ProgramA">
              <Sheets>
                <Sheet Name="S1">
                  <StartTime>10:00</StartTime>
                  <EndTime>10:01</EndTime>
                  <Times>
                    <Time Command="Cut">100</Time>
                    <Time Command="Drill">200</Time>
                  </Times>
                </Sheet>
              </Sheets>
            </Root>
            """
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            inspect_xml_file(xml_path)

        output = buffer.getvalue()
        self.assertIn("Found 1 Sheet element(s)", output)
        self.assertIn("StartTime: 10:00", output)
        self.assertIn("EndTime: 10:01", output)
        self.assertIn("Time #1: Command='Cut', Value='100'", output)

    def test_reports_file_not_found(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            inspect_xml_file("/tmp/does-not-exist.xml")
        self.assertIn("File not found", buffer.getvalue())

    def test_reports_parse_error(self):
        xml_path = self._write_temp_xml("<Root><Sheets></Root>")
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            inspect_xml_file(xml_path)

        self.assertIn("XML Parse Error", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
