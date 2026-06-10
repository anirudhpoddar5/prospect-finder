"""Steelman test of all features."""
import sys, os, time
sys.path.insert(0, "/Users/anirudhpoddar/prospect-finder")
from scraper import init_scan_state, run_scan_step

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEO_KEY = os.environ.get("GEOAPIFY_KEY", "")

def run(label, biz_types, locations):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")

    state = init_scan_state(
        api_key=API_KEY, business_types=biz_types, locations=locations,
        existing_csv_path="", max_leads=8, geoapify_key=GEO_KEY,
        keep_no_contact=True,
    )

    results = []
    for _ in range(500):
        update = run_scan_step(state)
        if update["type"] == "enrichment_progress":
            r = update.get("result")
            if r:
                tags = []
                if r.get("emails"): tags.append("📧")
                if r.get("phone"): tags.append("📞")
                if r.get("contact_person"): tags.append("👤")
                if r.get("linkedin_person"): tags.append("🔗in")
                if r.get("linkedin_company"): tags.append("🔗co")
                if "retry" in r.get("enrichment_notes",""): tags.append("🔄")
                cp = r.get("contact_person","")[:20] or ""
                ct = r.get("contact_title","")[:25] or ""
                lp = r.get("linkedin_person","")[:40] or ""
                print(f"  {update['current']:2d}/{update['total']:2d} {' '.join(tags):20s} {r['name'][:35]:35s} 👤{cp:20s} {ct:25s}")
                results.append(r)
        elif update["type"] == "complete":
            print(f"\n  ✅ Complete: {len(results)} results")
            break
        elif update.get("message"):
            print(f"  [{update['message'][:90]}]")
        time.sleep(0.02)

    cperson = sum(1 for r in results if r.get("contact_person"))
    lperson = sum(1 for r in results if r.get("linkedin_person"))
    lcompany = sum(1 for r in results if r.get("linkedin_company"))
    email = sum(1 for r in results if r.get("emails"))
    retry = sum(1 for r in results if "retry" in r.get("enrichment_notes",""))

    print(f"\n  RESULTS: {len(results)} | Email: {email} | Contact: {cperson} | LI person: {lperson} | LI co: {lcompany} | Retried: {retry}")

    for r in results:
        if r.get("contact_person"):
            print(f"    👤 {r['name'][:30]:30s} → {r['contact_person']:20s} ({r['contact_title']})")
    for r in results:
        if r.get("linkedin_person"):
            print(f"    🔗in {r['name'][:30]:30s} → {r['linkedin_person']}")

    return results

# ── TEST 1: UK block print bedcovers ──
r1 = run("Block Print Bedcovers in London (UK)",
    ["block print bedcovers"],
    [{"city":"London","state":"","country":"UK"}])

# ── TEST 2: Texas chiropractors ──
r2 = run("Chiropractors in Austin, Texas",
    ["chiropractors"],
    [{"city":"Austin","state":"Texas","country":"US"}])

print(f"\n{'='*70}")
print("  FINAL STEELMAN REPORT")
print(f"{'='*70}")
all_r = r1 + r2
print(f"  Total:               {len(all_r)}")
print(f"  With email:          {sum(1 for r in all_r if r.get('emails'))}")
print(f"  With phone:          {sum(1 for r in all_r if r.get('phone'))}")
print(f"  With contact person: {sum(1 for r in all_r if r.get('contact_person'))}")
print(f"  With LinkedIn person:{sum(1 for r in all_r if r.get('linkedin_person'))}")
print(f"  With LinkedIn co:    {sum(1 for r in all_r if r.get('linkedin_company'))}")
print(f"  Two-pass retried:    {sum(1 for r in all_r if 'retry' in r.get('enrichment_notes',''))}")
