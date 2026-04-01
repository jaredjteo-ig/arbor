"""Policy document text extraction service.

Extracts plain text from uploaded policy files (PDF, DOCX, TXT)
for storage in the CompanyPolicy content field.  Supports encoding
detection, repeated header/footer stripping, and extraction quality
validation.

Company Policy Upload feature.
"""

import hashlib
import io
import logging
import re
import threading
from collections import Counter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Maximum extracted text length (characters).
# ---------------------------------------------------------------------------
_MAX_TEXT_LENGTH = 500_000

# Minimum number of pages where a line must repeat to be considered a
# header or footer candidate for stripping.
_HEADER_FOOTER_REPEAT_THRESHOLD = 3

# Quality validation thresholds
_MIN_WORD_COUNT = 10
_MAX_CHAR_TO_WORD_RATIO = 20.0
_MAX_SPECIAL_CHAR_RATIO = 0.30


# ===========================================================================
# PDF extraction
# ===========================================================================


def extract_text_from_pdf(
    file_bytes: bytes,
    timeout_seconds: int = 15,
) -> tuple[str, str]:
    """Extract text from a PDF document using pdfplumber.

    Strips repeated headers and footers heuristically: if the first or
    last line of a page repeats verbatim across ``_HEADER_FOOTER_REPEAT_THRESHOLD``
    or more pages, those lines are removed from the output.

    Args:
        file_bytes: Raw PDF bytes.
        timeout_seconds: Maximum wall-clock seconds before the extraction
            is abandoned and ``("", "timeout")`` is returned.

    Returns:
        ``(extracted_text, status)`` where *status* is one of
        ``"success"``, ``"partial"``, ``"failed"``, or ``"timeout"``.
    """
    result: list[str] = []
    status: list[str] = ["success"]
    error: list[BaseException] = []

    def _do_extract() -> None:
        try:
            import pdfplumber

            page_texts: list[list[str]] = []

            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    lines = text.split("\n")
                    page_texts.append(lines)

            if not page_texts:
                result.append("")
                return

            # --- Heuristic header/footer detection ---
            first_lines: Counter[str] = Counter()
            last_lines: Counter[str] = Counter()
            for lines in page_texts:
                non_empty = [ln for ln in lines if ln.strip()]
                if non_empty:
                    first_lines[non_empty[0]] += 1
                    last_lines[non_empty[-1]] += 1

            repeated_headers = {
                line
                for line, count in first_lines.items()
                if count >= _HEADER_FOOTER_REPEAT_THRESHOLD
            }
            repeated_footers = {
                line
                for line, count in last_lines.items()
                if count >= _HEADER_FOOTER_REPEAT_THRESHOLD
            }

            # --- Reassemble with stripping ---
            cleaned_pages: list[str] = []
            for lines in page_texts:
                filtered = []
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if not stripped:
                        filtered.append(line)
                        continue
                    # Check if this is the first non-empty line and a repeated header
                    is_first_non_empty = all(
                        not lines[j].strip() for j in range(i)
                    )
                    # Check if this is the last non-empty line and a repeated footer
                    is_last_non_empty = all(
                        not lines[j].strip() for j in range(i + 1, len(lines))
                    )
                    if is_first_non_empty and stripped in repeated_headers:
                        continue
                    if is_last_non_empty and stripped in repeated_footers:
                        continue
                    filtered.append(line)
                cleaned_pages.append("\n".join(filtered))

            assembled = "\n\n".join(cleaned_pages).strip()
            result.append(assembled)

        except Exception as exc:
            error.append(exc)
            status[0] = "failed"

    thread = threading.Thread(target=_do_extract, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        logger.warning(
            "PDF text extraction timed out after %d seconds",
            timeout_seconds,
        )
        return ("", "timeout")

    if error:
        logger.warning(
            "PDF text extraction failed: %s", error[0],
        )
        return ("", "failed")

    return (result[0] if result else "", status[0])


# ===========================================================================
# DOCX extraction
# ===========================================================================


def extract_text_from_docx(file_bytes: bytes) -> tuple[str, str]:
    """Extract text from a DOCX document, including table content.

    Paragraphs are separated by ``\\n\\n``.  Table cells in a row are
    separated by `` | `` and rows by ``\\n``.

    Args:
        file_bytes: Raw DOCX bytes.

    Returns:
        ``(extracted_text, status)`` — ``"success"`` or ``"failed"``.
    """
    try:
        import docx
    except ImportError:
        logger.error(
            "python-docx is not installed. "
            "Install with: pip install python-docx"
        )
        return ("", "failed")

    try:
        document = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        logger.warning("DOCX parsing failed: %s", exc)
        return ("", "failed")

    parts: list[str] = []

    for element in document.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            # Paragraph
            paragraph_text = element.text or ""
            # python-docx paragraph text via element.text may miss runs;
            # walk runs instead.
            text_parts = []
            for node in element.iter():
                node_tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
                if node_tag == "t" and node.text:
                    text_parts.append(node.text)
            para_text = "".join(text_parts)
            parts.append(para_text)

        elif tag == "tbl":
            # Table — find matching python-docx Table object
            for table in document.tables:
                if table._element is element:
                    rows_text = []
                    for row in table.rows:
                        cells_text = [cell.text for cell in row.cells]
                        rows_text.append(" | ".join(cells_text))
                    parts.append("\n".join(rows_text))
                    break

    text = "\n\n".join(parts).strip()
    return (text, "success")


# ===========================================================================
# TXT extraction
# ===========================================================================


def extract_text_from_txt(file_bytes: bytes) -> tuple[str, str]:
    """Extract text from raw bytes, with encoding detection fallback.

    Tries UTF-8 first.  If that fails, uses ``chardet`` to detect the
    encoding.

    Args:
        file_bytes: Raw text bytes.

    Returns:
        ``(decoded_text, status)`` — ``"success"`` or ``"failed"``.
    """
    if not file_bytes:
        return ("", "success")

    # Attempt UTF-8 first
    try:
        return (file_bytes.decode("utf-8"), "success")
    except UnicodeDecodeError:
        pass

    # Fallback: chardet encoding detection
    try:
        import chardet
    except ImportError:
        logger.error(
            "chardet is not installed and UTF-8 decoding failed. "
            "Install with: pip install chardet"
        )
        return ("", "failed")

    try:
        detection = chardet.detect(file_bytes)
        encoding = detection.get("encoding")
        confidence = detection.get("confidence", 0.0)

        if not encoding:
            logger.warning(
                "chardet could not detect encoding (confidence=%.2f)",
                confidence,
            )
            return ("", "failed")

        logger.info(
            "Detected encoding '%s' with confidence %.2f",
            encoding,
            confidence,
        )
        decoded = file_bytes.decode(encoding)
        return (decoded, "success")

    except (UnicodeDecodeError, LookupError) as exc:
        logger.warning("Text decoding failed after chardet detection: %s", exc)
        return ("", "failed")


# ===========================================================================
# Dispatcher
# ===========================================================================


def extract_text(
    file_bytes: bytes,
    file_type: str,
) -> tuple[str, str]:
    """Top-level dispatcher for text extraction.

    Args:
        file_bytes: Raw document bytes.
        file_type: One of ``"pdf"``, ``"docx"``, or ``"txt"`` (case-insensitive,
            optional leading dot accepted).

    Returns:
        ``(text, status)`` where *text* is truncated to
        ``_MAX_TEXT_LENGTH`` characters.

    Raises:
        ValueError: If *file_type* is not a supported format.
    """
    # Normalise: strip leading dot, lowercase
    normalised = file_type.lower().lstrip(".")

    extractors = {
        "pdf": lambda: extract_text_from_pdf(file_bytes),
        "docx": lambda: extract_text_from_docx(file_bytes),
        "txt": lambda: extract_text_from_txt(file_bytes),
    }

    extractor = extractors.get(normalised)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type '{file_type}'. "
            f"Supported types: pdf, docx, txt"
        )

    text, status = extractor()

    # Truncate if necessary
    if len(text) > _MAX_TEXT_LENGTH:
        logger.info(
            "Extracted text truncated from %d to %d characters",
            len(text),
            _MAX_TEXT_LENGTH,
        )
        text = text[:_MAX_TEXT_LENGTH]

    return (text, status)


