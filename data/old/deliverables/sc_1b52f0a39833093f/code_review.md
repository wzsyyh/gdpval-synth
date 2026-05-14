# Code Review: pandas-dev/pandas#62103 - ENH: Introduce `pandas.col`

## Summary and Recommendation

This pull request introduces `pandas.col`, a new top-level function for creating column expressions that can be used in DataFrame methods such as `assign` and `loc`. The change is motivated by providing a more modern, introspectable, and less error-prone alternative to lambda functions for column operations. After review, I recommend approval. The implementation aligns with pandas conventions and addresses common user pitfalls, though some documentation and future considerations should be noted.

## Design and API Consistency

The choice of the name `col` follows the conventions of PySpark, Polars, Daft, and Datafusion, as noted in the PR description. This alignment with modern data tools is a strong design decision and promotes consistency across the ecosystem. The function is imported from `pandas.core.col` and exposed as `pd.col`, fitting the pattern of other pandas top-level functions. The PR also introduces an `Expression` class, exposed via `pandas.api.typing`, which supports introspection and pretty-printing of expressions, enhancing debuggability over anonymous lambdas.

## Documentation and User Guide

The documentation updates are appropriate. The `col` function is added to the top-level evaluation section in `reference/general_functions.rst`. The user guide (`dsintro.rst`) now includes an example using `pd.col` with the iris dataset to show a `sepal_ratio` calculation, providing a clear alternative to the lambda syntax. The what's-new entry in `v3.0.0.rst` introduces the enhancement with a simple example comparing the old lambda approach to the new `pd.col` syntax for summing columns. This provides a useful migration path for users.

## Implementation and Code Changes

The core implementation is in `pandas/core/col.py`, which defines the `col` function and the `Expression` class. The `col` function is imported into the main `pandas` namespace via `pandas/__init__.py`. The PR demonstrates support for Series methods (e.g., `.abs()`), namespace access (`.dt.year`, `.str.upper()`), and NumPy ufuncs (e.g., `np.log(pd.col('a'))`). The pretty-printing of expressions, such as `col('value')` and `(col('value') * col('weight'))`, improves readability. The diff shows 9 changed files with +423 additions and -3 deletions, indicating a focused but substantial addition.

## Motivation and Problem Solving

The PR effectively addresses common scoping issues with lambda functions in `assign`. For example, using `df.assign(**{col: lambda df: df[col] + 10 for col in ('a', 'b')})` produces incorrect results due to late binding, while `df.assign(**{col: pd.col(col) + 10 for col in ('a', 'b')})` works as expected. The `pd.col` syntax is more explicit and avoids this pitfall. Additionally, expressions are introspectable, meaning their repr is human-readable, unlike opaque lambda functions. This enhances debugging and code clarity.

## Potential Follow-ups and Future Work

The PR author mentions that for type hints to show up correctly, extra work is needed in `pandas-stubs`. This is noted as a potential follow-up. Additionally, the author suggests developing tooling to automate `Expression` documentation and types based on `Series` ones, which would reduce maintenance burden. A longer-term follow-up could involve serializing and deserializing expressions, though this is not yet implemented. These follow-ups are reasonable and should be tracked separately.

## Conclusion

Overall, PR #62103 introduces a valuable enhancement to pandas that aligns with modern data tool conventions, solves practical user issues, and includes solid documentation. The implementation is clean and focused. I recommend merging this PR. Future work should address the type stubs and consider automation for documentation to keep the new API well-maintained.
