#!/usr/bin/env python3
"""Local resume PDF utilities. Never sends documents to a remote service."""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape


def output_path(value):
    path = Path(value).resolve()
    if path.exists():
        raise ValueError(f"Output already exists; choose a new version: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(value, path):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def executable(name, override=None):
    found = shutil.which(override or name)
    if not found:
        raise ValueError(f"Missing {name}; install it or pass its executable path.")
    return found


def reader(path):
    from pypdf import PdfReader
    result = PdfReader(path)
    if result.is_encrypted and not result.decrypt(""):
        raise ValueError("Password-protected PDF: supply an authorized unlocked copy.")
    if not result.pages:
        raise ValueError("PDF has no pages.")
    return result


def doctor(args):
    modules = {m: importlib.util.find_spec(m) is not None for m in ("pypdf", "reportlab")}
    poppler = shutil.which(args.pdftoppm or "pdftoppm")
    result = {"python": sys.executable, "python_version": sys.version.split()[0],
              "packages": modules, "pdftoppm": poppler,
              "tesseract_optional": shutil.which(args.tesseract or "tesseract"),
              "ready": all(modules.values()) and bool(poppler)}
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 2


def extract(args):
    destination = output_path(args.output)
    pdf = reader(args.input)
    pages = []
    for number, page in enumerate(pdf.pages, 1):
        text = (page.extract_text(extraction_mode="layout") or "") if page.get_contents() is not None else ""
        method = "embedded_text"
        if args.ocr:
            # Explicit OCR mode applies to every page, including mixed scans/text.
            with tempfile.TemporaryDirectory(prefix="resume-ocr-") as temp:
                prefix = str(Path(temp) / "page")
                subprocess.run([executable("pdftoppm", args.pdftoppm), "-f", str(number),
                                "-l", str(number), "-singlefile", "-r", "200", "-png",
                                str(Path(args.input).resolve()), prefix], check=True,
                               capture_output=True, timeout=120)
                result = subprocess.run([executable("tesseract", args.tesseract),
                                         prefix + ".png", "stdout", "-l", args.lang],
                                        check=True, capture_output=True, text=True, timeout=120)
                text, method = result.stdout, "ocr_unverified"
        pages.append({"page": number, "text": text, "method": method,
                      "needs_review": args.ocr or len(text.strip()) < 40})
    needs_review = any(p["needs_review"] for p in pages)
    write_json({"source_filename": Path(args.input).name, "pages": pages,
                "needs_review": needs_review,
                "note": "Extraction is not proof of accurate reading order or visual completeness."}, destination)
    print(f"Extracted {len(pages)} page(s): {destination}")
    return 3 if needs_review else 0


def validated_source(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("Resume requires a nonempty name string.")
    if not isinstance(data.get("contact_lines", []), list):
        raise ValueError("contact_lines must be a list of strings.")
    texts = [data["name"]] + data.get("contact_lines", [])
    if not isinstance(data.get("sections"), list) or not data["sections"]:
        raise ValueError("sections must be a nonempty list.")
    for section in data["sections"]:
        if not isinstance(section, dict) or not isinstance(section.get("heading"), str):
            raise ValueError("Each section needs a heading string.")
        texts.append(section["heading"])
        if not isinstance(section.get("entries"), list) or not section["entries"]:
            raise ValueError("Each section needs a nonempty entries list.")
        for entry in section["entries"]:
            if not isinstance(entry, dict):
                raise ValueError("Each entry must be an object.")
            for key in ("title", "detail", "text"):
                if key in entry:
                    texts.append(entry[key])
            bullets = entry.get("bullets", [])
            if not isinstance(bullets, list):
                raise ValueError("bullets must be a list of strings.")
            texts.extend(bullets)
    if not all(isinstance(t, str) for t in texts):
        raise ValueError("All resume text must be strings.")
    return data, texts


def build(args):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    destination = output_path(args.output)
    data, texts = validated_source(args.input)
    regular, bold = "Helvetica", "Helvetica-Bold"
    if args.font:
        pdfmetrics.registerFont(TTFont("ResumeRegular", args.font))
        pdfmetrics.registerFont(TTFont("ResumeBold", args.bold_font or args.font))
        regular, bold = "ResumeRegular", "ResumeBold"
        for font in (regular, bold):
            cmap = pdfmetrics.getFont(font).face.charToGlyph
            missing = {c for t in texts for c in t if not c.isspace() and ord(c) not in cmap}
            if missing:
                raise ValueError(f"Font missing characters: {''.join(sorted(missing))!r}")
    else:
        for text in texts:
            try:
                text.encode("cp1252")
            except UnicodeEncodeError as error:
                raise ValueError("Non-Latin characters need --font with a suitable Unicode TrueType font.") from error
    body = ParagraphStyle("body", fontName=regular, fontSize=10.2, leading=14, spaceAfter=4)
    title = ParagraphStyle("name", parent=body, fontName=bold, fontSize=20, leading=24, spaceAfter=7)
    heading = ParagraphStyle("section", parent=body, fontName=bold, fontSize=11,
                             spaceBefore=11, spaceAfter=6, keepWithNext=True,
                             textColor=colors.HexColor("#24364B"))
    entry_title = ParagraphStyle("entry", parent=body, fontName=bold, keepWithNext=True)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, firstLineIndent=-7)

    def paragraph(text, style):
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    story = [paragraph(data["name"], title)]
    story.extend(paragraph(line, body) for line in data.get("contact_lines", []))
    for section in data["sections"]:
        story.append(paragraph(section["heading"], heading))
        for entry in section["entries"]:
            for key, style in (("title", entry_title), ("detail", body), ("text", body)):
                if entry.get(key):
                    story.append(paragraph(entry[key], style))
            story.extend(paragraph("- " + item, bullet) for item in entry.get("bullets", []))
            story.append(Spacer(1, 3))
    # Render to a temporary file first; never replace an existing user artifact.
    with tempfile.TemporaryDirectory(prefix="resume-build-") as temp:
        staged = Path(temp) / "resume.pdf"
        SimpleDocTemplate(str(staged), pagesize=A4 if args.page_size == "a4" else letter,
                          rightMargin=44, leftMargin=44, topMargin=38, bottomMargin=38,
                          title=data["name"] + " - Resume", author=data["name"]).build(story)
        with destination.open("xb") as output:
            output.write(staged.read_bytes())
    print(f"Created {destination}; run check, render and visual review before uploading.")
    return 0


def render(args):
    destination = output_path(args.output)
    tool = executable("pdftoppm", args.pdftoppm)
    pdf = reader(args.input)
    destination.mkdir()
    subprocess.run([tool, "-r", "120", "-png", str(Path(args.input).resolve()),
                    str(destination / "page")], check=True, capture_output=True, timeout=180)
    images = sorted(destination.glob("page-*.png"))
    if len(images) != len(pdf.pages):
        raise ValueError("Rendered page count differs from PDF; inspect the partial output.")
    print(json.dumps({"pages": len(images), "images": [str(p) for p in images]}, indent=2))
    return 0


def normalized(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def check(args):
    destination = output_path(args.output)
    pdf = reader(args.input)
    texts = [p.extract_text() or "" for p in pdf.pages]
    failures = []
    if len(texts) > args.max_pages:
        failures.append(f"Page count {len(texts)} exceeds requested maximum {args.max_pages}.")
    for index, text in enumerate(texts, 1):
        if not text.strip():
            failures.append(f"Page {index} has no extractable text.")
        if "\ufffd" in text or "\x00" in text:
            failures.append(f"Page {index} contains suspicious replacement characters.")
    if args.source:
        _, expected = validated_source(args.source)
        actual = normalized("\n".join(texts))
        for index, item in enumerate(expected):
            if item and normalized(item) not in actual:
                failures.append(f"Source text item {index} not found in extracted PDF text.")
    result = {"page_count": len(texts), "automated_checks_passed": not failures,
              "failures": failures, "visual_review_required": True,
              "note": "Does not prove original facts, correct reading order, or absence of clipping/overlap."}
    write_json(result, destination)
    print(json.dumps(result, indent=2))
    return 0 if not failures else 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "extract", "build", "render", "check"):
        sub = commands.add_parser(name)
        if name != "doctor":
            sub.add_argument("input")
            sub.add_argument("output", help="New output path; existing paths are never overwritten")
        if name in ("doctor", "extract", "render"):
            sub.add_argument("--pdftoppm", help="Poppler pdftoppm executable path")
        if name in ("doctor", "extract"):
            sub.add_argument("--tesseract", help="Optional Tesseract executable path")
        if name == "extract":
            sub.add_argument("--ocr", action="store_true")
            sub.add_argument("--lang", default="eng", help="Installed Tesseract languages, e.g. eng+chi_sim")
        if name == "build":
            sub.add_argument("--font", help="Unicode TrueType font covering all resume characters")
            sub.add_argument("--bold-font")
            sub.add_argument("--page-size", choices=("letter", "a4"), default="letter")
        if name == "check":
            sub.add_argument("--source", help="Resume JSON used to generate this PDF")
            sub.add_argument("--max-pages", type=int, default=2)
        sub.set_defaults(handler=globals()[name])
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
