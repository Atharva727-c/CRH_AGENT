from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Iterable

from fpdf import FPDF


def sanitize_text(text: str | None) -> str:
    """Remove/replace unicode characters that aren't supported by basic PDF fonts."""
    if not text:
        return ""

    replacements = {
        "•": "-",
        "—": "-",
        "–": "-",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "…": "...",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "©": "(c)",
        "®": "(R)",
        "™": "(TM)",
    }

    result = str(text)
    for unicode_char, ascii_char in replacements.items():
        result = result.replace(unicode_char, ascii_char)

    cleaned = ""
    for char in result:
        if ord(char) < 128 or char in ["\n", "\t", "\r"]:
            cleaned += char
        else:
            cleaned += "?"
    return cleaned


def _safe_pdf_output(pdf: FPDF) -> bytes:
    """Return PDF bytes across fpdf/fpdf2 variants."""
    try:
        result = pdf.output(dest="S")
        if isinstance(result, bytearray):
            return bytes(result)
        if isinstance(result, bytes):
            return result
        if isinstance(result, str):
            return result.encode("latin-1")
        return bytes(result)
    except Exception:
        result = pdf.output()
        if isinstance(result, (bytes, bytearray)):
            return bytes(result)
        return str(result).encode("latin-1")


def build_qa_pdf_payload(
    question: str,
    answer_text: str,
    thinking_steps: Iterable[dict] | None = None,
    tool_calls: Iterable[dict] | None = None,
    sources: Iterable[dict] | None = None,
) -> str:
    """Create a deterministic text payload so we can cache by string."""
    parts: list[str] = []
    parts.append(f"Q: {question.strip()}")
    parts.append("")
    parts.append(f"A: {answer_text.strip() if answer_text else ''}")

    ts = list(thinking_steps or [])
    if ts:
        parts.append("")
        parts.append("Thinking Steps:")
        for step in ts:
            title = (step.get("title") or "Planning the next steps").strip()
            desc = (step.get("description") or step.get("content") or "").strip()
            if not desc:
                continue
            parts.append(f"- {title}")
            parts.append(f"  {desc}")

    tc = list(tool_calls or [])
    if tc:
        parts.append("")
        parts.append("Tool Calls:")
        for call in tc:
            tool = (call.get("tool") or "Unknown").strip()
            inp = call.get("input", "")
            parts.append(f"- {tool}")
            parts.append(f"  Input: {inp}")

    src = list(sources or [])
    if src:
        parts.append("")
        parts.append("Sources:")
        for s in src:
            url = (s.get("url") or "").strip()
            title = (s.get("title") or url).strip()
            if not url and not title:
                continue
            parts.append(f"- {title if title else url}")
            if title and url and url != title:
                parts.append(f"- {url}")

    return "\n".join(parts)


