import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from sum_esttime import sum_esttime_values


class TestSumEsttime(unittest.TestCase):
    def _write_temp_xml(self, content):
        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_sum_esttime_values_sums_valid_values_and_skips_invalid(self):
        xml_path = self._write_temp_xml(
            """
            <Root EstTime="1.5">
              <A EstTime="2.25" />
              <B EstTime="bad" />
            </Root>
            """
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            total = sum_esttime_values(xml_path)

        self.assertAlmostEqual(total, 3.75, places=6)
        self.assertIn("Warning: Could not convert EstTime value", buffer.getvalue())

    def test_sum_esttime_values_returns_zero_when_no_esttime_attributes(self):
        xml_path = self._write_temp_xml("<Root><A /><B /></Root>")

        total = sum_esttime_values(xml_path)

        self.assertEqual(total, 0.0)

    def test_sum_esttime_values_returns_none_for_missing_file(self):
        result = sum_esttime_values("/tmp/does-not-exist.xml")
        self.assertIsNone(result)

    def test_sum_esttime_values_returns_none_for_parse_error(self):
        xml_path = self._write_temp_xml("<Root><A></Root>")
        result = sum_esttime_values(xml_path)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
