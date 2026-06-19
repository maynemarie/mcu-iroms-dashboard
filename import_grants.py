"""Insert the 6 actual in-house grants into Supabase."""
import re
from pathlib import Path
from supabase import create_client

# Load secrets
out = {}
for line in Path(".streamlit/secrets.toml").read_text().splitlines():
    m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', line)
    if m: out[m.group(1)] = m.group(2)

sb = create_client(out["SUPABASE_URL"], out["SUPABASE_KEY"])

GRANTS = [
    {
        "project_id": "CAS01",
        "title": "Antimicrobial Activity of Aqueous Extract from Black Sapote (Diospyros nigra) Fruit Against Selected Oral Pathogens",
        "pi": "Brylle Raphael U. Bigcas",
        "email": "tbd@mcu.edu.ph",
        "college": "Arts & Sciences",
        "track": "Basic Research",
        "duration": 5,
        "budget": 271152.00,
        "team": "",
        "outputs": "",
        "abstract": "Awarded in-house grant — in vitro antimicrobial study.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
    {
        "project_id": "CAS02",
        "title": "MUNTING TIYAN: Characterization of the Gut Microbiome and Parasitic Infections Among Preschool Children Across Barangays in Caloocan City",
        "pi": "Christian I. Zafra, Josephine C. Abrazaldo",
        "email": "tbd@mcu.edu.ph",
        "college": "Arts & Sciences",
        "track": "Applied Research",
        "duration": 6,
        "budget": 488051.00,
        "team": "Christian I. Zafra; Josephine C. Abrazaldo",
        "outputs": "",
        "abstract": "Community-based microbiome and parasitology study in Caloocan barangays.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
    {
        "project_id": "CON01",
        "title": "Enhancing Assessment Skills Through Virtual Reality in Healthcare Education: A Sequential Mixed-Methods Study",
        "pi": "Maria Elena C. Diasen",
        "email": "tbd@mcu.edu.ph",
        "college": "Nursing",
        "track": "Education & Pedagogy",
        "duration": 12,
        "budget": 129660.00,
        "team": "",
        "outputs": "",
        "abstract": "Mixed-methods study on VR-based clinical assessment training.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
    {
        "project_id": "CMT01",
        "title": "Antimicrobial Resistance Profiling of Hospital Wastewater in Caloocan City",
        "pi": "Patrick R. De Vera",
        "email": "tbd@mcu.edu.ph",
        "college": "Med Tech",
        "track": "Applied Research",
        "duration": 6,
        "budget": 262500.00,
        "team": "",
        "outputs": "",
        "abstract": "AMR profiling of hospital wastewater — Caloocan City.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
    {
        "project_id": "CMT02",
        "title": "Signals in the Sewers: A Pilot Study of Hospital Wastewater-Based Epidemiology (WBE)",
        "pi": "Josephine C. Abrazaldo",
        "email": "tbd@mcu.edu.ph",
        "college": "Med Tech",
        "track": "Applied Research",
        "duration": 6,
        "budget": 272400.00,
        "team": "",
        "outputs": "",
        "abstract": "Pilot wastewater-based epidemiology study.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
    {
        "project_id": "COD01",
        "title": "Evaluation of Masticatory Performance of Orthodontic Patients Before and After Orthodontic Strap-Up Using Gummy Jelly: A Prospective Longitudinal Study",
        "pi": "Arlyn Leslie R. Donesa",
        "email": "tbd@mcu.edu.ph",
        "college": "Dentistry",
        "track": "Applied Research",
        "duration": 4,
        "budget": 171703.00,
        "team": "",
        "outputs": "",
        "abstract": "Prospective longitudinal study on masticatory performance.",
        "aligned_with_agenda": True,
        "status": "Awarded",
    },
]

# Get existing project IDs to skip dupes
existing = sb.table("grant_projects").select("project_id").execute()
existing_ids = {r["project_id"] for r in (existing.data or [])}
print(f"Existing project IDs in DB: {sorted(existing_ids)}")

to_insert = [g for g in GRANTS if g["project_id"] not in existing_ids]
print(f"To insert: {len(to_insert)} new grants")
print(f"Skipping {len(GRANTS) - len(to_insert)} duplicates")

if to_insert:
    sb.table("grant_projects").insert(to_insert).execute()
    print(f"✅ Inserted {len(to_insert)} grants")

# Verify
final = sb.table("grant_projects").select("project_id, college, budget").execute()
print(f"\nDatabase now contains {len(final.data)} grants:")
total = 0
by_college = {}
for g in final.data:
    print(f"  {g['project_id']}  {g['college']:<20}  ₱{g['budget']:>12,.2f}")
    total += g["budget"]
    by_college[g["college"]] = by_college.get(g["college"], 0) + g["budget"]

print(f"\nTotal: ₱{total:,.2f}")
print("\nBy program:")
for c, amt in sorted(by_college.items(), key=lambda x: -x[1]):
    print(f"  {c:<20}  ₱{amt:>12,.2f}")
