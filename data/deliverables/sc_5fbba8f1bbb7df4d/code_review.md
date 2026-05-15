# Code Review: psf/requests#6258 - Add Example for Automatic Retries

# Executive Summary

PR #6258 adds a concise and useful "Example: Automatic Retries" subsection to the Transport Adapters section of the Advanced Usage documentation. The example correctly demonstrates a common and important use case—configuring automatic retries with backoff—that is currently underrepresented in the official docs. The contributor followed the existing documentation style closely, and the code example is technically sound. This review recommends the PR is ready for merge after addressing the import style question and confirming no changelog entry is needed. This change will significantly improve discoverability of a critical advanced feature for Requests users.

# Technical Accuracy

The code example is technically correct and demonstrates a valid configuration for `urllib3.util.Retry`.

-   **`total=3`**: Correctly sets the maximum number of retries.
-   **`backoff_factor=0.1`**: A valid factor for exponential backoff between retries. The urllib3 documentation states this will sleep for `{backoff_factor} * (2 ** ({number_of_retries} - 1))` seconds.
-   **`status_forcelist=[502, 503, 504]`**: Correctly targets common server error status codes that are appropriate for retries.
-   **`allowed_methods={'POST'}`**: This is the correct, non-deprecated parameter. The example appropriately uses this over the older `method_whitelist` parameter, aligning with modern urllib3 (v2+) conventions. Note: It is a `set` literal, which is correct.
-   **Adapter Mounting**: The pattern `s.mount('https://', HTTPAdapter(max_retries=retries))` is the standard and correct way to attach a retry configuration to a session for HTTPS traffic.

The example is safe, functional, and represents a good practice. There are no technical errors.

# Style and Consistency

The new section is well-integrated into the existing document structure.

-   **Heading Level**: The new subsection uses `^^^^^^^^^^^^^^^^^^^^^^^^^^` (caret) for its underline, which is consistent with the `Example` sub-sub-sections used elsewhere in the Transport Adapters section (e.g., after the SSLv3 example). This is the correct level for a sub-example.
-   **Introductory Text**: The opening sentence "By default, Requests does not retry failed connections..." is clear and sets the context appropriately. It mirrors the declarative style of other introductory sentences in the document.
-   **Code Block**: The example uses a `::` directive for the code block, which is the standard RST convention used throughout the file for literal blocks. The indentation and formatting are correct.
-   **Cross-Reference**: The new text includes a proper RST role for the Session class: `:class:`Session <requests.Session>``. This matches the format used elsewhere in the file.
-   **External Link**: The addition of the `.. _`urllib3.util.Retry`:` link target at the end of the file, near the other urllib3 links, is the correct place. The URL `https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry` points to the official and current documentation for that class. The use of backticks in the link name (`urllib3.util.Retry`) follows the existing pattern for the `urllib3` link target.
-   **Placement**: The new example is logically placed immediately after the existing SSLv3 example (`ssl_version=ssl.PROTOCOL_SSLv3`), keeping related Transport Adapter examples together. This is good organization.

The change adheres to the project's documentation style guide as evidenced by the surrounding content.

## Responses to Contributor Questions

The contributor asked two specific questions in the PR description, which are addressed below.

### Recommendation on Retry Import Style

**Recommendation:** Use `from urllib3.util import Retry` as shown in the submitted code example.

**Justification:**
1.  **Clarity and Accuracy**: The `urllib3.util.Retry` class is defined within the `urllib3.util` module. The import `from urllib3.util import Retry` is the most precise and explicit path. It directly mirrors the qualified class name shown in the official urllib3 documentation at the linked URL (https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry).
2.  **Library Boundaries**: Using `from urllib3 import Retry` also works due to urllib3's package `__init__.py`, but it is less explicit about the module location. The `urllib3.util` path is preferred for documentation as it teaches the correct module structure.
3.  **Avoiding Ownership Confusion**: The import `from requests.adapters import Retry` must be avoided. While it may work in some environments due to re-exports, it incorrectly implies that the `Retry` class is part of the Requests library. This could mislead users about where to seek support or file issues, contrary to the contributor's stated goal. Requests' role is to provide the `HTTPAdapter` that *consumes* the `Retry` object; it does not own or maintain the `Retry` class itself.

The import in the PR diff (`from urllib3.util import Retry`) is the correct and recommended style.

### Necessity of HISTORY Entry

**Recommendation:** No HISTORY entry (changelog update) is required for this change.

**Justification:** The `HISTORY.rst` file in the Requests repository is used to document notable changes in functionality, bug fixes, and major documentation updates that affect user-facing behavior or setup. The addition of a documentation example is a purely pedagogical change. It does not alter any library code, public API, or installation process. Project convention, as seen in past HISTORY entries, is to not list minor documentation improvements or new examples. Therefore, this change does not warrant a changelog entry. The contributor can merge the PR without updating HISTORY.

# Action Items

**Required Changes (Before Merge):**

None. The technical content is accurate, the style is consistent, and the import style question has been resolved in favor of the submitted code. No modifications are necessary.

**Optional Suggestions for Improvement:**

1.  Consider adding a brief note or link in the introductory paragraph explaining that `urllib3.util.Retry` provides many more configuration options (e.g., `respect_retry_after_header`, `raise_on_redirect`) and that users should consult the linked urllib3 documentation for the full API. This would further reinforce the boundary between Requests and urllib3.
2.  The status codes `502, 503, 504` are excellent common choices. As a minor point for completeness, one could note that these are server errors, but the contributor's choice is standard and appropriate.

**Merge Readiness:** This PR is ready for merge. The contribution successfully addresses a gap in the documentation by providing a clear, real-world example of a common advanced use case. I recommend approving and merging after the contributor has had a chance to review these comments.
