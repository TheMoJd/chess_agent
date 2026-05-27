"""Récupère des articles d'ouvertures depuis Wikipedia EN et les sauvegarde en markdown.

POURQUOI WIKIPEDIA ET PAS WIKICHESS (ficgs.com) ?
L'énoncé OC cite « Wikichess » comme source RAG mais précise « (toutes sources
pertinentes sont acceptées) ». Après inspection de ficgs.com/wikichess :
  - sa prose est dérivée de Wikipedia (texte souvent verbatim) ;
  - sa valeur structurelle (arbre position→coups + stats) est déjà couverte par
    le tool `opening_theory_lookup` (chessdb.cn) ;
  - 268k pages HTML legacy en latin-1, sans API → crawl disproportionné pour un POC.
On retient donc Wikipedia EN (API MediaWiki propre, UTF-8, licence CC BY-SA).
Justification complète : docs/architecture.md § "Source du corpus RAG".

Utilise l'API MediaWiki en direct (httpx + User-Agent custom) pour éviter les
blocages que subissent les wrappers comme `wikipedia` qui n'identifient pas
proprement leur client.

Sortie: backend/data/wikichess/<slug>.md, un fichier par ouverture.
Format: titre + intro + sections/sous-sections en hiérarchie markdown.

Idempotent: ré-exécuter écrase les fichiers existants.

Usage:
    cd backend
    .venv/bin/python scripts/fetch_wikichess.py
"""
import logging
import re
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_wikichess")

OPENINGS: list[str] = [
    # === Corpus initial ===
    "Italian Game",
    "Sicilian Defence",
    "Ruy Lopez",
    "French Defence",
    "Caro-Kann Defence",
    "Queen's Gambit",
    "King's Indian Defence",
    "English Opening",
    "Nimzo-Indian Defence",
    "London System",
    # === Tier 1 — umbrella + top réponses manquantes ===
    "Queen's Pawn Game",      # umbrella 1.d4 — corrige le bug "1.d4 → English Opening"
    "King's Pawn Game",       # umbrella 1.e4 (symétrique)
    "Slav Defense",           # WP utilise "Defense" (US) pour cet article
    "Scandinavian Defense",   # WP utilise "Defense" (US)
    # === Tier 2 — top-tier compétition ===
    "Grünfeld Defence",
    "Queen's Indian Defence",
    "Indian Defence",         # umbrella pour 1.d4 Nf6
    # === Tier 3 — opening complémentaire ===
    "Pirc Defence",
]

