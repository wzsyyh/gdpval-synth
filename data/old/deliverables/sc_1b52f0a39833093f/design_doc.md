# Design Document: pandas.col

## Problem Statement

A primary motivation for introducing `pandas.col` is to address a common and subtle scoping pitfall when using lambda functions with `DataFrame.assign`. When constructing dynamic column assignments using dictionary unpacking, the lambda captures the variable name, not its current value, leading to incorrect results.

Consider the following example from the PR description. The intent is to add 10 to each of columns 'a' and 'b'. Using a lambda within a dictionary comprehension results in all columns being assigned the same final value because the lambda closure captures the loop variable `col` by reference, which evaluates to its last value ('b') when the lambdas are finally executed.

```python
df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})
df.assign(**{col: lambda df: df[col] + 10 for col in ('a', 'b')})
```

The output of this lambda-based approach is:

```python
    a   b
0  14  14
1  15  15
2  16  16
```

In contrast, using `pd.col` avoids this scoping issue entirely. The expression `pd.col(col) + 10` is evaluated with the correct column name at the time of definition, not at the time of execution, yielding the intended result:

```python
df.assign(**{col: pd.col(col) + 10 for col in ('a', 'b')})
```

This produces the correct output:

```python
    a   b
0  11  14
1  12  15
2  13  16
```

## Design Principles

The design of `pandas.col` is guided by several principles intended to improve usability and align pandas with modern data manipulation paradigms.

First, expressions are introspectable. Unlike an anonymous lambda function, whose representation is typically an uninformative string like `<function __main__.<lambda>(df)`, the repr of a `pd.col` expression is human-readable and informative. For example, `pd.col('value') * pd.col('weight')` displays as `(col('value') * col('weight'))`, making debugging and logging more straightforward.

Second, the syntax aligns pandas with other modern data tools. As noted in the PR, the `col` name and functional style is used by PySpark, Polars, Daft, and Datafusion. This consistency lowers the cognitive load for users who work across multiple dataframe libraries.

Third, the API avoids common scoping pitfalls inherent in the lambda-based approach, as detailed in the Problem Statement. This makes dynamic column assignment safer and more predictable.

Finally, the syntax is considered more modern and readable. The chained method calls and operator overloads provide a fluent, expressive interface that can make complex transformations easier to follow.

## API Surface

The new API consists of a single top-level function, `col`, and an underlying `Expression` class that represents the constructed computation graph.

The function `col` is exposed at the top level of the pandas namespace as `pd.col`. It is defined in `pandas.core.col` and imported into `pandas/__init__.py` to be accessible as `pd.col`. The diff shows the addition `from pandas.core.col import col` in the init file and the inclusion of `"col"` in the module's `__all__` list.

The `Expression` class itself is also importable. It is added to `pandas/api/typing/__init__.py` via the import `from pandas.core.col import Expression`. This makes the type available for advanced use cases and type checking.

The primary interface is the `col` function. When called with a column name string, it returns an `Expression` object. This object supports standard Series methods (e.g., `.abs()`, `.mean()`), namespace accessors (e.g., `.dt`, `.str`), and arithmetic operations (`+`, `-`, `*`, `/`), which themselves return new `Expression` objects, allowing for the construction of complex, deferred computation expressions.

## Usage Examples

The PR provides comprehensive examples demonstrating the usage of `pd.col` in various contexts.

A primary use case is within `DataFrame.assign`. The following code creates a DataFrame with columns 'a', 'b', 'c' (datetime), and 'd' (string), then uses `pd.col` to define new columns via standard Series methods and operations:

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
    a_abs=pd.col("a").abs(),
    a_centered=pd.col("a") - pd.col("a").mean(),
    a_plus_b=pd.col("a") + pd.col("b"),
    c_year=pd.col("c").dt.year,
    c_month_name=pd.col("c").dt.strftime("%B"),
    d_upper=pd.col("d").str.upper(),
).loc[pd.col("a_abs") > 1]

print(result)
```

The resulting DataFrame is filtered to rows where `a_abs > 1` and includes all the calculated columns.

NumPy universal functions (ufuncs) are also supported. For example, applying the natural logarithm to column 'a' can be done as follows, with the output showing the log values for the absolute values of the original data:

```python
df.assign(a_log = np.log(pd.col('a')))
```

The expressions themselves have a readable representation. The PR demonstrates the following pretty-printing behavior:

```python
pd.col('value')  # col('value')
pd.col('value') * pd.col('weight')  # (col('value') * col('weight'))
(pd.col('value') - pd.col('value').mean()) / pd.col('value').std()  # ((col('value') - col('value').mean()) / col('value').std())
pd.col('timestamp').dt.strftime('%B')  # col('timestamp').dt.strftime('%B')
```

## Integration & Documentation

The feature is integrated into the pandas documentation across several key files, as shown in the diff.

The top-level API reference is updated. In `doc/source/reference/general_functions.rst`, the function `col` is added to the "Top-level evaluation" autosummary section, placing it alongside `eval`.

The user guide is updated with a practical example. In `doc/source/user_guide/dsintro.rst`, a new code block is added demonstrating the use of `pd.col` within `.assign()` to calculate a sepal ratio for the iris dataset, providing an alternative to the lambda-based example.

The release notes for pandas 3.0.0 are updated. In `doc/source/whatsnew/v3.0.0.rst`, the placeholder section titled "Enhancement2" (with anchor `_whatsnew_300.enhancements.enhancement2`) is replaced with a new section. The new section has the anchor `whatsnew_300.enhancements.col` and is titled with the new `pd.col` syntax functionality. It explains the feature and includes an example of summing columns 'a' and 'b' using `pd.col`.

No changes to the core library's API or typing stubs are needed beyond the initial imports, as the type hints for the `Expression` class are noted as a follow-up for `pandas-stubs`.

## Future Work

The PR description outlines two potential areas for future work.

First, the author notes a potential follow-up: "serialise / deserialise expressions." This would allow `pd.col` expressions to be saved and reconstructed, which could be useful for persisting complex transformation pipelines or for sending them across processes.

Second, it is suggested that tooling could be developed to automate the generation of documentation and type stubs for the `Expr` (Expression) class based on the existing documentation for `Series` methods. This would help keep the expression API's documentation and type information in sync with the underlying Series methods it delegates to, reducing maintenance burden.
