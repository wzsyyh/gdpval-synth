# Bug Fix Review: to_datetime origin time preservation (PR #63915)

## Root Cause Analysis

The root cause of the bug resided in the `_adjust_to_origin` helper function within `pandas/core/tools/datetimes.py`. When a user provided an `origin` parameter to `pd.to_datetime`, the function needed to calculate a numeric offset to adjust the input arg. The original flawed implementation performed the following steps:

1.  It computed a `Timedelta` offset by subtracting the Unix epoch (`Timestamp(0)`) from the user-provided `origin` timestamp: `td_offset = offset - Timestamp(0)`.
2.  It then attempted to convert this `td_offset` into the same unit as the input `arg` using integer division: `ioffset = td_offset // Timedelta(1, unit=unit)`.

The critical error was in this second step. The `Timedelta(1, unit=unit)` constructor creates a `Timedelta` object representing one period of the specified `unit` (e.g., one day if `unit='D'`). However, performing integer division (`//`) between two `Timedelta` objects truncates any remainder, effectively discarding all time components smaller than the specified `unit`. For example, if the `origin` had microsecond precision (`Timestamp('2000-01-01 00:00:00.123456')`) and `unit='D'`, the calculation would truncate the hours, minutes, seconds, and microseconds, resulting in an integer number of whole days. This silently dropped the finer time resolution present in the `origin`, leading to incorrect datetime conversions.

## Code Changes

The fix implemented in PR #63915 involved precise modifications to imports and the core calculation logic:

1.  **Import Changes:** The import of `Timedelta` was removed from the `pandas._libs.tslibs` module import statement. Instead, the function `to_timedelta` was imported from `pandas.core.tools.timedeltas`. This shift moves from using the `Timedelta` object directly to using the higher-level conversion function.
2.  **Logic Change in `_adjust_to_origin`:** The key change was in how the offset from the origin was calculated. The old code:
    ```python
    ioffset = td_offset // Timedelta(1, unit=unit)
    ```
    was replaced with a new calculation that preserves fractional parts:
    ```python
    ioffset = td_offset / to_timedelta(1, unit=unit)
    ```
    This uses standard floating-point division (`/`) instead of integer division (`//`). The result is that `ioffset` becomes a floating-point number (e.g., `365.25` for a leap year) rather than a truncated integer, thereby preserving the higher-resolution time information from the `origin` timestamp. The `to_timedelta` function is used to ensure the denominator `Timedelta` is correctly constructed from the numeric `1` and the specified `unit`.

## Test Case Demonstration

The following test case clearly demonstrates the bug and the fix. It converts a numeric value representing a day offset, using an origin timestamp that includes microsecond-level precision.

```python
import pandas as pd
from pandas import Timestamp, Series

# Define input data: a numeric offset of 1 day
numeric_series = Series([1.0])
# Define an origin with microsecond precision
origin = Timestamp('2000-01-01 00:00:00.123456')

# BUGGY OLD BEHAVIOR (before fix)
# The microsecond component (.123456) is truncated.
# The result is simply origin + 1 day, ignoring the microseconds.
# old_result = pd.to_datetime(numeric_series, unit='D', origin=origin)
# Expected old (incorrect) result: 2000-01-02 00:00:00.000000

# NEW FIXED BEHAVIOR (after fix)
# The microsecond component is preserved.
# The result correctly adds 1 day plus the fractional day from the origin's time.
# new_result = pd.to_datetime(numeric_series, unit='D', origin=origin)
# Expected new (correct) result: 2000-01-02 00:00:00.123456
```

**Explanation:** With `unit='D'`, the input `1.0` means 'add one day to the origin'. The origin `2000-01-01 00:00:00.123456` should yield `2000-01-02 00:00:00.123456`. The old code truncated the microsecond component, producing `2000-01-02 00:00:00.000000`.

## Impact and Scope

This fix addresses the bug reported in GitHub issue #63419. The impact is primarily on users who rely on the `origin` parameter of `pd.to_datetime` to convert numeric values (like offsets in days, hours, etc.) relative to a specific reference point that includes finer time resolution (e.g., milliseconds, microseconds, or nanoseconds).

Affected code patterns would include scenarios such as:
- Converting sensor data recorded in fractional day offsets from a specific, precisely-timed experiment start.
- Processing financial timestamps where nanosecond accuracy relative to a market open time is critical.
- Any pipeline that uses a high-resolution `origin` with a coarse `unit` like `'D'` or `'h'` expecting the origin's time-of-day to be preserved.

The fix is backward-compatible for cases where the `origin` is at midnight (00:00:00) or where the `unit` matches or exceeds the resolution of the origin's time component. In these cases, integer and floating-point division produce the same integer result. The change only affects the precision of the output when a finer-resolution origin is used with a coarser unit, which was the intended behavior from the start.

## Documentation Update

The pull request correctly includes an update to the project's documentation to inform users of the bug fix. The change was made to the `whatsnew` file for the upcoming release, `doc/source/whatsnew/v3.1.0.rst`.

The exact line added to the "Datetimelike" section under the Bug Fixes category is:

```rst
- Bug in :func:`to_datetime` when using a low time resolution ``unit``, higher resolution in ``origin`` is now preserved instead of silently dropped (e.g. ``unit="D"`` with microsecond precision origin) (:issue:`63419`)
```

This entry clearly describes the bug's context (low-resolution `unit`), the fix (preserving higher-resolution `origin`), provides a concrete example (`unit='D'` with microsecond precision), and links to the authoritative issue number `#63419`. This ensures users and contributors are aware of the behavioral correction in the upcoming `v3.1.0` release.
