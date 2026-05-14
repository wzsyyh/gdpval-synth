# Post-Merge Review: Quantile Regression Feature (PR #9978)

# Post-Merge Review: Quantile Regression Feature (PR #9978)

This document provides a comprehensive post-merge review of the quantile regression feature introduced in PR #9978, which addresses issue #3148. The feature adds the `QuantileRegressor` class to scikit-learn's `linear_model` module, enabling direct minimization of mean absolute error for linear regression models through quantile estimation.

## Feature Overview

Quantile regression estimates the median or other quantiles of y conditional on X, while ordinary least squares (OLS) estimates the conditional mean. This fundamental distinction allows practitioners to model the entire conditional distribution rather than just its central tendency.

As a linear model, the `QuantileRegressor` gives linear predictions ŷ(w, X) = Xw for the q-th quantile, where q ∈ (0, 1). The weights or coefficients w are found by the following minimization problem: min_w (1/n_samples) * Σ_i PB_q(y_i - X_i w) + α||w||_1.

The pinball loss (also known as linear loss) is defined as: PB_q(t) = q * max(t, 0) + (1 - q) * max(-t, 0). This can be expressed piecewise as: PB_q(t) = { q*t if t > 0; 0 if t = 0; (1-q)*t if t < 0 }.

The L1 penalty controlled by parameter `alpha` is similar to `Lasso`, providing sparsity in the coefficient estimates. This feature directly fixes issue #3148 as stated in the PR description.

## API Design Review

The `QuantileRegressor` is correctly placed in the robust estimators section of `doc/modules/classes.rst`, alongside `HuberRegressor`, `RANSACRegressor`, and `TheilSenRegressor`. This placement is appropriate because quantile regression shares the property of being robust to outliers, similar to these other estimators.

The estimator exposes two primary parameters: `quantile` (q) for selecting the target quantile in (0, 1), and `alpha` for controlling the L1 penalty strength. The documentation explicitly references `sklearn.metrics.mean_pinball_loss` for evaluation, providing users with the appropriate metric for assessing model performance.

The parameter naming follows scikit-learn conventions, with `alpha` being consistent with `Lasso` for L1 regularization. The `quantile` parameter clearly communicates its purpose and aligns with the mathematical formulation in the documentation.

## Mathematical Correctness Review

The pinball loss formula PB_q(t) = q * max(t, 0) + (1 - q) * max(-t, 0) is mathematically correct and matches the standard formulation in the literature. The piecewise definition provided in the documentation is accurate: for t > 0, PB_q(t) = q*t; for t = 0, PB_q(t) = 0; for t < 0, PB_q(t) = (1-q)*t.

The documentation correctly notes that as the pinball loss is only linear in the residuals, quantile regression is much more robust to outliers than squared error based estimation of the mean. This property is particularly valuable when dealing with heavy-tailed distributions or contaminated datasets.

The relationship between quantile regression and the `HuberRegressor` is appropriately described, with `HuberRegressor` being "somewhat in between" ordinary least squares and quantile regression in terms of outlier robustness.

## Documentation Quality Assessment

The addition of the `.. _quantile_regression:` anchor in `doc/modules/linear_model.rst` follows the established documentation pattern and enables proper cross-referencing within the scikit-learn documentation system.

The figure reference to `/auto_examples/linear_model/images/sphx_glr_plot_quantile_regression_001.png` with a target to `../auto_examples/linear_model/plot_quantile_regression.html` provides visual support for understanding the feature. The scale of 50% and center alignment are appropriate for documentation display.

The documentation appropriately notes that conditional quantiles can also be estimated by models other than linear models, specifically mentioning `GradientBoostingRegressor` with `loss="quantile"` and `alpha` parameter set to the target quantile. This cross-referencing helps users understand the broader ecosystem of quantile estimation tools in scikit-learn.

## Integration and Compatibility

The `QuantileRegressor` is correctly added to the `linear_model` module, which is the appropriate location for linear regression models. The addition to `doc/modules/classes.rst` in the robust estimators section maintains consistency with the existing API organization.

The feature follows the established pattern of other robust estimators in scikit-learn. The documentation structure, mathematical formulation presentation, and API design are consistent with how `HuberRegressor`, `RANSACRegressor`, and `TheilSenRegressor` are documented and exposed.

The comparison with `HuberRegressor` as being "somewhat in between" quantile regression and squared error methods is technically accurate and helps users understand the trade-offs between different robust regression approaches.

## Recommendations

Based on this review, the quantile regression feature is well-designed and properly integrated into scikit-learn. The mathematical formulation is correct, the API follows established conventions, and the documentation is comprehensive.

For users of this feature, it is recommended to use `mean_pinball_loss` for model evaluation and to consider the trade-off between the `alpha` penalty and model complexity. The feature is particularly useful for prediction interval estimation when error distributions are non-normal or heteroscedastic.

Future maintenance should focus on ensuring the implementation remains consistent with the documented mathematical formulation and that any updates to the pinball loss metric are reflected in both the estimator and the evaluation metric.
