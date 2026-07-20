import json
import math
import re
import unicodedata
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz

from app.services.anonymizer import generate_masked_candidate_id
from app.services.parser.structured import build_structured_resume


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 44
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
BOTTOM_MARGIN = 54

NAVY = (0.05, 0.09, 0.16)
INK = (0.11, 0.16, 0.25)
MUTED = (0.39, 0.45, 0.55)
CYAN = (0.02, 0.68, 0.79)
LIGHT_BG = (0.95, 0.98, 1.0)
LINE = (0.82, 0.88, 0.94)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


class MaskedResumeError(ValueError):
    pass


def _repair_export_text(text: str) -> str:
    if not text:
        return ""
    if any(marker in text for marker in ("Ã", "â", "Â", "ð")):
        for source_encoding in ("cp1252", "latin-1"):
            try:
                repaired = text.encode(source_encoding).decode("utf-8")
            except Exception:
                continue
            if repaired and repaired.count("�") <= text.count("�"):
                text = repaired
                break
    replacements = {
        "\u00a0": " ",
        "•": "- ",
        "◦": "- ",
        "●": "- ",
        "▪": "- ",
        "–": "-",
        "—": "-",
        "−": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "…": "...",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text


def _text(value: Any) -> str:
    if isinstance(value, dict):
        val = value.get("value") or ""
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        text = str(val).strip()
    elif isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace").strip()
    elif value is None:
        text = ""
    else:
        text = str(value).strip()
    
    # Normalize Unicode text
    text = unicodedata.normalize("NFKC", text)
    text = _repair_export_text(text)
    
    # Clean text: remove control characters except newline and tab
    text = "".join(
        ch for ch in text 
        if (ch == "\n" or ch == "\t" or (ch.isprintable() and not (0 <= ord(ch) <= 31)))
    )
    
    return text


def _load_parsed_resume(resume: Any) -> dict[str, Any]:
    version = getattr(resume, "current_version", None)
    if version is None or not getattr(version, "parsed_json", None):
        raise MaskedResumeError("Parsed resume data is unavailable")
    try:
        parsed_json = version.parsed_json
        if isinstance(parsed_json, bytes):
            parsed_json = parsed_json.decode("utf-8", errors="replace")
        parsed = json.loads(parsed_json)
    except Exception as exc:
        raise MaskedResumeError("Parsed resume JSON is invalid") from exc
    if not isinstance(parsed, dict):
        raise MaskedResumeError("Parsed resume JSON is invalid")
    return parsed


def _structured_resume(parsed: dict[str, Any]) -> dict[str, Any]:
    structured = parsed.get("structured")
    if isinstance(structured, dict):
        return build_structured_resume({**parsed, "structured": structured})
    return build_structured_resume(parsed)


def _candidate_code(resume: Any) -> str:
    source_id = getattr(resume, "candidate_id", None) or getattr(resume, "id", "")
    return f"CAND-{generate_masked_candidate_id(source_id)[:8].upper()}"


def masked_resume_filename(resume: Any) -> str:
    code = _candidate_code(resume)
    return f"masked_{code}.pdf"


def _collect_replacements(parsed: dict[str, Any], structured: dict[str, Any], resume: Any, code: str) -> list[tuple[str, str]]:
    replacements: list[tuple[str, str]] = []

    def add(value: Any, replacement: str = "[withheld]") -> None:
        text = _text(value)
        if len(text) >= 3:
            replacements.append((text, replacement))

    add(structured.get("name"), code)
    add(parsed.get("full_name"), code)

    candidate = getattr(resume, "candidate", None)
    if candidate is not None:
        full_name = " ".join(part for part in [getattr(candidate, "first_name", ""), getattr(candidate, "last_name", "")] if part)
        add(full_name, code)
        add(getattr(candidate, "email", None))
        add(getattr(candidate, "phone", None))

    for item in parsed.get("emails") or []:
        add(item)
    for item in parsed.get("phones") or []:
        add(item)

    for key in ("email", "phone", "location", "linkedin", "github"):
        add(structured.get(key))
        add(parsed.get(key))

    for index, item in enumerate(structured.get("experience") or [], start=1):
        if isinstance(item, dict):
            add(item.get("company"), f"Employer {index}")
            add(item.get("location"))

    for item in structured.get("education") or []:
        if isinstance(item, dict):
            add(item.get("institution"), "Institution withheld")

    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for original, replacement in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        key = original.lower()
        if key not in seen:
            seen.add(key)
            unique.append((original, replacement))
    return unique


def _mask(value: Any, replacements: list[tuple[str, str]]) -> str:
    text = _text(value)
    if not text:
        return ""
    for original, replacement in replacements:
        text = re.sub(re.escape(original), replacement, text, flags=re.IGNORECASE)
    text = EMAIL_RE.sub("[withheld]", text)
    text = URL_RE.sub("[withheld]", text)
    text = PHONE_RE.sub("[withheld]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _estimate_height(text: str, font_size: float, width: float, min_height: float = 18) -> float:
    if not text:
        return min_height
    chars_per_line = max(24, int(width / (font_size * 0.48)))
    lines = 0
    for paragraph in text.splitlines() or [text]:
        lines += max(1, math.ceil(len(paragraph) / chars_per_line))
    return max(min_height, lines * (font_size + 4) + 6)


class _PdfTemplate:
    def __init__(self, code: str, headline: str) -> None:
        self.doc = fitz.open()
        self.code = code
        self.headline = headline
        self.page: fitz.Page | None = None
        self.y = MARGIN
        self.regular_font = "helv"
        self.bold_font = "hebo"
        self.regular_font_file = self._find_font(
            [
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\calibri.ttf",
            ]
        )
        self.bold_font_file = self._find_font(
            [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
            ]
        )
        self._new_page(first=True)

    def _find_font(self, candidates: list[str]) -> str | None:
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        return None

    def _new_page(self, first: bool = False) -> None:
        self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        if self.regular_font_file:
            self.page.insert_font(fontname=self.regular_font, fontfile=self.regular_font_file)
        if self.bold_font_file:
            self.page.insert_font(fontname=self.bold_font, fontfile=self.bold_font_file)
        if first:
            self.page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, 118), fill=NAVY, color=NAVY)
            self.page.draw_rect(fitz.Rect(0, 112, PAGE_WIDTH, 118), fill=CYAN, color=CYAN)
            self.page.insert_text(
                fitz.Point(MARGIN, 42),
                "MASKED CANDIDATE RESUME",
                fontsize=9,
                fontname=self.bold_font,
                color=CYAN,
            )
            self.page.insert_text(
                fitz.Point(MARGIN, 74),
                self.code,
                fontsize=24,
                fontname=self.bold_font,
                color=(1, 1, 1),
            )
            self.page.insert_textbox(
                fitz.Rect(MARGIN, 88, PAGE_WIDTH - MARGIN, 110),
                self.headline or "Technical candidate profile",
                fontsize=10,
                fontname=self.regular_font,
                color=(0.82, 0.9, 0.96),
                align=0,
            )
            self.y = 142
        else:
            self.page.insert_textbox(
                fitz.Rect(MARGIN, 24, PAGE_WIDTH - MARGIN, 44),
                f"{self.code} | Masked resume",
                fontsize=9,
                fontname=self.bold_font,
                color=MUTED,
            )
            self.page.draw_line(fitz.Point(MARGIN, 48), fitz.Point(PAGE_WIDTH - MARGIN, 48), color=LINE, width=0.7)
            self.y = 68

        self.page.insert_textbox(
            fitz.Rect(MARGIN, PAGE_HEIGHT - 32, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 18),
            "Generated by ResumeParser.AI | Identity, contact, employer, and institution details withheld",
            fontsize=7.5,
            fontname=self.regular_font,
            color=MUTED,
            align=1,
        )

    def _ensure(self, height: float) -> None:
        if self.y + height > PAGE_HEIGHT - BOTTOM_MARGIN:
            self._new_page()

    def section(self, title: str) -> None:
        self._ensure(36)
        assert self.page is not None
        self.page.draw_line(fitz.Point(MARGIN, self.y + 18), fitz.Point(PAGE_WIDTH - MARGIN, self.y + 18), color=LINE, width=0.7)
        self.page.draw_rect(fitz.Rect(MARGIN, self.y + 8, MARGIN + 26, self.y + 11), fill=CYAN, color=CYAN)
        self.page.insert_textbox(
            fitz.Rect(MARGIN, self.y, PAGE_WIDTH - MARGIN, self.y + 18),
            title.upper(),
            fontsize=10,
            fontname=self.bold_font,
            color=INK,
        )
        self.y += 32

    def paragraph(self, text: str, font_size: float = 10.5, color: tuple[float, float, float] = INK) -> None:
        text = text.strip()
        if not text:
            return
        height = _estimate_height(text, font_size, CONTENT_WIDTH)
        self._ensure(height)
        assert self.page is not None
        self.page.insert_textbox(
            fitz.Rect(MARGIN, self.y, PAGE_WIDTH - MARGIN, self.y + height),
            text,
            fontsize=font_size,
            fontname=self.regular_font,
            color=color,
            lineheight=1.18,
        )
        self.y += height + 4

    def bullet_list(self, items: list[str], columns: int = 2) -> None:
        clean_items = [item for item in items if item]
        if not clean_items:
            return
        column_gap = 18
        col_width = (CONTENT_WIDTH - column_gap * (columns - 1)) / columns
        rows = math.ceil(len(clean_items) / columns)
        height = rows * 19 + 8
        self._ensure(height)
        assert self.page is not None
        for index, item in enumerate(clean_items):
            col = index // rows
            row = index % rows
            x = MARGIN + col * (col_width + column_gap)
            y = self.y + row * 19
            self.page.draw_circle(fitz.Point(x + 3, y + 7), 2.1, fill=CYAN, color=CYAN)
            self.page.insert_textbox(
                fitz.Rect(x + 12, y, x + col_width, y + 16),
                item,
                fontsize=9.5,
                fontname=self.regular_font,
                color=INK,
            )
        self.y += height + 6

    def item(self, title: str, meta: str = "", body: str = "") -> None:
        title = title.strip()
        meta = meta.strip()
        body = body.strip()
        body_height = _estimate_height(body, 9.5, CONTENT_WIDTH - 24, 16) if body else 0
        height = (46 if meta else 30) + body_height + 10
        self._ensure(height + 10)
        assert self.page is not None
        self.page.draw_rect(fitz.Rect(MARGIN, self.y, PAGE_WIDTH - MARGIN, self.y + height), fill=LIGHT_BG, color=LINE, width=0.6)
        self.page.insert_textbox(
            fitz.Rect(MARGIN + 12, self.y + 9, PAGE_WIDTH - MARGIN - 12, self.y + 25),
            title,
            fontsize=10.5,
            fontname=self.bold_font,
            color=INK,
        )
        if meta:
            self.page.insert_textbox(
                fitz.Rect(MARGIN + 12, self.y + 27, PAGE_WIDTH - MARGIN - 12, self.y + 43),
                meta,
                fontsize=8.8,
                fontname=self.regular_font,
                color=MUTED,
            )
            body_top = self.y + 45
        else:
            body_top = self.y + 29
        if body:
            self.page.insert_textbox(
                fitz.Rect(MARGIN + 12, body_top, PAGE_WIDTH - MARGIN - 12, self.y + height - 8),
                body,
                fontsize=9.5,
                fontname=self.regular_font,
                color=INK,
                lineheight=1.16,
            )
        self.y += height + 10

    def bytes(self) -> bytes:
        output = self.doc.tobytes(garbage=4, deflate=True)
        self.doc.close()
        return output


