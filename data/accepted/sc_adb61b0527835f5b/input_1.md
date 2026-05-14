# PR description from scikit-learn/scikit-learn#9978


# Seed Material: scikit-learn/scikit-learn#9978: [MRG] Add quantile regression
Source: github_issue_pr
Identifier: pr:scikit-learn/scikit-learn#9978

Repository: scikit-learn/scikit-learn
PR Number: #9978
PR Title: [MRG] Add quantile regression
Merged At: 2021-05-25T12:02:37Z
Changed Files: 7
Additions: +729, Deletions: -0

## PR Description
This PR fixes issue #3148

This new feature implements quantile regression - an algorithm that directly minimizes mean absolute error of a linear regression model. 

~~The work is still in progress, but I do want to receive some feedback.~~

## Diff (first 3000 chars)
diff --git a/doc/modules/classes.rst b/doc/modules/classes.rst
index 5462e06f81214..cdeb6f0523422 100644
--- a/doc/modules/classes.rst
+++ b/doc/modules/classes.rst
@@ -839,6 +839,7 @@ Any estimator using the Huber loss would also be robust to outliers, e.g.
    :template: class.rst
 
    linear_model.HuberRegressor
+   linear_model.QuantileRegressor
    linear_model.RANSACRegressor
    linear_model.TheilSenRegressor
 
diff --git a/doc/modules/linear_model.rst b/doc/modules/linear_model.rst
index f1f376dc641c9..7fc14693c198d 100644
--- a/doc/modules/linear_model.rst
+++ b/doc/modules/linear_model.rst
@@ -1423,6 +1423,83 @@ Note that this estimator is different from the R implementation of Robust Regres
 squares implementation with weights given to each sample on the basis of how much the residual is
 greater than a certain threshold.
 
+.. _quantile_regression:
+
+Quantile Regression
+===================
+
+Quantile regression estimates the median or other quantiles of :math:`y`
+conditional on :math:`X`, while ordinary least squares (OLS) estimates the
+conditional mean.
+
+As a linear model, the :class:`QuantileRegressor` gives linear predictions
+:math:`\hat{y}(w, X) = Xw` for the :math:`q`-th quantile, :math:`q \in (0, 1)`.
+The weights or coefficients :math:`w` are then found by the following
+minimization problem:
+
+.. math::
+    \min_{w} {\frac{1}{n_{\text{samples}}}
+    \sum_i PB_q(y_i - X_i w) + \alpha ||w||_1}.
+
+This consists of the pinball loss (also known as linear loss),
+see also :class:`~sklearn.metrics.mean_pinball_loss`,
+
+.. math::
+    PB_q(t) = q \max(t, 0) + (1 - q) \max(-t, 0) =
+    \begin{cases}
+        q t, & t > 0, \\
+        0,    & t = 0, \\
+        (1-q) t, & t < 0
+    \end{cases}
+
+and the L1 penalty controlled by parameter ``alpha``, similar to
+:class:`Lasso`.
+
+As the pinball loss is only linear in the residuals, quantile regression is
+much more robust to outliers than squared error based estimation of the mean.
+Somewhat in between is the :class:`HuberRegressor`.
+
+Quantile regression may be useful if one is interested in predicting an
+interval instead of point prediction. Sometimes, prediction intervals are
+calculated based on the assumption that prediction error is distributed
+normally with zero mean and constant variance. Quantile regression provides
+sensible prediction intervals even for errors with non-constant (but
+predictable) variance or non-normal distribution.
+
+.. figure:: /auto_examples/linear_model/images/sphx_glr_plot_quantile_regression_001.png
+   :target: ../auto_examples/linear_model/plot_quantile_regression.html
+   :align: center
+   :scale: 50%
+
+Based on minimizing the pinball loss, conditional quantiles can also be
+estimated by models other than linear models. For example,
+:class:`~sklearn.ensemble.GradientBoostingRegressor` can predict conditional
+quantiles if its parameter ``loss`` is set to ``"quantile"`` and parameter
+``alpha`` is set to the quantile that should