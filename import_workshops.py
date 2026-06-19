"""Import the 10 completed capacity-building workshops into Supabase."""
import re
from pathlib import Path
from supabase import create_client

# Load secrets
out = {}
for line in Path(".streamlit/secrets.toml").read_text().splitlines():
    m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', line)
    if m: out[m.group(1)] = m.group(2)
sb = create_client(out["SUPABASE_URL"], out["SUPABASE_KEY"])

WORKSHOPS = [
    {
        "title": "Book Writing",
        "start_date": "2025-04-01",   # month-only — use 1st as placeholder
        "end_date": None,
        "speakers": "C & E",
        "workshop_type": "Academic Writing",
        "status": "Completed",
    },
    {
        "title": "Scopus-Indexed Writing & Publication",
        "start_date": "2025-07-30",
        "end_date": None,
        "speakers": "Dr. Albert Rosanna (DLSU); Dr. Tan Boon Fei (SMART–Singapore); Dr. Charmaine Ng (NUS–Singapore)",
        "workshop_type": "Publication",
        "status": "Completed",
    },
    {
        "title": "Writing with Integrity: Integrating ERB and IACUC in Chapter 3",
        "start_date": "2025-09-10",
        "end_date": None,
        "speakers": "Nieves Capili (CAS-MCU); Cecilia Calisang (CMT-MCU)",
        "workshop_type": "Research Ethics",
        "status": "Completed",
    },
    {
        "title": "Qualitative and Quantitative Research Methods",
        "start_date": "2025-11-04",
        "end_date": None,
        "speakers": "Dr. Agnes Raymundo (CON-MCU); Ramon Paulo Masagca (CAS-MCU)",
        "workshop_type": "Research Methods",
        "status": "Completed",
    },
    {
        "title": "Introduction to Intellectual Property and Commercialization",
        "start_date": "2025-11-05",
        "end_date": "2025-11-06",
        "speakers": "Mr. Adrian Sablan (IPOPHL); Engr. Aldrex Aviso (IPOPHL)",
        "workshop_type": "IP & Commercialization",
        "status": "Completed",
    },
    {
        "title": "Qualitative and Mixed-Method Research using NVivo",
        "start_date": "2026-04-07",
        "end_date": None,
        "speakers": "Dr. Nicamil Sanchez",
        "workshop_type": "Research Methods",
        "status": "Completed",
    },
    {
        "title": "AI-Assisted Systematic Literature Review Writeshop",
        "start_date": "2026-04-10",
        "end_date": None,
        "speakers": "Dr. Feorillo Petronilo A. Demeterio III (DLSU)",
        "workshop_type": "Publication",
        "status": "Completed",
    },
    {
        "title": "MCU Research Congress 2026",
        "start_date": "2026-04-20",
        "end_date": None,
        "speakers": "Dr. Alexander Co Abad (DLSU)",
        "workshop_type": "Congress / Symposium",
        "status": "Completed",
    },
    {
        "title": "Brown Bag Research Monitoring Session 2026",
        "start_date": "2026-04-21",
        "end_date": "2026-04-22",
        "speakers": "Dr. Marie Grace Gomez (UP Diliman)",
        "workshop_type": "Research Monitoring",
        "status": "Completed",
    },
    {
        "title": "Training Workshop on Statistical Analysis",
        "start_date": "2026-04-23",
        "end_date": None,
        "speakers": "Dr. Dennis Iledan (CAS-MCU)",
        "workshop_type": "Statistics",
        "status": "Completed",
    },
]

# Skip duplicates by title + date
existing = sb.table("capacity_workshops").select("title, start_date").execute()
existing_keys = {(r["title"], r["start_date"]) for r in (existing.data or [])}

to_insert = [w for w in WORKSHOPS
             if (w["title"], w["start_date"]) not in existing_keys]

print(f"Existing workshops: {len(existing_keys)}")
print(f"To insert: {len(to_insert)}")
print(f"Skipping duplicates: {len(WORKSHOPS) - len(to_insert)}")

if to_insert:
    sb.table("capacity_workshops").insert(to_insert).execute()
    print(f"✅ Inserted {len(to_insert)} workshops")

# Verify
final = sb.table("capacity_workshops").select("title, start_date, status, workshop_type").order(
    "start_date", desc=True).execute()
print(f"\nDatabase now contains {len(final.data)} workshops:")
for w in final.data:
    print(f"  [{w['start_date']}] {w['workshop_type']:<25} {w['title'][:60]}")
