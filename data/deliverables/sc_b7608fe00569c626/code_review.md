# Code Review: PR #5688 — Upgrade to chardet 4.x

# Code Review: PR #5688 — Upgrade to chardet 4.x

This document presents a code review of PR #5688 in the psf/requests repository, titled "Upgrade to chardet 4.x". The pull request updates the allowed version range for the chardet dependency from chardet 3.x to include chardet 4.x, enabling users and downstream consumers to benefit from the performance improvements in chardet 4.0.0. This review evaluates the dependency constraint changes, runtime compatibility checks, backward compatibility, and associated risks.

## Summary of the Change

PR #5688, titled "Upgrade to chardet 4.x", was merged on December 14, 2020. The pull request modifies exactly two files in the requests repository: `requests/__init__.py` and `setup.py`. The change adds +3 lines and removes -5 lines across both files.

The primary purpose of this PR is to widen the permitted version range for the `chardet` dependency so that chardet 4.x versions are accepted. The PR author released chardet 4.0.0 and notes in the description that it is faster and fully backward compatible with chardet 3.x, as long as consumers are not directly accessing internal models.

## Dependency Constraint Analysis

In `setup.py`, the dependency specification for chardet is changed from `'chardet>=3.0.2,<4'` to `'chardet>=3.0.2,<5'`. This means that when installing requests, any version of chardet from 3.0.2 up to but not including 5.0.0 will satisfy the dependency requirement.

The lower bound of 3.0.2 remains unchanged, which is correct since this was the minimum version requests has historically required. The upper bound is raised from 4 (exclusive) to 5 (exclusive), which opens the range to include all chardet 3.x versions from 3.0.2 onward and all chardet 4.x versions. This is an appropriate range given that the PR description states chardet 4.0.0 is fully backward compatible with chardet 3.x for normal usage.

## Runtime Compatibility Check Analysis

The `check_compatibility` function in `requests/__init__.py` performs runtime validation of the installed chardet version. The original code used three separate assert statements: `assert major == 3` (restricting to major version 3), `assert minor < 1` (restricting minor version to 0), and `assert patch >= 2` (requiring patch 2 or higher). Together, these enforced a range of chardet 3.0.2 through 3.0.x.

The new code replaces these three assertions with a single tuple comparison: `assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)`. This is a significant improvement in both clarity and correctness. The tuple comparison leverages Python's native tuple ordering semantics, where `(3, 0, 2) <= (major, minor, patch)` ensures the version is at least 3.0.2, and `(major, minor, patch) < (5, 0, 0)` ensures it is below 5.0.0.

Importantly, the old logic had a subtle issue: `assert minor < 1` meant it would reject chardet 3.1.0, 3.2.0, etc. The comment in the original code said "chardet >= 3.0.2, < 3.1.0", so this was intentional but restrictive. The new comment reads "chardet >= 3.0.2, < 5.0.0", and the new assertion correctly matches this range. The new logic properly accepts any chardet version from 3.0.2 through 4.x.x, which aligns with the goal of supporting chardet 4.x.

## Backward Compatibility Assessment

According to the PR description, chardet 4.0.0 is "fully backward compatible with chardet 3.x (as long as you aren't mucking around in the models it uses under-the-hood directly)." This means that the public API of chardet that requests relies upon has not changed, and existing functionality should continue to work without modification.

The requests library uses chardet for character encoding detection in HTTP responses, and it does not interact with chardet's internal models directly. Therefore, the backward compatibility caveat about internal model access does not apply to requests. The upgrade to chardet 4.x should be seamless for requests users.

## Risk Assessment and Recommendations

The PR description notes that "the next major release will be Python 3.6+", referring to a future chardet release beyond 4.x. The current chardet 4.0.0 does not impose this restriction yet, but the upper bound of `< 5` in the dependency constraint would prevent any future major release with breaking Python version requirements from being automatically installed. This is a reasonable safety measure.

One minor observation is that the original runtime check in `check_compatibility` was more restrictive, only accepting chardet 3.0.x. The new check widens the accepted range significantly to include all of chardet 4.x. While the PR description assures backward compatibility, there is inherently slightly more surface area for potential issues when accepting a wider range of versions. However, given that chardet 4.0.0 was explicitly designed to be backward compatible and the PR was merged by the requests maintainers, the risk is low.

Recommendation: This change is safe for production adoption. The dependency constraint and runtime checks are correctly updated to allow chardet 4.x while maintaining appropriate boundaries. The backward compatibility assurance from the chardet author, combined with the defensive upper bound of < 5.0.0, makes this a well-structured dependency upgrade.
