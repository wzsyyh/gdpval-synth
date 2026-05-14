**Repository:** pandas-dev/pandas

**PR:** #62103

## Diff Excerpt

```diff
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
```
