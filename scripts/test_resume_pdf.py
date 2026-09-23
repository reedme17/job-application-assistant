"""Offline regression checks using synthetic data and a temporary directory."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("resume_pdf.py")
TEMPLATE = SCRIPT.parent.parent / "assets" / "resume-template.json"


class ResumePdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="resume-pdf-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_tool(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_roundtrip_and_no_overwrite(self):
        pdf = self.root / "resume.pdf"
        self.run_tool("build", TEMPLATE, pdf)
        self.run_tool("check", pdf, self.root / "check.json", "--source", TEMPLATE, "--max-pages", 1)
        self.run_tool("extract", pdf, self.root / "extracted.json")
        extracted = json.loads((self.root / "extracted.json").read_text())
        self.assertIn("Example Candidate", extracted["pages"][0]["text"])
        before = pdf.read_bytes()
        self.run_tool("build", TEMPLATE, pdf, expected=2)
        self.assertEqual(before, pdf.read_bytes())

    def test_missing_content_and_page_limit(self):
        pdf = self.root / "resume.pdf"
        self.run_tool("build", TEMPLATE, pdf)
        data = json.loads(TEMPLATE.read_text())
        data["name"] = "Absent Person"
        source = self.root / "changed.json"
        source.write_text(json.dumps(data))
        self.run_tool("check", pdf, self.root / "bad.json", "--source", source, "--max-pages", 0, expected=3)
        report = json.loads((self.root / "bad.json").read_text())
        self.assertEqual(len(report["failures"]), 2)

    def test_markup_is_literal_and_unicode_requires_font(self):
        data = json.loads(TEMPLATE.read_text())
        data["name"] = "A & B <Candidate>"
        source = self.root / "source.json"
        source.write_text(json.dumps(data))
        self.run_tool("build", source, self.root / "literal.pdf")
        self.run_tool("check", self.root / "literal.pdf", self.root / "check.json", "--source", source)
        data["name"] = "中文姓名"
        source.write_text(json.dumps(data))
        self.run_tool("build", source, self.root / "unicode.pdf", expected=2)
        self.assertFalse((self.root / "unicode.pdf").exists())

    def test_blank_pdf_requires_review(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        blank = self.root / "blank.pdf"
        with blank.open("wb") as stream:
            writer.write(stream)
        self.run_tool("extract", blank, self.root / "extracted.json", expected=3)
        self.run_tool("check", blank, self.root / "check.json", expected=3)


if __name__ == "__main__":
    unittest.main()
