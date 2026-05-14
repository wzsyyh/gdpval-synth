# Design Document: Adding Polars Output Support to the set_output API (PR #27315)

## Motivation

This change is motivated by the need to extend the `set_output` API to support the Polars dataframe library, a growing alternative to pandas in the Python data ecosystem. The PR is directly related to several existing community discussions: https://github.com/scikit-learn/scikit-learn/issues/25896, https://github.com/scikit-learn/scikit-learn/pull/26683, https://github.com/scikit-learn/scikit-learn/pull/27258, and https://github.com/scikit-learn/scikit-learn/issues/26835.

The goal is to allow users to seamlessly use Polars DataFrames as the output of scikit-learn transformers, similar to how `set_output(transform="pandas")` works for pandas DataFrames. This makes scikit-learn more interoperable with the broader data tooling ecosystem.

## Proposed Design

The core of the design abstracts the dataframe-specific API requirements into a `ContainerAdapterProtocol`. This protocol defines a generic interface for converting to and from numpy ndarrays and for managing column names and dtypes.

Implementing support for Polars involves creating a concrete class that adheres to this protocol. The design notes that, in principle, support for other containers like Xarray would require only another class implementing the same `ContainerAdapterProtocol`, and everything else should "just work". This makes the architecture extensible for future dataframe-like libraries.

## Implementation Details

The primary user-facing change is the addition of a new "polars" option to the `set_output` API. Users will be able to configure this globally via `sklearn.set_config(transform_output="polars")` or per-estimator using `estimator.set_output(transform="polars")`. The documentation for `set_config` and `config_context` in `sklearn/_config.py` is updated to reflect this, with a `versionadded:: 1.4` note for the "polars" option.

A key technical consideration is noted in the PR description: polars does not have a "zero round trip" between numpy ndarrays and `pl.DataFrame`. For transformers in a pipeline, wrapping and unwrapping a polars dataframe will result in memory copies. This is different from pandas, which uses a block manager for 2d ndarrays to avoid such copies.

The implementation involves changes across multiple files, including updates to `sklearn/compose/_column_transformer.py` and other core modules. The minimum dependency version for polars for testing is also updated from 0.18.2 to 0.19.12 in `sklearn/_min_dependencies.py`.

## Scope and Impact

This change impacts all transformer modules, as the `set_output` API is a cross-cutting concern. The PR notes that merging related PRs #27258 or #26683 would make this change smaller, as this PR uses code from those.

The changes are documented as a major feature in the `doc/whats_new/v1.4.rst` file under "Changes impacting all modules", indicating this is intended for inclusion in scikit-learn version 1.4.

The test suite's minimum polars dependency is raised to version 0.19.12, ensuring compatibility with the features used in the implementation. The core pandas support remains unchanged, but the new option provides a supported path for users preferring Polars.
