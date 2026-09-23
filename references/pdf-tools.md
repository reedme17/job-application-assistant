# Bundled PDF toolchain

Use `scripts/resume_pdf.py` for local extraction, rebuilding, rendering and checks. It does not call a model or upload files. Codex performs the fact-grounded edits to an intermediate JSON source. This is content editing and PDF regeneration, not in-place editing or exact reproduction of the original design. For a source DOCX/LaTeX resume with an established template, prefer its existing authoring path when available.

## Environment setup

Requires Python 3.10+, pypdf and reportlab. Rendering uses Poppler's `pdftoppm`; OCR optionally uses Tesseract with installed language data. Do not assume another computer has this machine's runtime paths. Discover the target environment's tools first; when using Codex bundled dependencies, use the runtime paths returned by its dependency tool.

From the skill folder, choose the appropriate Python executable and run:

```bash
python3 scripts/resume_pdf.py doctor
```

If packages are missing, create a virtual environment outside the skill (for example in the private job-search workspace) and install:

```bash
python3 -m venv /path/to/job-search-workspace/.venv
/path/to/job-search-workspace/.venv/bin/python -m pip install -r scripts/requirements.txt
```

On Windows the interpreter is `.venv\Scripts\python.exe`. Install Poppler through the environment's normal package manager (macOS: `brew install poppler`; Debian/Ubuntu: `sudo apt-get install poppler-utils`). Windows needs a working Poppler distribution on PATH or the explicit executable path. Respect host installation permissions; do not automatically invoke administrator commands. Pass `--pdftoppm /actual/path/to/pdftoppm` if it is not on PATH. OCR likewise accepts `--tesseract` and `--lang`; Tesseract is optional and not required for ordinary text PDFs.

## Read, edit, write, verify

Use fresh versioned output paths; commands refuse existing outputs, including directories. Commands below use illustrative paths; resolve them in the actual workspace.

```bash
python3 scripts/resume_pdf.py extract /work/base.pdf /work/base-extracted.json
python3 scripts/resume_pdf.py render /work/base.pdf /work/base-preview
```

Read all extracted pages and inspect the original images. Scan/low-text pages return exit code 3 and `needs_review: true`. Multi-column extraction can scramble reading order even if this flag is false. For scans, optionally rerun on a new output path:

```bash
python3 scripts/resume_pdf.py extract /work/base.pdf /work/base-ocr.json --ocr --lang eng
```

OCR processes every page and always marks its text unverified; verify names, dates and numbers against images before establishing facts. If OCR is unavailable, request an editable source or transcribe from inspected images with explicit uncertainty; never invent missing content.

Using `assets/resume-template.json` as a schema example, create `resume-source.json` from verified source facts. Replace every sample string. Save one baseline and one tailored JSON per job. Codex edits the tailored JSON using `resume-rules.md`, records the changes, and runs:

```bash
python3 scripts/resume_pdf.py build /work/resume-tailored.json /work/resume-v1.pdf
python3 scripts/resume_pdf.py check /work/resume-v1.pdf /work/check-v1.json --source /work/resume-tailored.json --max-pages 2
python3 scripts/resume_pdf.py render /work/resume-v1.pdf /work/preview-v1
```

Set `--max-pages` to the user's requested length. Do not silently shrink text to force one page. Long content can span pages. The builder escapes input markup, preserves selectable text, and uses a simple single-column layout. Default fonts cover Western text; for Chinese or other scripts supply `--font` and optionally `--bold-font` pointing to licensed TrueType fonts with all required glyphs. The tool refuses unsupported characters rather than silently producing missing glyphs. Complex-script shaping/layout is not guaranteed; use a suitable dedicated renderer and visual review where required.

Read the check report and view EVERY rendered page. Automated checks detect empty text, page limits, suspicious characters, and source strings missing from extraction; they do not certify reading order, layout, factual accuracy or ATS acceptance. Inspect clipping, overlap, contact lines, bullet indentation and page breaks. Fix the JSON/layout as needed and generate a new version. Only mark the resume upload-ready after both automated checks and visual inspection pass. Save the PDF, JSON source, check report, preview paths and factual change log in the application record.

Exit codes: 0 completed/passed; 2 missing dependency, invalid input, or operational error; 3 extraction needs review or automated checks failed. OCR output with code 3 is intentionally usable for review, not a successful verification. Do not confuse the existence of an output file with a passed check.
