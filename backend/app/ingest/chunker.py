from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import tiktoken

# Use cl100k_base tokenizer (standard for text-embedding-3-small)
TOKENIZER = tiktoken.get_encoding("cl100k_base")

SECTION_HEADER_RE = re.compile(
    r"^##\s*(item\s+(?:1[a-c]?|[2-9]|1[0-5])[\.\:\s][^\n]*)",
    re.IGNORECASE,
)


@dataclass
class DocumentChunkData:
    chunk_index: int
    content: str
    token_count: int
    section: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_index": self.chunk_index,
            "content": self.content,
            "token_count": self.token_count,
            "section": self.section,
            "metadata": self.metadata,
        }


def count_tokens(text: str) -> int:
    """Return token count for a text string."""
    return len(TOKENIZER.encode(text))


def chunk_markdown(
    markdown_text: str,
    *,
    ticker: str,
    form: str,
    filing_date: str,
    accession_number: str,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[DocumentChunkData]:
    """Chunk Markdown into token-bounded passages with section awareness."""
    # Split by double-newlines to preserve paragraphs and tables
    paragraphs = markdown_text.split("\n\n")

    chunks: list[DocumentChunkData] = []
    current_section = "General"
    current_paragraphs: list[str] = []
    current_tokens = 0
    chunk_index = 0

    def make_header(sec: str) -> str:
        return f"[{ticker} | {form} | {filing_date} | Section: {sec}]\n"

    def flush_chunk(paragraphs_to_flush: list[str], sec: str) -> None:
        nonlocal chunk_index
        if not paragraphs_to_flush:
            return

        body = "\n\n".join(paragraphs_to_flush).strip()
        if not body:
            return

        header = make_header(sec)
        full_content = f"{header}{body}"
        token_count = count_tokens(full_content)

        chunks.append(
            DocumentChunkData(
                chunk_index=chunk_index,
                content=full_content,
                token_count=token_count,
                section=sec,
                metadata={
                    "ticker": ticker,
                    "form": form,
                    "filing_date": filing_date,
                    "accession_number": accession_number,
                    "section": sec,
                    "chunk_index": chunk_index,
                },
            )
        )
        chunk_index += 1

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Check if this paragraph is a section header
        section_match = SECTION_HEADER_RE.match(para_clean)
        if section_match:
            new_section = section_match.group(1).strip()
            # If we already have accumulated content, flush it under the previous section
            if current_paragraphs:
                flush_chunk(current_paragraphs, current_section)
                current_paragraphs = []
                current_tokens = 0
            current_section = new_section

        para_tokens = count_tokens(para_clean)

        # If a single paragraph/table is larger than max_tokens, split it by lines
        if para_tokens > max_tokens:
            if current_paragraphs:
                flush_chunk(current_paragraphs, current_section)
                current_paragraphs = []
                current_tokens = 0

            lines = para_clean.split("\n")
            line_sub: list[str] = []
            line_tokens = 0
            for line in lines:
                l_tokens = count_tokens(line)
                if line_tokens + l_tokens > max_tokens and line_sub:
                    flush_chunk(["\n".join(line_sub)], current_section)
                    line_sub = [line]
                    line_tokens = l_tokens
                else:
                    line_sub.append(line)
                    line_tokens += l_tokens
            if line_sub:
                flush_chunk(["\n".join(line_sub)], current_section)
            continue

        # Check if adding this paragraph exceeds max_tokens
        if current_tokens + para_tokens > max_tokens and current_paragraphs:
            flush_chunk(current_paragraphs, current_section)

            # Build overlap from the end of the previous chunk
            overlap_p: list[str] = []
            overlap_count = 0
            for prev_p in reversed(current_paragraphs):
                p_toks = count_tokens(prev_p)
                if overlap_count + p_toks <= overlap_tokens:
                    overlap_p.insert(0, prev_p)
                    overlap_count += p_toks
                else:
                    break

            current_paragraphs = overlap_p + [para_clean]
            current_tokens = overlap_count + para_tokens
        else:
            current_paragraphs.append(para_clean)
            current_tokens += para_tokens

    # Flush any remaining paragraphs
    if current_paragraphs:
        flush_chunk(current_paragraphs, current_section)

    return chunks