def build_masked_resume_pdf(resume: Any) -> bytes:
    parsed = _load_parsed_resume(resume)
    structured = _structured_resume(parsed)
    code = _candidate_code(resume)
    replacements = _collect_replacements(parsed, structured, resume, code)

    first_experience = next((item for item in structured.get("experience") or [] if isinstance(item, dict)), {})
    headline = _mask(first_experience.get("title") if first_experience else "", replacements) or "Technical candidate profile"
    pdf = _PdfTemplate(code, headline)

    pdf.section("Profile")
    pdf.item("Anonymous candidate snapshot", "Identity and contact details withheld", "Use this version for unbiased technical screening.")
    summary = _mask(structured.get("summary"), replacements)
    if summary:
        pdf.paragraph(summary)

    skills = [_mask(skill, replacements) for skill in structured.get("skills") or []]
    if skills:
        pdf.section("Core skills")
        pdf.bullet_list(skills[:42], columns=2)

    experience = [item for item in structured.get("experience") or [] if isinstance(item, dict)]
    if experience:
        pdf.section("Experience")
        for index, item in enumerate(experience, start=1):
            title = _mask(item.get("title"), replacements) or "Role withheld"
            employer = f"Employer {index}" if item.get("company") else "Employer withheld"
            dates = " - ".join(part for part in [_mask(item.get("start_date"), replacements), _mask(item.get("end_date"), replacements)] if part)
            meta = " | ".join(part for part in [employer, dates] if part)
            pdf.item(title, meta, _mask(item.get("description"), replacements))

    education = [item for item in structured.get("education") or [] if isinstance(item, dict)]
    if education:
        pdf.section("Education")
        for item in education:
            degree = _mask(item.get("degree"), replacements) or "Qualification"
            field = _mask(item.get("field"), replacements)
            graduation = _mask(item.get("graduation_date"), replacements)
            details = " | ".join(part for part in [field, graduation, "Institution withheld" if item.get("institution") else ""] if part)
            pdf.item(degree, details)

    certifications = [_mask(cert, replacements) for cert in structured.get("certifications") or []]
    if certifications:
        pdf.section("Certifications")
        pdf.bullet_list(certifications[:24], columns=1)

    return pdf.bytes()


def build_masked_resumes_zip(resumes: list[Any]) -> bytes:
    output = BytesIO()
    seen_names: set[str] = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for resume in resumes:
            file_name = masked_resume_filename(resume)
            if file_name in seen_names:
                stem, ext = file_name.rsplit(".", 1)
                file_name = f"{stem}_{getattr(resume, 'id', '')[:8]}.{ext}"
            seen_names.add(file_name)
            archive.writestr(file_name, build_masked_resume_pdf(resume))
    return output.getvalue()
