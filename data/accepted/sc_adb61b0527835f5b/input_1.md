# PR description text fixing issue #3148


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

## Diff
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
+``alpha`` is set to the quantile that should be predicted. See the example in
+:ref:`sphx_glr_auto_examples_ensemble_plot_gradient_boosting_quantile.py`.
+
+Most implementations of quantile regression are based on linear programming
+problem. The current implementation is based on
+:func:`scipy.optimize.linprog`.
+
+.. topic:: Examples:
+
+  * :ref:`sphx_glr_auto_examples_linear_model_plot_quantile_regression.py`
+
+.. topic:: References:
+
+  * Koenker, R., & Bassett Jr, G. (1978). `Regression quantiles.
+    <https://gib.people.uic.edu/RQ.pdf>`_
+    Econometrica: journal of the Econometric Society, 33-50.
+
+  * Portnoy, S., & Koenker, R. (1997). The Gaussian hare and the Laplacian
+    tortoise: computability of squared-error versus absolute-error estimators.
+    Statistical Science, 12, 279-300. https://doi.org/10.1214/ss/1030037960
+
+  * Koenker, R. (2005). Quantile Regression.
+    Cambridge University Press. https://doi.org/10.1017/CBO9780511754098
+
+
 .. _polynomial_regression:
 
 Polynomial regression: extending linear models with basis functions
diff --git a/doc/whats_new/v1.0.rst b/doc/whats_new/v1.0.rst
index 87b0441bade5f..26d11b08bff9b 100644
--- a/doc/whats_new/v1.0.rst
+++ b/doc/whats_new/v1.0.rst
@@ -282,6 +282,11 @@ Changelog
 :mod:`sklearn.linear_model`
 ...........................
 
+- |Feature| Added :class:`linear_model.QuantileRegressor` which implements
+  linear quantile regression with L1 penalty.
+  :pr:`9978` by :user:`David Dale <avidale>` and
+  :user:`Christian Lorentzen <lorentzenchr>`.
+
 - |Feature| The new :class:`linear_model.SGDOneClassSVM` provides an SGD
   implementation of the linear One-Class SVM. Combined with kernel
   approximation techniques, this implementation approximates the solution of
