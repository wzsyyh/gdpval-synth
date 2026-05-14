#!/usr/bin/env python3
"""Comprehensive validation of all deliverable files in data/deliverables/.

Checks:
- .docx: Can be opened, has paragraphs/tables, non-zero content
- .xlsx: Can be opened, has sheets/cells, formulas are valid
- .md: Can be read, has content, frontmatter/headings check
- File metadata: size, expected vs actual
"""

import sys
import os
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DELIVERABLES_DIR = Path("data/deliverables")
ACCEPTED_DIR = Path("data/accepted")


def check_docx(path: Path) -> list[str]:
    """Check docx structural integrity."""
    issues = []
    try:
        from docx import Document
        doc = Document(str(path))
        paras = [p for p in doc.paragraphs if p.text.strip()]
        if not paras:
            issues.append("EMPTY: No non-empty paragraphs found")
        else:
            issues.append(f"OK: {len(paras)} paragraphs, ~{sum(len(p.text) for p in paras)} chars")

        # Check for tables
        if doc.tables:
            issues.append(f"  tables: {len(doc.tables)}")
            for i, t in enumerate(doc.tables):
                issues.append(f"    table[{i}]: {len(t.rows)}x{len(t.columns)}")
    except ImportError:
        # Fallback: check zip structure
        try:
            with ZipFile(path, 'r') as zf:
                names = zf.namelist()
                if 'word/document.xml' in names:
                    doc_xml = zf.read('word/document.xml')
                    issues.append(f"OK: valid docx, {len(doc_xml)} bytes in document.xml")
                else:
                    issues.append("BROKEN: word/document.xml not found in zip")
        except BadZipFile:
            issues.append("BROKEN: Not a valid zip file (corrupted docx)")
    except Exception as e:
        issues.append(f"ERROR: {e}")
    return issues


def check_xlsx(path: Path) -> list[str]:
    """Check xlsx structural integrity."""
    issues = []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(path), data_only=False)
        issues.append(f"OK: {len(wb.sheetnames)} sheets: {wb.sheetnames}")
        for name in wb.sheetnames:
            ws = wb[name]
            issues.append(f"  sheet '{name}': {ws.max_row}x{ws.max_column}")
            # Check for formulas
            formula_count = 0
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith('='):
                        formula_count += 1
            if formula_count:
                issues.append(f"    formulas: {formula_count}")
    except BadZipFile:
        issues.append("BROKEN: Not a valid zip file (corrupted xlsx)")
    except Exception as e:
        issues.append(f"ERROR: {e}")
    return issues


def check_md(path: Path) -> list[str]:
    """Check markdown content."""
    issues = []
    try:
        text = path.read_text(encoding='utf-8')
        if not text.strip():
            issues.append("EMPTY: File is empty or whitespace-only")
        else:
            lines = text.split('\n')
            issues.append(f"OK: {len(lines)} lines, {len(text)} chars")
            headings = [l for l in lines if l.strip().startswith('#')]
            if headings:
                issues.append(f"  headings: {len(headings)}")
            code_blocks = text.count('```') // 2
            if code_blocks:
                issues.append(f"  code blocks: {code_blocks}")
    except Exception as e:
        issues.append(f"ERROR: {e}")
    return issues


def check_file_size(path: Path) -> str:
    """Basic file size check."""
    size = path.stat().st_size
    if size == 0:
        return "EMPTY FILE"
    return f"{size:>8,} bytes"


