# Design Doc: QuantileRegressor for scikit-learn

# Design Doc: QuantileRegressor for scikit-learn

This document outlines the design for the new QuantileRegressor estimator proposed in scikit-learn PR #9978. It serves as a technical specification to align implementation with the existing scikit-learn API, guide testing, and inform users of the new capability for estimating conditional quantiles.

## Overview

This design document covers the implementation of the QuantileRegressor estimator as part of scikit-learn PR #9978, which fixes issue #3148. The feature adds support for quantile regression, an algorithm that directly minimizes mean absolute error of a linear regression model.

Quantile regression estimates the median or other quantiles of y conditional on X, while ordinary least squares (OLS) estimates the conditional mean. This provides a more robust alternative to OLS, especially in the presence of outliers, because the pinball loss (linear loss) used in quantile regression is less sensitive to extreme values than squared error.

## Mathematical Formulation

The QuantileRegressor finds weights w by solving the following minimization problem: min_w (1/n_samples) * sum_i PB_q(y_i - X_i w) + alpha ||w||_1. Here, n_samples is the number of training samples, X_i is the feature vector for sample i, y_i is the target value, q is the desired quantile in (0, 1), and alpha is the regularization parameter.

The pinball loss PB_q(t) is defined as: PB_q(t) = q * max(t, 0) + (1 - q) * max(-t, 0). This can be expressed piecewise as: q*t if t > 0, 0 if t = 0, and (1-q)*t if t < 0. The pinball loss is also known as the linear loss.

The L1 penalty term alpha * ||w||_1 is similar to the penalty used in Lasso regression. It encourages sparsity in the coefficient vector w, which helps prevent overfitting and can improve model interpretability. The parameter alpha controls the strength of this regularization.

## API Design

The new estimator will be implemented as the class QuantileRegressor within the sklearn.linear_model module. This aligns with the existing structure of linear models in scikit-learn, placing it alongside related robust regressors like HuberRegressor and RANSACRegressor.

The class will expose two primary parameters: 'quantile' (float, default=0.5) which specifies the quantile q to be estimated (must be between 0 and 1 exclusive), and 'alpha' (float, default=1.0) which controls the strength of the L1 regularization penalty. The default quantile of 0.5 corresponds to median regression, which is a common use case.

The estimator will follow the standard scikit-learn API with fit(), predict(), and score() methods. After fitting, the learned coefficients w will be available as the coef_ attribute, and the intercept as intercept_. The implementation will use a linear programming solver internally to minimize the pinball loss plus L1 penalty.

## Integration Points

The integration of QuantileRegressor into scikit-learn requires updates to two documentation files: doc/modules/classes.rst and doc/modules/linear_model.rst. These files define the API reference documentation and the user guide for linear models.

In doc/modules/classes.rst, QuantileRegressor will be added to the list of linear model classes. Specifically, it should be listed alongside HuberRegressor and RANSACRegressor in the section for robust regression estimators. The PR diff shows the addition of 'linear_model.QuantileRegressor' immediately after 'linear_model.HuberRegressor'.

In doc/modules/linear_model.rst, a new section titled 'Quantile Regression' will be added. This section will contain the mathematical description, usage examples, and links to relevant figures and example plots. The content will explain the benefits of quantile regression for prediction intervals and robustness to outliers.

## Testing Strategy

Testing the QuantileRegressor requires a multi-faceted approach to ensure correctness, robustness, and integration. The test suite should cover basic functionality, mathematical correctness, and parameter sensitivity.

First, a test should verify that the estimator produces correct predictions for the median (q=0.5) on a simple synthetic dataset where the true median relationship is known. This confirms the basic fit-predict workflow functions as expected.

Second, a test should verify that the pinball loss is minimized on a synthetic dataset. This can be done by fitting the model and computing the pinball loss on the training data, then comparing it to the loss from alternative coefficient vectors to ensure the fitted coefficients achieve a lower loss.

Third, a test should verify that the regularization parameter alpha affects the coefficient magnitude. By fitting models with increasing alpha values, we can confirm that the L1 norm of the coefficient vector decreases, demonstrating the expected regularization effect.

Additional tests should check edge cases such as quantile values near 0 or 1, handling of perfect multicollinearity, and compatibility with scikit-learn's pipeline and cross-validation utilities.
