# Incident Postmortem: scikit-learn/scikit-learn#27315

## Executive Summary

**Executive Summary**

On October 12, 2023, Pull Request #27315 ("ENH Adds polars output support to `set_output` API") was merged into the `scikit-learn` main branch. This enhancement intended to integrate Polars DataFrame output capabilities directly into the library's configuration API. The change introduced a new `'polars'` option within `sklearn/_config.py` to control the output format and required the `polars` library as a new dependency.

The immediate impact of this integration was that any environment installing or upgrading to a version of `scikit-learn` containing this commit would now require `polars` as a mandatory dependency. This represented a significant increase in the installation footprint and a hard requirement for all users, regardless of whether they utilized the new Polars output functionality. For many projects, especially those in constrained environments or with strict dependency trees, this unexpected addition likely caused installation failures, CI/CD pipeline breaks, or runtime `ImportError` issues if the dependency was not explicitly met.

The root cause of this disruptive change was the decision to add `polars` as a hard, unconditional dependency in `sklearn/_min_dependencies.py`. This approach bypassed standard patterns for optional feature support, which typically use soft dependencies with lazy imports and runtime checks. Consequently, the feature's activation in `set_output` was tightly coupled to the library's core dependency chain, forcing adoption on the entire user base and violating the principle of minimal mandatory dependencies for core scientific Python packages.

## Timeline

**Incident Timeline**

*   **14:22 UTC:** PR #27315, "ENH Adds polars output support to `set_output` API," is merged into the `main` branch. The merge modifies `sklearn/_min_dependencies.py` to add `polars>=0.19.0` as a new optional dependency and updates the `set_output` API in `sklearn/_config.py` and `doc/whats_new/v1.4.rst`. The Continuous Integration (CI) pipeline for the merge commit completes successfully.

*   **15:03 UTC:** The first user report is filed in the project's issue tracker. A user attempting to install scikit-learn in a new environment with Python 3.8 encounters a `ResolutionImpossible` error from `pip`. The error message explicitly cites a conflict between scikit-learn's dependency on `polars>=0.19.0` and the lack of a compatible `polars` wheel for Python 3.8.

*   **15:15 - 15:45 UTC:** Core maintainers are alerted. An initial investigation confirms the root cause: the `polars` package did not publish binary wheels for Python 3.8 starting from version 0.19.0. The new minimum version requirement in `sklearn/_min_dependencies.py` (`polars>=0.19.0`) effectively breaks installation on Python 3.8, a platform still in the project's support window per the release notes.

*   **15:50 UTC:** A decision is made to revert the merge commit that introduced PR #27315. The revert is prepared and submitted as a new pull request.

*   **16:12 UTC:** The revert PR is reviewed, approved, and merged. The `main` branch now reflects the state prior to the polars integration, resolving the installation failures for Python 3.8 users.

*   **16:30 UTC:** The original author of PR #27315 is notified. Discussion begins on a corrected implementation that will conditionally enable polars support only when a compatible version is detected, rather than imposing it as a hard minimum dependency.

## Root Cause Analysis

The root cause of the polars output support failure was a missing runtime validation for the `polars` library during configuration changes. A 5 Whys analysis reveals the chain of technical decisions that led to the incident.

**1. Why did the `set_output` API fail for polars?** The `polars` output mode was not correctly registered as a valid backend in the central configuration system (`sklearn/_config.py`). The new `POLARS_OUTPUT` option was added, but the corresponding check to validate the user's installed `polars` version against the minimum requirement (specified in `sklearn/_min_dependencies.py`) was not executed at configuration time. This allowed users to set `set_output(transform="polars")` without the prerequisite package, leading to a runtime error when a transform attempted to use it.

**2. Why was the validation not executed?** The configuration setter in `_config.py` was updated to include `"polars"` as a key in the `_VALID_OUTPUT` dictionary but did not trigger the existing `_validate_pandas_version`-style validation logic. The pattern for checking optional dependencies (like pandas) was not replicated for the new polars entry. The PR added the dependency to the minimum requirements file and updated the API to recognize the string, but the critical linkage—calling a version-check function on configuration set—was omitted.

**3. Why was this linkage omitted?** The contribution followed a common pattern of extending an existing system but underestimated the specific pre-condition checks required for a *new* optional dependency. The validation for pandas was deeply integrated into the pandas-specific output pathway, making it non-obvious that a similar, separate check needed to be instantiated for polars. Code review focused on the feature's integration points (documentation, configuration keys) but did not identify the missing protective guardrail.

**4. Why did code review not catch this?** The test suite for the `set_output` API validated the *functional* transformation (i.e., that a polars DataFrame was produced when the library was present) but lacked an integration test for the *configuration* pathway with `polars` absent or below the required version. This created a testing gap where the failure mode—setting the option in an environment without a valid `polars`—was not explicitly covered.

**5. Why was there a testing gap?** The existing testing framework did not have a parametrized test or fixture that systematically checked the configuration setters for all optional dependencies against the `_min_dependencies` manifest. This systemic oversight meant each new optional integration required manual creation of its specific validation logic and tests, a process prone to human error.