def cross_ref_deliverable(task_path: Path, file_path: Path) -> list[str]:
    """Cross-reference delivered file against task JSON expectations."""
    issues = []
    try:
        task = json.loads(task_path.read_text(encoding='utf-8'))
        candidate = task if 'candidate_id' in task else task.get('candidate', task)
        did = candidate.get('candidate_id', 'unknown')

        # Check format expectation
        deliv = candidate.get('deliverable', {})
        expected_fmt = deliv.get('primary_format', 'unknown')

        actual_fmt = file_path.suffix.lstrip('.')
        if actual_fmt == 'md' and expected_fmt == 'markdown':
            pass  # OK
        elif actual_fmt != expected_fmt:
            issues.append(f"FORMAT MISMATCH: expected {expected_fmt}, got {actual_fmt}")

        # Check expected size if present
        exp_size = deliv.get('expected_size')
        if exp_size:
            actual_size = file_path.stat().st_size
            ratio = actual_size / exp_size
            if ratio < 0.1 or ratio > 10:
                issues.append(f"SIZE OUTLIER: expected ~{exp_size}, actual {actual_size} ({ratio:.1f}x)")

        # Check input attachments
        input_paths = candidate.get('input_attachment_paths', []) or []
        for ip in input_paths:
            ip_path = Path(ip)
            if not ip_path.exists():
                issues.append(f"MISSING INPUT: {ip}")
            else:
                issues.append(f"  input exists: {ip_path.name} ({ip_path.stat().st_size:,} bytes)")

    except Exception as e:
        issues.append(f"REF ERROR: {e}")
    return issues


def main():
    all_results = {}
    total_issues = 0

    # Build task-id -> task JSON path mapping
    task_map = {}
    if ACCEPTED_DIR.exists():
        for f in ACCEPTED_DIR.glob("sc_*.json"):
            if f.name == '_alignment_report.json':
                continue
            task_id = f.stem
            task_map[task_id] = f

    if not DELIVERABLES_DIR.exists():
        print(f"ERROR: {DELIVERABLES_DIR} not found")
        sys.exit(1)

    # Collect all deliverable files by task-id
    deliverable_dirs = sorted(DELIVERABLES_DIR.iterdir())
    file_count = 0

    for ddir in deliverable_dirs:
        if not ddir.is_dir():
            continue
        files = list(ddir.iterdir())
        if not files:
            all_results[ddir.name] = {"status": "EMPTY_DIR", "issues": ["Directory is empty"]}
            total_issues += 1
            continue

        for fpath in sorted(files):
            file_count += 1
            fmt = fpath.suffix.lstrip('.').lower()
            size_str = check_file_size(fpath)
            task_id = ddir.name

            issues = [f"Format: {fmt}, Size: {size_str}"]

            if fpath.stat().st_size == 0:
                issues.append("EMPTY FILE")
                all_results[f"{task_id}/{fpath.name}"] = {"status": "EMPTY", "issues": issues}
                total_issues += 1
                continue

            # Format-specific checks
            if fmt == 'docx':
                detail_issues = check_docx(fpath)
            elif fmt == 'xlsx':
                detail_issues = check_xlsx(fpath)
            elif fmt in ('md', 'markdown'):
                detail_issues = check_md(fpath)
            else:
                detail_issues = [f"UNKNOWN FORMAT: .{fmt}"]

            issues.extend(detail_issues)

            # Cross-reference with task JSON
            if task_id in task_map:
                ref_issues = cross_ref_deliverable(task_map[task_id], fpath)
                issues.extend(ref_issues)

            # Count issues
            n_issues = sum(1 for i in issues if any(kw in i for kw in ['BROKEN', 'EMPTY', 'ERROR', 'MISMATCH', 'MISSING', 'CORRUPT']))
            total_issues += n_issues
            status = "OK" if n_issues == 0 else f"ISSUES({n_issues})"
            all_results[f"{task_id}/{fpath.name}"] = {"status": status, "issues": issues}

    # Summary
    print(f"=" * 70)
    print(f"  DELIVERABLE VALIDATION REPORT")
    print(f"  Total files: {file_count}, Tasks with issues: {sum(1 for v in all_results.values() if v['status'] != 'OK')}")
    print(f"=" * 70)

    for name, result in sorted(all_results.items()):
        status = result['status']
        symbol = "✅" if status == "OK" else "❌"
        print(f"\n{symbol} {name} [{status}]")
        for issue in result['issues']:
            print(f"   {issue}")

    print(f"\n{'=' * 70}")
    print(f"  Total files: {file_count}")
    print(f"  Files with issues: {sum(1 for v in all_results.values() if v['status'] != 'OK')}")
    print(f"  Total issues found: {total_issues}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
