# Bug Fix Write-Up: PR #36897 – Regression Fix for Merging DataFrame with DatetimeIndex with Empty DataFrame

## Summary

This document describes the bug fix implemented in PR #36897, which addresses a regression reported in issue #36895. The regression occurs when attempting to merge a DataFrame that has a DatetimeIndex against an empty DataFrame. The operation raises a KeyError instead of completing successfully. This bug was introduced during the 1.1 development cycle and affects users who rely on merging indexed DataFrames with potentially empty counterparts. The fix is targeted for the pandas v1.2.0 release.

## Root Cause

The root cause is in the `_maybe_add_join_keys` method of the merge operation, located in `pandas/core/reshape/merge.py` around line 830. This method is responsible for constructing the key columns in the merged result when the merge is performed on columns derived from the index. The original code contained an asymmetric check: it computed a mask for the left_indexer where entries equal -1 (indicating no match) and tested if the mask was entirely true. If so, it used the right-side values exclusively. However, it did not perform the analogous check for the right_indexer. When the right DataFrame was empty, the right_indexer was entirely -1, but the code fell through to the else branch, attempting to use `Index(lvals).where(~mask, rvals)`. This operation failed because `rvals` contained invalid placeholder values, leading to the KeyError.

The asymmetry meant that merging a non-empty left DataFrame with an empty right DataFrame (where all right_indexer values are -1) was not handled correctly, while the reverse case (empty left, non-empty right) was handled by the `mask.all()` check. This oversight caused the regression when the DatetimeIndex merge path was used.

## Fix Description

The fix in PR #36897 consists of three coordinated changes within the `_maybe_add_join_keys` method:

1. **Variable Renaming**: The original `mask` variable, which checked `left_indexer == -1`, was renamed to `mask_left` for clarity. A new variable `mask_right` was introduced to check `right_indexer == -1`. This makes the intent explicit: we are masking out unmatched entries on each side.

2. **Symmetrical Handling**: An `elif` branch was added: `elif mask_right.all(): key_col = lvals`. This ensures that when all entries in the right_indexer are -1 (i.e., the right DataFrame is empty or has no matches), the result key column is populated entirely with the left-side values (`lvals`). This mirrors the existing `if mask_left.all()` branch that uses the right-side values.

3. **Corrected Where Clause**: The final `where` call was updated from `Index(lvals).where(~mask, rvals)` to `Index(lvals).where(~mask_left, rvals)`. This ensures that only entries unmatched on the left are replaced with right-side values, which is the correct behavior for the mixed case where neither side is entirely unmatched.

Together, these changes ensure that merging a DataFrame with a DatetimeIndex against an empty DataFrame completes without error and produces the correct result. The fix is minimal and targeted, affecting only the key column assembly logic.

## Test Added

A new test case was added to `pandas/tests/reshape/merge/test_multi.py` to verify the fix. The test file's imports were updated to include `Timestamp` from pandas (i.e., `from pandas import DataFrame, Index, MultiIndex, Series, Timestamp`). The test, defined as a method within the existing test class, creates a DataFrame with a DatetimeIndex and merges it with an empty DataFrame. The test verifies that the merge operation completes without raising a KeyError and that the result matches the expected output. This test directly reproduces the scenario from issue #36895, ensuring the regression is fixed and does not recur.

## Whatsnew Entry

The fix is documented in the pandas v1.2.0 release notes. In `doc/source/whatsnew/v1.2.0.rst`, under the Reshaping section, the following entry was added: "Fixed regression in :func:`merge` on merging DatetimeIndex with empty DataFrame (:issue:`36895`)". This entry ensures users are aware of the regression fix and can locate the relevant issue for more details.

## Checklist Verification

The PR description includes a checklist confirming that all standard quality gates were met: tests were added and passed, the code passes `black pandas` formatting, the diff passes `flake8 --diff` linting, and a whatsnew entry was included. All items are checked off, indicating the PR is ready for merge pending review. This checklist verifies that the fix adheres to the pandas project's contribution standards.