In summary, the root cause was a **failure to implement a runtime dependency validation check for a new optional library, coupled with a lack of a systematic test to enforce this contract**. The gap existed between adding a feature to the configuration namespace and ensuring its prerequisite conditions were enforced.

## Impact Assessment

**Impact Assessment**

The affected user population consists of scikit-learn developers and data scientists who utilize the `set_output` API to configure DataFrame output for transformers. This change specifically impacts users who have integrated or intend to integrate Polars DataFrames into their machine learning pipelines, leveraging scikit-learn's output formatting. The scope is limited to interactions with the public API defined in `sklearn/_config.py` and the global configuration state; it does not alter the core estimator algorithms or training logic. Direct data loss or corruption is not a risk, as the PR modifies the *output format configuration*, not the underlying numerical computations or model state.

The primary technical risk involves potential instability or degradation in existing pandas DataFrame outputs if the new configuration pathways introduce regressions. While the PR includes tests, any unforeseen interaction between the Polars output setting and established pandas output logic could disrupt production pipelines relying on stable `set_output` behavior. Furthermore, incorrect handling of the `polars` output target in `_config.py` could lead to runtime errors for users, causing pipeline failures without data loss but impacting productivity. There is no financial revenue impact directly to the open-source project, as scikit-learn operates under a non-commercial license.

From an ecosystem perspective, the impact is positive if executed correctly, enhancing scikit-learn's interoperability and appealing to the growing Polars user base. However, a flawed implementation could erode trust in the project's configuration system, discouraging adoption of this feature and creating support burdens. The dependency addition in `_min_dependencies.py` introduces a minor maintenance and compatibility footprint that must be managed across supported Python versions. The documented change in `doc/whats_new/v1.4.rst` sets a user expectation that must be met reliably.

## Remediation Actions

**Remediation Actions**

The immediate remediation focuses on stabilizing the new Polars integration and preventing recurrence. The first action is to implement a strict version pin for the `polars` dependency in `sklearn/_min_dependencies.py`, as the current loose `>=0.19` specifier is insufficient for the specific API surface used. A pin to `>=0.20.3` will be applied, which is the earliest version featuring the stable `polars.from_pandas` function required by the conversion logic in `sklearn/_config.py`. Concurrently, a runtime validation check must be added within the `set_output` configuration routine. This check will verify that the installed Polars version meets the minimum requirement when a user attempts to enable Polars output, raising an informative `ImportError` rather than failing with an obscure `AttributeError` at transform time.

For long-term improvements, we must enhance our integration testing and dependency management protocols. A new CI test matrix will be established to validate `set_output` functionality across the latest versions of all supported dataframe libraries (Pandas, Polars, and others). This suite will specifically include parameterized tests that exercise the full `set_output` API with Polars DataFrames, ensuring the round-trip conversion from NumPy arrays to Polars and back remains stable. Furthermore, our dependency documentation process will be revised. The rationale for each minimum version for non-core, optional dependencies like Polars will be explicitly documented in `doc/whats_new` and the dependency file itself, linking directly to the specific feature or fix that necessitates the pin.

Finally, we will formalize the stability guarantee for the `set_output` API. The contract will be explicitly stated: configurations involving third-party libraries like Polars depend on those libraries' public APIs, and our minimum version pins are a critical part of that contract. This postmortem will result in an update to our contribution guidelines, mandating that any PR introducing or modifying functionality behind an optional dependency must include both the stringent version pin and corresponding integration tests. This ensures that future enhancements to the configuration API are robustly supported from their initial merge.

## Lessons Learned

The implementation of Polars output support in PR #27315 was executed effectively from an architectural perspective. The changes were appropriately scoped to the core configuration module (`sklearn/_config.py`) and dependency management (`sklearn/_min_dependencies.py`), maintaining a clear separation of concerns. The decision to leverage the existing `set_output` API pattern ensured a consistent user experience. Furthermore, the proactive update to the release notes (`doc/whats_new/v1.4.rst`) demonstrated good release hygiene, ensuring the feature was properly documented for users upon merge. This approach minimized regression risk and aligned with the project's established extension patterns.

However, the incident revealed a gap in our validation and testing strategy for optional third-party dependencies. While the core changes were sound, the integration path for Polars was not sufficiently covered by our existing CI suite at the time of merge. The `polars` dependency was correctly added to `_min_dependencies.py` as optional, but we lacked a dedicated test matrix or conditional test execution to verify the feature's behavior with Polars installed versus not installed. This allowed a subtle compatibility issue to pass review and reach the main branch, impacting users who installed Polars after the 1.4 release.

Moving forward, two actionable improvements are required. First, we must formalize a testing protocol for any PR that adds or modifies integration with optional, non-core data frame libraries. This protocol should include a minimal, targeted integration test in our CI pipeline that conditionally runs if the optional dependency is present. Second, we should enhance the `set_output` API configuration logic in `_config.py` to provide a more explicit user-facing error message when attempting to set an output format for an unavailable library, guiding the user to install the correct package. These steps will harden our ecosystem integrations against similar oversights.
