from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _parse_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_separator(cells: list[str]) -> bool:
    if not cells:
        return True
    return all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells if cell)


def _add_markdown_table(doc: Document, table_lines: list[str]) -> None:
    rows: list[list[str]] = []
    for line in table_lines:
        cells = _parse_table_cells(line)
        if _is_table_separator(cells):
            continue
        rows.append(cells)
    if not rows:
        return

    col_count = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=col_count)
    table.style = "Table Grid"
    for row_idx, row in enumerate(rows):
        for col_idx in range(col_count):
            value = row[col_idx] if col_idx < len(row) else ""
            table.rows[row_idx].cells[col_idx].text = value


def export_docx(content: str, output_path: Path) -> Path:
    doc = Document()
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if not line:
            doc.add_paragraph("")
            index += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
            index += 1
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:], level=2)
            index += 1
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
            index += 1
            continue
        if line.startswith("|") and line.endswith("|"):
            table_lines: list[str] = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not candidate.startswith("|"):
                    break
                table_lines.append(candidate)
                index += 1
            _add_markdown_table(doc, table_lines)
            continue

        doc.add_paragraph(re.sub(r"\*\*(.+?)\*\*", r"\1", line))
        index += 1

    doc.save(str(output_path))
    return output_path


def export_pdf(content: str, output_path: Path) -> Path:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    x, y = 40, height - 40
    line_height = 14
    c.setFont("Helvetica", 10)
    for raw in content.splitlines():
        line = raw.strip() or " "
        # Simple wrap
        chunks = _wrap(line, 90)
        for chunk in chunks:
            if y < 40:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 40
            c.drawString(x, y, chunk)
            y -= line_height
    c.save()
    return output_path


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        test = " ".join(current + [w])
        if len(test) <= width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def render_agenda_variables(
    template: str,
    client_name: str,
    meeting_date: str,
    suggestions: str = "",
) -> str:
    content = template.replace("[NOME CLIENTE]", client_name)
    content = content.replace("[DATA]", meeting_date)
    if suggestions and "• XX" in content:
        content = content.replace("• XX", suggestions, 1)
    return content


def render_minutes_variables(
    template: str,
    client_name: str,
    meeting_date: str,
    participants: str,
) -> str:
    content = template.replace("[NOME CLIENTE]", client_name.upper())
    content = content.replace("[DATA]", meeting_date)
    content = content.replace("[PARTICIPANTES]", participants)
    return content


def short_summary_from_content(content: str, max_len: int = 280) -> str:
    plain = re.sub(r"[#*|_\[\]]", "", content)
    plain = " ".join(plain.split())
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 3] + "..."
