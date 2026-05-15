# Design Document: QuantileRegressor for scikit-learn

## Overview and Motivation

This design document describes the QuantileRegressor class added to sklearn.linear_model in PR #9978. The addition addresses feature request #3148, which asked for a scikit-learn implementation of quantile regression. Unlike ordinary least squares (OLS) which estimates the conditional mean of y given X, quantile regression estimates conditional quantiles—such as the median or any q-th quantile. This is particularly valuable when the error distribution exhibits heteroscedasticity (non-constant variance) or skewness, where the mean alone is insufficient to characterize the response.

The existing HuberRegressor provides robustness to outliers by using the Huber loss, but it still targets the mean. The new QuantileRegressor targets arbitrary quantiles directly through the pinball loss. This enables use cases such as constructing prediction intervals (e.g., fitting the 0.05 and 0.95 quantiles), modeling asymmetric error distributions, and quantifying uncertainty in predictions even when errors are non-normal. The implementation is based on formulating the problem as a linear program and solving it with scipy.optimize.linprog.

The contribution was authored by David Dale and Christian Lorentzen. It was merged on May 25, 2021 as part of the scikit-learn 1.0 release cycle. The implementation consists of the core class in sklearn/linear_model/_quantile.py, test suite in sklearn/linear_model/tests/test_quantile.py, an example script, and documentation updates across multiple RST files.

## Mathematical Formulation

The QuantileRegressor solves the following optimization problem to find weights w that predict the q-th conditional quantile: min_w { (1/n_samples) * sum_i PB_q(y_i - X_i w) + alpha * ||w||_1 }, where PB_q is the pinball loss function. The pinball loss is defined as PB_q(t) = q * max(t, 0) + (1 - q) * max(-t, 0), which equals q*t for t>0, 0 for t=0, and (1-q)*t for t<0. When q=0.5, this reduces to the absolute error (MAE) scaled by 0.5, making the median the solution.

The implementation reformulates this as a linear program. The decision variables are split into positive and negative slack components: x = (s0, s, t0, t, u, v) where s0 and t0 represent the intercept decomposition, s and t represent the coefficient decomposition (coef = s - t), and u and v represent the residual decomposition (residual = y - X@coef - intercept = u - v). The cost vector c is constructed as c = (alpha*1_p, alpha*1_p, quantile*1_n, (1-quantile)*1_n) where p = n_features + fit_intercept and n = n_samples (after filtering zero weights).

The equality constraint matrix A_eq is constructed as (1_n, X, -1_n, -X, diag(1_n), -diag(1_n)) when fit_intercept=True, with b_eq = y. This formulation ensures that all variables are non-negative (x >= 0), which linprog handles natively. The intercept is explicitly excluded from penalty by setting c[0] = 0 and c[n_params] = 0. The regularization parameter alpha is internally scaled by the sum of sample weights: alpha_internal = sum(sample_weight) * alpha.

## API Design

The QuantileRegressor class inherits from LinearModel, RegressorMixin, and BaseEstimator, following the standard scikit-learn estimator pattern. It accepts five constructor parameters: quantile (float, default 0.5) specifying the target quantile; alpha (float, default 1.0) controlling L1 regularization strength; fit_intercept (bool, default True) whether to include a bias term; solver (str, default 'interior-point') specifying the scipy.optimize.linprog method; and solver_options (dict, default None) for additional solver configuration.

Parameter validation is performed in the fit method. The quantile must be strictly between 0.0 and 1.0 (exclusive). The alpha must be non-negative. The fit_intercept must be a boolean. The solver must be one of five allowed values: 'highs-ds', 'highs-ipm', 'highs', 'interior-point', or 'revised simplex'. Version constraints are enforced: the 'revised simplex' solver requires scipy >= 1.3.0, while the three 'highs' variants require scipy >= 1.6.0. The solver_options parameter, if provided, must be a dictionary.

When solver_options is None and the solver is 'interior-point', the implementation sets solver_options = {'lstsq': True} for numerical stability. The fit method accepts an optional sample_weight parameter validated via _check_sample_weight. After fitting, the estimator exposes three attributes: coef_ (array of shape (n_features,) containing estimated coefficients), intercept_ (float, set to 0.0 when fit_intercept=False), and n_iter_ (int, the number of solver iterations from result.nit). The class is registered in sklearn/linear_model/__init__.py and exported in __all__.

## Implementation Details

The core implementation resides in sklearn/linear_model/_quantile.py, authored by David Dale and Christian Lorentzen under the BSD 3-clause license. The file is approximately 280 lines. The fit method begins by validating input data using _validate_data with accept_sparse=False, y_numeric=True, and multi_output=False—meaning the current implementation does not support sparse matrices or multi-output targets.

A key implementation detail is the filtering of zero-weight samples before constructing the linear program. The mask = sample_weight != 0 is applied to X, y, and sample_weight, and n_mask is used instead of n_samples throughout the LP construction. This reduces the problem size and avoids numerical issues with the solver. The sample_weight array is incorporated into the cost vector c by multiplying the quantile and (1-quantile) terms element-wise.

