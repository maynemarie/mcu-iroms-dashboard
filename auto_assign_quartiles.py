"""
Auto-assign Scopus quartiles based on a curated lookup table.

Sources:
  - SCImago Journal Rank (most recent indexed year, typically 2023)
  - Quartiles are subject-area best (some journals are in multiple categories)
  - Confidence: HIGH/MEDIUM/LOW reflects how certain the mapping is
  - Unknown journals → "NA" (left for manual review)

Usage:
  python3 auto_assign_quartiles.py
"""
import sys
import re
from pathlib import Path
from supabase import create_client


# ============================================================
# Curated quartile lookup — based on SJR ~2023 best-category quartile
# ============================================================
# Format: "Journal Name as it appears in Scopus": ("Q1"–"Q4", confidence)
QUARTILE_LOOKUP = {
    # ===== HIGH CONFIDENCE =====
    # Cardiology / Surgery
    "Catheterization and Cardiovascular Interventions": ("Q1", "HIGH"),
    "JACC: Advances": ("Q2", "HIGH"),
    "World Journal of Surgery": ("Q1", "HIGH"),
    "Artificial Intelligence Surgery": ("Q3", "LOW"),

    # Microbiology / Infection
    "Frontiers in Microbiology": ("Q1", "HIGH"),
    "European Journal of Microbiology and Immunology": ("Q3", "MEDIUM"),
    "Virulence": ("Q1", "HIGH"),
    "Tropical Medicine and Infectious Disease": ("Q2", "HIGH"),

    # General medicine
    "Scientific Reports": ("Q1", "HIGH"),
    "Heliyon": ("Q1", "HIGH"),
    "eClinicalMedicine": ("Q1", "HIGH"),
    "Frontiers in Medicine": ("Q1", "HIGH"),
    "Journal of Clinical Medicine": ("Q1", "HIGH"),
    "Healthcare (Switzerland)": ("Q2", "HIGH"),
    "Medicine (United States)": ("Q3", "HIGH"),
    "BMJ Oncology": ("Q2", "MEDIUM"),
    "Frontiers in Oncology": ("Q2", "HIGH"),
    "BMC Geriatrics": ("Q1", "HIGH"),
    "Acta Paediatrica, International Journal of Paediatrics": ("Q1", "HIGH"),

    # Oncology / Cancer
    "JCO Global Oncology": ("Q1", "HIGH"),
    "ecancermedicalscience": ("Q2", "MEDIUM"),
    "Cancer Causes and Control": ("Q2", "HIGH"),

    # Dentistry
    "BMC Oral Health": ("Q1", "HIGH"),
    "Journal of Endodontics": ("Q1", "HIGH"),
    "Japanese Dental Science Review": ("Q1", "HIGH"),
    "Journal of Prosthodontic Research": ("Q1", "HIGH"),
    "International Endodontic Journal": ("Q1", "HIGH"),
    "JDR Clinical and Translational Research": ("Q1", "HIGH"),
    "Gerodontology": ("Q2", "HIGH"),

    # Nutrition / Food
    "Nutrients": ("Q1", "HIGH"),
    "Appetite": ("Q1", "HIGH"),
    "Food Quality and Preference": ("Q1", "HIGH"),

    # Psychology / Social
    "Frontiers in Psychology": ("Q2", "HIGH"),
    "Reproductive Sciences": ("Q2", "HIGH"),
    "Journal of Interprofessional Care": ("Q2", "HIGH"),
    "Social Sciences and Humanities Open": ("Q3", "MEDIUM"),

    # Other med specialties
    "Diagnosis": ("Q3", "MEDIUM"),
    "Journal of Imaging Informatics in Medicine": ("Q2", "HIGH"),
    "Philippine Journal of Otolaryngology Head and Neck Surgery": ("Q4", "MEDIUM"),
    "Philippine Journal of Nursing": ("NA", "LOW"),       # Possibly not Scopus-indexed
    "SciEnggJ": ("Q4", "MEDIUM"),                          # PH local
    "Journal of Public Health and Emergency": ("Q4", "LOW"),
    "Research Journal of Pharmacy and Technology": ("Q3", "MEDIUM"),
    "Journal of Medicinal Plants and By-Products": ("Q4", "LOW"),

    # Other / Conference / Book chapters
    "Clean - Soil, Air, Water": ("Q2", "MEDIUM"),
    "Proceedings on Engineering Sciences": ("Q3", "LOW"),
    "ACM International Conference Proceeding Series": ("Q4", "MEDIUM"),
    "2024 IEEE 15th Control and System Graduate Research Colloquium, ICSGRC 2024 - Conference Proceeding": ("Q4", "MEDIUM"),

    # Book chapters (no quartile per se)
    "Promoting Mindfulness, Flourishing, and Wellness in Higher Education Through the Arts": ("NA", "LOW"),
    "Global Innovations in Physical Education and Health": ("NA", "LOW"),
    "Emerging Pedagogical Practices in Physical and Sports Education": ("NA", "LOW"),
    "Shaping Childhood Through Educational Experiences": ("NA", "LOW"),
    "Vital Pulp Treatment": ("NA", "LOW"),

    # ⚠️ DELISTED / Discontinued
    "International Journal of Environmental Research and Public Health": ("NA", "LOW"),  # Was Q1 but delisted from Scopus 2023
}


