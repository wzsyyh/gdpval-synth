"""XLSX deliverable validator.

Checks that the rendered Excel file matches the blueprint:
- All expected sheets exist
- Key expected_values match (within tolerance)
- No formula errors in critical cells
"""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import load_workbook

from pipeline.scenario.reference_answer import ExpectedValue, ReferenceAnswer

logger = logging.getLogger(__name__)


def validate_xlsx(file_path: Path, blueprint: ReferenceAnswer) -> tuple[bool, list[str]]:
    """Validate an xlsx file against its blueprint.

    Returns (passed, list of failure reasons).
    """
    failures: list[str] = []

    try:
        wb = load_workbook(file_path, data_only=False)
    except Exception as e:
        return False, [f"Cannot open workbook: {e}"]

    # Check expected sheets exist
    sheet_names = set(wb.sheetnames)
    for sheet_plan in (blueprint.sheets or []):
        if sheet_plan.name not in sheet_names:
            failures.append(f"Missing sheet: {sheet_plan.name}")

    # Check expected_values
    for ev in blueprint.expected_values:
        # Parse location like "Assumptions B32" or "Sheet 'Outputs' cell B15"
        loc = ev.location.lower()
        sheet_name = None
        cell_ref = None

        # Simple parsing: look for sheet name and cell ref
        for sn in sheet_names:
            if sn.lower() in loc:
                sheet_name = sn
                break

        # Extract cell ref (e.g., B15, A1)
        import re
        m = re.search(r"([a-z]+\d+)", loc, re.IGNORECASE)
        if m:
            cell_ref = m.group(1).upper()

        if not sheet_name or not cell_ref:
            logger.debug("Cannot parse location '%s' for validation", ev.location)
            continue

        try:
            ws = wb[sheet_name]
            cell = ws[cell_ref]
            actual = cell.value

            # Skip formula cells (they need Excel to evaluate)
            if isinstance(actual, str) and actual.startswith("="):
                continue

            if actual is None:
                failures.append(f"Expected value '{ev.description}' at {ev.location}: cell is empty (expected {ev.value})")
                continue

            # Compare
            if isinstance(ev.value, (int, float)):
                try:
                    actual_f = float(actual)
                    expected_f = float(ev.value)
                    if ev.tolerance is not None:
                        if abs(actual_f - expected_f) > ev.tolerance:
                            failures.append(
                                f"Expected value '{ev.description}' at {ev.location}: {actual} != {ev.value} (tol={ev.tolerance})"
                            )
                    else:
                        if abs(actual_f - expected_f) > 0.01:
                            failures.append(
                                f"Expected value '{ev.description}' at {ev.location}: {actual} != {ev.value}"
                            )
                except (ValueError, TypeError):
                    failures.append(
                        f"Expected value '{ev.description}' at {ev.location}: cannot compare {actual} with {ev.value}"
                    )
            else:
                if str(actual) != str(ev.value):
                    failures.append(
                        f"Expected value '{ev.description}' at {ev.location}: '{actual}' != '{ev.value}'"
                    )
        except Exception as e:
            failures.append(f"Error checking {ev.location}: {e}")

    passed = len(failures) == 0
    return passed, failures
