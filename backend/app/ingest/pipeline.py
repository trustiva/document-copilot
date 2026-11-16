from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path

import structlog

from app.database.documents import (
    count_documents_and_chunks,
    insert_document_chunks,
    upsert_source_document,
)
from app.database.session import SessionLocal
from app.ingest.chunker import chunk_markdown
from app.ingest.embedder import generate_embeddings
from app.ingest.parser import parse_sec_html

logger = structlog.get_logger(__name__)


def run_pipeline(
    manifest_path: Path,
    *,
    limit: int | None = None,
) -> dict[str, int]:
    """Execute the end-to-end ingestion pipeline: parse, chunk, embed, and store."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    filings = manifest.get("filings", [])
    if limit is not None:
        filings = filings[:limit]

    logger.info(
        "Starting SEC filing ingestion pipeline",
        total_filings=len(filings),
        manifest=str(manifest_path),
    )

    base_dir = manifest_path.parent
    processed_count = 0
    total_chunks_inserted = 0

    with SessionLocal() as session:
        for idx, filing in enumerate(filings, start=1):
            ticker = filing["ticker"]
            form = filing["form"]
            filing_date_str = filing["filing_date"]
            accession_number = filing["accession_number"]
            source_url = filing["source_url"]
            local_rel_path = filing["local_path"]
            local_file = base_dir / local_rel_path

            if not local_file.exists():
                logger.warning(
                    "Filing file missing, skipping",
                    ticker=ticker,
                    path=str(local_file),
                )
                continue

            t_start = time.time()
            logger.info(
                f"[{idx}/{len(filings)}] Processing {ticker} {form} ({filing_date_str})...",
                accession=accession_number,
            )

            # 1. Parse HTML to clean Markdown
            html_content = local_file.read_text(encoding="utf-8", errors="ignore")
            markdown_text = parse_sec_html(html_content)

            # 2. Upsert SourceDocument record
            filing_dt = date.fromisoformat(filing_date_str)
            doc = upsert_source_document(
                session,
                ticker=ticker,
                form=form,
                filing_date=filing_dt,
                accession_number=accession_number,
                source_url=source_url,
                markdown=markdown_text,
            )

            # 3. Chunk Markdown text
            chunks_data = chunk_markdown(
                markdown_text,
                ticker=ticker,
                form=form,
                filing_date=filing_date_str,
                accession_number=accession_number,
            )

            # 4. Generate embeddings for all chunks
            chunk_texts = [c.content for c in chunks_data]
            embeddings = generate_embeddings(chunk_texts)

            # 5. Insert chunks into document_chunks
            chunks_to_insert = [
                {
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "embedding": emb,
                }
                for c, emb in zip(chunks_data, embeddings, strict=True)
            ]

            inserted = insert_document_chunks(session, doc.id, chunks_to_insert)
            session.commit()

            duration = time.time() - t_start
            total_chunks_inserted += inserted
            processed_count += 1

            logger.info(
                f"Successfully ingested {ticker} {form}",
                document_id=str(doc.id),
                chunks=inserted,
                elapsed_sec=round(duration, 2),
            )

        db_counts = count_documents_and_chunks(session)
        logger.info(
            "Ingestion pipeline complete",
            filings_processed=processed_count,
            chunks_inserted=total_chunks_inserted,
            total_documents_in_db=db_counts["source_documents"],
            total_chunks_in_db=db_counts["document_chunks"],
        )
        return db_counts


def _find_default_manifest() -> Path:
    candidates = [
        Path("data/downloads/manifest.json"),
        Path("../data/downloads/manifest.json"),
        Path(__file__).resolve().parents[3] / "data" / "downloads" / "manifest.json",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Document Copilot Ingestion Pipeline")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_find_default_manifest(),
        help="Path to manifest.json (default: data/downloads/manifest.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of filings to process",
    )
    args = parser.parse_args()

    run_pipeline(args.manifest, limit=args.limit)


if __name__ == "__main__":
    main()
