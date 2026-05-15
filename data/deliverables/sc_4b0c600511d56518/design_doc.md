# Release Engineering Plan - HTTPX 0.23.0

# Release Engineering Plan - HTTPX 0.23.0

## Summary

HTTPX version 0.23.0 was released on 23rd May, 2022. This release bumps the project version from 0.22.0 to 0.23.0 in `httpx/__version__.py` and introduces two breaking changes: the removal of Python 3.6 support and the replacement of the `charset-normalizer` dependency with a default `utf-8` character set encoding. The release also includes ten bug fixes addressing issues across URL handling, authentication, the command-line client, streaming, multipart uploads, and redirect behavior.

## Motivation

The decision to drop Python 3.6 support was driven by the need to align with the Python ecosystem's lifecycle, as referenced in issue #2097. The replacement of `charset-normalizer` with a default `utf-8` encoding was motivated by discussion #2083, which proposed simplifying the dependency tree. PR #2165 introduced an alternative approach for users who require automatic character set detection, allowing the core library to remove the `charset-normalizer` dependency entirely. The median point bump from 0.22.0 to 0.23.0 was chosen to signal these breaking changes clearly to downstream consumers, as a minor version increment in the 0.x series indicates backward-incompatible modifications.

## Affected Components

Two files were modified in PR #2214. First, `CHANGELOG.md` received a new section documenting the 0.23.0 release, including the two 'Changed' items and ten 'Fixed' items with their associated issue numbers. Second, `httpx/__version__.py` had its `__version__` string updated from `"0.22.0"` to `"0.23.0"` to reflect the new release. No other source code files were altered in this PR, as the functional changes were already merged in prior pull requests.

## Migration Guide for Downstream Users

For users currently running HTTPX on Python 3.6, the immediate migration step is to upgrade to Python 3.7 or later. Python 3.6 reached end-of-life in December 2021, and this release formalizes HTTPX's minimum supported version as Python 3.7. Users should update their CI configurations, dependency files, and deployment environments accordingly.

For users who rely on automatic character set detection, the default behavior has changed from using `charset-normalizer` to assuming `utf-8`. To re-enable auto-detection, users must explicitly configure the client as described in the official documentation at https://www.python-httpx.org/advanced/#character-set-encodings-and-auto-detection. This involves installing the optional dependency and passing the appropriate parameter when constructing the HTTPX client.

## Bug Fixes Included

The release includes ten bug fixes, grouped by subsystem as follows:

**URL Handling:**
- Fix `URL.copy_with` for some oddly formed URL cases. (#2185)

**Authentication:**
- Digest authentication should use case-insensitive comparison for determining which algorithm is being used. (#2204)

**Command-Line Client (CLI):**
- Fix console markup escaping in command line client. (#1866)
- When responses have binary output, don't print the output to the console in the command line client. Use output like `<16086 bytes of binary data>` instead. (#2076)
- Fix display of `--proxies` argument in the command line client help. (#2125)

**Streaming:**
- Ensure that `iter_bytes` never yields zero-length chunks. (#2068)
- Close responses when task cancellations occur during stream reading. (#2156)

**Multipart Uploads:**
- When files are used in multipart upload, ensure we always seek to the start of the file. (#2065)

**Redirects:**
- Preserve `Authorization` header for redirects that are to the same origin, but are an `http`-to-`https` upgrade. (#2074)

**Exception Handling:**
- Fix type error on accessing `.request` on `HTTPError` exceptions. (#2158)

## Release Checklist

Before tagging and publishing the 0.23.0 release, the following checklist should be completed:

1. Verify that `httpx/__version__.py` contains `__version__ = "0.23.0"`.
2. Confirm that `CHANGELOG.md` includes the full release notes for version 0.23.0 as merged in PR #2214.
3. Run the complete test suite to ensure no regressions were introduced by the breaking changes or bug fixes.
4. Update the project documentation site to reflect the new default character set behavior and the dropped Python 3.6 support.
5. Create a git tag for `0.23.0` and publish the release to PyPI.
6. Notify downstream consumers via the project's communication channels (GitHub releases, mailing list, social media).
