# PR #6258 description and discussion


# Seed Material: psf/requests#6258: Add an Example for automatic retries to the Advanced Usage docs
Source: github_issue_pr
Identifier: pr:psf/requests#6258

Repository: psf/requests
PR Number: #6258
PR Title: Add an Example for automatic retries to the Advanced Usage docs
Merged At: 2023-07-03T20:38:22Z
Changed Files: 1
Additions: +22, Deletions: -0

## PR Description
While Requests doesn't automatically retry failures, this is an extremely common advanced use case in real world applications.

Although there's a mention of this capability in the [`HTTPAdapter` API docs](https://requests.readthedocs.io/en/latest/api/#requests.adapters.HTTPAdapter), it's a bit buried and not very specific.

The ubiquity of the use case fits perfectly in the [Transport Adapters section of the Advanced Usage docs](https://requests.readthedocs.io/en/latest/user/advanced/#transport-adapters), so I thought it would be useful to have a simple Example of this capability.

I took a stab at such an addition, and tried to follow the style of the rest of the docs pretty closely.

Linking over to the [`urllib3.util.Retry` docs](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry) seems like it should reinforce the fact that Requests isn't the owner of that code and that library should be consulted with questions about that class (rather than Requests' support of it).

I'm curious if maintainers have any feedback about the content or code example. Specifically I was curious whether you have any opinions as to the appropriate standard for the `Retry` import. While `urllib3.util.Retry` is where the class lives and what the `urllib3` docs reference, `from urllib3 import Retry` also works, and in some StackOverflow posts I've seen people use `from requests.adapters import Retry`. I felt that last one would telegraph an ownership by Requests that would be undesirable, but I'm wondering if anyone is particularly picky about the best practice for that import.

Also, let me know if this is non-trivial enough to add a HISTORY entry for.

## Diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index c664a83d30..055c88a956 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -1026,8 +1026,30 @@ library to use SSLv3::
                 num_pools=connections, maxsize=maxsize,
                 block=block, ssl_version=ssl.PROTOCOL_SSLv3)
 
+Example: Automatic Retries
+^^^^^^^^^^^^^^^^^^^^^^^^^^
+
+By default, Requests does not retry failed connections. However, it is possible
+to implement automatic retries with a powerful array of features, including
+backoff, within a Requests :class:`Session <requests.Session>` using the
+`urllib3.util.Retry`_ class::
+
+    from urllib3.util import Retry
+    from requests import Session
+    from requests.adapters import HTTPAdapter
+
+    s = Session()
+    retries = Retry(
+        total=3,
+        backoff_factor=0.1,
+        status_forcelist=[502, 503, 504],
+        allowed_methods={'POST'},
+    )
+    s.mount('https://', HTTPAdapter(max_retries=retries))
+
 .. _`described here`: https://kenreitz.org/essays/2012/06/14/the-future-of-python-http
 .. _`urllib3`: https://github.com/urllib3/urllib3
+.. _`urllib3.util.Retry`: https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry
 
 .. _blocking-or-nonblocking:
 
