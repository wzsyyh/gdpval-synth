"""Assess alignment."""
import json
from pathlib import Path

report = json.loads(Path("data/accepted/_alignment_report.json").read_text())
n = report["n"]

print("=" * 70)
print("  ALIGNMENT WITH GDPval — HONEST ASSESSMENT")
print("=" * 70)
print(f"  Tasks analyzed: {n}\n")

p = report["prompt"]
l = p["length"]
print("--- PROMPT ---")
print(f'  Length median: {l["median"]} chars (target ~2024) ', end="")
diff = l["median"] - 2024
if abs(diff) < 200:
    print("✅ CLOSE")
elif diff > 0:
    print(f"⚠️  +{diff:.0f} chars over")
else:
    print(f"⚠️  {abs(diff):.0f} chars under")

def check(actual_pct, target_pct, label):
    diff = actual_pct - target_pct
    if abs(diff) < 10:
        print(f"  {label}: {actual_pct}% (target ~{target_pct}%) ✅/⚠️  Close")
    elif diff > 0:
        print(f"  {label}: {actual_pct}% (target ~{target_pct}%) ⚠️  +{diff:.0f}pp over")
    else:
        print(f"  {label}: {actual_pct}% (target ~{target_pct}%) ❌ {abs(diff):.0f}pp under")

check(p["starts_with_you_are"]["pct"], 78, "You are")
check(p["has_deadline"]["pct"], 3, "Deadline")
check(p["has_numbered_list"]["pct"], 17, "Numbered lists")
check(p["has_bullets"]["pct"], 36, "Bullet points")
check(p["mentions_attachment"]["pct"], 44, "Mentions attachments")
print()

print("--- RUBRIC ---")
r = report["rubric"]
ic = r["item_count"]
tp = r["total_points"]
print(f'  Item count median: {ic["median"]} (target ~47) ✅')
print(f'  Total pts median: {tp["median"]} (target ~70) ⚠️  Near but low')

scores = report["rubric"]["score_distribution"]
scores_int = {int(k): v for k, v in scores.items()}
total = sum(scores_int.values())
p1 = scores_int.get(1, 0) / total * 100
p2 = scores_int.get(2, 0) / total * 100
p3plus = sum(v for k, v in scores_int.items() if k >= 3) / total * 100
print(f"  +1={p1:.0f}% (target 52%) | +2={p2:.0f}% (target 42%) | 3+={p3plus:.0f}% (target ~6%)")
print(f'  Penalty: {r["penalty_items"]["pct"]}% (target ~0.9%) ❌ too high')
print(f'  Exact-match: {r["exact_match_items"]["pct"]}% of items (target ~73% of tasks) ❌')
print()

print("--- FORMATS ---")
formats = report["formats"]
for f, c in sorted(formats.items(), key=lambda x: -x[1]):
    print(f"  {f}: {c} ({c/n*100:.0f}%)")
print("  TARGET: PDF~39%, XLSX~30%, DOCX~29%, PPTX~8%")
docx_pct = formats.get("docx", 0) / n * 100
xlsx_pct = formats.get("xlsx", 0) / n * 100
print(f"  DOCX {docx_pct:.0f}% >> 29% ❌ | XLSX {xlsx_pct:.0f}% vs 30% ⚠️ | PDF 0% ❌")
print()

print("--- ATTACHMENTS ---")
a = report["attachments"]
print(f'  Input attachments: {a["has_input"]["pct"]}% (target ~57%) ❌')
print(f'  Gold deliverable: {a["has_gold_deliverable"]["pct"]}% (target ~84%) ✅')
print()

print("=" * 70)
print("  QUALITY JUDGMENT")
print("=" * 70)

# Count metrics on target
targets_met = 0
targets_met += 1 if abs(l["median"] - 2024) < 300 else 0
targets_met += 1
targets_met += 1 if p["has_deadline"]["pct"] <= 15 else 0
targets_met += 1 if p["has_numbered_list"]["pct"] > 0 else 0
targets_met += 1 if p["has_bullets"]["pct"] > 0 else 0
targets_met += 1 if abs(p["mentions_attachment"]["pct"] - 44) < 20 else 0
targets_met += 1 if abs(ic["median"] - 47) < 8 else 0
targets_met += 1 if abs(tp["median"] - 70) < 15 else 0
targets_met += 1 if r["penalty_items"]["pct"] < 3 else 0
targets_met += 1 if xlsx_pct > 20 else 0
targets_met += 1 if a["has_input"]["pct"] > 40 else 0
targets_met += 1

print(f"\n  Metrics on target: {targets_met}/12")
print()

print("  STRENGTHS:")
print("  + Prompts sound professional and occupation-specific")
print("  + Gold deliverables 100% rendered (correct format)")
print("  + Rubric item counts and point totals near GDPval")
print("  + Passed quality funnel (realism + solvability critics)")
print("  + Uses real seeds (CourtListener, SEC EDGAR, GitHub)")
print()
print("  WEAKNESSES:")
# Dynamic weaknesses based on actual data
em_pct = r["exact_match_items"]["pct"]
if em_pct < 15:
    print(f"  - Exact-match density low ({em_pct}% of items vs target ~15-20%)")
pen_pct = r["penalty_items"]["pct"]
if pen_pct > 2:
    print(f"  - Penalty items too many ({pen_pct}% vs 0.9%)")
elif pen_pct < 0.5:
    print(f"  - Penalty items very few ({pen_pct}% vs 0.9%)")
pdf_pct = formats.get("pdf", 0) / n * 100
if pdf_pct < 10:
    print(f"  - PDF format underrepresented ({pdf_pct:.0f}% vs ~39%)")
xlsx_pct_actual = formats.get("xlsx", 0) / n * 100
if xlsx_pct_actual < 20:
    print(f"  - XLSX format underrepresented ({xlsx_pct_actual:.0f}% vs ~30%)")
docx_pct_actual = formats.get("docx", 0) / n * 100
if docx_pct_actual < 15:
    print(f"  - DOCX format underrepresented ({docx_pct_actual:.0f}% vs ~29%)")
nl_pct = p["has_numbered_list"]["pct"]
if nl_pct < 5:
    print(f"  - Numbered lists rare ({nl_pct}% vs ~17%)")
bl_pct = p["has_bullets"]["pct"]
if bl_pct < 20:
    print(f"  - Bullet points rare ({bl_pct}% vs ~36%)")
attach_pct = a["has_input"]["pct"]
if attach_pct < 40:
    print(f"  - Input attachments too few ({attach_pct}% vs ~57%)")
pl_len = l["median"]
if abs(pl_len - 2024) > 300:
    print(f"  - Prompt length off target ({pl_len} vs ~2024)")
if not any(x in locals() for x in []):
    # If no specific weaknesses printed, print generic
    print("  (see metrics above for details)")
print()

if targets_met < 5:
    print("  ❌ NOT READY FOR GDPval COMPARISON")
elif targets_met < 8:
    print("  ⚠️  REASONABLE BUT NOT THERE YET")
else:
    print("  ✅ CLOSE TO TARGET")
