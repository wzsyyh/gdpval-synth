# PR #63915 diff and description (BUG:to_datetime with origin)


# Seed Material: pandas-dev/pandas#63915: BUG:to_datetime with origin
Source: github_issue_pr
Identifier: pr:pandas-dev/pandas#63915

Repository: pandas-dev/pandas
PR Number: #63915
PR Title: BUG:to_datetime with origin
Merged At: 2026-05-08T19:11:55Z
Changed Files: 3
Additions: +80, Deletions: -28

## PR Description
When pass in parameter origin to to_datetime will truncate time in origin. This fix preserves time in origin.

Closes https://github.com/pandas-dev/pandas/issues/63419

- [x] closes #xxxx (Replace xxxx with the GitHub issue number)
- [x] [Tests added and passed](https://pandas.pydata.org/pandas-docs/dev/development/contributing_codebase.html#writing-tests) if fixing a bug or adding a new feature
- [x] All [code checks passed](https://pandas.pydata.org/pandas-docs/dev/development/contributing_codebase.html#pre-commit).
- [ ] Added [type annotations](https://pandas.pydata.org/pandas-docs/dev/development/contributing_codebase.html#type-hints) to new arguments/methods/functions.
- [x] Added an entry in the latest `doc/source/whatsnew/vX.X.X.rst` file if fixing a bug or adding a new feature.
- [x] I have reviewed and followed all the [contribution guidelines](https://pandas.pydata.org/docs/dev/development/contributing.html)
- [ ] If I used AI to develop this pull request, I prompted it to follow `AGENTS.md`.


## Diff (first 3000 chars)
diff --git a/doc/source/whatsnew/v3.1.0.rst b/doc/source/whatsnew/v3.1.0.rst
index aa1a5c2e2b893..2fb4fc1cf830c 100644
--- a/doc/source/whatsnew/v3.1.0.rst
+++ b/doc/source/whatsnew/v3.1.0.rst
@@ -224,6 +224,7 @@ Datetimelike
 - Bug in :func:`date_range` where calendar-based offsets (e.g. ``MS``, ``ME``, ``QS``, ``YS``) could exclude the last offset boundary when ``end``'s time-of-day was earlier than ``start``'s (:issue:`35342`)
 - Bug in :func:`to_datetime` and :func:`to_timedelta` on ARM platforms where round ``float`` values outside the int64 domain (e.g. ``float(2**63)``) could silently produce incorrect results instead of raising (:issue:`64619`)
 - Bug in :func:`to_datetime` and :func:`to_timedelta` where ``uint64`` values greater than ``int64`` max silently overflowed instead of raising :class:`OutOfBoundsDatetime` or :class:`OutOfBoundsTimedelta` (:issue:`60677`)
+- Bug in :func:`to_datetime` when using a low time resolution ``unit``, higher resolution in ``origin`` is now preserved instead of silently dropped (e.g. ``unit="D"`` with microsecond precision origin) (:issue:`63419`)
 - Bug in :meth:`DataFrame.replace` and :meth:`Series.replace` raising ``AssertionError`` instead of :class:`OutOfBoundsDatetime` when replacing with a ``datetime`` value outside the ``datetime64[ns]`` range (:issue:`61671`)
 - Bug in :meth:`DataFrame.to_string` and :meth:`Series.to_string` where ``na_rep`` was ignored for datetime and timedelta columns, always displaying ``NaT`` (:issue:`55426`)
 - Bug in :meth:`DatetimeArray.isin` and :meth:`TimedeltaArray.isin` where mismatched resolutions could silently truncate finer-resolution values, leading to false matches (:issue:`64545`)
diff --git a/pandas/core/tools/datetimes.py b/pandas/core/tools/datetimes.py
index da02621225045..eeb5db911cd76 100644
--- a/pandas/core/tools/datetimes.py
+++ b/pandas/core/tools/datetimes.py
@@ -23,7 +23,6 @@
 from pandas._libs.tslibs import (
     NaT,
     OutOfBoundsDatetime,
-    Timedelta,
     Timestamp,
     astype_overflowsafe,
     get_supported_dtype,
@@ -77,6 +76,7 @@
 from pandas.core.construction import extract_array
 from pandas.core.indexes.base import Index
 from pandas.core.indexes.datetimes import DatetimeIndex
+from pandas.core.tools.timedeltas import to_timedelta
 
 if TYPE_CHECKING:
     from collections.abc import (
@@ -601,7 +601,7 @@ def _adjust_to_origin(arg, origin, unit):
 
     Returns
     -------
-    ndarray or scalar of adjusted date(s)
+    DatetimeArray, ndarray, or scalar of adjusted date(s)
     """
     if origin == "julian":
         original = arg
@@ -647,16 +647,7 @@ def _adjust_to_origin(arg, origin, unit):
 
         if offset.tz is not None:
             raise ValueError(f"origin offset {offset} must be tz-naive")
-        td_offset = offset - Timestamp(0)
-
-        # convert the offset to the unit of the arg
-        # this should be lossless in terms of precision
-        ioffset = td_offset // Timedelta(1, unit=unit)
-
-        # scalar