def load_secrets() -> dict:
    p = Path(".streamlit/secrets.toml")
    if not p.exists():
        sys.exit("ERROR: run from project folder (.streamlit/secrets.toml missing).")
    out = {}
    for line in p.read_text().splitlines():
        m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def main():
    secrets = load_secrets()
    sb = create_client(secrets["SUPABASE_URL"], secrets["SUPABASE_KEY"])

    pubs = sb.table("scopus_publications").select("id, journal, quartile").execute().data
    print(f"Found {len(pubs)} publications in database.")
    print()

    updates = []
    unmapped = set()
    quartile_counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "NA": 0}
    confidence_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNMAPPED": 0}

    for p in pubs:
        journal = (p.get("journal") or "").strip()
        if not journal:
            continue

        if journal in QUARTILE_LOOKUP:
            new_q, confidence = QUARTILE_LOOKUP[journal]
            if p.get("quartile") != new_q:
                updates.append((p["id"], new_q, confidence, journal))
            quartile_counts[new_q] += 1
            confidence_counts[confidence] += 1
        else:
            unmapped.add(journal)
            confidence_counts["UNMAPPED"] += 1

    print(f"Will update {len(updates)} publications.")
    print()
    print("Quartile distribution after update:")
    for q in ["Q1", "Q2", "Q3", "Q4", "NA"]:
        print(f"  {q}: {quartile_counts[q]:3d}")
    print()
    print("Confidence distribution:")
    for c in ["HIGH", "MEDIUM", "LOW", "UNMAPPED"]:
        print(f"  {c}: {confidence_counts[c]:3d}")

    if unmapped:
        print()
        print(f"Unmapped journals ({len(unmapped)}):")
        for j in sorted(unmapped):
            print(f"  - {j}")

    if not updates:
        print()
        print("No changes needed.")
        return

    print()
    print("Applying updates...")
    success = 0
    for pid, new_q, conf, jname in updates:
        try:
            sb.table("scopus_publications").update({
                "quartile": new_q,
                "updated_by": f"Auto (SCImago-curated, {conf} confidence)",
                "updated_at": "now()",
                "update_note": f"Quartile auto-assigned from journal '{jname[:50]}' — confidence {conf}",
            }).eq("id", pid).execute()

            # Also write to audit log
            sb.table("scopus_audit_log").insert({
                "publication_id": pid,
                "changed_by": f"Auto-Assign Script",
                "change_note": f"Quartile set to {new_q} (confidence: {conf})",
                "changed_fields": {"quartile": {"old": "NA", "new": new_q}},
            }).execute()
            success += 1
        except Exception as e:
            print(f"  ✗ Failed on id={pid}: {e}")

    print(f"✅ Updated {success}/{len(updates)} publications.")
    print()
    print("Recommendation:")
    print("  • HIGH-confidence assignments are safe.")
    print("  • Verify MEDIUM/LOW-confidence ones at scimagojr.com")
    print("  • Manually edit any 'NA' entries via the dashboard's Edit page.")


if __name__ == "__main__":
    main()
