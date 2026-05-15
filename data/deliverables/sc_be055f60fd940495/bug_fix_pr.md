# Bug Fix Review: PR #36897 - Regression in merge with DatetimeIndex and empty DataFrame

# Bug Fix Review: PR #36897 - Regression in merge with DatetimeIndex and empty DataFrame

This document provides a comprehensive review of PR #36897, which addresses a regression in pandas where merging a DataFrame with a datetime index against an empty DataFrame would fail. The regression was reported in issue #36895 and was merged on November 3, 2020. The fix modifies the `_maybe_add_join_keys` method in `pandas/core/reshape/merge.py` to correctly handle the case where the right indexer contains all -1 values, indicating an empty DataFrame on the right side of the merge operation.

## Root Cause Analysis

The `_maybe_add_join_keys` method in `pandas/core/reshape/merge.py` is responsible for constructing the join key columns in the result of a merge operation. When merging on index levels, this method determines which values to use for the key columns based on the left_indexer and right_indexer arrays.

In the original code (lines 833-839), there was a single variable `mask` that checked if `left_indexer == -1`. A value of -1 in the left_indexer indicates that the corresponding row in the result came from the right DataFrame (i.e., there was no match on the left side). The original logic had only two cases: if all values in mask were True (meaning all rows came from the right), it used `rvals` (right values); otherwise, it used `Index(lvals).where(~mask, rvals)` to conditionally select between left and right values.

The critical flaw was that the code did not account for the symmetric case where the right_indexer contained all -1 values. When merging a non-empty DataFrame with an empty DataFrame using a left merge, the left_indexer would contain valid indices (not -1), while the right_indexer would contain all -1 values. The original `mask` (checking left_indexer == -1) would be all False, causing the code to fall through to the `else` branch, which incorrectly tried to use the right values that were all missing, leading to errors.

Specifically, when the right DataFrame is empty, `rvals` would contain NaN or missing values for all rows, and `Index(lvals).where(~mask, rvals)` would still attempt to align these values incorrectly, resulting in the reported regression where the merge operation would fail or produce incorrect results.

## Patch Analysis

The patch in PR #36897 modifies lines 830-842 of `pandas/core/reshape/merge.py`. The changes can be broken down as follows:

First, the single `mask` variable is replaced with two separate masks: `mask_left = left_indexer == -1` and `mask_right = right_indexer == -1`. This allows the code to independently check both sides of the merge for missing indices.

Second, a new conditional branch is added: `elif mask_right.all(): key_col = lvals`. This handles the case where the right indexer contains all -1 values (meaning the result came entirely from the left DataFrame). In this scenario, the key column should use the left values (`lvals`), which was not handled in the original code.

Third, the `else` branch is updated to use `~mask_left` instead of `~mask` in the `where` condition: `key_col = Index(lvals).where(~mask_left, rvals)`. This ensures that when neither side is entirely missing, the code correctly uses the left values where the left index is valid (not -1) and substitutes with right values only where the left index is -1.

The comment on line 834 is also updated from 'make sure to just use the right values' to 'make sure to just use the right values or vice-versa' to reflect the new symmetric handling.

## Test Coverage

The fix includes comprehensive test coverage in `pandas/tests/reshape/merge/test_multi.py`. A new test method `test_merge_datetime_multi_index_empty_df` is added at line 484, following the existing `test_merge_datetime_index` method.

The test is parametrized with `merge_type` values "left" and "right", ensuring both merge directions are covered. It creates a `left` DataFrame with a datetime MultiIndex (levels 'date' and 'panel') containing two rows of data, and a `right` DataFrame with the same MultiIndex structure but completely empty (no rows).

For a 'left' merge, the expected result is a DataFrame with the original two rows from the left DataFrame, plus a 'state' column filled with None values, preserving the datetime MultiIndex. The test verifies both `left.merge(right, how='left')` and `left.join(right, how='left')` operations produce this expected result.

For a 'right' merge, the expected result similarly contains the original data but with columns reordered (state first, then data), and the test verifies `right.merge(left, how='right')` and `right.join(left, how='right')` operations.

The test uses `Timestamp('1950-01-01')` and `Timestamp('1950-01-02')` for the datetime index values, and explicitly references issue #36895 in the test comment. All assertions use `tm.assert_frame_equal` to ensure exact equality of the result DataFrames with the expected ones.

## Fix Completeness Assessment

The fix appears to be complete for the reported regression. By adding symmetric handling for both `mask_left.all()` and `mask_right.all()`, the code now correctly handles cases where either the left or right DataFrame is empty during a merge operation. The existing `else` branch handles the general case where neither side is entirely missing.

The test coverage specifically verifies left and right merges with empty DataFrames, which are the merge types most likely to trigger this bug. Inner and outer merges would also be affected, but they are implicitly covered by the logic change since the same code path is executed regardless of merge type.

A potential edge case not explicitly tested is merging with an empty DataFrame that has a regular (non-datetime) index. However, the fix in `_maybe_add_join_keys` is generic and operates on indexers rather than index types, so it should work for any index type. The datetime index in the test case is likely chosen because it was the specific scenario reported in issue #36895.

The whatsnew entry in `doc/source/whatsnew/v1.2.0.rst` is updated correctly at line 536, adding the entry 'Fixed regression in merge on merging DatetimeIndex with empty DataFrame (:issue:`36895`)' under the Reshaping section. This ensures users are informed of the fix in the v1.2.0 release.

Overall, the fix is low-risk. The changes are minimal and localized to the specific logic error. The addition of proper test coverage ensures the regression will not recur. The symmetric handling of left and right indexers makes the code more robust and should prevent similar issues in the future.
