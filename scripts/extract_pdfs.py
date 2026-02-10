#!/usr/bin/env python3
"""
Full PDF extraction pipeline adapted from ta-llm.

Pipeline: Marker-PDF (deep learning) -> pymupdf4llm (fallback) -> PyMuPDF raw (last resort)

For each PDF:
1. Extract with Marker-PDF (equation-aware, layout-aware, OCR-capable)
2. Apply regex LaTeX fixes (font encoding artifacts, bare math commands)
3. Score equation quality (garbled patterns, raw math, LaTeX equations)
4. Write cleaned markdown with YAML frontmatter

Usage:
    python scripts/extract_pdfs.py [--raw-dir raw/] [--cleaned-dir cleaned/] [--quality-file workspace/extraction_quality.json]
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

import yaml

# ─── Extraction backends ───────────────────────────────────────────────

MARKER_AVAILABLE = False
PYMUPDF4LLM_AVAILABLE = False
PYMUPDF_AVAILABLE = False

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    pass

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    pass

try:
    import pymupdf  # fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz as pymupdf
        PYMUPDF_AVAILABLE = True
    except ImportError:
        pass


# ─── Marker singleton ─────────────────────────────────────────────────

_marker_converter = None

def get_marker_converter():
    """Lazily initialize the Marker converter (loads ML models once)."""
    global _marker_converter
    if _marker_converter is None:
        print("  [marker] Loading ML models (first time may download ~1-2 GB)...")
        artifact_dict = create_model_dict()
        _marker_converter = PdfConverter(artifact_dict=artifact_dict)
        print("  [marker] Models loaded.")
    return _marker_converter


# ─── Extraction functions ──────────────────────────────────────────────

def extract_with_marker(pdf_path: str, max_pages: int = None) -> tuple[str, str]:
    """Extract PDF using Marker-PDF (deep learning). Returns (markdown, method)."""
    converter = get_marker_converter()
    rendered = converter(pdf_path)
    text, metadata, images = text_from_rendered(rendered)

    if max_pages and text:
        # Marker doesn't have a native page limit; approximate by splitting on page markers
        # Marker uses "---" or similar as page breaks in some outputs
        pass  # Keep full extraction; page limiting handled at read time

    return text, "marker-pdf"


def extract_with_pymupdf4llm(pdf_path: str, max_pages: int = None) -> tuple[str, str]:
    """Extract PDF using pymupdf4llm (rule-based, fast). Returns (markdown, method)."""
    kwargs = {}
    if max_pages:
        kwargs["pages"] = list(range(max_pages))

    md_text = pymupdf4llm.to_markdown(pdf_path, **kwargs)
    return md_text, "pymupdf4llm"


def extract_with_pymupdf(pdf_path: str, max_pages: int = None) -> tuple[str, str]:
    """Extract PDF using raw PyMuPDF (basic text). Returns (text, method)."""
    doc = pymupdf.open(pdf_path)
    pages_to_extract = min(len(doc), max_pages) if max_pages else len(doc)

    text_parts = []
    for i in range(pages_to_extract):
        page = doc[i]
        text_parts.append(f"<!-- Page {i+1} -->\n{page.get_text()}")

    doc.close()
    return "\n\n".join(text_parts), "pymupdf-raw"


def extract_pdf(pdf_path: str, max_pages: int = None) -> tuple[str, str, list[str]]:
    """
    Try extraction backends in order: marker -> pymupdf4llm -> pymupdf raw.
    Returns (markdown_text, method_used, warnings).
    """
    warnings = []

    # Try Marker first (best quality)
    if MARKER_AVAILABLE:
        try:
            text, method = extract_with_marker(pdf_path, max_pages)
            if text and len(text.strip()) > 100:
                return text, method, warnings
            else:
                warnings.append("marker returned empty/short output, falling back")
        except Exception as e:
            warnings.append(f"marker failed: {e}")

    # Try pymupdf4llm (good quality, fast)
    if PYMUPDF4LLM_AVAILABLE:
        try:
            text, method = extract_with_pymupdf4llm(pdf_path, max_pages)
            if text and len(text.strip()) > 100:
                return text, method, warnings
            else:
                warnings.append("pymupdf4llm returned empty/short output, falling back")
        except Exception as e:
            warnings.append(f"pymupdf4llm failed: {e}")

    # Last resort: raw PyMuPDF
    if PYMUPDF_AVAILABLE:
        try:
            text, method = extract_with_pymupdf(pdf_path, max_pages)
            return text, method, warnings
        except Exception as e:
            warnings.append(f"pymupdf-raw failed: {e}")

    return "", "none", warnings + ["ALL extraction methods failed"]


# ─── Regex LaTeX fixes (adapted from ta-llm) ──────────────────────────

# Font encoding artifact map (common PDF extraction artifacts)
FONT_ARTIFACTS = {
    'ð': '(',
    'Þ': ')',
    'þ': '+',
    '¤': 'ff',
    '‰': 'ffi',
    '½': '[',
    '¼': '=',
    'ﬁ': 'fi',
    'ﬂ': 'fl',
    'ﬀ': 'ff',
    'ﬃ': 'ffi',
    'ﬄ': 'ffl',
}

# LaTeX commands that should be wrapped in $...$ if found bare
LATEX_COMMANDS = [
    r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon', r'\\varepsilon',
    r'\\zeta', r'\\eta', r'\\theta', r'\\vartheta', r'\\iota', r'\\kappa',
    r'\\lambda', r'\\mu', r'\\nu', r'\\xi', r'\\pi', r'\\rho', r'\\sigma',
    r'\\tau', r'\\upsilon', r'\\phi', r'\\varphi', r'\\chi', r'\\psi', r'\\omega',
    r'\\Gamma', r'\\Delta', r'\\Theta', r'\\Lambda', r'\\Xi', r'\\Pi',
    r'\\Sigma', r'\\Upsilon', r'\\Phi', r'\\Psi', r'\\Omega',
    r'\\hat', r'\\tilde', r'\\bar', r'\\vec', r'\\dot', r'\\ddot',
    r'\\sum', r'\\prod', r'\\int', r'\\partial', r'\\nabla', r'\\infty',
    r'\\sqrt', r'\\frac', r'\\mathbb', r'\\mathcal', r'\\mathbf', r'\\mathrm',
    r'\\text', r'\\operatorname',
]

# Math operators that should be in math mode
MATH_OPERATORS = [
    r'E\s*\(', r'Var\s*\(', r'Cov\s*\(', r'Corr\s*\(',
    r'plim', r'argmin', r'argmax', r'sup\b', r'inf\b',
    r'log\s*\(', r'exp\s*\(', r'tr\s*\(',
]

# Convergence arrow patterns
CONVERGENCE_PATTERNS = [
    (r'→d\b', r'$\\xrightarrow{d}$'),
    (r'→p\b', r'$\\xrightarrow{p}$'),
    (r'→a\.s\.\b', r'$\\xrightarrow{a.s.}$'),
    (r'\+d\b(?!\w)', r'$\\xrightarrow{d}$'),
    (r'\+p\b(?!\w)', r'$\\xrightarrow{p}$'),
]


def is_in_math_mode(text: str, pos: int) -> bool:
    """Check if position is inside $...$ or $$...$$ or \\[...\\]."""
    # Count $ signs before position
    before = text[:pos]

    # Check $$...$$
    dd_count = before.count('$$')
    if dd_count % 2 == 1:
        return True

    # Check $...$  (but not $$)
    # Remove $$ first, then count remaining $
    stripped = before.replace('$$', '')
    single_count = stripped.count('$')
    if single_count % 2 == 1:
        return True

    # Check \[...\]
    open_brackets = len(re.findall(r'\\\[', before))
    close_brackets = len(re.findall(r'\\\]', before))
    if open_brackets > close_brackets:
        return True

    return False


def is_in_code_block(text: str, pos: int) -> bool:
    """Check if position is inside a fenced code block."""
    before = text[:pos]
    fence_count = len(re.findall(r'^```', before, re.MULTILINE))
    return fence_count % 2 == 1


def is_in_yaml_frontmatter(text: str, pos: int) -> bool:
    """Check if position is inside YAML frontmatter (between --- delimiters at start)."""
    if not text.startswith('---'):
        return False
    end_marker = text.find('---', 3)
    if end_marker == -1:
        return False
    return pos < end_marker + 3


def apply_regex_latex_fixes(text: str) -> tuple[str, int]:
    """
    Apply regex-based LaTeX fixes adapted from ta-llm.
    Returns (fixed_text, fix_count).
    """
    fix_count = 0

    # 1. Fix font encoding artifacts
    for artifact, replacement in FONT_ARTIFACTS.items():
        if artifact in text:
            count = text.count(artifact)
            text = text.replace(artifact, replacement)
            fix_count += count

    # 2. Wrap bare LaTeX commands in $...$
    for cmd in LATEX_COMMANDS:
        # Match the command NOT already inside math mode
        pattern = re.compile(r'(?<!\$)(' + cmd + r'(?:\{[^}]*\})?)(?!\$)')

        for match in pattern.finditer(text):
            pos = match.start()
            if not is_in_math_mode(text, pos) and not is_in_code_block(text, pos) and not is_in_yaml_frontmatter(text, pos):
                # Only wrap if not already in math
                pass  # Complex replacement done below

        # Simpler approach: find bare commands and wrap them
        def wrap_if_bare(m):
            nonlocal fix_count, text
            start = m.start()
            # Quick check: is there a $ immediately before?
            if start > 0 and text[start-1] == '$':
                return m.group(0)
            if is_in_code_block(text, start):
                return m.group(0)
            fix_count += 1
            return f'${m.group(0)}$'

        # Reset and apply
        text = pattern.sub(wrap_if_bare, text)

    # 3. Fix convergence arrows
    for pattern_str, replacement in CONVERGENCE_PATTERNS:
        matches = re.findall(pattern_str, text)
        if matches:
            text = re.sub(pattern_str, replacement, text)
            fix_count += len(matches)

    return text, fix_count


# ─── Equation quality scoring ──────────────────────────────────────────

def score_equation_quality(text: str) -> dict:
    """
    Score the quality of equation extraction in the text.
    Returns quality metrics dict.
    """
    # Count LaTeX equations (good)
    display_eqs = len(re.findall(r'\$\$.+?\$\$', text, re.DOTALL))
    inline_eqs = len(re.findall(r'(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)', text))
    env_eqs = len(re.findall(r'\\begin\{(equation|align|gather|multline)', text))
    total_latex = display_eqs + inline_eqs + env_eqs

    # Count garbled patterns (bad) — common PDF extraction failures
    garbled_patterns = [
        r'[^\x00-\x7F]{3,}',  # Long sequences of non-ASCII
        r'(?:\?\?){2,}',  # Multiple ??
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # Control characters
        r'[□■▪▫◊◇○●]',  # Box/geometric chars (often garbled math)
    ]
    garbled_count = 0
    for p in garbled_patterns:
        garbled_count += len(re.findall(p, text))

    # Count raw math patterns (mediocre — extracted but not in LaTeX)
    raw_math_patterns = [
        r'(?<!\$)(?:α|β|γ|δ|ε|θ|λ|μ|σ|τ|φ|ψ|ω|Γ|Δ|Θ|Λ|Σ|Φ|Ψ|Ω)(?!\$)',  # Unicode Greek not in math
        r'(?<!\$)(?:∑|∏|∫|∂|∇|∞|√|≤|≥|≠|≈|∈|∉|⊂|⊃|∩|∪)(?!\$)',  # Unicode math operators
        r'(?<!\$)(?:→|←|↔|⇒|⇐|⇔)(?!\$)',  # Arrows not in math
    ]
    raw_math_count = 0
    for p in raw_math_patterns:
        raw_math_count += len(re.findall(p, text))

    # Score: start at 100, penalize garbled and raw
    score = 100
    score -= garbled_count * 5  # Heavy penalty
    score -= raw_math_count * 2  # Light penalty
    score = max(0, min(100, score))

    # Bonus for having many proper LaTeX equations
    if total_latex > 10:
        score = min(100, score + 5)

    return {
        "quality_score": score,
        "latex_equations": total_latex,
        "display_equations": display_eqs,
        "inline_equations": inline_eqs,
        "environment_equations": env_eqs,
        "garbled_patterns": garbled_count,
        "raw_math_unicode": raw_math_count,
    }


# ─── .tex file handling ────────────────────────────────────────────────

def process_tex_file(tex_path: str) -> tuple[str, dict]:
    """Process a .tex file — wrap in markdown with code fence."""
    with open(tex_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Extract metadata from LaTeX
    title_match = re.search(r'\\title\{(.+?)\}', content, re.DOTALL)
    author_match = re.search(r'\\author\{(.+?)\}', content, re.DOTALL)

    title = title_match.group(1).strip() if title_match else Path(tex_path).stem
    authors = author_match.group(1).strip() if author_match else "Unknown"

    # Wrap in code fence for preservation
    markdown = f"# {title}\n\n```latex\n{content}\n```\n"

    line_count = content.count('\n') + 1

    quality = {
        "quality_score": 100,
        "latex_equations": len(re.findall(r'\\begin\{(equation|align|theorem|proof|lemma)', content)),
        "note": "Native LaTeX source — no extraction needed",
    }

    return markdown, {
        "title": title,
        "authors": authors,
        "page_count": line_count // 50,  # Approximate
        "word_count": len(content.split()),
        "line_count": line_count,
        "extraction_method": "native-tex",
        "quality": quality,
    }


# ─── Main pipeline ─────────────────────────────────────────────────────

def detect_file_type(path: str) -> str:
    """Detect if file is a textbook (large) or paper (small)."""
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 3:
        return "textbook"
    return "paper"


def process_file(
    file_path: str,
    source_type: str,
    cleaned_dir: str,
    textbook_page_limit: int = 50,
) -> dict:
    """
    Process a single file through the full pipeline.
    Returns extraction report dict.
    """
    fname = Path(file_path).name
    stem = Path(file_path).stem
    ext = Path(file_path).suffix.lower()

    report = {
        "source_file": file_path,
        "source_type": source_type,
        "filename": fname,
        "file_size_mb": round(os.path.getsize(file_path) / (1024*1024), 2),
    }

    start_time = time.time()

    try:
        if ext == '.tex':
            # .tex files — direct processing
            markdown, meta = process_tex_file(file_path)
            report.update(meta)
            report["extraction_method"] = "native-tex"
            report["extraction_time_s"] = round(time.time() - start_time, 1)

        elif ext == '.pdf':
            # Determine page limit for textbooks
            file_type = detect_file_type(file_path)
            max_pages = textbook_page_limit if file_type == "textbook" else None
            report["file_type"] = file_type

            if max_pages:
                report["page_limit_applied"] = max_pages

            # Step 1: Extract
            print(f"  Extracting: {fname} ({report['file_size_mb']} MB, {file_type})")
            raw_text, method, warnings = extract_pdf(file_path, max_pages)
            report["extraction_method"] = method
            report["extraction_warnings"] = warnings

            if not raw_text or len(raw_text.strip()) < 50:
                report["status"] = "FAILED"
                report["error"] = "Extraction returned empty text"
                return report

            # Get page count from PyMuPDF regardless of extraction method
            if PYMUPDF_AVAILABLE:
                try:
                    doc = pymupdf.open(file_path)
                    report["page_count"] = len(doc)
                    doc.close()
                except:
                    pass

            report["raw_word_count"] = len(raw_text.split())
            report["raw_char_count"] = len(raw_text)

            # Step 2: Apply regex LaTeX fixes
            fixed_text, fix_count = apply_regex_latex_fixes(raw_text)
            report["latex_fixes_applied"] = fix_count

            # Step 3: Score equation quality
            quality = score_equation_quality(fixed_text)
            report["quality"] = quality

            markdown = fixed_text
            report["extraction_time_s"] = round(time.time() - start_time, 1)

        else:
            report["status"] = "SKIPPED"
            report["error"] = f"Unsupported file type: {ext}"
            return report

        # Step 4: Write cleaned file with YAML frontmatter
        out_dir = Path(cleaned_dir) / source_type
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{stem}.md"

        # Build YAML frontmatter
        frontmatter = {
            "source_file": f"raw/{source_type}/{fname}",
            "source_type": source_type,
            "extraction_method": report.get("extraction_method", "unknown"),
            "extraction_quality": report.get("quality", {}).get("quality_score", 0),
        }
        if "page_count" in report:
            frontmatter["page_count"] = report["page_count"]
        if "page_limit_applied" in report:
            frontmatter["page_limit"] = report["page_limit_applied"]

        frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"---\n{frontmatter_str}---\n\n{markdown}")

        report["output_file"] = str(out_path)
        report["output_size_kb"] = round(os.path.getsize(out_path) / 1024, 1)
        report["status"] = "OK"

    except Exception as e:
        report["status"] = "FAILED"
        report["error"] = str(e)
        report["traceback"] = traceback.format_exc()

    return report


def main():
    parser = argparse.ArgumentParser(description="Extract PDFs using Marker-PDF pipeline")
    parser.add_argument("--raw-dir", default="raw/", help="Raw input directory")
    parser.add_argument("--cleaned-dir", default="cleaned/", help="Cleaned output directory")
    parser.add_argument("--quality-file", default="workspace/extraction_quality.json", help="Quality report output")
    parser.add_argument("--textbook-page-limit", type=int, default=50, help="Max pages for textbooks")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    cleaned_dir = Path(args.cleaned_dir)

    # Print available backends
    print("=" * 60)
    print("PDF Extraction Pipeline (adapted from ta-llm)")
    print("=" * 60)
    print(f"  Marker-PDF:  {'AVAILABLE' if MARKER_AVAILABLE else 'NOT AVAILABLE (fallback to pymupdf4llm)'}")
    print(f"  pymupdf4llm: {'AVAILABLE' if PYMUPDF4LLM_AVAILABLE else 'NOT AVAILABLE'}")
    print(f"  PyMuPDF raw: {'AVAILABLE' if PYMUPDF_AVAILABLE else 'NOT AVAILABLE'}")
    print(f"  Textbook page limit: {args.textbook_page_limit}")
    print()

    # Scan raw/ directories
    categories = ["draft", "style", "objective", "reference"]
    all_files = []

    for cat in categories:
        cat_dir = raw_dir / cat
        if not cat_dir.exists():
            print(f"  Warning: {cat_dir} does not exist, skipping")
            continue

        for f in sorted(cat_dir.iterdir()):
            if f.suffix.lower() in ('.pdf', '.tex'):
                all_files.append((str(f), cat))

    print(f"Found {len(all_files)} files to process:")
    for cat in categories:
        count = sum(1 for _, c in all_files if c == cat)
        if count > 0:
            print(f"  {cat}: {count} files")
    print()

    # Process each file
    reports = []
    total = len(all_files)

    for i, (fpath, cat) in enumerate(all_files, 1):
        fname = Path(fpath).name
        print(f"[{i}/{total}] {cat}/{fname}")

        report = process_file(fpath, cat, str(cleaned_dir), args.textbook_page_limit)
        reports.append(report)

        status = report.get("status", "UNKNOWN")
        method = report.get("extraction_method", "?")
        quality = report.get("quality", {}).get("quality_score", "N/A")
        fixes = report.get("latex_fixes_applied", 0)
        time_s = report.get("extraction_time_s", "?")

        print(f"  -> {status} | method={method} | quality={quality} | fixes={fixes} | {time_s}s")
        if report.get("extraction_warnings"):
            for w in report["extraction_warnings"]:
                print(f"  ⚠  {w}")
        print()

    # Write quality report
    os.makedirs(os.path.dirname(args.quality_file), exist_ok=True)

    summary = {
        "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backends": {
            "marker_pdf": MARKER_AVAILABLE,
            "pymupdf4llm": PYMUPDF4LLM_AVAILABLE,
            "pymupdf_raw": PYMUPDF_AVAILABLE,
        },
        "total_files": total,
        "successful": sum(1 for r in reports if r.get("status") == "OK"),
        "failed": sum(1 for r in reports if r.get("status") == "FAILED"),
        "skipped": sum(1 for r in reports if r.get("status") == "SKIPPED"),
        "total_pages": sum(r.get("page_count", 0) for r in reports),
        "total_words": sum(r.get("raw_word_count", 0) for r in reports),
        "methods_used": {},
        "quality_distribution": {
            "excellent_90_100": sum(1 for r in reports if r.get("quality", {}).get("quality_score", 0) >= 90),
            "good_70_89": sum(1 for r in reports if 70 <= r.get("quality", {}).get("quality_score", 0) < 90),
            "fair_50_69": sum(1 for r in reports if 50 <= r.get("quality", {}).get("quality_score", 0) < 70),
            "poor_below_50": sum(1 for r in reports if 0 < r.get("quality", {}).get("quality_score", 0) < 50),
        },
        "files_needing_review": [
            r["filename"] for r in reports
            if r.get("quality", {}).get("quality_score", 100) < 80
        ],
        "per_file_reports": reports,
    }

    # Count methods
    for r in reports:
        m = r.get("extraction_method", "unknown")
        summary["methods_used"][m] = summary["methods_used"].get(m, 0) + 1

    with open(args.quality_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Print summary
    print("=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"  Total files:   {summary['total_files']}")
    print(f"  Successful:    {summary['successful']}")
    print(f"  Failed:        {summary['failed']}")
    print(f"  Skipped:       {summary['skipped']}")
    print(f"  Total pages:   {summary['total_pages']}")
    print(f"  Total words:   {summary['total_words']}")
    print(f"  Methods used:  {summary['methods_used']}")
    print(f"  Quality file:  {args.quality_file}")

    if summary["files_needing_review"]:
        print(f"\n  Files needing manual review (quality < 80):")
        for fname in summary["files_needing_review"]:
            print(f"    - {fname}")

    print()
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
