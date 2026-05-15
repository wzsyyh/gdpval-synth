# PR #2214 diff and description for HTTPX version 0


# Seed Material: encode/httpx#2214: Version 0.23.0
Source: github_issue_pr
Identifier: pr:encode/httpx#2214

Repository: encode/httpx
PR Number: #2214
PR Title: Version 0.23.0
Merged At: 2022-05-23T15:31:13Z
Changed Files: 2
Additions: +21, Deletions: -1

## PR Description
Drafting up our next release.

Since we're dropping Python 3.6, this needs to be a median point bump.

One thing I'd like to discuss before we push on with this is resolving https://github.com/encode/httpx/discussions/2083 (See PR #2165). The median point bump is a good motivator to drop our `charset-normalizer` dependancy, so it seems like an efficient use of time to address it as part of this release, if possible.

I'm planning to push on with that by addressing @[adriangb](https://github.com/adriangb)'s comment, so that we have two alternative approaches for consideration.

---

Release notes...

## 0.23.0 (23rd May, 2022)

 ### Changed

 * Drop support for Python 3.6. (#2097)
 * Use `utf-8` as the default character set, instead of falling back to `charset-normalizer` for auto-detection. To enable automatic character set detection, see [the documentation](https://www.python-httpx.org/advanced/#character-set-encodings-and-auto-detection). (#2165)

 ### Fixed

 * Fix `URL.copy_with` for some oddly formed URL cases. (#2185)
 * Digest authentication should use case-insensitive comparison for determining which algorithm is being used. (#2204)
 * Fix console markup escaping in command line client. (#1866)
 * When files are used in multipart upload, ensure we always seek to the start of the file. (#2065)
 * Ensure that `iter_bytes` never yields zero-length chunks. (#2068)
 * Preserve `Authorization` header for redirects that are to the same origin, but are an `http`-to-`https` upgrade. (#2074)
 * When responses have binary output, don't print the output to the console in the command line client. Use output like `<16086 bytes of binary data>` instead. (#2076)
 * Fix display of `--proxies` argument in the command line client help. (#2125)
 * Close responses when task cancellations occur during stream reading. (#2156)
 * Fix type error on accessing `.request` on `HTTPError` exceptions. (#2158)

## Diff
diff --git a/CHANGELOG.md b/CHANGELOG.md
index f4e940ee16..6f5e7c4256 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -4,6 +4,26 @@ All notable changes to this project will be documented in this file.
 
 The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
 
+## 0.23.0 (23rd May, 2022)
+
+### Changed
+
+* Drop support for Python 3.6. (#2097)
+* Use `utf-8` as the default character set, instead of falling back to `charset-normalizer` for auto-detection. To enable automatic character set detection, see [the documentation](https://www.python-httpx.org/advanced/#character-set-encodings-and-auto-detection). (#2165)
+
+### Fixed
+
+* Fix `URL.copy_with` for some oddly formed URL cases. (#2185)
+* Digest authentication should use case-insensitive comparison for determining which algorithm is being used. (#2204)
+* Fix console markup escaping in command line client. (#1866)
+* When files are used in multipart upload, ensure we always seek to the start of the file. (#2065)
+* Ensure that `iter_bytes` never yields zero-length chunks. (#2068)
+* Preserve `Authorization` header for redirects that are to the same origin, but are an `http`-to-`https` upgrade. (#2074)
+* When responses have binary output, don't print the output to the console in the command line client. Use output like `<16086 bytes of binary data>` instead. (#2076)
+* Fix display of `--proxies` argument in the command line client help. (#2125)
+* Close responses when task cancellations occur during stream reading. (#2156)
+* Fix type error on accessing `.request` on `HTTPError` exceptions. (#2158)
+
 ## 0.22.0 (26th January, 2022)
 
 ### Added
diff --git a/httpx/__version__.py b/httpx/__version__.py
index f08752c89c..68831d05c8 100644
--- a/httpx/__version__.py
+++ b/httpx/__version__.py
@@ -1,3 +1,3 @@
 __title__ = "httpx"
 __description__ = "A next generation HTTP client, for Python 3."
-__version__ = "0.22.0"
+__version__ = "0.23.0"
