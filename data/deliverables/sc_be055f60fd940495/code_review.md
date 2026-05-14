# Code Review: PR #36897 - Regression Fix for Merging DatetimeIndex with Empty DataFrame

# PR #36897: Regression Fix for Merging DatetimeIndex with Empty DataFrame

This pull request addresses a regression reported in issue #36895 where merging a DataFrame with a DatetimeIndex against an empty DataFrame raised a TypeError. The regression was introduced in the development leading up to pandas v1.2.0. The root cause was insufficient handling in the `_maybe_add_join_keys` method of `pandas/core/reshape/merge.py`, which only considered the case where all left indexer values were -1 (indicating missing matches) but did not account for the symmetric case where all right indexer values were -1. The fix adds a check for `mask_right.all()` to use left values when the right side is empty, and renames the mask variable for clarity.

The fix modifies the merge logic in `pandas/core/reshape/merge.py` and adds a regression test in `pandas/tests/reshape/merge/test_multi.py`. Additionally, a whatsnew entry is included in the 'Reshaping' section of the v1.2.0 release notes (`doc/source/whatsnew/v1.2.0.rst`). The PR was merged on 2020-11-03.

## Code Changes Analysis

### `pandas/core/reshape/merge.py` Changes

The key change is in the `_maybe_add_join_keys` method. The original code (lines 833-842 in the original file context) contained the following logic:

```python
# if we have an all missing left_indexer
# make sure to just use the right values
mask = left_indexer == -1
if mask.all():
    key_col = rvals
else:
    key_col = Index(lvals).where(~mask, rvals)
```

The fix updates this to:

```python
# if we have an all missing left_indexer
# make sure to just use the right values or vice-versa
mask_left = left_indexer == -1
mask_right = right_indexer == -1
if mask_left.all():
    key_col = rvals
elif mask_right.all():
    key_col = lvals
else:
    key_col = Index(lvals).where(~mask_left, rvals)
```

The change adds a symmetric condition: when all right indexer values are -1 (meaning the right DataFrame is empty in the merge), the key column is set to the left values (`lvals`). This prevents the TypeError that occurred when attempting to use right values from an empty DataFrame. The variable rename from `mask` to `mask_left` improves clarity.

### `pandas/tests/reshape/merge/test_multi.py` Changes

The diff shows an addition of a new test function after `test_merge_datetime_index`. Although the exact test name is truncated in the provided diff (it starts with `@pytes` which is likely `@pytest.mark.parametrize`), it is reasonable to infer the test is named something like `test_merge_datetime_index_with_empty` based on the issue. The test uses `DataFrame`, `Timestamp`, and likely constructs a DataFrame with a DatetimeIndex and an empty DataFrame, then performs a merge and asserts the result matches an expected DataFrame using `tm.assert_frame_equal`. This test directly validates the regression fix.

### `doc/source/whatsnew/v1.2.0.rst` Changes

A new entry is added to the 'Reshaping' section under the v1.2.0 release notes. The exact text is:

```
- Fixed regression in :func:`merge` on merging DatetimeIndex with empty DataFrame (:issue:`36895`)
```

This entry is correctly placed under the 'Reshaping' subsection (after the entry for issue #37591) and uses the proper cross-referencing syntax for the `merge` function and the issue number. It clearly communicates the fix to users.

## Testing Assessment

The test added in this PR covers the specific regression scenario where merging a DataFrame with a DatetimeIndex with an empty DataFrame fails. The test uses `tm.assert_frame_equal`, which is the standard pandas testing utility for DataFrame equality checks, ensuring consistency with project standards.

However, the diff only shows one test addition. The fix addresses two symmetric cases: when the left indexer is all -1 (empty left DataFrame) and when the right indexer is all -1 (empty right DataFrame). The test likely covers one of these cases (probably merging a non-empty DataFrame with an empty one). To ensure full coverage, an additional test that merges an empty DataFrame with a non-empty DataFrame (the other symmetric case) would be beneficial. This would verify that both `mask_left.all()` and `mask_right.all()` branches are exercised.

## Code Quality and Standards

The PR description indicates that all checklist items are marked: tests added/passed, `black pandas`, `git diff upstream/master -u -- "*.py" | flake8 --diff`, and whatsnew entry. The changes in the diff appear to follow PEP 8 style (the new code uses consistent indentation and line breaks). The variable rename from `mask` to `mask_left` and the addition of `mask_right` improves readability and aligns with the intent of the code.

One potential edge case not explicitly covered by the test is when both left and right indexers are all -1 (i.e., both DataFrames are empty in a way that yields no matches). The current fix would use `lvals` due to the `elif mask_right.all()` condition (since `mask_left.all()` would be false if both are all -1? Actually, if both are all -1, then `mask_left.all()` is true, so it would use `rvals`. This scenario might not be problematic, but it is worth verifying with a test. Additionally, the fix does not change the behavior when only some indexer values are -1, which is handled by the existing `where` logic.

## Conclusion and Recommendation

Overall, the PR effectively fixes the regression by adding the missing symmetric condition for empty right DataFrames. The code change is minimal, focused, and improves variable naming. The whatsnew entry is correctly formatted and placed. The test covers the primary regression case.

Recommendation: **Approve with minor comments**. The test could be expanded to cover the symmetric case (empty left DataFrame) to ensure full coverage of the new logic branches. However, this is not a blocking issue, as the fix is correct and the existing test validates the reported regression. The PR meets all quality standards and is ready for inclusion in v1.2.0.
