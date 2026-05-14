# Code Review: PR #27315 - ENH Adds polars output support to `set_output` API

# Code Review: PR #27315 - Adds polars output support to `set_output` API

# Code Review: PR #27315 - ENH Adds polars output support to `set_output` API



**Repository:** scikit-learn/scikit-learn

**PR Number:** #27315

**Author:** Thomas Fan

**Merged At:** 2023-11-19T21:46:56Z

**Reviewer:** [Your Name]

**Date:** [Current Date]

## 1. Summary

This PR implements support for the Polars DataFrame library as an output format for all scikit-learn transformers via the `set_output` API. The primary goal is to allow users to configure transformers to output Polars DataFrames instead of the default NumPy arrays or Pandas DataFrames. This enhancement addresses several community requests, as indicated by the linked issues and PRs (#25896, #26683, #27258, #26835).

The PR abstracts the dataframe-specific API requirements into a new `ContainerAdapaterProtocol`. This protocol is designed to be generic enough to support other container types in the future, such as Xarray, with the expectation that support for new containers would only require implementing the protocol. The scope of the change is substantial, with 20 files modified, 712 additions, and 250 deletions, touching core configuration, documentation, and composition modules.

## 2. Design & Architecture

The introduction of the `ContainerAdapaterProtocol` is a significant architectural improvement. By defining a clear interface for dataframe-like containers, the PR decouples the core `set_output` logic from the specific implementations for Pandas or Polars. This promotes the open-closed principle: the system is open for extension (new containers) but closed for modification (the core protocol). The design anticipates future needs, as the author explicitly notes that "In principle, `Xarray` support will only require another class that implements the `ContainerAdapaterProtocol` and everything else should 'just work'." This forward-thinking approach should reduce the maintenance burden for adding new dataframe libraries.

However, a key design consideration highlighted in the PR description is the performance implication for Polars. Unlike Pandas, which can share memory with NumPy arrays via its block manager, Polars does not have a "zero round trip" between `ndarray` and `pl.DataFrame`. This means that in a pipeline, each transformer step will incur memory copies when wrapping and unwrapping Polars DataFrames. While this is a known limitation of the Polars library itself, the review should assess whether the documentation and implementation adequately warn users about this potential performance hit for long pipelines. The architecture does not mitigate this, which is acceptable, but user guidance is critical.

## 3. Implementation Details

The diff provides a snapshot of several key changes. In `doc/whats_new/v1.4.rst`, a new `|MajorFeature|` entry is added under "Changes impacting all modules," correctly crediting Thomas Fan via `:pr:`27315`. This follows the project's changelog conventions. The entry clearly states the feature: "Transformers now support polars output with `set_output(transform="polars")`."

In `sklearn/_config.py`, the `set_config` and `config_context` functions are updated to document the new `"polars"` option for the `transform` parameter. The docstrings now include `"polars": Polars output` and the `versionadded:: 1.4` directive. This is necessary for API documentation and helps users discover the feature. The change in `sklearn/_min_dependencies.py` bumps the minimum required version of the `polars` test dependency from `0.18.2` to `0.19.12`. This suggests the implementation relies on features or fixes present in the newer version. Finally, in `sklearn/compose/_column_transformer.py`, the import of `check_pandas_support` is removed, replaced by imports of `Bunch`, `_get_column_indices`, and `_safe_indexing`. This indicates the column transformer is being refactored to handle the new protocol, likely moving away from direct Pandas-specific logic.

## 4. Documentation & Changelog

The changelog entry in `v1.4.rst` is concise and follows the standard format. It is placed correctly under the "Changes impacting all modules" section, which is appropriate for a feature that affects the entire transformer API. The entry includes the PR number and author, which is good practice for attribution.

The docstring updates in `sklearn/_config.py` are thorough, adding the new option and a `versionadded` note. However, the review should verify that similar updates are made to the `set_output` method docstrings on the transformer classes themselves (e.g., in `TransformerMixin`). Since the full diff is not provided, this is a point to check in the complete PR. The documentation should also include a dedicated section or example in the user guide explaining how to use `set_output(transform="polars")` and discussing the memory copy implications noted in the PR description.

## 5. Backward Compatibility & Impact

The PR is designed to be fully backward compatible. The default output format for transformers remains unchanged (NumPy arrays), so existing code will not break. Users must explicitly opt-in by calling `set_output(transform="polars")`. The addition of the feature is purely additive.

The main impact on users is the potential performance consideration when using Polars in multi-step pipelines. As noted, each transformation will involve data copies, which could slow down pipelines compared to using Pandas. This is an inherent characteristic of Polars and not a flaw in the PR, but it must be clearly communicated. The bump of the minimum polars test dependency to `0.19.12` is a minor change that affects developers running the test suite, not end-users. It should be ensured that this version is widely available in common package managers.

## 6. Questions & Concerns

1. **Protocol Implementation:** Can you provide more detail on the `ContainerAdapaterProtocol`? What specific methods does it define, and how does it ensure consistency between Pandas and Polars implementations? Are there any known edge cases in type coercion or missing value handling?

2. **Testing:** The diff shows a dependency version bump. Have the test suites been updated to cover the new Polars output path, including edge cases like pipelines with mixed output types and transformers that modify the number of rows? What is the test coverage report for the new code?

3. **Documentation:** Beyond the changelog and config docstrings, where is the user-facing documentation for this feature? Is there a planned update to the "Transforming output in a Pipeline" section of the user guide to include Polars examples and warn about the memory copy issue?

4. **Performance:** For a long pipeline (e.g., 10+ steps), what is the estimated performance overhead of the Polars wrapping/unwrapping versus Pandas? Are there any benchmarks or guidelines to help users decide when to use Polars output versus converting to Pandas once at the end?

5. **Extensibility:** How was the protocol tested for extensibility? Is there a proof-of-concept or test that implements the protocol for a mock container (e.g., Xarray) to validate the "just work" claim?

## 7. Recommendation

**Recommendation: Approve with minor revisions.**

The PR introduces a valuable feature with a clean, extensible design. The implementation in the shown diff appears correct and follows project conventions. The memory copy caveat is inherent to Polars and is properly disclosed. However, before merging, I recommend addressing the following:

- **Action 1:** Ensure comprehensive user documentation is in place, including a user guide example and a clear note about performance implications for pipelines.

- **Action 2:** Confirm that the test suite has been extended to thoroughly cover the Polars output path, especially in multi-step pipelines and with various transformer types.

- **Action 3:** Verify that the `ContainerAdapaterProtocol` is well-documented within the codebase for future contributors.

Once these documentation and testing points are confirmed, the PR is ready for merge. It is a significant step forward in supporting the growing ecosystem of DataFrame libraries.
