# Design Document: Introduction of `pandas.col` API

## Executive Summary

The `pandas.col` (or `pd.col`) function is a new top-level API introduced in pandas v3.0.0 that enables a more expressive and safe way to build column expressions. It returns an `Expression` object that can be used directly in `DataFrame.assign` and `DataFrame.loc`, replacing the need for lambda functions. The primary motivation is to eliminate common scoping bugs that arise when using lambda functions in dictionary comprehensions with `assign`, providing a syntax that is both introspectable and aligned with modern data frameworks like PySpark and Polars.

## Motivation and Problem Statement

A key motivation for introducing `pd.col` is to avoid a common and subtle scoping issue when using lambda functions with `DataFrame.assign`. The problem arises when attempting to create multiple new columns using a dictionary comprehension with lambdas.

The following code, intended to increment both columns 'a' and 'b' by 10, does not work as expected due to Python's late-binding closures. The lambda captures the variable `col` by reference, so by the time the lambdas execute, the loop has finished and `col` retains its last value ('b'), causing both new columns to be computed using column 'b'.

```python
df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})
df.assign(**{col: lambda df: df[col] + 10 for col in ('a', 'b')})
```

The output incorrectly shows both columns derived from 'b':

```python
    a   b
0  14  14
1  15  15
2  16  16
```

Using `pd.col` resolves this issue by creating a distinct expression object for each column name at the time of definition, eliminating the late-binding closure problem.

```python
df.assign(**{col: pd.col(col) + 10 for col in ('a', 'b')})
```

This produces the correct result:

```python
    a   b
0  11  14
1  12  15
2  13  16
```

The name `col` was chosen to follow the established convention used by other major data frameworks: PySpark, Polars, Daft, and Datafusion. This alignment helps users familiar with those ecosystems adopt the new pandas API more easily.

## API Specification

The `pd.col` function is a top-level function added to the pandas namespace. Its signature is `col(*args)`, where `args` are passed to the underlying `Expression` constructor. It returns an `Expression` object.

The `Expression` class supports a wide range of operations, allowing for the construction of complex column transformations:

- **Arithmetic Operations**: Standard arithmetic operators (`+`, `-`, `*`, `/`) are supported between two expressions or between an expression and a scalar. For example, `pd.col('a') + pd.col('b')` or `pd.col('a') - pd.col('a').mean()`.

- **Unary Methods**: Common Series methods like `.abs()` can be called directly on the expression, as in `pd.col('a').abs()`.

- **Namespace Accessors**: The `.dt` and `.str` accessors are available. Examples include `pd.col('c').dt.year`, `pd.col('c').dt.strftime('%B')`, and `pd.col('d').str.upper()`.

- **NumPy Ufunc Compatibility**: NumPy universal functions (ufuncs) can be applied to expressions. For instance, `np.log(pd.col('a'))`.

Expressions are introspectable and have a human-readable repr that mimics their construction. This improves debuggability compared to anonymous lambda functions.

```python
In [4]: pd.col('value')
Out[4]: col('value')

In [5]: pd.col('value') * pd.col('weight')
Out[5]: (col('value') * col('weight'))

In [6]: (pd.col('value') - pd.col('value').mean()) / pd.col('value').std()
Out[6]: ((col('value') - col('value').mean()) / col('value').std())

In [7]: pd.col('timestamp').dt.strftime('%B')
Out[7]: col('timestamp').dt.strftime('%B')
```

## Implementation Overview

The implementation of the `pd.col` feature involves several key integration points within the pandas codebase:

- **Core Module**: A new module `pandas.core.col` is created, containing the `col` function and the `Expression` class definition.

- **Public API Export**: The `col` function is imported and exported from the top-level `pandas` namespace (`pandas/__init__.py`), making it accessible as `pd.col`.

- **Typing Support**: The `Expression` class is added to the `pandas.api.typing` module (`pandas/api/typing/__init__.py`) to support type-checking and static analysis for downstream libraries and user code.

- **Documentation Updates**: The PR includes updates to several documentation files to introduce and explain the new feature:

  - `doc/source/reference/general_functions.rst`: `col` is added to the "Top-level evaluation" section of the API reference.

  - `doc/source/user_guide/dsintro.rst`: An example using `pd.col` is added to the `assign` section of the user guide, alongside the existing lambda example.

  - `doc/source/whatsnew/v3.0.0.rst`: A new section titled "`pd.col` syntax can now be used in `DataFrame.assign` and `DataFrame.loc`" is added under enhancements, with a brief example and explanation.

## Examples and Use Cases

The following example, taken directly from the PR, demonstrates the core usage of `pd.col` in `assign` to create multiple derived columns, and in `loc` to filter rows based on an expression.

```python
import pandas as pd
from datetime import datetime

df = pd.DataFrame(
    {
        "a": [1, -2, 3],
        "b": [4, 5, 6],
        "c": [datetime(2020, 1, 1), datetime(2025, 4, 2), datetime(2026, 12, 3)],
        "d": ["fox", "beluga", "narwhal"],
    }
)

result = df.assign(
    # The usual Series methods are supported
    a_abs=pd.col("a").abs(),
    # And can be combined
    a_centered=pd.col("a") - pd.col("a").mean(),
    a_plus_b=pd.col("a") + pd.col("b"),
    # Namespace are supported too
    c_year=pd.col("c").dt.year,
    c_month_name=pd.col("c").dt.strftime("%B"),
    d_upper=pd.col("d").str.upper(),
).loc[pd.col("a_abs") > 1]  # This works in `loc` too

print(result)
```

The output of this code is:

```python
   a  b          c        d  a_abs  a_centered  a_plus_b  c_year c_month_name  d_upper
1 -2  5 2025-04-02   beluga      2   -2.666667         3    2025        April   BELUGA
2  3  6 2026-12-03  narwhal      3    2.333333         9    2026     December  NARWHAL
```

This example showcases the use of `.abs()`, arithmetic between columns, `.dt.year`, `.dt.strftime`, and `.str.upper()`, as well as filtering with `.loc`.

## Future Work and Considerations

The PR description notes two key areas for future work:

1.  **Serialization / Deserialization**: A potential follow-up is to develop functionality to serialize and deserialize `Expression` objects. This would allow expressions to be saved, transferred, and reconstructed, enabling more advanced use cases and integrations.

2.  **Type Stub Accuracy**: The initial implementation provides the core functionality, but for type hints to display correctly in IDEs and for static type-checking tools, additional work is required in the external `pandas-stubs` library. The PR suggests that tooling could potentially be developed to automate the generation of `Expression` types and documentation based on the existing `Series` types.

Furthermore, as the feature is new, community feedback and usage patterns will inform potential refinements to the API or additional methods to be supported on the `Expression` class.

## Conclusion

The introduction of `pandas.col` represents a significant enhancement to the pandas API, addressing a long-standing usability issue with column expression construction. By providing a syntax that avoids scoping pitfalls, is introspectable for better debugging, and aligns with modern data frameworks, this feature lowers the barrier for complex DataFrame transformations. Its integration into `assign` and `loc`, coupled with support for core pandas Series operations and NumPy ufuncs, makes it a versatile and powerful tool for data manipulation in pandas v3.0.0 and beyond.
