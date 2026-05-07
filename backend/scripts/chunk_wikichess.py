"""Découpe les articles Wikichess en chunks par section H2.

Stratégie : structure-aware chunking pur. Avec text-embedding-3-large
(8192 tokens de contexte ≈ 30k chars), chaque section ## tient sans troncature.
Pas de size cap. Pas de fallback. Une section = un chunk.

Lit : backend/data/wikichess/*.md
Écrit : backend/data/wikichess_chunks.jsonl

Métadonnées par chunk :
    opening_name : titre de l'article ('Italian Game')
    section      : nom de la section ('History', etc.) ou None pour l'intro
    source_url   : URL Wikipedia
    chunk_index  : ordre dans l'article
    text         : contenu de la section (incluant les ### sous-sections inline)

Idempotent : ré-exécuter écrase le fichier de sortie.
"""
import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("chunk_wikichess")

INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "wikichess"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "wikichess_chunks.jsonl"

SOURCE_URL_RE = re.compile(r"<!--\s*source:\s*(\S+)\s*-->", re.IGNORECASE)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_markdown_file(content: str) -> tuple[str, str | None, list[tuple[str | None, str]]]:
    """Parse un .md en (title, source_url, [(section_name|None, text), ...])."""
    source_match = SOURCE_URL_RE.search(content)
    source_url = source_match.group(1) if source_match else None
    if source_match:
        content = content[: source_match.start()].rstrip()

    title_match = H1_RE.search(content)
    if not title_match:
        raise ValueError("No H1 title found")
    title = title_match.group(1).strip()
    content = content[title_match.end():].lstrip()

    h2_matches = list(H2_RE.finditer(content))
    sections: list[tuple[str | None, str]] = []

    if not h2_matches:
        if content.strip():
            sections.append((None, content.strip()))
        return title, source_url, sections

    intro = content[: h2_matches[0].start()].strip()
    if intro:
        sections.append((None, intro))

    for i, match in enumerate(h2_matches):
        name = match.group(1).strip()
        start = match.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(content)
        text = content[start:end].strip()
        if text:
            sections.append((name, text))

    return title, source_url, sections


def main() -> int:
    if not INPUT_DIR.exists():
        logger.error("Input dir not found: %s", INPUT_DIR)
        return 1

    md_files = sorted(INPUT_DIR.glob("*.md"))
    if not md_files:
        logger.error("No markdown files found in %s", INPUT_DIR)
        return 1

    chunks: list[dict] = []
    rows: list[tuple[str, int, int, int]] = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        try:
            title, source_url, sections = parse_markdown_file(content)
        except ValueError as exc:
            logger.error("Failed to parse %s: %s", md_file.name, exc)
            continue

        if not sections:
            logger.warning("Empty article: %s", md_file.name)
            continue

        sizes: list[int] = []
        for chunk_index, (section_name, section_text) in enumerate(sections):
            chunks.append(
                {
                    "opening_name": title,
                    "section": section_name,
                    "source_url": source_url,
                    "chunk_index": chunk_index,
                    "text": section_text,
                }
            )
            sizes.append(len(section_text))

        rows.append((title, len(sections), min(sizes), max(sizes)))
        logger.info("  %s → %d chunks (sizes %d–%d chars)", title, len(sections), min(sizes), max(sizes))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    logger.info("Wrote %d chunks → %s", len(chunks), OUTPUT_FILE)

    print("\n=== Summary ===")
    header = f"{'Opening':<28} {'Chunks':>7} {'Min chars':>10} {'Max chars':>10}"
    print(header)
    print("-" * len(header))
    for opening, n, mn, mx in rows:
        print(f"{opening:<28} {n:>7} {mn:>10} {mx:>10}")

    total_chunks = sum(r[1] for r in rows)
    largest = max(len(c["text"]) for c in chunks)
    avg_size = sum(len(c["text"]) for c in chunks) / max(1, len(chunks))
    largest_tokens = largest // 4  # rough estimate, ~4 chars/token EN

    print(f"\nTotal: {total_chunks} chunks across {len(rows)} articles")
    print(f"Avg chunk size:    {avg_size:>7.0f} chars  (~{avg_size / 4:.0f} tokens)")
    print(f"Largest chunk:     {largest:>7,} chars  (~{largest_tokens:,} tokens)")
    print(f"text-embedding-3-large limit: 8,192 tokens — {'OK ✓' if largest_tokens < 8192 else 'TROP GROS ⚠'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
