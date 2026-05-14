# Design Document: HTML Visualization for Estimators (PR #14180)

## Overview

This design document details the implementation of the HTML visualization feature for scikit-learn estimators, introduced in Pull Request #14180. The feature provides a rich, interactive HTML representation of estimator objects, designed primarily for display within Jupyter notebooks and JupyterLab environments.

The feature was authored by Thomas Fan and closes the corresponding issue #14061. A core design principle of this implementation is that it is built entirely with pure HTML and CSS, requiring no JavaScript or external dependencies. This ensures maximum compatibility and ease of integration into various notebook environments.

## API Design

The public API for this feature is exposed through the function `estimator_html_repr`, which is added to the `sklearn.utils` module. This function accepts an estimator object and returns a string containing its complete HTML representation.

The primary way to activate the visualization within a Jupyter context is through the global configuration setting. Users call `sklearn.set_config(display='diagram')`. Once set, simply displaying an estimator object (e.g., by evaluating its variable in a notebook cell) will render the interactive HTML diagram.

Internally, the layout logic for composite (meta) estimators is determined by a private function `_type_of_html_estimator`. This function classifies meta-estimators into two layout types: 'parallel' for transformers that apply operations side-by-side (such as `ColumnTransformer` and `FeatureUnion`), and 'serial' for pipelines where steps are executed sequentially (like `Pipeline`). The system is designed to be easily extensible to other meta-estimators by adding them to this function.

## Rendering Architecture

The visualization renders an interactive diagram where users can hover over individual estimator elements to see their parameters. This interactivity is achieved purely through CSS, specifically using the `:hover` pseudo-class to toggle the visibility of parameter detail overlays.

A notable implementation detail is the inclusion of a hidden `<div>` element with the id `sk-final-spacer`. This element acts as a layout hack, providing sufficient space at the bottom of the visualization to ensure that parameter information displayed on hover is not clipped or obscured by the notebook interface.

By default, the visualization uses a `print_changed_only=True` setting when generating the HTML for `export_html`. This means only the parameters that differ from the estimator's default values are displayed, keeping the diagram concise and focused on the user's configuration choices.

## Configuration & Activation

The HTML visualization feature can be activated globally for a session using the scikit-learn configuration system. The relevant setting is `display`, which must be set to the string `'diagram'`. This is done by calling `from sklearn import set_config` and then `set_config(display='diagram')`.

For use cases outside of a live Jupyter session, or to save the visualization for later inspection, the raw HTML string can be obtained programmatically using the `estimator_html_repr` function. The documentation provides the following pattern: `from sklearn.utils import estimator_html_repr`, followed by writing the result to a file (e.g., `with open('my_estimator.html', 'w') as f: f.write(estimator_html_repr(clf))`).

## Integration with Existing Codebase

The integration of this feature involved updates to the project's documentation to describe the new functionality and API. The following files were modified as part of the pull request:

1. `doc/modules/classes.rst`: A new entry for `utils.estimator_html_repr` was added to the API reference documentation, under the 'Plotting' section.

2. `doc/modules/compose.rst`: A new subsection titled 'Visualizing Composite Estimators' was added. This section explains the `display='diagram'` configuration and provides a code example for writing the HTML to a file.

3. `doc/whats_new/v0.23.rst`: Two changelog entries were added. One under the `sklearn.utils` module section, noting the addition of `utils.estimator_html_repr` as a feature. A second, more general entry was added under the 'Miscellaneous' section, highlighting the major feature of HTML representation in Jupyter.

## Example Usage

The following example, reconstructed from the PR description, demonstrates the feature with a complex composite estimator. It showcases the use of `ColumnTransformer`, `FeatureUnion`, `Pipeline`, and a `VotingClassifier`.

```python
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.feature_selection import SelectPercentile
from sklearn.inspection import display_estimator

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median'))])

feat_u2 = FeatureUnion([
    ('pca', PCA(n_components=1)),
    ('svd', Pipeline([('tsvd1', TruncatedSVD(n_components=2)),
                      ('select', SelectPercentile())]))
])

numeric_transformer2 = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('scaler', StandardScaler(with_std=False)),
    ('feats', feat_u2)
])

categorical_features = ['embarked', 'sex', 'pclass']
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', missing_values='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', drop='first'))])

preprocessor = ColumnTransformer(
    transformers=[
        ('num1', numeric_transformer, numeric_features),
        ('num2', numeric_transformer2, numeric_features),
        ('cat', categorical_transformer, categorical_features)])

feat_u = FeatureUnion([
    ('pca', PCA(n_components=1, whiten=True, svd_solver='full')),
    ('svd', TruncatedSVD(n_components=2, n_iter=10))])

clf1 = LogisticRegression(solver='lbfgs', multi_class='multinomial',
                         random_state=1, max_iter=200)
clf2 = RandomForestClassifier(n_estimators=50, random_state=1, max_depth=8,
                             warm_start=True, n_jobs=3, oob_score=True)
clf3 = GaussianNB()
eclf1 = VotingClassifier(estimators=[
    ('lr', clf1), ('rf', clf2), ('gnb', clf3)], voting='hard')

clf = Pipeline(steps=[('preprocessor', preprocessor),
                      ('feat_u', feat_u),
                      ('classifier', eclf1)])
display_estimator(clf)
```

The final call to `display_estimator(clf)` triggers the rendering of the interactive HTML diagram within the notebook environment.
