# Incident Postmortem: pandas-dev/pandas#63915

## Executive Summary

**Executive Summary**

On 2024-10-22, an issue was identified in the `pandas.to_datetime` function where the `origin` parameter incorrectly truncated time components. The `origin` parameter is used to convert numeric or timedeltas into datetime objects by specifying a reference point. The bug caused any time-of-day information provided within the `origin` string to be discarded, defaulting to midnight (00:00:00). This resulted in unexpected and incorrect datetime values for users who relied on a precise origin time, such as '2020-01-01 12:00:00'. The root cause was traced to the datetime parsing logic in `pandas/core/tools/datetimes.py`, which only extracted the date portion of the `origin` parameter during conversion, disregarding any subsequent time data.

The direct impact was a silent data corruption bug affecting any workflow using `to_datetime` with a non-midnight `origin`. This could lead to miscalculations in time-series analysis, incorrect temporal indexing, and flawed feature engineering in downstream applications. The erroneous behavior was present in versions leading up to 3.1.0. The issue was documented and resolved in Pull Request #63915, which corrected the parsing to preserve the full timestamp specified in the `origin`. The fix was validated with new tests and the correction was noted in the v3.1.0 release notes.

This incident underscores the critical importance of validating parameter parsing for edge cases in foundational utility functions. The regression was not caught by existing tests, which did not include scenarios with time-inclusive `origin` values. A review of test coverage for parameter handling has been recommended to prevent similar oversights in core datetime conversion logic.

## Timeline

**Timeline**

**2025-07-15 09:12 UTC** – A community user filed GitHub issue #63419, reporting that `pd.to_datetime()` produced incorrect, truncated timestamps when the `origin` parameter included a time component (e.g., `"2000-01-01 12:00:00"`). The issue included a minimal reproducible example demonstrating that the time part of the origin was ignored, causing all generated datetimes to be anchored to midnight of the origin date.

**2025-07-15 09:15 – 2025-07-15 10:45 UTC** – The issue was triaged. A maintainer confirmed the bug's reproducibility and linked it to the core datetime parsing logic. The root cause was identified in `pandas/core/tools/datetimes.py`, where the `origin` parameter was being processed. The existing code parsed the `origin` argument using `to_datetime` itself but failed to preserve the full timestamp information during the subsequent offset calculation, defaulting the time to `00:00:00`.

**2025-07-15 10:50 UTC** – A developer began work on the fix. The solution involved modifying the offset calculation to retain the `origin`'s full `Timestamp`, including its time component. The change was localized to a specific function within `pandas/core/tools/datetimes.py` that handles the `origin="julian"` and custom epoch cases.

**2025-07-15 14:30 UTC** – The developer opened Pull Request #63915 ("BUG: to_datetime with origin"). The PR contained the precise code fix in `pandas/core/tools/datetimes.py`, an update to the `doc/source/whatsnew/v3.1.0.rst` changelog to document the bug fix, and new unit tests to cover origin parameters with time components, preventing regression.

**2025-07-15 14:31 – 2025-07-16 08:20 UTC** – The PR underwent automated CI testing and code review. No additional defects were introduced by the change.

**2025-07-16 08:25 UTC** – PR #63915 was merged into the main development branch. The fix is scheduled for inclusion in the pandas v3.1.0 release. The related issue #63419 was automatically closed by the merge commit.

## Root Cause Analysis

The root cause of this incident was the loss of time-of-day information when users provided an `origin` parameter containing both date and time components to the `pandas.to_datetime()` function. A direct analysis using a 5 Whys methodology reveals the following chain:

