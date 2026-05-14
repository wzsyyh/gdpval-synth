#!/usr/bin/env python3
"""Deep inspect all docx files - categorize by content depth."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DELIVERABLES_DIR = Path("data/deliverables")

docx_files = sorted(DELIVERABLES_DIR.rglob("*.docx"))

print(f"{'File':<50} {'Style':<12} {'Paras':>5} {'Chars':>6}  Content")
print(f"{'-'*110}")

for path in docx_files:
    from docx import Document
    doc = Document(str(path))
    paras = [p for p in doc.paragraphs if p.text.strip()]
    total_chars = sum(len(p.text) for p in paras)

    # Check if headings-only
    non_heading = [p for p in paras if p.style.name not in ('Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Title')]
    headings_only = len(non_heading) <= 2  # only TO/DATE/RE and separator

    h_count = sum(1 for p in paras if p.style.name.startswith('Heading'))
    body_count = len(paras) - h_count

    issues = []
    if headings_only:
        issues.append("HEADINGS_ONLY")
    if total_chars < 500:
        issues.append(f"TOO_SHORT({total_chars})")

    label = ",".join(issues) if issues else "OK"
    print(f"{path.parent.name + '/' + path.name:<50} {label:<12} {len(paras):>5} {total_chars:>6}  h={h_count}, body={body_count}")

print(f"\n--- Summary ---")
print(f"Total docx files: {len(docx_files)}")
problematic = [f for f in docx_files if 'HEADINGS_ONLY' in str(f)]
print(f"Headings-only (missing narrative): {len(problematic)}")
for p in problematic:
    from docx import Document
    doc = Document(str(p))
    paras = [pp for pp in doc.paragraphs if pp.text.strip()]
    print(f"  {p.parent.name}/{p.name}: {len(paras)} paras, {sum(len(pp.text) for pp in paras)} chars")
