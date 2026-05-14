"""Quick exact-match count."""
import json
from pathlib import Path

accepted = sorted(Path("data/accepted").glob("sc_*.json"))
total_exact = 0
total_items = 0
tasks_with_exact = 0

for tf in accepted:
    task = json.loads(tf.read_text())
    tid = tf.stem
    occ = task.get("occupation")
    rubric = task.get("rubric", [])

    exact_items = []
    for r in rubric:
        crit = r["criterion"].lower()

        has_num = any(c.isdigit() for c in crit)
        has_cite = any(kw in crit for kw in ["f.", "u.s.", "u.s.c.", "§ "])
        has_quote = '"' in r["criterion"]
        has_code = "`" in r["criterion"]
        has_id = "identifies" in crit or "lists" in crit or "names" in crit

        if has_cite:
            is_exact = True
        elif has_code:
            is_exact = True
        elif has_id and has_num:
            is_exact = True
        elif has_quote and has_num:
            is_exact = True
        elif has_num and any(kw in crit for kw in ["$", "million", "billion", "%"]):
            is_exact = True
        else:
            is_exact = False

        if is_exact:
            exact_items.append(r["criterion"][:80])

    if exact_items:
        tasks_with_exact += 1

    total_exact += len(exact_items)
    total_items += len(rubric)

    print(f"{tid} | {occ:<18} | {len(rubric):>2} items | {len(exact_items):>2} exact")
    for e in exact_items[:3]:
        print(f"      -> {e}")

print()
print(f"Summary: {tasks_with_exact}/{len(accepted)} tasks have exact-match items")
if total_items:
    print(f"Exact-match rate: {total_exact}/{total_items} = {total_exact/total_items*100:.1f}%")