def generate_qa_pdf_bytes(title: str, payload_text: str) -> bytes:
    """Generate a single-Q/A PDF from a pre-built payload text.

    Beautified layout:
    - Header bar + title
    - Shaded Question/Answer blocks
    - Section headings (Thinking Steps / Tool Calls / Sources)
    - Bullets + indentation
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Theme colors
    navy = (30, 58, 138)
    bg = (245, 247, 250)
    ink = (25, 25, 28)
    muted = (90, 95, 105)
    card = (235, 238, 244)

    def _hline(spacing: float = 4.0):
        pdf.ln(spacing)

    def _section_title(text: str):
        pdf.set_text_color(*navy)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 7, sanitize_text(text), ln=True)
        pdf.set_text_color(*ink)

    def _card_block(label: str, text: str):
        _section_title(label)
        pdf.set_fill_color(*card)
        pdf.set_text_color(*ink)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, sanitize_text(text), fill=True)
        _hline(3)

    def _bullet(text: str, level: int = 0):
        indent = 6 * max(level, 0)
        pdf.set_x(pdf.l_margin + indent)
        pdf.set_font("Arial", "", 11)
        pdf.set_text_color(*ink)
        pdf.multi_cell(0, 6, sanitize_text(f"- {text}"))

    def _muted(text: str, level: int = 0):
        indent = 6 * max(level, 0)
        pdf.set_x(pdf.l_margin + indent)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(*muted)
        pdf.multi_cell(0, 5, sanitize_text(text))
        pdf.set_text_color(*ink)

    # Header bar
    pdf.set_fill_color(*bg)
    pdf.rect(0, 0, 210, 28, "F")  # A4 width in mm for default FPDF
    pdf.set_fill_color(*navy)
    pdf.rect(0, 0, 210, 7, "F")

    pdf.set_y(10)
    pdf.set_text_color(*navy)
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 8, sanitize_text(title), ln=True, align="C")

    pdf.set_text_color(*muted)
    pdf.set_font("Arial", "", 10)
    pdf.cell(
        0,
        6,
        sanitize_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
        ln=True,
        align="C",
    )
    _hline(4)

    # Parse payload into sections (based on our deterministic formatting),
    # then render in the requested chronology:
    # Question -> Thinking Steps -> Answer -> Sources
    question_text = ""
    answer_text = ""
    thinking_steps: list[tuple[str, list[str]]] = []
    tool_calls: list[tuple[str, list[str]]] = []
    sources: list[str] = []

    section: str | None = None
    pending_title: str | None = None
    pending_lines: list[str] = []

    def _flush_pending():
        nonlocal pending_title, pending_lines
        if pending_title is None:
            return
        if section == "thinking_steps":
            thinking_steps.append((pending_title, pending_lines))
        elif section == "tool_calls":
            tool_calls.append((pending_title, pending_lines))
        pending_title = None
        pending_lines = []

    lines = (payload_text or "").splitlines()
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue

        if line.startswith("Q:"):
            _flush_pending()
            section = "q"
            question_text = line[2:].strip()
            continue

        if line.startswith("A:"):
            _flush_pending()
            section = "a"
            answer_text = line[2:].strip()
            continue

        if line.strip() in {"Thinking Steps:", "Tool Calls:", "Sources:"}:
            _flush_pending()
            section = line.strip().rstrip(":").lower().replace(" ", "_")
            continue

        # Indented continuation lines (descriptions / inputs)
        if line.startswith("  "):
            if section in {"thinking_steps", "tool_calls"} and pending_title:
                pending_lines.append(line.strip())
            elif section == "q":
                question_text = (question_text + "\n" + line.strip()).strip()
            elif section == "a":
                answer_text = (answer_text + "\n" + line.strip()).strip()
            continue

        # Bullet lines
        if line.startswith("- "):
            if section in {"thinking_steps", "tool_calls"}:
                _flush_pending()
                pending_title = line[2:].strip()
                pending_lines = []
            elif section == "sources":
                sources.append(line[2:].strip())
            continue

        # Plain text lines
        if section == "q":
            question_text = (question_text + "\n" + line).strip()
        elif section == "a":
            answer_text = (answer_text + "\n" + line).strip()
        elif section == "sources":
            sources.append(line.strip())
        else:
            # Ignore unknown sections
            continue

    _flush_pending()

    # Render in requested order
    if question_text:
        _card_block("Question", question_text)

    if thinking_steps:
        _section_title("Thinking Steps")
        for t, desc_lines in thinking_steps:
            _bullet(t, level=0)
            for dl in desc_lines:
                _muted(dl, level=1)
        _hline(4)

    if tool_calls:
        _section_title("Tool Calls")
        for t, inp_lines in tool_calls:
            _bullet(t, level=0)
            for il in inp_lines:
                _muted(il, level=1)
        _hline(4)

    if answer_text:
        _card_block("Answer", answer_text)

    if sources:
        _section_title("Sources")
        for s in sources:
            _bullet(s, level=0)
        _hline(2)

    return _safe_pdf_output(pdf)


@lru_cache(maxsize=256)
def generate_qa_pdf_bytes_cached(title: str, payload_text: str) -> bytes:
    return generate_qa_pdf_bytes(title=title, payload_text=payload_text)


