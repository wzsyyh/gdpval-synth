# Release Design Doc - HTTPX 0.23.0

# Release Design Doc - HTTPX 0.23.0

Release Design Doc - HTTPX 0.23.0

Version: 0.23.0 | Release Date: 23rd May, 2022

## Release Overview

HTTPX version 0.23.0, released on 23rd May, 2022, is a median point release that introduces two major changes alongside numerous bug fixes. The release drops support for Python 3.6 (issue #2097) and changes the default character-set handling for responses, eliminating the dependency on `charset-normalizer` in favor of a default `utf-8` encoding (PR #2165, addressing discussion #2083).

The median point bump from 0.22.0 to 0.23.0 was chosen because dropping Python 3.6 support warrants a version increment that signals compatibility changes to downstream users. This release represents a focused effort to simplify the library's dependency tree and improve out-of-the-box behavior for the majority of use cases.

## Character-Set Handling Change

Previously, HTTPX used `charset-normalizer` as a fallback to automatically detect the character encoding of responses when no explicit charset was specified in the Content-Type header. This approach added an external dependency and introduced variability in encoding detection across different environments.

In version 0.23.0, the default behavior is simplified: responses are decoded using `utf-8` unless a charset is explicitly specified. This change removes the `charset-normalizer` dependency, reducing the library's dependency footprint and making behavior more predictable. For users who require automatic character-set detection (e.g., for legacy systems serving non-UTF-8 content), HTTPX provides opt-in functionality. The documentation at https://www.python-httpx.org/advanced/#character-set-encodings-and-auto-detection explains how to re-enable this feature.

This change was motivated by the discussion in issue #2083 and implemented in PR #2165. It aligns with the library's goal of providing sensible defaults while allowing advanced configuration when needed.

## Bug Fix Summary

The 0.23.0 release includes 10 bug fixes, categorized by subsystem as follows:

**URL Handling**: Fix `URL.copy_with` for some oddly formed URL cases. (#2185)

**Authentication**: Digest authentication should use case-insensitive comparison for determining which algorithm is being used. (#2204)

**Multipart Uploads**: When files are used in multipart upload, ensure we always seek to the start of the file. (#2065)

**Stream Reading**: Ensure that `iter_bytes` never yields zero-length chunks. (#2068). Close responses when task cancellations occur during stream reading. (#2156).

**CLI Client**: Fix console markup escaping in command line client. (#1866). When responses have binary output, don't print the output to the console in the command line client; use output like `<16086 bytes of binary data>` instead. (#2076). Fix display of `--proxies` argument in the command line client help. (#2125).

**Headers and Requests**: Preserve `Authorization` header for redirects that are to the same origin, but are an `http`-to-`https` upgrade. (#2074).

**Exceptions**: Fix type error on accessing `.request` on `HTTPError` exceptions. (#2158).

## Migration Impact Assessment

Users upgrading to HTTPX 0.23.0 should be aware of two primary impacts. First, applications running on Python 3.6 will need to upgrade their Python version to 3.7 or later, as support has been dropped (issue #2097). Second, applications that rely on automatic character-set detection for non-UTF-8 responses may experience decoding errors or incorrect text output.

To mitigate these risks, users should follow these steps after upgrading: (1) Verify that their application no longer targets Python 3.6. (2) For any endpoint that serves non-UTF-8 encoded content, explicitly configure the character-set detection as described in the documentation: https://www.python-httpx.org/advanced/#character-set-encodings-and-auto-detection. (3) Run comprehensive integration tests that cover all response types, including binary and non-UTF-8 text responses. (4) Monitor application logs for encoding-related warnings or errors during the transition period.

The migration path is designed to be straightforward for most users, as UTF-8 is the predominant encoding on the modern web. However, specialized applications interfacing with legacy systems should take extra care to validate their decoding behavior.

## Release Checklist

The following checklist should be completed before publishing the 0.23.0 release:

- [ ] **Version Bump Verification**: Confirm that `httpx/__version__.py` contains `__version__ = "0.23.0"` and that the CHANGELOG.md header matches.

- [ ] **Changelog Review**: Ensure all changes listed in the CHANGELOG.md under 0.23.0 are accurate and include the correct issue/PR references.

- [ ] **Dependency Updates**: Verify that `charset-normalizer` has been removed from the project's dependencies (e.g., in `setup.py` or `pyproject.toml`).

- [ ] **Testing**: Run the full test suite on Python 3.7, 3.8, 3.9, 3.10, and 3.11 to ensure compatibility and correctness.

- [ ] **Documentation Updates**: Confirm that the documentation for character-set encodings and auto-detection is published and accessible at the provided URL.

- [ ] **Release Notes**: Draft and publish release notes on GitHub and PyPI summarizing the key changes and migration guidance.
