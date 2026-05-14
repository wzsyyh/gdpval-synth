# PR #62103 description and diff excerpt (provided in material)


# Seed Material: pandas-dev/pandas#62103: ENH: Introduce `pandas.col`
Source: github_issue_pr
Identifier: pr:pandas-dev/pandas#62103

Repository: pandas-dev/pandas
PR Number: #62103
PR Title: ENH: Introduce `pandas.col`
Merged At: 2025-08-22T16:50:55Z
Changed Files: 9
Additions: +423, Deletions: -3

## PR Description
xref @jbrockmendel 's comment https://github.com/pandas-dev/pandas/issues/56499#issuecomment-3180770808 

I'd also discussed this with @phofl , @WillAyd , and @jorisvandenbossche (who originally showed us something like this in Basel at euroscipy 2023)

Demo:
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
Output:
```python
   a  b          c        d  a_abs  a_centered  a_plus_b  c_year c_month_name  d_upper
1 -2  5 2025-04-02   beluga      2   -2.666667         3    2025        April   BELUGA
2  3  6 2026-12-03  narwhal      3    2.333333         9    2026     December  NARWHAL
```

NumPy ufuncs are also supported:
```python
In [6]: df.assign(a_log = np.log(pd.col('a')))
Out[6]: 
   a     a_log
0  1  0.000000
1  2  0.693147
2  3  1.098612
```

Expressions also get pretty-printed, demo:
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

What's here should be enough for it to be usable. For the type hints to show up correctly, extra work should be done in `pandas-stubs`. But, I think it should be possible to develop tooling to automate the `Expr` docs and types based on the `Series` ones (going to cc @Dr-Irv here too then)

As for the "`col`" name, that's what PySpark, Polars,  Daft, and Datafusion use, so I think it'd make sense to follow the convention

---

~~I'm opening as a request for comments. Would people want this API to be part of pandas?~~ This is ready for review

One of my main motivations for introducing it is that it avoids common issues with scoping. For example, if you use `assign` to increment two columns' values by 10 and try to write `df.assign(**{col: lambda df: df[col] + 10 for col in ('a', 'b')})` then you'll be in for a big surprise
```python
In [19]: df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})

In [20]: df.assign(**{col: lambda df: df[col] + 10 for col in ('a', 'b')})
Out[20]:
    a   b
0  14  14
1  15  15
2  16  16
```
whereas with `pd.col`, you get what you were probably expecting:
```python
In [4]: df.assign(**{col: pd.col(col) + 10 for col in ('a', 'b')})
Out[4]: 
    a   b
0  11  14
1  12  15
2  13  16
```

Further advantages:
- expressions are introspectable so the repr can be made to look nice, whereas an anonymous lambda is always going to look something like ` <function __main__.<lambda>(df)`
- the syntax looks more modern and more aligned with modern tools

Expected objections:
- this expands the pandas API even further. Sure, I don't disagree, but I think this is a common enough and longstanding enough request that it's worth expanding it for this

---

TODO:
- [x] tests, API docs, user guide. But first, I just wanted to get a feel for people's thoughts, and to see if anyone's opposed to it

Potential follow-ups (if there's interest):
- serialise / deserialise expressions

## Diff (first 3000 chars)
diff --git a/doc/source/reference/general_functions.rst b/doc/source/reference/general_functions.rst
index e93514de5f762..a76e51ace86d2 100644
--- a/doc/source/reference/general_functions.rst
+++ b/doc/source/reference/general_functions.rst
@@ -71,6 +71,7 @@ Top-level evaluation
 .. autosummary::
    :toctree: api/
 
+   col
    eval
 
 Datetime formats
diff --git a/doc/source/user_guide/dsintro.rst b/doc/source/user_guide/dsintro.rst
index 89981786d60b5..919dafb291b86 100644
--- a/doc/source/user_guide/dsintro.rst
+++ b/doc/source/user_guide/dsintro.rst
@@ -553,6 +553,12 @@ a function of one argument to be evaluated on the DataFrame being assigned to.
 
    iris.assign(sepal_ratio=lambda x: (x["SepalWidth"] / x["SepalLength"])).head()
 
+or, using :meth:`pandas.col`:
+
+.. ipython:: python
+
+   iris.assign(sepal_ratio=pd.col("SepalWidth") / pd.col("SepalLength")).head()
+
 :meth:`~pandas.DataFrame.assign` **always** returns a copy of the data, leaving the original
 DataFrame untouched.
 
diff --git a/doc/source/whatsnew/v3.0.0.rst b/doc/source/whatsnew/v3.0.0.rst
index b94d82f3c9783..372e93b216e26 100644
--- a/doc/source/whatsnew/v3.0.0.rst
+++ b/doc/source/whatsnew/v3.0.0.rst
@@ -117,10 +117,28 @@ process in more detail.
 
     `PDEP-7: Consistent copy/view semantics in pandas with Copy-on-Write <https://pandas.pydata.org/pdeps/0007-copy-on-write.html>`__
 
-.. _whatsnew_300.enhancements.enhancement2:
+.. _whatsnew_300.enhancements.col:
 
-Enhancement2
-^^^^^^^^^^^^
+``pd.col`` syntax can now be used in :meth:`DataFrame.assign` and :meth:`DataFrame.loc`
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+
+You can now use ``pd.col`` to create callables for use in dataframe methods which accept them. For example, if you have a dataframe
+
+.. ipython:: python
+
+    df = pd.DataFrame({'a': [1, 1, 2], 'b': [4, 5, 6]})
+
+and you want to create a new column ``'c'`` by summing ``'a'`` and ``'b'``, then instead of
+
+.. ipython:: python
+
+    df.assign(c = lambda df: df['a'] + df['b'])
+
+you can now write:
+
+.. ipython:: python
+
+    df.assign(c = pd.col('a') + pd.col('b'))
 
 New Deprecation Policy
 ^^^^^^^^^^^^^^^^^^^^^^
diff --git a/pandas/__init__.py b/pandas/__init__.py
index 8b92ad6cdfebb..cc786d1141c48 100644
--- a/pandas/__init__.py
+++ b/pandas/__init__.py
@@ -105,6 +105,7 @@
     Series,
     DataFrame,
 )
+from pandas.core.col import col
 
 from pandas.core.dtypes.dtypes import SparseDtype
 
@@ -281,6 +282,7 @@
     "array",
     "arrays",
     "bdate_range",
+    "col",
     "concat",
     "crosstab",
     "cut",
diff --git a/pandas/api/typing/__init__.py b/pandas/api/typing/__init__.py
index c1178c72f3edc..de6657b58ee80 100644
--- a/pandas/api/typing/__init__.py
+++ b/pandas/api/typing/__init__.py
@@ -6,6 +6,7 @@
 from pandas._libs.lib import NoDefault
 from pandas._libs.missing import NAType
 
+from pandas.core.col import Expression
 from pandas.core.groupby import (
     DataFrameGroupBy,
   