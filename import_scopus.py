"""
One-off bulk importer: Scopus CSV → Supabase scopus_publications table.

Usage:
    python3 import_scopus.py "/path/to/scopus_export.csv"

Reads Streamlit secrets from .streamlit/secrets.toml.
Skips rows with duplicate DOIs already in the database.
"""
import csv
import sys
import re
from pathlib import Path
from supabase import create_client


def load_secrets() -> dict:
    """Minimal TOML reader for our 2-line secrets file (works on Python 3.9)."""
    p = Path(".streamlit/secrets.toml")
    if not p.exists():
        sys.exit("ERROR: .streamlit/secrets.toml not found. Run from project folder.")
    out = {}
    for line in p.read_text().splitlines():
        m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def map_doc_type(scopus_type: str) -> str:
    """Map Scopus 'Document Type' → our 'publication_type' enum."""
    t = (scopus_type or "").strip().lower()
    mapping = {
        "article": "Article",
        "review": "Review",
        "conference paper": "Conference Paper",
        "book chapter": "Book Chapter",
        "editorial": "Editorial",
        "letter": "Letter",
        "note": "Note",
        "short survey": "Short Survey",
        "erratum": "Article",
        "data paper": "Article",
    }
    return mapping.get(t, "Article")


def map_open_access(oa: str) -> bool:
    """Open Access field is non-empty whenever it's open."""
    return bool((oa or "").strip())


def first_author(authors_str: str) -> str:
    """Extract the first author from a semicolon-separated list."""
    if not authors_str:
        return ""
    return authors_str.split(";")[0].strip()


def safe_int(s: str, default: int = 0) -> int:
    try:
        return int((s or "").strip())
    except ValueError:
        return default


def pages_from(start: str, end: str) -> str:
    s, e = (start or "").strip(), (end or "").strip()
    if s and e:
        return f"{s}-{e}"
    return s or e or ""


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 import_scopus.py /path/to/scopus.csv")

    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        sys.exit(f"ERROR: file not found: {csv_path}")

    secrets = load_secrets()
    sb = create_client(secrets["SUPABASE_URL"], secrets["SUPABASE_KEY"])

    # Get existing DOIs so we don't double-insert
    existing = sb.table("scopus_publications").select("doi").execute()
    existing_dois = {r["doi"] for r in (existing.data or []) if r.get("doi")}
    print(f"Found {len(existing_dois)} existing publications in database (will skip duplicates).")

    rows_to_insert = []
    skipped = 0

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doi = (row.get("DOI") or "").strip() or None

            if doi and doi in existing_dois:
                skipped += 1
                continue

            new_row = {
                "title": (row.get("Title") or "").strip()[:300],
                "authors": (row.get("Authors") or "").strip()[:1000],
                "lead_author": first_author(row.get("Authors") or "")[:150],
                "year": safe_int(row.get("Year"), 2024),
                "journal": (row.get("Source title") or "").strip()[:200],
                "volume": (row.get("Volume") or "").strip() or None,
                "issue": (row.get("Issue") or "").strip() or None,
                "pages": pages_from(row.get("Page start"), row.get("Page end")) or None,
                "doi": doi,
                "scopus_link": (row.get("Link") or "").strip() or None,
                "quartile": "Q?",                           # Not in Scopus export — edit later
                "publication_type": map_doc_type(row.get("Document Type")),
                "college": "TBD",                           # Not in Scopus export — edit later
                "open_access": map_open_access(row.get("Open Access")),
                "citation_count": safe_int(row.get("Cited by")),
                "funding_source": None,
                "acknowledgment": None,
            }
            rows_to_insert.append(new_row)

    print(f"Skipping {skipped} duplicates.")
    print(f"Inserting {len(rows_to_insert)} new publications...")

    if not rows_to_insert:
        print("Nothing to insert.")
        return

    # Insert in batches of 50 to be safe
    batch_size = 50
    inserted = 0
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i + batch_size]
        try:
            sb.table("scopus_publications").insert(batch).execute()
            inserted += len(batch)
            print(f"  ✓ Batch {i // batch_size + 1}: {len(batch)} rows")
        except Exception as e:
            print(f"  ✗ Batch {i // batch_size + 1} failed: {e}")
            print(f"    First row in failed batch: {batch[0].get('title', 'no title')[:80]}")

    print(f"\n✅ Done. Inserted {inserted}/{len(rows_to_insert)} publications.")
    print("\nNext steps:")
    print("  1. Open the dashboard → Scopus Publications (view) to verify")
    print("  2. Use Edit Scopus Publication to set the Quartile (Q1–Q4) and College for each")


if __name__ == "__main__":
    main()
