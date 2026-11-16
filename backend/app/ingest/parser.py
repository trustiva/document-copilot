from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag

# Standard SEC 10-K / 10-Q Item header regex
ITEM_REGEX = re.compile(
    r"(?i)\n\s*(item\s+(?:1[a-c]?|[2-9]|1[0-5])[\.\:\s][^\n]{0,100})",
    re.MULTILINE,
)


def _format_table_to_markdown(table: Tag) -> str:
    """Convert an HTML table into a clean, compact Markdown table."""
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [
            re.sub(r"\s+", " ", td.get_text()).replace("\xa0", " ").strip()
            for td in tr.find_all(["td", "th"])
        ]
        # Keep non-empty cells
        non_empty = [c for c in cells if c]
        if non_empty:
            rows.append(non_empty)

    if not rows:
        return ""

    max_cols = max(len(r) for r in rows)

    # If it's just a single cell or single line callout, return as plain text
    if max_cols == 1 and len(rows) <= 2:
        return "\n\n" + " ".join(rows[0]) + "\n\n"

    # Build Markdown table
    md_lines: list[str] = []
    header = rows[0] + [""] * (max_cols - len(rows[0]))
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    for r in rows[1:]:
        padded_row = r + [""] * (max_cols - len(r))
        md_lines.append("| " + " | ".join(padded_row) + " |")

    return "\n\n" + "\n".join(md_lines) + "\n\n"


def parse_sec_html(html_content: str) -> str:
    """Parse raw SEC EDGAR 10-K/10-Q HTML into normalized Markdown."""
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Strip script, style, head, noscript, and meta tags
    for tag in soup(["script", "style", "head", "noscript", "meta", "title"]):
        tag.decompose()

    # 2. Decompose iXBRL metadata and hidden elements
    for tag in list(soup.find_all(True)):
        if not isinstance(tag, Tag):
            continue
        tag_name = tag.name or ""
        if tag_name.startswith("ix:") or tag_name.startswith("xbrl"):
            tag.decompose()
            continue
        if tag.attrs:
            style = tag.attrs.get("style", "")
            if isinstance(style, str) and "display:none" in style.replace(" ", "").lower():
                tag.decompose()
                continue

    # 3. Convert data tables into readable Markdown tables
    for table in list(soup.find_all("table")):
        md_table = _format_table_to_markdown(table)
        if md_table:
            table.replace_with(md_table)
        else:
            table.decompose()

    # 4. Extract text and replace non-breaking spaces
    text = soup.get_text("\n")
    text = text.replace("\xa0", " ")

    # 5. Format SEC Item section headings as Markdown headers
    text = ITEM_REGEX.sub(r"\n\n## \1\n\n", text)

    # 6. Clean up line-by-line whitespace and multiple newlines
    lines = [line.strip() for line in text.splitlines()]
    clean_text = "\n".join(lines)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

    return clean_text.strip()
