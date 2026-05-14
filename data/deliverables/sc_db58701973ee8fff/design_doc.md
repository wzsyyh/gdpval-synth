# Design Doc - Polars Output Support for set_output API

# Design Doc - Polars Output Support for set_output API

## Overview

This design document outlines the architecture for adding Polars DataFrame output support to scikit-learn's `set_output` API. The feature, implemented in PR #27315 by Thomas Fan, enables all transformers to output Polars DataFrames by setting `set_output(transform="polars")`. This addresses user demand for better Polars integration, as tracked in issues #25896 and #26835, and builds upon prior work in PRs #26683 and #27258. The implementation abstracts DataFrame-specific logic into a `ContainerAdapaterProtocol`, making the system extensible for future container types like Xarray.

## Goals and Non-Goals

Primary Goals:
- Support `set_output(transform="polars")` both globally via `set_config` and per-transformer.
- Implement a `ContainerAdapaterProtocol` to abstract DataFrame-specific operations, enabling future extensions.
- Ensure backward compatibility for existing `set_output` configurations.

Non-Goals:
- Optimizing for zero-copy conversion between `ndarray` and `pl.DataFrame`. Unlike Pandas, Polars does not support a zero-round-trip between NumPy arrays and DataFrames, leading to memory copies in pipelines. This is an inherent limitation of the Polars library and will not be addressed in this PR.
- Adding support for other containers like Xarray within this PR. The `ContainerAdapaterProtocol` is designed to be generic enough for future extensions, but Xarray support will require a separate implementation.

## Detailed Design

The core of the design is the `ContainerAdapaterProtocol`, which defines a generic interface for converting transformer outputs to DataFrame-like containers. This protocol abstracts away the specifics of Pandas and Polars, allowing the `set_output` logic to remain container-agnostic. A new Polars-specific class will implement this protocol to handle conversion from `ndarray` to `pl.DataFrame` and vice versa.

Configuration changes are required in `sklearn/_config.py` to add the "polars" option to `set_config` and `config_context`. The documentation for these functions will be updated to include the new option, with version notes for scikit-learn 1.4. The dependency for Polars will be updated from version 0.18.2 to 0.19.12 in `sklearn/_min_dependencies.py` to ensure compatibility.

The `sklearn/compose/_column_transformer.py` will be modified to remove the direct import of `check_pandas_support` and instead use the new protocol. This change simplifies the code and aligns with the abstraction goal. However, due to Polars' lack of zero-copy conversion between `ndarray` and `pl.DataFrame`, memory copies will occur during pipeline transformations. This is an accepted trade-off for the added functionality.

## Impact on Existing API

The changes are fully backward compatible. The existing `set_output` options, including "default" and "pandas", remain unchanged. The addition of "polars" is purely additive. The `set_config` and `config_context` functions in `sklearn/_config.py` will have updated docstrings to document the new "polars" option, but their signatures and core behavior are preserved. Users can switch between output formats without breaking existing code.

## Testing Strategy

Testing will involve unit tests for the `ContainerAdapaterProtocol` implementation to ensure correct conversion between `ndarray` and `pl.DataFrame`. Integration tests will verify that pipelines with transformers set to `set_output(transform="polars")` function correctly, producing expected outputs. Special attention will be paid to memory behavior: tests will confirm that memory copies occur as expected due to Polars' limitations, but that performance remains acceptable. Regression tests will ensure that existing configurations ("default", "pandas") are unaffected and that the new option works seamlessly in all supported contexts.

## References

- Primary PR: #27315 ("ENH Adds polars output support to `set_output` API") by Thomas Fan.
- Related Issues: #25896, #26835.
- Related PRs: #26683, #27258.
- Files Modified: `doc/whats_new/v1.4.rst`, `sklearn/_config.py`, `sklearn/_min_dependencies.py`, `sklearn/compose/_column_transformer.py`.