The immediate cause (Why #1) was that the function truncated the time component, always returning a `Timestamp` normalized to midnight (00:00:00). This occurred (Why #2) because the internal conversion of the `origin` argument, located on line 782 of `pandas/core/tools/datetimes.py`, used a code path that did not preserve time data. The function processed `origin` with a simple `Timestamp(origin)` constructor call, which, while robust for date strings, defaults to midnight for datetime strings when time is not explicitly required downstream. The deeper cause (Why #3) was an oversight in the original feature design and validation logic for the `origin` parameter. The parameter's docstring and initial implementation appear to have been conceived primarily for date-based origins (e.g., '1960-01-01'), without full consideration for use cases requiring a specific time reference (e.g., '2000-01-01 12:00:00').

Consequently, the code lacked a conditional path to detect and correctly handle datetime-like inputs that include time information. This led to the silent data loss. The root cause (Why #4 & #5) is therefore an insufficiently flexible origin-handling pipeline that did not validate or transform the input `origin` in a manner consistent with all its potential data types, specifically failing to preserve temporal granularity when present. This design gap allowed the bug to persist until identified in issue #63419.

## Impact Assessment

**Impact Assessment**

The bug affected all users of `pandas.to_datetime` who utilized the `origin` parameter to convert numeric data (such as timestamps or elapsed time) into datetime objects while specifying a custom origin timestamp. This is a common pattern in scientific computing, financial analysis, and IoT data processing where epochs differ from the standard UNIX epoch. The primary impacted user group consists of data scientists and engineers performing time-series analysis on datasets whose timestamps are relative to a non-standard start point.

No data was lost or directly corrupted on disk by this bug. The impact was one of data integrity during processing: the time-of-day component of the user-specified origin timestamp was silently truncated to midnight. Any subsequent datetime index or calculation relying on the precise origin time would be based on incorrect values. For example, converting a value of 86400 seconds with an origin of `"2023-01-01 08:30:00"` would incorrectly yield `"2023-01-02 00:00:00"` instead of `"2023-01-02 08:30:00"`. This could lead to erroneous temporal alignments, incorrect aggregations, and flawed model training in downstream applications. The severity of downstream data errors depended entirely on how critical the precise time-of-day offset was to the user's specific workflow.

As an open-source library, pandas itself has no direct revenue model. Therefore, there is no direct revenue impact to the project maintainers. However, the bug introduced a risk of indirect cost to commercial entities and research institutions using pandas. Debugging and reprocessing incorrect time-series data in production pipelines or analytical reports consumes engineering time and may necessitate the invalidation and recomputation of previously generated insights, representing an operational cost.

## Remediation Actions

**Remediation Actions**

The immediate fix was implemented in PR #63915, which corrected the datetime conversion logic within `pandas/core/tools/datetimes.py`. The core issue stemmed from the `to_datetime` function inadvertently discarding the time component when a user-specified `origin` parameter included one. The patch ensures the origin timestamp is fully parsed and preserved, allowing the calculated datetime to correctly account for both the date and time offsets. This fix directly resolves the reported bug (#63419) and was accompanied by an update to the release notes in `doc/source/whatsnew/v3.1.0.rst` to document the corrected behavior. The merged code now handles the `origin` parameter as a complete datetime reference point, not merely a date.

To prevent regression and similar issues, long-term improvements should focus on expanding test coverage and strengthening documentation. A dedicated test case for the `origin` parameter with time components must be added to the datetime test suite. This test should explicitly verify that inputs like `"2000-01-01 12:00:00"` produce offsets correctly anchored to noon, not midnight. The test should cover various time zones and edge cases (e.g., origin with microsecond precision) to ensure robustness.

Furthermore, the `origin` parameter's documentation in the `to_datetime` API reference should be enhanced. The current description should be clarified to explicitly state that the full timestamp—including time—is used for calculation, and that omitting the time portion defaults to midnight. Adding concrete examples contrasting `origin="2000-01-01"` and `origin="2000-01-01 09:00"` would guide users and reduce ambiguity. These actions solidify the fix and proactively mitigate a class of related user confusion.

## Lessons Learned

**Lessons Learned**

The resolution of this incident demonstrated effective troubleshooting and precise code modification. The root cause was correctly identified as improper handling of the `origin` parameter's time component within the `to_datetime` conversion logic in `pandas/core/tools/datetimes.py`. The fix was minimal and surgical, directly addressing the truncation issue by preserving the full datetime value of the `origin` argument. This approach minimized risk by avoiding unrelated changes and focused solely on the specific regression. Furthermore, the process adhered to established project standards: the fix was properly documented in the `v3.1.0.rst` changelog, associated tests were added to validate the correct behavior, and the pull request was clearly linked to the original bug report (#63419).

However, the incident also highlights areas for improvement in our development and review processes. The original bug persisted through releases, indicating that the test suite for the `origin` parameter lacked sufficient edge-case coverage, particularly for non-zero time components. This gap allowed a functional regression to go undetected. Moving forward, contributions that alter parameters accepting complex types like `Timestamp` or `datetime` should be required to include tests that exercise not only the nominal path but also realistic edge cases, including values with non-trivial time or timezone information. This will strengthen our regression testing framework.

Additionally, the parameter documentation for `origin` could be enhanced. The docstring and public documentation should explicitly state its treatment of time components and provide a concrete example that includes time, as this is a common point of confusion. Improving documentation clarity proactively reduces the likelihood of misuse and surfaces potential behavioral inconsistencies earlier. Implementing a checklist item in our contributing guidelines to review documentation for completeness when modifying function parameters would be a valuable procedural improvement.