diff --git a/examples/linear_model/plot_quantile_regression.py b/examples/linear_model/plot_quantile_regression.py
new file mode 100644
index 0000000000000..8af7785cc6733
--- /dev/null
+++ b/examples/linear_model/plot_quantile_regression.py
@@ -0,0 +1,110 @@
+"""
+===================
+Quantile regression
+===================
+This example illustrates how quantile regression can predict non-trivial
+conditional quantiles.
+
+The left figure shows the case when the error distribution is normal,
+but has non-constant variance, i.e. with heteroscedasticity.
+
+The right figure shows an example of an asymmetric error distribution,
+namely the Pareto distribution.
+"""
+print(__doc__)
+# Authors: David Dale <dale.david@mail.ru>
+#          Christian Lorentzen <lorentzen.ch@gmail.com>
+# License: BSD 3 clause
+import numpy as np
+import matplotlib.pyplot as plt
+
+from sklearn.linear_model import QuantileRegressor, LinearRegression
+from sklearn.metrics import mean_absolute_error, mean_squared_error
+from sklearn.model_selection import cross_val_score
+
+
+def plot_points_highlighted(x, y, model_low, model_high, ax):
+    """Plot points with highlighting."""
+    mask = y <= model_low.predict(X)
+    ax.scatter(x[mask], y[mask], c="k", marker="x")
+    mask = y > model_high.predict(X)
+    ax.scatter(x[mask], y[mask], c="k", marker="x")
+    mask = (y > model_low.predict(X)) & (y <= model_high.predict(X))
+    ax.scatter(x[mask], y[mask], c="k")
+
+
+fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
+
+rng = np.random.RandomState(42)
+x = np.linspace(0, 10, 100)
+X = x[:, np.newaxis]
+y = 10 + 0.5 * x + rng.normal(loc=0, scale=0.5 + 0.5 * x, size=x.shape[0])
+y_mean = 10 + 0.5 * x
+ax1.plot(x, y_mean, "k--")
+
+quantiles = [0.05, 0.5, 0.95]
+models = []
+for quantile in quantiles:
+    qr = QuantileRegressor(quantile=quantile, alpha=0)
+    qr.fit(X, y)
+    ax1.plot(x, qr.predict(X))
+    models.append(qr)
+
+plot_points_highlighted(x, y, models[0], models[2], ax1)
+ax1.set_xlabel("x")
+ax1.set_ylabel("y")
+ax1.set_title("Quantiles of heteroscedastic Normal distributed target")
+ax1.legend(["true mean"] + quantiles)
+
+
+a = 5
+y = 10 + 0.5 * x + 10 * (rng.pareto(a, size=x.shape[0]) - 1 / (a - 1))
+ax2.plot(x, y_mean, "k--")
+
+models = []
+for quantile in quantiles:
+    qr = QuantileRegressor(quantile=quantile, alpha=0)
+    qr.fit(X, y)
+    ax2.plot([0, 10], qr.predict([[0], [10]]))
+    models.append(qr)
+
+plot_points_highlighted(x, y, models[0], models[2], ax2)
+ax2.set_xlabel("x")
+ax2.set_ylabel("y")
+ax2.set_title("Quantiles of asymmetric Pareto distributed target")
+ax2.legend(["true mean"] + quantiles, loc="lower right")
+ax2.yaxis.set_tick_params(labelbottom=True)
+
+plt.show()
+
+# %%
+# Note that both targets have the same mean value, indicated by the dashed
+# black line. As the Normal distribution is symmetric, mean and median are
+# identical and the predicted 0.5 quantile almost hits the true mean.
+# In the Pareto case, the difference between predicted median and true mean
+# is evident. We also marked the points below the 0.05 and above 0.95
+# predicted quantiles by small crosses. You might count them and consider
+# that we have 100 samples in total.
+#
+# The second part of the example shows that LinearRegression minimizes MSE
+# in order to predict the mean, while QuantileRegressor with `quantile=0.5`
+# minimizes MAE in order to predict the median. Both do their own job well.
+
+models = [LinearRegression(), QuantileRegressor(alpha=0)]
+names = ["OLS", "Quantile"]
+
+print("# In-sample performance")
+for model_name, model in zip(names, models):
+    print(model_name + ":")
+    model.fit(X, y)
+    mae = mean_absolute_error(model.predict(X), y)
+    rmse = np.sqrt(mean_squared_error(model.predict(X), y))
+    print(f"MAE = {mae:.4}  RMSE = {rmse:.4}")
+print("\n# Cross-validated performance")
+for model_name, model in zip(names, models):
+    print(model_name + ":")
+    mae = -cross_val_score(model, X, y, cv=3,
+                           scoring="neg_mean_absolute_error").mean()
+    rmse = np.sqrt(-cross_val_score(model, X, y, cv=3,
+                                    scoring="neg_mean_squared_error").mean())
+    print(f"MAE = {mae:.4}  RMSE = {rmse:.4}")
diff --git a/sklearn/linear_model/__init__.py b/sklearn/linear_model/__init__.py
index f715e30795961..02e8cafaa7b88 100644
--- a/sklearn/linear_model/__init__.py
+++ b/sklearn/linear_model/__init__.py
@@ -28,6 +28,7 @@
 from ._passive_aggressive import PassiveAggressiveRegressor
 from ._perceptron import Perceptron
 
+from ._quantile import QuantileRegressor
 from ._ransac import RANSACRegressor
 from ._theil_sen import TheilSenRegressor
 
@@ -59,6 +60,7 @@
            'PassiveAggressiveClassifier',
            'PassiveAggressiveRegressor',
            'Perceptron',
+           'QuantileRegressor',
            'Ridge',
            'RidgeCV',
            'RidgeClassifier',
