import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

try:
    from visualize_esttime import analyze_esttime_by_element, create_visualizations
except ModuleNotFoundError:
    analyze_esttime_by_element = None
    create_visualizations = None


@unittest.skipIf(analyze_esttime_by_element is None, "matplotlib is not installed")
class TestVisualizeEsttime(unittest.TestCase):
    def _write_temp_xml(self, content):
        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_analyze_esttime_by_element_groups_values(self):
        xml_path = self._write_temp_xml(
            """
            <Root>
              <Cut EstTime="1.0" />
              <Cut EstTime="2.0" />
              <Drill EstTime="3.5" />
              <Bad EstTime="x" />
            </Root>
            """
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            result = analyze_esttime_by_element(xml_path)

        self.assertEqual(result["Cut"], [1.0, 2.0])
        self.assertEqual(result["Drill"], [3.5])
        self.assertNotIn("Bad", result)
        self.assertIn("Warning: Could not convert EstTime value", buffer.getvalue())

    def test_analyze_esttime_by_element_returns_none_for_missing_file(self):
        result = analyze_esttime_by_element("/tmp/does-not-exist.xml")
        self.assertIsNone(result)

    def test_create_visualizations_prints_message_for_empty_input(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            create_visualizations({}, "/tmp/example.xml")
        self.assertIn("No data to visualize", buffer.getvalue())

    def test_create_visualizations_creates_png_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = os.path.join(temp_dir, "sample.xml")
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write("<Root />")

            data = {"Cut": [1.0, 2.0], "Drill": [3.0]}

            create_visualizations(data, xml_path)

            output_path = os.path.join(temp_dir, "sample_esttime_analysis.png")
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)


if __name__ == "__main__":
    unittest.main()
