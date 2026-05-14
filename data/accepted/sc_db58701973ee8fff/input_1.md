# Diff of the first 3000 characters showing changes to doc/whats_new/v1


# Seed Material: scikit-learn/scikit-learn#27315: ENH Adds polars output support to `set_output` API
Source: github_issue_pr
Identifier: pr:scikit-learn/scikit-learn#27315

Repository: scikit-learn/scikit-learn
PR Number: #27315
PR Title: ENH Adds polars output support to `set_output` API
Merged At: 2023-11-19T21:46:56Z
Changed Files: 20
Additions: +712, Deletions: -250

## PR Description
<!--
Thanks for contributing a pull request! Please ensure you have taken a look at
the contribution guidelines: https://github.com/scikit-learn/scikit-learn/blob/main/CONTRIBUTING.md
-->

#### Reference Issues/PRs
<!--
Example: Fixes #1234. See also #3456.
Please use keywords (e.g., Fixes) to create link to the issues or pull requests
you resolved, so that they will automatically be closed when your pull request
is merged. See https://github.com/blog/1506-closing-issues-via-pull-requests
-->
Related to https://github.com/scikit-learn/scikit-learn/issues/25896
Related to https://github.com/scikit-learn/scikit-learn/pull/26683
Related to https://github.com/scikit-learn/scikit-learn/pull/27258
Related to https://github.com/scikit-learn/scikit-learn/issues/26835

#### What does this implement/fix? Explain your changes.
This PR adds `set_output="polars"` to all transformers. Overall this PR abstracts the dataframe specific API requirements to `set_output` into a `ContainerAdapaterProtocol`. `ContainerAdapaterProtocol` is generic enough to support other containers. In principle, `Xarray` support will only require another class that implements the `ContainerAdapaterProtocol` and everything else should "just work".

Note that polars does not have a "zero round trip" between `ndarrays` and `pl.DataFrame`. For transformers in a pipeline, wrapping and unwrapping a polars dataframe will result in memory copies. Pandas dataframes does not have this issue because it uses block manager for 2d ndarrays.

#### Any other comments?
Merging https://github.com/scikit-learn/scikit-learn/pull/27258 or https://github.com/scikit-learn/scikit-learn/pull/26683 will make this PR smaller. This PR uses code from those two PRs.

<!--
Please be aware that we are a loose team of volunteers so patience is
necessary; assistance handling other issues is very welcome. We value
all user contributions, no matter how minor they are. If we are slow to
review, either the pull request needs some benchmarking, tinkering,
convincing, etc. or more likely the reviewers are simply busy. In either
case, we ask for your understanding during the review process.
For more information, see our FAQ on this topic:
http://scikit-learn.org/dev/faq.html#why-is-my-pull-request-not-getting-any-attention.

Thanks for contributing!
-->


## Linked Issue #1234
This should clean up the stuff I pushed earlier.
cc @ogrisel @gaelvaroquaux Could you have a brief look? What I pushed earlier is buggy but I didn't dare push again after so many failed fixes.


## Diff (first 3000 chars)
diff --git a/doc/whats_new/v1.4.rst b/doc/whats_new/v1.4.rst
index 507b22cdf510a..f3f40fd26e27a 100644
--- a/doc/whats_new/v1.4.rst
+++ b/doc/whats_new/v1.4.rst
@@ -41,6 +41,9 @@ random sampling procedures.
 Changes impacting all modules
 -----------------------------
 
+- |MajorFeature| Transformers now support polars output with `set_output(transform="polars")`.
+  :pr:`27315` by `Thomas Fan`_.
+
 - |Enhancement| All estimators now recognizes the column names from any dataframe
   that adopts the
   `DataFrame Interchange Protocol <https://data-apis.org/dataframe-protocol/latest/purpose_and_scope.html>`__.
diff --git a/sklearn/_config.py b/sklearn/_config.py
index 91d149c81dc59..8c0b83d1bfaa8 100644
--- a/sklearn/_config.py
+++ b/sklearn/_config.py
@@ -134,9 +134,12 @@ def set_config(
 
         - `"default"`: Default output format of a transformer
         - `"pandas"`: DataFrame output
+        - `"polars"`: Polars output
         - `None`: Transform configuration is unchanged
 
         .. versionadded:: 1.2
+        .. versionadded:: 1.4
+            `"polars"` option was added.
 
     enable_metadata_routing : bool, default=None
         Enable metadata routing. By default this feature is disabled.
@@ -281,9 +284,12 @@ def config_context(
 
         - `"default"`: Default output format of a transformer
         - `"pandas"`: DataFrame output
+        - `"polars"`: Polars output
         - `None`: Transform configuration is unchanged
 
         .. versionadded:: 1.2
+        .. versionadded:: 1.4
+            `"polars"` option was added.
 
     enable_metadata_routing : bool, default=None
         Enable metadata routing. By default this feature is disabled.
diff --git a/sklearn/_min_dependencies.py b/sklearn/_min_dependencies.py
index f91ca6594e987..d875f63fb9b75 100644
--- a/sklearn/_min_dependencies.py
+++ b/sklearn/_min_dependencies.py
@@ -40,7 +40,7 @@
     "black": ("23.3.0", "tests"),
     "mypy": ("1.3", "tests"),
     "pyamg": ("4.0.0", "tests"),
-    "polars": ("0.18.2", "tests"),
+    "polars": ("0.19.12", "tests"),
     "pyarrow": ("12.0.0", "tests"),
     "sphinx": ("6.0.0", "docs"),
     "sphinx-copybutton": ("0.5.2", "docs"),
diff --git a/sklearn/compose/_column_transformer.py b/sklearn/compose/_column_transformer.py
index 394b5baf50769..efcd7acb22fa0 100644
--- a/sklearn/compose/_column_transformer.py
+++ b/sklearn/compose/_column_transformer.py
@@ -3,6 +3,7 @@
 to work with heterogeneous data and to apply different transformers to
 different columns.
 """
+
 # Author: Andreas Mueller
 #         Joris Van den Bossche
 # License: BSD
@@ -16,11 +17,15 @@
 from ..base import TransformerMixin, _fit_context, clone
 from ..pipeline import _fit_transform_one, _name_estimators, _transform_one
 from ..preprocessing import FunctionTransformer
-from ..utils import Bunch, _get_column_indices, _safe_indexing, check_pandas_support
+from ..utils import Bunch, _get_column_indices, _safe_indexing
 from ..utils._estimator_html_repr import _Vi