diff --git a/sklearn/linear_model/_quantile.py b/sklearn/linear_model/_quantile.py
new file mode 100644
index 0000000000000..bf8fea4552c9d
--- /dev/null
+++ b/sklearn/linear_model/_quantile.py
@@ -0,0 +1,280 @@
+# Authors: David Dale <dale.david@mail.ru>
+#          Christian Lorentzen <lorentzen.ch@gmail.com>
+# License: BSD 3 clause
+import warnings
+
+import numpy as np
+from scipy.optimize import linprog
+
+from ..base import BaseEstimator, RegressorMixin
+from ._base import LinearModel
+from ..exceptions import ConvergenceWarning
+from ..utils.validation import _check_sample_weight
+from ..utils.fixes import sp_version, parse_version
+
+
+class QuantileRegressor(LinearModel, RegressorMixin, BaseEstimator):
+    """Linear regression model that predicts conditional quantiles.
+
+    The linear :class:`QuantileRegressor` optimizes the pinball loss for a
+    desired `quantile` and is robust to outliers.
+
+    This model uses an L1 regularization like
+    :class:`~sklearn.linear_model.Lasso`.
+
+    Read more in the :ref:`User Guide <quantile_regression>`.
+
+    .. versionadded:: 1.0
+
+    Parameters
+    ----------
+    quantile : float, default=0.5
+        The quantile that the model tries to predict. It must be strictly
+        between 0 and 1. If 0.5 (default), the model predicts the 50%
+        quantile, i.e. the median.
+
+    alpha : float, default=1.0
+        Regularization constant that multiplies the L1 penalty term.
+
+    fit_intercept : bool, default=True
+        Whether or not to fit the intercept.
+
+    solver : {'highs-ds', 'highs-ipm', 'highs', 'interior-point', \
+            'revised simplex'}, default='interior-point'
+        Method used by :func:`scipy.optimize.linprog` to solve the linear
+        programming formulation. Note that the highs methods are recommended
+        for usage with `scipy>=1.6.0` because they are the fastest ones.
+
+    solver_options : dict, default=None
+        Additional parameters passed to :func:`scipy.optimize.linprog` as
+        options. If `None` and if `solver='interior-point'`, then
+        `{"lstsq": True}` is passed to :func:`scipy.optimize.linprog` for the
+        sake of stability.
+
+    Attributes
+    ----------
+    coef_ : array of shape (n_features,)
+        Estimated coefficients for the features.
+
+    intercept_ : float
+        The intercept of the model, aka bias term.
+
+    n_iter_ : int
+        The actual number of iterations performed by the solver.
+
+    See Also
+    --------
+    Lasso : The Lasso is a linear model that estimates sparse coefficients
+        with l1 regularization.
+    HuberRegressor : Linear regression model that is robust to outliers.
+
+    Examples
+    --------
+    >>> from sklearn.linear_model import QuantileRegressor
+    >>> import numpy as np
+    >>> n_samples, n_features = 10, 2
+    >>> rng = np.random.RandomState(0)
+    >>> y = rng.randn(n_samples)
+    >>> X = rng.randn(n_samples, n_features)
+    >>> reg = QuantileRegressor(quantile=0.8).fit(X, y)
+    >>> np.mean(y <= reg.predict(X))
+    0.8
+    """
+
+    def __init__(
+        self,
+        *,
+        quantile=0.5,
+        alpha=1.0,
+        fit_intercept=True,
+        solver="interior-point",
+        solver_options=None,
+    ):
+        self.quantile = quantile
+        self.alpha = alpha
+        self.fit_intercept = fit_intercept
+        self.solver = solver
+        self.solver_options = solver_options
+
+    def fit(self, X, y, sample_weight=None):
+        """Fit the model according to the given training data.
+
+        Parameters
+        ----------
+        X : array-like of shape (n_samples, n_features)
+            Training data.
+
+        y : array-like of shape (n_samples,)
+            Target values.
+
+        sample_weight : array-like of shape (n_samples,), default=None
+            Sample weights.
+
+        Returns
+        -------
+        self : object
+            Returns self.
+        """
+        X, y = self._validate_data(
+            X, y, accept_sparse=False, y_numeric=True, multi_output=False
+        )
+        sample_weight = _check_sample_weight(sample_weight, X)
+
+        n_features = X.shape[1]
+        n_params = n_features
+
+        if self.fit_intercept:
+            n_params += 1
+            # Note that centering y and X with _preprocess_data does not work
+            # for quantile regression.
+
+        # The objective is defined as 1/n * sum(pinball loss) + alpha * L1.
+        # So we rescale the penalty term, which is equivalent.
+        if self.alpha >= 0:
+            alpha = np.sum(sample_weight) * self.alpha
+        else:
+            raise ValueError(
+                f"Penalty alpha must be a non-negative number, "
+                f"got {self.alpha}"
+            )
+
+        if self.quantile >= 1.0 or self.quantile <= 0.0:
+            raise ValueError(
+                f"Quantile should be strictly between 0.0 and 1.0, got "
+                f"{self.quantile}"
+            )
+
+        if not isinstance(self.fit_intercept, bool):
+            raise ValueError(
+                f"The argument fit_intercept must be bool, "
+                f"got {self.fit_intercept}"
+            )
+
+        if self.solver not in (
+            "highs-ds",
+            "highs-ipm",
+            "highs",
+            "interior-point",
+            "revised simplex",
+        ):
+            raise ValueError(
+                f"Invalid value for argument solver, got {self.solver}"
+            )
+        elif self.solver == "revised simplex" and sp_version < parse_version(
+            "1.3.0"
+        ):
+            raise ValueError(
+                f"Solver 'revised simplex' is only available "
+                f"with scipy>=1.3.0, got {sp_version}"
+            )
+        elif self.solver in (
+            "highs-ds",
+            "highs-ipm",
+            "highs",
+        ) and sp_version < parse_version("1.6.0"):
+            raise ValueError(
+                f"Solver {self.solver} is only available "
+                f"with scipy>=1.6.0, got {sp_version}"
+            )
+
+        if self.solver_options is not None and not isinstance(
+            self.solver_options, dict
+        ):
+            raise ValueError(
+                f"Invalid value for argument solver_options, "
+                f"must be None or a dictionary, got "
+                f"{self.solver_options}"
+            )
+
+        # make default solver more stable
+        if self.solver_options is None and self.solver == "interior-point":
+            solver_options = {"lstsq": True}
+        else:
+            solver_options = self.solver_options
+
+        # Use linear programming formulation of quantile regression
+        #     min_x c x
+        #           A_eq x = b_eq
+        #                0 <= x
+        # x = (s0, s, t0, t, u, v) = slack variables
+        # intercept = s0 + t0
+        # coef = s + t
+        # c = (alpha * 1_p, alpha * 1_p, quantile * 1_n, (1-quantile) * 1_n)
+        # residual = y - X@coef - intercept = u - v
+        # A_eq = (1_n, X, -1_n, -X, diag(1_n), -diag(1_n))
+        # b_eq = y
+        # p = n_features + fit_intercept
+        # n = n_samples
+        # 1_n = vector of length n with entries equal one
+        # see https://stats.stackexchange.com/questions/384909/
+        #
+        # Filtering out zero samples weights from the beginning makes life
+        # easier for the linprog solver.
+        mask = sample_weight != 0
+        n_mask = int(np.sum(mask))  # use n_mask instead of n_samples
+        c = np.concatenate(
+            [
+                np.full(2 * n_params, fill_value=alpha),
+                sample_weight[mask] * self.quantile,
+                sample_weight[mask] * (1 - self.quantile),
+            ]
+        )
+        if self.fit_intercept:
+            # do not penalize the intercept
+            c[0] = 0
+            c[n_params] = 0
+
+            A_eq = np.concatenate(
+                [
+                    np.ones((n_mask, 1)),
+                    X[mask],
+                    -np.ones((n_mask, 1)),
+                    -X[mask],
+                    np.eye(n_mask),
+                    -np.eye(n_mask),
+                ],
+                axis=1,
+            )
+        else:
+            A_eq = np.concatenate(
+                [X[mask], -X[mask], np.eye(n_mask), -np.eye(n_mask)], axis=1
+            )
+
+        b_eq = y[mask]
+
+        result = linprog(
+            c=c,
+            A_eq=A_eq,
+            b_eq=b_eq,
+            method=self.solver,
+            options=solver_options,
+        )
+        solution = result.x
+        if not result.success:
+            failure = {
+                1: "Iteration limit reached.",
+                2: "Problem appears to be infeasible.",
+                3: "Problem appears to be unbounded.",
+                4: "Numerical difficulties encountered.",
+            }
+            warnings.warn(
+                f"Linear programming for QuantileRegressor did not succeed.\n"
+                f"Status is {result.status}: "
+                + failure.setdefault(result.status, "unknown reason") + "\n"
+                + "Result message of linprog:\n" + result.message,
+                ConvergenceWarning
+            )
+
+        # positive slack - negative slack
+        # solution is an array with (params_pos, params_neg, u, v)
+        params = solution[:n_params] - solution[n_params:2 * n_params]
+
+        self.n_iter_ = result.nit
+
+        if self.fit_intercept:
+            self.coef_ = params[1:]
+            self.intercept_ = params[0]
+        else:
+            self.coef_ = params
+            self.intercept_ = 0.0
+        return self
diff --git a/sklearn/linear_model/tests/test_quantile.py b/sklearn/linear_model/tests/test_quantile.py
new file mode 100644
index 0000000000000..6118889f4d1b6
--- /dev/null
+++ b/sklearn/linear_model/tests/test_quantile.py
@@ -0,0 +1,254 @@
+# Authors: David Dale <dale.david@mail.ru>
+#          Christian Lorentzen <lorentzen.ch@gmail.com>
+# License: BSD 3 clause
+
+import numpy as np
+import pytest
+from pytest import approx
+from scipy.optimize import minimize
+
+from sklearn.datasets import make_regression
+from sklearn.exceptions import ConvergenceWarning
+from sklearn.linear_model import HuberRegressor, QuantileRegressor
+from sklearn.metrics import mean_pinball_loss
+from sklearn.utils._testing import assert_allclose
+from sklearn.utils.fixes import parse_version, sp_version
+
+
+@pytest.fixture
+def X_y_data():
+    X, y = make_regression(n_samples=10, n_features=1, random_state=0, noise=1)
+    return X, y
+
+
+@pytest.mark.parametrize(
+    "params, err_msg",
+    [
+        ({"quantile": 2}, "Quantile should be strictly between 0.0 and 1.0"),
+        ({"quantile": 1}, "Quantile should be strictly between 0.0 and 1.0"),
+        ({"quantile": 0}, "Quantile should be strictly between 0.0 and 1.0"),
+        ({"quantile": -1}, "Quantile should be strictly between 0.0 and 1.0"),
+        ({"alpha": -1.5}, "Penalty alpha must be a non-negative number"),
+        ({"fit_intercept": "blah"}, "The argument fit_intercept must be bool"),
+        ({"fit_intercept": 0}, "The argument fit_intercept must be bool"),
+        ({"solver": "blah"}, "Invalid value for argument solver"),
+        (
+            {"solver_options": "blah"},
+            "Invalid value for argument solver_options",
+        ),
+    ],
+)
+def test_init_parameters_validation(X_y_data, params, err_msg):
+    """Test that invalid init parameters raise errors."""
+    X, y = X_y_data
+    with pytest.raises(ValueError, match=err_msg):
+        QuantileRegressor(**params).fit(X, y)
+
+
+@pytest.mark.parametrize("solver", ("highs-ds", "highs-ipm", "highs"))
+@pytest.mark.skipif(sp_version >= parse_version('1.6.0'),
+                    reason="Solvers are available as of scipy 1.6.0")
+def test_too_new_solver_methods_raise_error(X_y_data, solver):
+    """Test that highs solver raises for scipy<1.6.0."""
+    X, y = X_y_data
+    with pytest.raises(ValueError, match="scipy>=1.6.0"):
+        QuantileRegressor(solver=solver).fit(X, y)
+
+
+@pytest.mark.parametrize(
+    "quantile, alpha, intercept, coef",
+    [
+        # for 50% quantile w/o regularization, any slope in [1, 10] is okay
+        [0.5, 0, 1, None],
+        # if positive error costs more, the slope is maximal
+        [0.51, 0, 1, 10],
+        # if negative error costs more, the slope is minimal
+        [0.49, 0, 1, 1],
+        # for a small lasso penalty, the slope is also minimal
+        [0.5, 0.01, 1, 1],
+        # for a large lasso penalty, the model predicts the constant median
+        [0.5, 100, 2, 0],
+    ],
+)
+def test_quantile_toy_example(quantile, alpha, intercept, coef):
+    # test how different parameters affect a small intuitive example
+    X = [[0], [1], [1]]
+    y = [1, 2, 11]
+    model = QuantileRegressor(quantile=quantile, alpha=alpha).fit(X, y)
+    assert_allclose(model.intercept_, intercept, atol=1e-2)
+    if coef is not None:
+        assert_allclose(model.coef_[0], coef, atol=1e-2)
+    if alpha < 100:
+        assert model.coef_[0] >= 1
+    assert model.coef_[0] <= 10
+
+
+@pytest.mark.parametrize("fit_intercept", [True, False])
+def test_quantile_equals_huber_for_low_epsilon(fit_intercept):
+    X, y = make_regression(
+        n_samples=100, n_features=20, random_state=0, noise=1.0
+    )
+    alpha = 1e-4
+    huber = HuberRegressor(
+        epsilon=1 + 1e-4, alpha=alpha, fit_intercept=fit_intercept
+    ).fit(X, y)
+    quant = QuantileRegressor(alpha=alpha, fit_intercept=fit_intercept).fit(
+        X, y
+    )
+    assert_allclose(huber.coef_, quant.coef_, atol=1e-1)
+    if fit_intercept:
+        assert huber.intercept_ == approx(quant.intercept_, abs=1e-1)
+        # check that we still predict fraction
+        assert np.mean(y < quant.predict(X)) == approx(0.5, abs=1e-1)
+
+
+@pytest.mark.parametrize("q", [0.5, 0.9, 0.05])
+def test_quantile_estimates_calibration(q):
+    # Test that model estimates percentage of points below the prediction
+    X, y = make_regression(
+        n_samples=1000, n_features=20, random_state=0, noise=1.0
+    )
+    quant = QuantileRegressor(
+        quantile=q,
+        alpha=0,
+        solver_options={"lstsq": False},
+    ).fit(X, y)
+    assert np.mean(y < quant.predict(X)) == approx(q, abs=1e-2)
+
+
+def test_quantile_sample_weight():
+    # test that with unequal sample weights we still estimate weighted fraction
+    n = 1000
+    X, y = make_regression(
+        n_samples=n, n_features=5, random_state=0, noise=10.0
+    )
+    weight = np.ones(n)
+    # when we increase weight of upper observations,
+    # estimate of quantile should go up
+    weight[y > y.mean()] = 100
+    quant = QuantileRegressor(
+        quantile=0.5,
+        alpha=1e-8,
+        solver_options={"lstsq": False}
+    )
+    quant.fit(X, y, sample_weight=weight)
+    fraction_below = np.mean(y < quant.predict(X))
+    assert fraction_below > 0.5
+    weighted_fraction_below = np.average(y < quant.predict(X), weights=weight)
+    assert weighted_fraction_below == approx(0.5, abs=3e-2)
+
+
+@pytest.mark.parametrize("quantile", [0.2, 0.5, 0.8])
+def test_asymmetric_error(quantile):
+    """Test quantile regression for asymmetric distributed targets."""
+    n_samples = 1000
+    rng = np.random.RandomState(42)
+    # take care that X @ coef + intercept > 0
+    X = np.concatenate(
+        (
+            np.abs(rng.randn(n_samples)[:, None]),
+            -rng.randint(2, size=(n_samples, 1)),
+        ),
+        axis=1,
+    )
+    intercept = 1.23
+    coef = np.array([0.5, -2])
+    # For an exponential distribution with rate lambda, e.g. exp(-lambda * x),
+    # the quantile at level q is:
+    #   quantile(q) = - log(1 - q) / lambda
+    #   scale = 1/lambda = -quantile(q) / log(1-q)
+    y = rng.exponential(
+        scale=-(X @ coef + intercept) / np.log(1 - quantile), size=n_samples
+    )
+    model = QuantileRegressor(
+        quantile=quantile,
+        alpha=0,
+        solver="interior-point",
+        solver_options={"tol": 1e-5},
+    ).fit(X, y)
+    assert model.intercept_ == approx(intercept, rel=0.2)
+    assert_allclose(model.coef_, coef, rtol=0.6)
+    assert_allclose(np.mean(model.predict(X) > y), quantile)
+
+    # Now compare to Nelder-Mead optimization with L1 penalty
+    alpha = 0.01
+    model.set_params(alpha=alpha).fit(X, y)
+    model_coef = np.r_[model.intercept_, model.coef_]
+
+    def func(coef):
+        loss = mean_pinball_loss(y, X @ coef[1:] + coef[0], alpha=quantile)
+        L1 = np.sum(np.abs(coef[1:]))
+        return loss + alpha * L1
+
+    res = minimize(
+        fun=func,
+        x0=[1, 0, -1],
+        method="Nelder-Mead",
+        tol=1e-12,
+        options={"maxiter": 2000},
+    )
+
+    assert func(model_coef) == approx(func(res.x), rel=1e-3)
+    assert_allclose(model.intercept_, res.x[0], rtol=1e-3)
+    assert_allclose(model.coef_, res.x[1:], rtol=1e-3)
+    assert_allclose(np.mean(model.predict(X) > y), quantile, rtol=8e-3)
+
+
+@pytest.mark.parametrize("quantile", [0.2, 0.5, 0.8])
+def test_equivariance(quantile):
+    """Test equivariace of quantile regression.
+
+    See Koenker (2005) Quantile Regression, Chapter 2.2.3.
+    """
+    rng = np.random.RandomState(42)
+    n_samples, n_features = 100, 5
+    X, y = make_regression(
+        n_samples=n_samples,
+        n_features=n_features,
+        n_informative=n_features,
+        noise=0,
+        random_state=rng,
+        shuffle=False,
+    )
+    # make y asymmetric
+    y += rng.exponential(scale=100, size=y.shape)
+    params = dict(alpha=0, solver_options={"lstsq": True, "tol": 1e-10})
+    model1 = QuantileRegressor(quantile=quantile, **params).fit(X, y)
+
+    # coef(q; a*y, X) = a * coef(q; y, X)
+    a = 2.5
+    model2 = QuantileRegressor(quantile=quantile, **params).fit(X, a * y)
+    assert model2.intercept_ == approx(a * model1.intercept_, rel=1e-5)
+    assert_allclose(model2.coef_, a * model1.coef_, rtol=1e-5)
+
+    # coef(1-q; -a*y, X) = -a * coef(q; y, X)
+    model2 = QuantileRegressor(quantile=1 - quantile, **params).fit(X, -a * y)
+    assert model2.intercept_ == approx(-a * model1.intercept_, rel=1e-5)
+    assert_allclose(model2.coef_, -a * model1.coef_, rtol=1e-5)
+
+    # coef(q; y + X @ g, X) = coef(q; y, X) + g
+    g_intercept, g_coef = rng.randn(), rng.randn(n_features)
+    model2 = QuantileRegressor(quantile=quantile, **params)
+    model2.fit(X, y + X @ g_coef + g_intercept)
+    assert model2.intercept_ == approx(model1.intercept_ + g_intercept)
+    assert_allclose(model2.coef_, model1.coef_ + g_coef, rtol=1e-6)
+
+    # coef(q; y, X @ A) = A^-1 @ coef(q; y, X)
+    A = rng.randn(n_features, n_features)
+    model2 = QuantileRegressor(quantile=quantile, **params)
+    model2.fit(X @ A, y)
+    assert model2.intercept_ == approx(model1.intercept_, rel=1e-5)
+    assert_allclose(model2.coef_, np.linalg.solve(A, model1.coef_), rtol=1e-5)
+
+
+def test_linprog_failure():
+    """Test that linprog fails."""
+    X = np.linspace(0, 10, num=10).reshape(-1, 1)
+    y = np.linspace(0, 10, num=10)
+    reg = QuantileRegressor(
+        alpha=0, solver="interior-point", solver_options={"maxiter": 1}
+    )
+
+    msg = "Linear programming for QuantileRegressor did not succeed."
+    with pytest.warns(ConvergenceWarning, match=msg):
+        reg.fit(X, y)
