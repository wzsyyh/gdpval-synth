"""Print one real GDPval task. Usage:

    uv run python scripts/show_real_gdpval.py Lawyers
    uv run python scripts/show_real_gdpval.py "Financial and Investment Analysts" 2
    uv run python scripts/show_real_gdpval.py "Software Developers"
"""

import json
import sys


def main() -> None:
    target_occ = sys.argv[1] if len(sys.argv) > 1 else "Lawyers"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    tasks = [
        json.loads(line)
        for line in open("data/gdpval_reference/tasks.jsonl")
        if line.strip()
    ]
    matched = [t for t in tasks if t["occupation"] == target_occ]
    if not matched:
        print(f"No tasks for occupation '{target_occ}'.")
        print("\nAvailable occupations:")
        for o in sorted({t["occupation"] for t in tasks}):
            print(f"  - {o}")
        return
    t = matched[idx]
    print(f"=== Real GDPval task: {target_occ} #{idx} ===")
    print(f"task_id: {t['task_id']}")
    print(f"sector:  {t['sector']}")
    print()
    print("--- PROMPT ---")
    print(t["prompt"])
    print()
    print(f"--- REFERENCE FILES (input attachments): {len(t['reference_files'])} ---")
    for f in t["reference_files"]:
        print(f"  - {f}")
    print()
    print(f"--- DELIVERABLE FILES (gold answer): {len(t['deliverable_files'])} ---")
    for f in t["deliverable_files"]:
        print(f"  - {f}")
    print()
    print("--- RUBRIC ---")
    print(t["rubric_pretty"])


if __name__ == "__main__":
    main()
