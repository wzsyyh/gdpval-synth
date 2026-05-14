#!/usr/bin/env python3
"""Deep inspect docx files - extract full text content."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DELIVERABLES_DIR = Path("data/deliverables")

# Suspicious files (very short content)
suspicious = [
    "sc_0d71216d4a58a810/motion_to_dismiss.docx",
    "sc_150eb71a045885de/deposition_outline.docx",
]

for rel in suspicious:
    path = DELIVERABLES_DIR / rel
    print(f"\n{'='*70}")
    print(f"  {rel}")
    print(f"{'='*70}")

    if not path.exists():
        print(f"  FILE NOT FOUND")
        continue

    try:
        from docx import Document
        doc = Document(str(path))

        print(f"\n--- Full text ---")
        for i, p in enumerate(doc.paragraphs):
            if p.text.strip():
                print(f"  p[{i}] (style='{p.style.name}'): {p.text[:200]}")

        if doc.tables:
            print(f"\n--- Tables ({len(doc.tables)}) ---")
            for ti, t in enumerate(doc.tables):
                print(f"  Table {ti}: {len(t.rows)}x{len(t.columns)}")
                for ri, row in enumerate(t.rows[:5]):
                    cells = [c.text[:50] for c in row.cells]
                    print(f"    row[{ri}]: {cells}")

        # Check headers/footers
        for si, section in enumerate(doc.sections):
            header = section.header
            footer = section.footer
            h_text = ' '.join(p.text for p in header.paragraphs if p.text.strip())
            f_text = ' '.join(p.text for p in footer.paragraphs if p.text.strip())
            if h_text:
                print(f"  Header s{si}: {h_text[:100]}")
            if f_text:
                print(f"  Footer s{si}: {f_text[:100]}")

    except Exception as e:
        print(f"  ERROR: {e}")