# ===========================================================================
# Content hashing
# ===========================================================================


def compute_content_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content* (UTF-8 encoded).

    Args:
        content: The text to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ===========================================================================
# Quality validation
# ===========================================================================


def validate_extraction_quality(text: str) -> tuple[str, list[str]]:
    """Assess the quality of extracted text.

    Checks performed:
    - **Minimum word count**: fewer than ``_MIN_WORD_COUNT`` words is
      classified as garbage / near-empty.
    - **Character-to-word ratio**: a ratio exceeding ``_MAX_CHAR_TO_WORD_RATIO``
      suggests binary or garbled content.
    - **Special character ratio**: if more than ``_MAX_SPECIAL_CHAR_RATIO``
      of characters are non-alphanumeric (excluding spaces), the text
      likely contains OCR noise.

    Args:
        text: The extracted text to validate.

    Returns:
        ``(quality_status, warnings)`` where *quality_status* is one of
        ``"good"``, ``"low_quality"``, or ``"empty"``, and *warnings* is
        a list of human-readable descriptions of quality issues found.
    """
    warnings: list[str] = []

    stripped = text.strip()
    if not stripped:
        return ("empty", ["Text is empty or whitespace-only"])

    words = stripped.split()
    word_count = len(words)

    # --- Check 1: minimum word count ---
    if word_count < _MIN_WORD_COUNT:
        warnings.append(
            f"Minimum word count not met: found {word_count} words, "
            f"expected at least {_MIN_WORD_COUNT}"
        )

    # --- Check 2: char-to-word ratio (binary detection) ---
    if word_count > 0:
        ratio = len(stripped) / word_count
        if ratio > _MAX_CHAR_TO_WORD_RATIO:
            warnings.append(
                f"High character-to-word ratio ({ratio:.1f}), "
                f"may indicate binary or garbled content"
            )

    # --- Check 3: special character ratio (OCR noise) ---
    # Count non-alphanumeric, non-space characters
    alpha_or_space = sum(1 for c in stripped if c.isalnum() or c.isspace())
    total = len(stripped)
    if total > 0:
        special_ratio = 1.0 - (alpha_or_space / total)
        if special_ratio > _MAX_SPECIAL_CHAR_RATIO:
            warnings.append(
                f"Excessive special characters ({special_ratio:.0%}), "
                f"may indicate OCR noise or encoding issues"
            )

    if warnings:
        return ("low_quality", warnings)

    return ("good", [])