The intercept is explicitly excluded from L1 regularization by setting the first and (n_params+1)-th elements of the cost vector c to zero. This corresponds to the positions of the positive and negative slack variables for the intercept. After solving the linear program, the model parameters are recovered by subtracting negative slacks from positive slacks: params = solution[:n_params] - solution[n_params:2*n_params]. If fit_intercept is True, params[0] becomes the intercept and params[1:] become the coefficients; otherwise, params becomes the coefficients and intercept_ is set to 0.0.

The implementation includes careful error handling for solver failures. When result.success is False, a ConvergenceWarning is issued with the specific failure reason mapped from the status code: 1 for iteration limit reached, 2 for infeasible problem, 3 for unbounded problem, and 4 for numerical difficulties. The warning message includes both the status code and the solver's result.message for debugging.

## Testing Strategy

The test suite in sklearn/linear_model/tests/test_quantile.py contains 254 lines and covers a comprehensive range of scenarios. The test_init_parameters_validation function uses a parametrized fixture with 9 cases testing invalid values for quantile (values of 2, 1, 0, -1), alpha (-1.5), fit_intercept ('blah', 0), solver ('blah'), and solver_options ('blah'), each expecting a specific ValueError message. The test_too_new_solver_methods_raise_error function verifies that the 'highs-ds', 'highs-ipm', and 'highs' solvers raise appropriate errors when scipy < 1.6.0.

The test_quantile_toy_example function tests five specific configurations with the small dataset X = [[0], [1], [1]], y = [1, 2, 11]: (quantile=0.5, alpha=0, intercept=1, coef in [1,10]), (quantile=0.51, alpha=0, intercept=1, coef=10), (quantile=0.49, alpha=0, intercept=1, coef=1), (quantile=0.5, alpha=0.01, intercept=1, coef=1), and (quantile=0.5, alpha=100, intercept=2, coef=0). The test_quantile_estimates_calibration function verifies that for quantiles 0.5, 0.9, and 0.05 with alpha=0 on 1000 samples, the fraction of points below the prediction approximates the target quantile within 1e-2.

The test_quantile_sample_weight function creates 1000 samples and assigns weight=100 to observations above the mean, then verifies that the weighted fraction below the prediction approximates 0.5 within 3e-2. The test_quantile_equals_huber_for_low_epsilon function verifies that QuantileRegressor with alpha=1e-4 produces coefficients close to HuberRegressor with epsilon=1+1e-4 within tolerance 1e-1. The test_equivariance function tests three mathematical properties from Koenker (2005) Chapter 2.2.3: scale equivariance (coef(q; a*y, X) = a*coef(q; y, X)), quantile symmetry (coef(1-q; -a*y, X) = -a*coef(q; y, X)), and shift equivariance (coef(q; y+X@g, X) = coef(q; y, X) + g). The test_linprog_failure function forces convergence failure by setting maxiter=1 and verifies a ConvergenceWarning is raised.

## Documentation and Examples

The documentation added in doc/modules/linear_model.rst spans approximately 77 lines and introduces a new 'Quantile Regression' section with the anchor _quantile_regression. The section explains the mathematical formulation using Sphinx :math: directives for the optimization objective and pinball loss function. It describes the advantages of quantile regression over OLS for heteroscedastic and asymmetric distributions, includes a figure from the example script, and cross-references GradientBoostingRegressor as an alternative non-linear approach when its loss parameter is set to 'quantile'.

Three academic references are cited: Koenker & Bassett (1978) 'Regression quantiles' from Econometrica, Portnoy & Koenker (1997) 'The Gaussian hare and the Laplacian tortoise' from Statistical Science, and Koenker (2005) 'Quantile Regression' from Cambridge University Press. The section also notes that the implementation is based on scipy.optimize.linprog and links to the example script.

The example script examples/linear_model/plot_quantile_regression.py demonstrates two scenarios: a heteroscedastic Normal distribution (left panel) and an asymmetric Pareto distribution (right panel). It fits quantiles [0.05, 0.5, 0.95] with alpha=0 and visualizes prediction intervals. The second part compares LinearRegression and QuantileRegressor on in-sample and cross-validated MAE/RMSE metrics. The class is also registered in doc/modules/classes.rst alongside HuberRegressor and RANSACRegressor, and a changelog entry in doc/whats_new/v1.0.rst announces the feature under the sklearn.linear_model section.

## Limitations and Future Work

The current implementation has several known limitations. First, it does not support sparse matrices—_validate_data is called with accept_sparse=False, which means large sparse datasets common in NLP or recommendation systems cannot be used directly. Second, multi-output regression is not supported (multi_output=False), so users predicting multiple quantiles must fit separate models. Third, the linear programming formulation, while exact, may scale poorly to very large datasets since the number of variables grows linearly with n_samples.

The solver version constraints present a practical limitation: the recommended 'highs' family of solvers requires scipy >= 1.6.0, and even 'revised simplex' requires scipy >= 1.3.0. Users with older scipy versions are limited to the 'interior-point' solver, which is made more stable by the default {'lstsq': True} option but may still encounter numerical difficulties as indicated by the ConvergenceWarning handling.

Future work could include: adding sparse matrix support by using sparse-aware LP formulations, implementing warm starting for sequential quantile estimation, exploring second-order cone programming alternatives, supporting sample-weight-aware cross-validation, and potentially adding a non-linear kernel variant. The equivariance properties documented in the tests (from Koenker 2005) provide a strong mathematical foundation for these extensions.
