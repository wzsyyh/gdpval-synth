"""Verify deliverables against rubric and expected values — item by item."""

import json
import re
from pathlib import Path

import docx
import openpyxl


def read_deliverable(path: Path) -> str:
    """Read any deliverable file into plain text for searching."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        return path.read_text()
    if suffix == ".docx":
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix == ".xlsx":
        # Try data_only first (computed values), then fallback to formulas
        texts = []
        for data_only in [True, False]:
            try:
                wb = openpyxl.load_workbook(path, data_only=data_only)
                parts = []
                for sheet in wb.worksheets:
                    parts.append(f"--- Sheet: {sheet.title} ---")
                    for row in sheet.iter_rows():
                        row_vals = [str(c.value) if c.value is not None else "" for c in row]
                        if any(row_vals):
                            parts.append("\t".join(row_vals))
                texts.append("\n".join(parts))
            except Exception:
                pass
        return "\n".join(texts) if texts else ""
    if suffix == ".pdf":
        # Try to convert via LibreOffice to text, or just return empty with warning
        txt_path = path.with_suffix(".txt")
        if txt_path.exists():
            return txt_path.read_text()
        # Fallback: return empty; caller should use docx version instead
        return ""
    return path.read_text()


def find_deliverable_file(task_dir: Path, task_json: dict) -> Path | None:
    """Find the actual deliverable file for a task."""
    gold = task_json.get("gold_deliverable_path", "")
    if gold:
        p = Path(gold)
        if p.exists():
            return p
    # Search task_dir
    files = list(task_dir.iterdir())
    # Prefer docx/xlsx/md over pdf (pdf is rendered from docx, so docx has same content)
    for suffix in [".docx", ".xlsx", ".md"]:
        for f in files:
            if f.suffix.lower() == suffix:
                return f
    for f in files:
        if f.suffix.lower() == ".pdf":
            return f
    return None


def normalize_number(s: str) -> str:
    """Strip currency symbols, commas, suffixes to get raw numeric string."""
    s = s.replace("$", "").replace(",", "").replace("%", "")
    s = re.sub(r"\s+", "", s)
    # Remove trailing 'M', 'B', 'x', etc. for comparison
    s = re.sub(r"[MBKxX]$", "", s)
    return s.strip()


def check_value_in_text(text: str, value) -> bool:
    """Check if expected value appears in text (flexible matching)."""
    if value is None:
        return False
    s = str(value)
    # Direct containment
    if s in text:
        return True
    # Try without extra whitespace
    normalized_text = re.sub(r"\s+", " ", text)
    normalized_val = re.sub(r"\s+", " ", s)
    if normalized_val in normalized_text:
        return True
    # Try case-insensitive for text values > 3 chars
    if len(s) > 3 and s.lower() in text.lower():
        return True
    # Numeric flexible matching: $85,138M vs 85138 vs 85.1B
    try:
        num_text = normalize_number(s)
        if num_text and re.match(r"^-?\d+(\.\d+)?$", num_text):
            # Search for this number (or rounded version) in text
            pattern = re.compile(r"[^\d.]" + re.escape(num_text) + r"[^\d.]")
            if pattern.search(text):
                return True
            # Also try without decimal part if it's .0
            if num_text.endswith(".0"):
                int_part = num_text[:-2]
                pattern2 = re.compile(r"[^\d.]" + re.escape(int_part) + r"[^\d.]")
                if pattern2.search(text):
                    return True
    except Exception:
        pass
    return False


def verify_task(json_path: Path) -> dict:
    """Verify one task: rubric items vs deliverable content."""
    task = json.loads(json_path.read_text())
    task_id = task["candidate_id"]
    deliverable_id = task["deliverable"]["deliverable_id"]
    occupation = task["occupation"]

    # Find deliverable
    task_dir = Path(f"data/deliverables/{task_id}")
    deliverable_path = find_deliverable_file(task_dir, task)
    if deliverable_path is None:
        return {"task_id": task_id, "error": "No deliverable file found"}

    text = read_deliverable(deliverable_path)
    if not text:
        # Try docx if pdf was empty
        if deliverable_path.suffix.lower() == ".pdf":
            docx_path = deliverable_path.with_suffix(".docx")
            if docx_path.exists():
                text = read_deliverable(docx_path)

    rubric = task.get("rubric", [])
    canonical = task.get("canonical", {})
    ref = canonical.get("reference_answer", {})
    expected_values = ref.get("expected_values", [])

    # ── Check 1: Expected values in deliverable ──
    ev_checks = []
    for ev in expected_values:
        found = check_value_in_text(text, ev["value"])
        ev_checks.append({
            "description": ev["description"],
            "value": str(ev["value"]),
            "found": found,
            "location_expected": ev.get("location", ""),
        })

    # ── Check 2: Rubric categories coverage ──
    categories = {}
    for r in rubric:
        cat = r.get("category", "unknown")
        categories.setdefault(cat, []).append(r)

    # Sample checks per category
    cat_results = {}
    for cat, items in categories.items():
        # Check if category-specific keywords appear in text
        checked = 0
        matched = 0
        for item in items[:5]:  # sample first 5 per category
            crit = item.get("criterion", "")
            # Extract key noun phrases (naive: words > 4 chars)
            keywords = [w for w in re.findall(r"[A-Za-z]{4,}", crit) if w.lower() not in {
                "deliverable", "should", "document", "file", "provided", "correct",
                "appropriate", "professional", "consistent", "complete", "accurate",
                "clear", "proper", "relevant", "specific", "detailed", "sufficient"
            }]
            if keywords:
                checked += 1
                # Check if ANY keyword appears
                found_kw = any(kw.lower() in text.lower() for kw in keywords[:3])
                if found_kw:
                    matched += 1
        cat_results[cat] = {"sampled": checked, "matched": matched, "total_items": len(items)}

    # ── Check 3: Format alignment ──
    fmt = ref.get("format", "")
    actual_suffix = deliverable_path.suffix.lower().lstrip(".")
    fmt_normalized = {"markdown": "md"}.get(fmt, fmt)
    format_ok = (fmt_normalized == actual_suffix) or (fmt == "pdf" and actual_suffix in ("pdf", "docx"))

    # ── Check 4: Key rubric criteria spot-checks ──
    spot_checks = []
    important_items = [r for r in rubric if r.get("score", 0) >= 2 and not r.get("is_penalty", False)]
    for item in important_items[:8]:
        crit = item.get("criterion", "")
        # Check if criterion's key subject appears in deliverable
        keywords = re.findall(r"[A-Z][a-zA-Z\s]{3,20}(?=[\s,;:]|$)", crit)
        found = False
        for kw in keywords[:2]:
            if kw.strip().lower() in text.lower():
                found = True
                break
        spot_checks.append({
            "criterion": crit[:100],
            "score": item.get("score"),
            "found_evidence": found,
        })

    return {
        "task_id": task_id,
        "occupation": occupation,
        "deliverable_id": deliverable_id,
        "format_expected": fmt,
        "format_actual": actual_suffix,
        "format_aligned": format_ok,
        "deliverable_path": str(deliverable_path),
        "deliverable_chars": len(text),
        "expected_values": ev_checks,
        "ev_found_rate": sum(1 for e in ev_checks if e["found"]) / max(len(ev_checks), 1),
        "category_coverage": cat_results,
        "spot_checks": spot_checks,
        "rubric_total": len(rubric),
        "penalty_count": sum(1 for r in rubric if r.get("is_penalty")),
    }


def main():
    accepted_dir = Path("data/accepted")
    json_files = sorted(accepted_dir.glob("*.json"))

    print("=" * 80)
    print("DELIVERABLE vs RUBRIC — ITEM-BY-ITEM VERIFICATION")
    print("=" * 80)

    all_results = []
    for jf in json_files:
        result = verify_task(jf)
        all_results.append(result)

        task_id = result["task_id"]
        occ = result["occupation"]
        deliv = result["deliverable_id"]
        print(f"\n{'─' * 80}")
        print(f"Task: {task_id} | {occ}/{deliv}")
        print(f"File: {result.get('deliverable_path', 'N/A')}")
        print(f"Format: {result['format_expected']} → {result['format_actual']} {'✅' if result['format_aligned'] else '❌'}")
        print(f"Deliverable size: {result['deliverable_chars']} chars")
        print(f"Rubric items: {result['rubric_total']} (penalties: {result['penalty_count']})")

        # Expected values
        print("\n  Expected Values:")
        for ev in result["expected_values"]:
            status = "✅" if ev["found"] else "❌"
            print(f"    {status} [{ev['description'][:40]}] value='{str(ev['value'])[:50]}'")

        # Category coverage
        print("\n  Category Coverage (sampled):")
        for cat, res in result["category_coverage"].items():
            pct = res["matched"] / max(res["sampled"], 1) * 100
            print(f"    {cat}: {res['matched']}/{res['sampled']} keywords found ({pct:.0f}%) — {res['total_items']} items")

        # Spot checks
        print("\n  Spot Checks (high-score rubric items):")
        for sc in result["spot_checks"]:
            status = "✅" if sc["found_evidence"] else "⚠️"
            print(f"    {status} (+{sc['score']}) {sc['criterion'][:70]}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    total_ev = sum(len(r["expected_values"]) for r in all_results)
    found_ev = sum(sum(1 for e in r["expected_values"] if e["found"]) for r in all_results)
    print(f"Expected values found: {found_ev}/{total_ev} ({found_ev/max(total_ev,1)*100:.0f}%)")
    format_ok = sum(1 for r in all_results if r.get("format_aligned"))
    print(f"Format aligned: {format_ok}/{len(all_results)}")
    avg_rubric = sum(r["rubric_total"] for r in all_results) / max(len(all_results), 1)
    print(f"Avg rubric items: {avg_rubric:.0f}")
    avg_penalty = sum(r["penalty_count"] for r in all_results) / max(len(all_results), 1)
    print(f"Avg penalty items: {avg_penalty:.1f}")


if __name__ == "__main__":
    main()
