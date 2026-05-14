# The full diff of PR psf/requests#5797


# Seed Material: psf/requests#5797: Switch LGPL'd chardet for MIT licensed charset_normalizer
Source: github_issue_pr
Identifier: pr:psf/requests#5797

Repository: psf/requests
PR Number: #5797
PR Title: Switch LGPL'd chardet for MIT licensed charset_normalizer
Merged At: 2021-07-06T23:55:02Z
Changed Files: 10
Additions: +119, Deletions: -27

## PR Description
At least for Python 3 -- charset_normalizer doesn't support Python2, so for that chardet is still used -- this means the "have chardet" path is also still tested.

Although using the (non-vendored) chardet library is fine for requests itself, but using a LGPL dependency the story is a lot less clear for downstream projects, particularly ones that might like to bundle requests (and thus chardet) in to a single binary -- think something similar to what docker-compose is doing. By including an LGPL'd module it is no longer clear if the resulting artefact must also be LGPL'd.

By changing out this dependency for one under MIT we remove all license ambiguity.

As an "escape hatch" I have made the code so that it will use chardet first if it is installed, but we no longer depend upon it directly, although there is a new extra added, `requests[lgpl]`. This should minimize the impact to users, and give them an escape hatch if charset_normalizer turns out to be not as good. (In my non-exhaustive tests it detects the same encoding as chartdet in every case I threw at it)

I've read https://github.com/psf/requests/pull/4115, https://github.com/psf/requests/issues/3389, and https://github.com/chardet/chardet/issues/36#issuecomment-768281452 so I'm aware of the history, but I hope that the approach in this PR will allow this to be merged, as right now, the Apache Software Foundation doesn't allow projects to depend upon LGPL'd code (this is something I'm trying to get changed, but it is a _very_ slow process)


## Diff (first 3000 chars)
diff --git a/.gitignore b/.gitignore
index dd9e006f35..de61154e3e 100644
--- a/.gitignore
+++ b/.gitignore
@@ -23,6 +23,12 @@ env/
 
 .workon
 
+# in case you work with IntelliJ/PyCharm
+.idea
+*.iml
+.python-version
+
+
 t.py
 
 t2.py
diff --git a/HISTORY.md b/HISTORY.md
index 0331d187f7..9b08a7f2d6 100644
--- a/HISTORY.md
+++ b/HISTORY.md
@@ -6,6 +6,22 @@ dev
 
 -   \[Short description of non-trivial change.\]
 
+**Dependencies**
+
+- Instead of `chardet`, use the MIT-licensed `charset_normalizer` for Python3
+  to remove license ambiguity for projects bundling requests. If `chardet`
+  is already installed on your machine it will be used instead of `charset_normalizer`
+  to keep backwards compatibility.
+
+  You can also install `chardet` while installing requests by
+  specifying `[use_chardet_on_py3]` extra as follows:
+
+    ```shell
+    pip install "requests[use_chardet_on_py3]"
+    ```
+
+  Python2 still depends upon the `chardet` module.
+
 2.25.1 (2020-12-16)
 -------------------
 
@@ -1707,4 +1723,3 @@ This is not a backwards compatible change.
 
 -   Frustration
 -   Conception
-
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index aa4b1ddb6a..34d400d513 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -697,10 +697,22 @@ Encodings
 When you receive a response, Requests makes a guess at the encoding to
 use for decoding the response when you access the :attr:`Response.text
 <requests.Response.text>` attribute. Requests will first check for an
-encoding in the HTTP header, and if none is present, will use `chardet
-<https://pypi.org/project/chardet/>`_ to attempt to guess the encoding.
-
-The only time Requests will not do this is if no explicit charset
+encoding in the HTTP header, and if none is present, will use
+`charset_normalizer <https://pypi.org/project/charset_normalizer/>`_
+or `chardet <https://github.com/chardet/chardet>`_ to attempt to
+guess the encoding.
+
+If ``chardet`` is installed, ``requests`` uses it, however for python3
+``chardet`` is no longer a mandatory dependency. The ``chardet``
+library is an LGPL-licenced dependency and some users of requests
+cannot depend on mandatory LGPL-licensed dependencies.
+
+When you install ``request`` without specifying ``[use_chardet_on_py3]]`` extra,
+and ``chardet`` is not already installed, ``requests`` uses ``charset-normalizer``
+(MIT-licensed) to guess the encoding. For Python 2, ``requests`` uses only
+``chardet`` and is a mandatory dependency there.
+
+The only time Requests will not guess the encoding is if no explicit charset
 is present in the HTTP headers **and** the ``Content-Type``
 header contains ``text``. In this situation, `RFC 2616
 <https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1>`_ specifies
diff --git a/requests/__init__.py b/requests/__init__.py
index f8f94295f9..0ac7713b81 100644
--- a/requests/__init__.py
+++ b/requests/__init__.py
@@ -41,12 +41,20 @@
 """
 
 import urllib3
-import chardet
 import warni