NOISE_SECTIONS: set[str] = {
    "references",
    "external links",
    "notes",
    "bibliography",
    "see also",
    "further reading",
    "footnotes",
    "citations",
    "notes and references",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "wikichess"

WIKI_API = "https://en.wikipedia.org/w/api.php"
# La politique Wikipedia exige un UA descriptif avec contact.
USER_AGENT = "ChessAgentPOC/0.1 (FFE chess opening tutor POC; contact: moetez@polaria.ai)"

# Politesse: 0.5s entre requêtes — bien en-dessous des limites Wikipedia.
SLEEP_BETWEEN_REQUESTS_S = 0.5

SECTION_HEADER_RE = re.compile(r"^(==+)\s*(.+?)\s*\1\s*$", re.MULTILINE)


def slugify(name: str) -> str:
    s = name.lower().replace("'", "").replace("–", "-")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def fetch_article(client: httpx.Client, title: str, max_retries: int = 3) -> dict | None:
    """Récupère un article Wikipedia via l'API MediaWiki, avec retries.

    Returns:
        {"title": str, "content": str, "url": str} ou None si introuvable.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts|info",
        "explaintext": 1,        # texte brut, pas de HTML
        "redirects": 1,          # suit les redirections automatiquement
        "inprops": "url",
    }
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.get(WIKI_API, params=params)
            response.raise_for_status()
            data = response.json()
            break
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)
                logger.warning("  attempt %d/%d failed (%s), retrying in %ds...",
                               attempt, max_retries, type(exc).__name__, backoff)
                time.sleep(backoff)
            else:
                raise
    else:
        raise last_error if last_error else RuntimeError("unreachable")

    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if page_id == "-1":
            return None
        return {
            "title": page_data["title"],
            "content": page_data.get("extract", ""),
            "url": page_data.get("fullurl") or f"https://en.wikipedia.org/wiki/{page_data['title'].replace(' ', '_')}",
        }
    return None


def split_into_level2_sections(content: str) -> list[tuple[str, str]]:
    """Découpe le contenu MediaWiki en (nom, texte) au niveau 2.

    L'intro (avant la 1ʳᵉ section) est rendue avec name=''.
    Les sous-sections (niveau 3+) restent intégrées au texte de leur section parente.
    """
    headers = [
        (m.start(), m.end(), len(m.group(1)), m.group(2).strip())
        for m in SECTION_HEADER_RE.finditer(content)
    ]
    level2_indices = [i for i, h in enumerate(headers) if h[2] == 2]

    sections: list[tuple[str, str]] = []
    if not level2_indices:
        if content.strip():
            sections.append(("", content.strip()))
        return sections

    intro = content[: headers[level2_indices[0]][0]].strip()
    if intro:
        sections.append(("", intro))

    for idx, l2_idx in enumerate(level2_indices):
        _, header_end, _, name = headers[l2_idx]
        next_start = (
            headers[level2_indices[idx + 1]][0]
            if idx + 1 < len(level2_indices)
            else len(content)
        )
        text = content[header_end:next_start].strip()
        if text:
            sections.append((name, text))
    return sections


def normalize_subheaders(text: str) -> str:
    """'=== X ===' → '### X', etc. — conversion vers la hiérarchie markdown."""

    def _replace(match: re.Match[str]) -> str:
        level = len(match.group(1))
        return f"{'#' * level} {match.group(2).strip()}"

    return SECTION_HEADER_RE.sub(_replace, text)


def article_to_markdown(article: dict) -> tuple[str, int]:
    parts: list[str] = [f"# {article['title']}", ""]
    sections = split_into_level2_sections(article["content"])

    kept = 0
    for name, text in sections:
        if name and name.lower().strip() in NOISE_SECTIONS:
            continue
        normalized = normalize_subheaders(text)
        if name == "":
            parts.append(normalized)
            parts.append("")
        else:
            parts.append(f"## {name}")
            parts.append("")
            parts.append(normalized)
            parts.append("")
            kept += 1

    parts.append(f"<!-- source: {article['url']} -->")
    return "\n".join(parts), kept


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, int, int]] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
        for i, title in enumerate(OPENINGS):
            logger.info("Fetching '%s'...", title)
            try:
                article = fetch_article(client, title)
            except httpx.HTTPError as exc:
                logger.error("  HTTP error for '%s': %s", title, exc)
                rows.append((title, "ERROR", 0, 0))
                continue

            if article is None:
                logger.error("  Page not found: '%s'", title)
                rows.append((title, "MISSING", 0, 0))
                continue

            md, section_count = article_to_markdown(article)
            slug = slugify(article["title"])
            target = DATA_DIR / f"{slug}.md"
            target.write_text(md, encoding="utf-8")
            rows.append((article["title"], slug, len(md), section_count))
            logger.info(
                "  ✓ '%s' (%d chars, %d level-2 sections kept) → %s",
                article["title"],
                len(md),
                section_count,
                target.name,
            )

            if i < len(OPENINGS) - 1:
                time.sleep(SLEEP_BETWEEN_REQUESTS_S)

    print("\n=== Summary ===")
    header = f"{'Title':<28} {'Slug':<28} {'Chars':>8} {'Sections':>10}"
    print(header)
    print("-" * len(header))
    for title, slug, chars, section_count in rows:
        print(f"{title:<28} {slug:<28} {chars:>8} {section_count:>10}")

    successful = [r for r in rows if r[1] not in ("ERROR", "MISSING")]
    total_chars = sum(r[2] for r in successful)
    print(
        f"\n{len(successful)}/{len(rows)} articles fetched, "
        f"{total_chars:,} chars total, "
        f"avg {total_chars // max(1, len(successful)):,} chars/article"
    )
    return 0 if len(successful) == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
