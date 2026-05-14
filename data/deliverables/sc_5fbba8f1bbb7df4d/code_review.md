# Code Review: PR #6258 - Add an Example for automatic retries to the Advanced Usage docs

# Code Review: PR #6258 - Add an Example for automatic retries to the Advanced Usage docs

## Executive Summary

This review recommends approving PR #6258 with minor modifications. The proposed addition of an 'Example: Automatic Retries' section to the Advanced Usage documentation is a valuable contribution that addresses a common and underdocumented use case. The code example is technically sound and follows the style of the existing documentation. The primary points for discussion are the import style for `Retry` and the potential need for a HISTORY entry. With minor editorial adjustments and a decision on the import standard, this change is ready for merge.

## Content and Technical Accuracy

The code example correctly demonstrates the integration of `urllib3.util.Retry` with a `requests.Session` and `HTTPAdapter`. The `Retry` object is instantiated with four parameters: `total=3`, `backoff_factor=0.1`, `status_forcelist=[502, 503, 504]`, and `allowed_methods={'POST'}`. These parameters are all valid attributes of the `urllib3.util.Retry` class and are configured in a manner consistent with a realistic retry strategy for transient server errors. Setting `total=3` allows up to three retries, which is a common default. The `backoff_factor=0.1` will introduce a small, growing delay between retries, which is a best practice to avoid overwhelming the server. The `status_forcelist` correctly targets common 5xx gateway errors that are often transient. The `allowed_methods` parameter restricts retries to `POST` requests, which is an important safety consideration to avoid non-idempotent operations unless explicitly intended. The example mounts this configured adapter to the `https://` scheme, making it active for all HTTPS requests made by the session. This is a complete, self-contained example that effectively illustrates the feature.

## Documentation Style and Consistency

The new section follows the existing documentation style. The heading 'Example: Automatic Retries' uses the `^^^^` underline character, which is consistent with the third-level heading format used for other examples within the 'Transport Adapters' section of the Advanced Usage guide. The introductory text is clear and concise, correctly noting that Requests does not retry by default and that this capability comes from urllib3. The RST link definition `.. _`urllib3.util.Retry`: ...` is placed correctly among the other link definitions at the end of the relevant code block. The link target points to the correct urllib3 documentation URL (`https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry`). The placement of the new section, immediately after the existing 'SSLv3' example and before the link definitions, is logical and maintains the flow of the document.

## Import Style Feedback

The PR author has raised a pertinent question about the best practice for importing the `Retry` class. The three options are: (1) `from urllib3.util import Retry`, (2) `from urllib3 import Retry`, and (3) `from requests.adapters import Retry`. Option (3) should be avoided as it falsely implies that Requests owns or defines the `Retry` class, which could mislead users about where to seek support or documentation, and could become a maintenance issue if urllib3 ever changes its internal structure. Option (2) `from urllib3 import Retry` works because `urllib3` re-exports it from its top-level namespace for convenience, but this is not the canonical location as defined in urllib3's own documentation. Option (1) `from urllib3.util import Retry` is the canonical import path as used in the urllib3 documentation (e.g., in the urllib3.util.Retry class reference). Therefore, the import style chosen in the PR (`from urllib3.util import Retry`) is the recommended best practice. It is explicit, aligns with the upstream library's documentation, and correctly signals to the user where the class is defined.

## Specific Comments and Suggestions

## HISTORY Entry

Regarding the author's question, this change does not warrant a HISTORY entry. HISTORY entries in the Requests project are typically reserved for changes that affect the library's public API, behavior, or core functionality. This PR is a documentation-only change that adds an example. While valuable to users, it does not alter how the library behaves or what it exposes. Therefore, it should not be documented in the HISTORY file.
