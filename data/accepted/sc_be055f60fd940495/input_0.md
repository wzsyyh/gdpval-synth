# PR #36897 diff showing changes to three files: doc/source/whatsnew/v1


# Seed Material: pandas-dev/pandas#36897: regression fix for merging DF with datetime index with empty DF
Source: github_issue_pr
Identifier: pr:pandas-dev/pandas#36897

Repository: pandas-dev/pandas
PR Number: #36897
PR Title: regression fix for merging DF with datetime index with empty DF
Merged At: 2020-11-03T13:30:03Z
Changed Files: 3
Additions: +56, Deletions: -6

## PR Description
- [X ] closes https://github.com/pandas-dev/pandas/issues/36895
- [X ] tests added / passed
- [X ] passes `black pandas`
- [ X] passes `git diff upstream/master -u -- "*.py" | flake8 --diff`
- [ X] whatsnew entry


## Diff
diff --git a/doc/source/whatsnew/v1.2.0.rst b/doc/source/whatsnew/v1.2.0.rst
index 6f137302d4994..167af1e5e282e 100644
--- a/doc/source/whatsnew/v1.2.0.rst
+++ b/doc/source/whatsnew/v1.2.0.rst
@@ -467,7 +467,6 @@ MultiIndex
 
 - Bug in :meth:`DataFrame.xs` when used with :class:`IndexSlice` raises ``TypeError`` with message ``"Expected label or tuple of labels"`` (:issue:`35301`)
 - Bug in :meth:`DataFrame.reset_index` with ``NaT`` values in index raises ``ValueError`` with message ``"cannot convert float NaN to integer"`` (:issue:`36541`)
--
 
 I/O
 ^^^
@@ -534,6 +533,7 @@ Reshaping
 - Bug in :meth:`DataFrame.pivot` did not preserve :class:`MultiIndex` level names for columns when rows and columns both multiindexed (:issue:`36360`)
 - Bug in :func:`join` returned a non deterministic level-order for the resulting :class:`MultiIndex` (:issue:`36910`)
 - Bug in :meth:`DataFrame.combine_first()` caused wrong alignment with dtype ``string`` and one level of ``MultiIndex`` containing only ``NA`` (:issue:`37591`)
+- Fixed regression in :func:`merge` on merging DatetimeIndex with empty DataFrame (:issue:`36895`)
 
 Sparse
 ^^^^^^
diff --git a/pandas/core/reshape/merge.py b/pandas/core/reshape/merge.py
index 5012be593820e..516ae90360be7 100644
--- a/pandas/core/reshape/merge.py
+++ b/pandas/core/reshape/merge.py
@@ -830,12 +830,15 @@ def _maybe_add_join_keys(self, result, left_indexer, right_indexer):
                     rvals = algos.take_1d(take_right, right_indexer, fill_value=rfill)
 
                 # if we have an all missing left_indexer
-                # make sure to just use the right values
-                mask = left_indexer == -1
-                if mask.all():
+                # make sure to just use the right values or vice-versa
+                mask_left = left_indexer == -1
+                mask_right = right_indexer == -1
+                if mask_left.all():
                     key_col = rvals
+                elif mask_right.all():
+                    key_col = lvals
                 else:
-                    key_col = Index(lvals).where(~mask, rvals)
+                    key_col = Index(lvals).where(~mask_left, rvals)
 
                 if result._is_label_reference(name):
                     result[name] = key_col
diff --git a/pandas/tests/reshape/merge/test_multi.py b/pandas/tests/reshape/merge/test_multi.py
index b1922241c7843..260a0e9d486b2 100644
--- a/pandas/tests/reshape/merge/test_multi.py
+++ b/pandas/tests/reshape/merge/test_multi.py
@@ -2,7 +2,7 @@
 import pytest
 
 import pandas as pd
-from pandas import DataFrame, Index, MultiIndex, Series
+from pandas import DataFrame, Index, MultiIndex, Series, Timestamp
 import pandas._testing as tm
 from pandas.core.reshape.concat import concat
 from pandas.core.reshape.merge import merge
@@ -481,6 +481,53 @@ def test_merge_datetime_index(self, klass):
         result = df.merge(df, on=[df.index.year], how="inner")
         tm.assert_frame_equal(result, expected)
 
+    @pytest.mark.parametrize("merge_type", ["left", "right"])
+    def test_merge_datetime_multi_index_empty_df(self, merge_type):
+        # see gh-36895
+
+        left = DataFrame(
+            data={
+                "data": [1.5, 1.5],
+            },
+            index=MultiIndex.from_tuples(
+                [[Timestamp("1950-01-01"), "A"], [Timestamp("1950-01-02"), "B"]],
+                names=["date", "panel"],
+            ),
+        )
+
+        right = DataFrame(
+            index=MultiIndex.from_tuples([], names=["date", "panel"]), columns=["state"]
+        )
+
+        expected_index = MultiIndex.from_tuples(
+            [[Timestamp("1950-01-01"), "A"], [Timestamp("1950-01-02"), "B"]],
+            names=["date", "panel"],
+        )
+
+        if merge_type == "left":
+            expected = DataFrame(
+                data={
+                    "data": [1.5, 1.5],
+                    "state": [None, None],
+                },
+                index=expected_index,
+            )
+            results_merge = left.merge(right, how="left", on=["date", "panel"])
+            results_join = left.join(right, how="left")
+        else:
+            expected = DataFrame(
+                data={
+                    "state": [None, None],
+                    "data": [1.5, 1.5],
+                },
+                index=expected_index,
+            )
+            results_merge = right.merge(left, how="right", on=["date", "panel"])
+            results_join = right.join(left, how="right")
+
+        tm.assert_frame_equal(results_merge, expected)
+        tm.assert_frame_equal(results_join, expected)
+
     def test_join_multi_levels(self):
 
         # GH 3662
