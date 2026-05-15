# The full diff of PR #5797 from the psf/requests repository


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


## Diff
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
 import warnings
 from .exceptions import RequestsDependencyWarning
 
+try:
+    from charset_normalizer import __version__ as charset_normalizer_version
+except ImportError:
+    charset_normalizer_version = None
 
-def check_compatibility(urllib3_version, chardet_version):
+try:
+    from chardet import __version__ as chardet_version
+except ImportError:
+    chardet_version = None
+
+def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
     urllib3_version = urllib3_version.split('.')
     assert urllib3_version != ['dev']  # Verify urllib3 isn't installed from git.
 
@@ -62,12 +70,19 @@ def check_compatibility(urllib3_version, chardet_version):
     assert minor >= 21
     assert minor <= 26
 
-    # Check chardet for compatibility.
-    major, minor, patch = chardet_version.split('.')[:3]
-    major, minor, patch = int(major), int(minor), int(patch)
-    # chardet >= 3.0.2, < 5.0.0
-    assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
-
+    # Check charset_normalizer for compatibility.
+    if chardet_version:
+        major, minor, patch = chardet_version.split('.')[:3]
+        major, minor, patch = int(major), int(minor), int(patch)
+        # chardet_version >= 3.0.2, < 5.0.0
+        assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
+    elif charset_normalizer_version:
+        major, minor, patch = charset_normalizer_version.split('.')[:3]
+        major, minor, patch = int(major), int(minor), int(patch)
+        # charset_normalizer >= 2.0.0 < 3.0.0
+        assert (2, 0, 0) <= (major, minor, patch) < (3, 0, 0)
+    else:
+        raise Exception("You need either charset_normalizer or chardet installed")
 
 def _check_cryptography(cryptography_version):
     # cryptography < 1.3.4
@@ -82,10 +97,10 @@ def _check_cryptography(cryptography_version):
 
 # Check imported dependencies for compatibility.
 try:
-    check_compatibility(urllib3.__version__, chardet.__version__)
+    check_compatibility(urllib3.__version__, chardet_version, charset_normalizer_version)
 except (AssertionError, ValueError):
-    warnings.warn("urllib3 ({}) or chardet ({}) doesn't match a supported "
-                  "version!".format(urllib3.__version__, chardet.__version__),
+    warnings.warn("urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
+                  "version!".format(urllib3.__version__, chardet_version, charset_normalizer_version),
                   RequestsDependencyWarning)
 
 # Attempt to enable urllib3's fallback for SNI support
diff --git a/requests/compat.py b/requests/compat.py
index 5de0769f50..0b14f5015c 100644
--- a/requests/compat.py
+++ b/requests/compat.py
@@ -8,7 +8,10 @@
 Python 3.
 """
 
-import chardet
+try:
+    import chardet
+except ImportError:
+    import charset_normalizer as chardet
 
 import sys
 
diff --git a/requests/help.py b/requests/help.py
index e53d35ef6d..4cd6389f55 100644
--- a/requests/help.py
+++ b/requests/help.py
@@ -8,10 +8,19 @@
 
 import idna
 import urllib3
-import chardet
 
 from . import __version__ as requests_version
 
+try:
+    import charset_normalizer
+except ImportError:
+    charset_normalizer = None
+
+try:
+    import chardet
+except ImportError:
+    chardet = None
+
 try:
     from urllib3.contrib import pyopenssl
 except ImportError:
@@ -71,7 +80,12 @@ def info():
 
     implementation_info = _implementation()
     urllib3_info = {'version': urllib3.__version__}
-    chardet_info = {'version': chardet.__version__}
+    charset_normalizer_info = {'version': None}
+    chardet_info = {'version': None}
+    if charset_normalizer:
+        charset_normalizer_info = {'version': charset_normalizer.__version__}
+    if chardet:
+        chardet_info = {'version': chardet.__version__}
 
     pyopenssl_info = {
         'version': None,
@@ -99,9 +113,11 @@ def info():
         'implementation': implementation_info,
         'system_ssl': system_ssl_info,
         'using_pyopenssl': pyopenssl is not None,
+        'using_charset_normalizer': chardet is None,
         'pyOpenSSL': pyopenssl_info,
         'urllib3': urllib3_info,
         'chardet': chardet_info,
+        'charset_normalizer': charset_normalizer_info,
         'cryptography': cryptography_info,
         'idna': idna_info,
         'requests': {
diff --git a/requests/models.py b/requests/models.py
index 93b901b4e3..aa6fb86e4e 100644
--- a/requests/models.py
+++ b/requests/models.py
@@ -731,7 +731,7 @@ def next(self):
 
     @property
     def apparent_encoding(self):
-        """The apparent encoding, provided by the chardet library."""
+        """The apparent encoding, provided by the charset_normalizer or chardet libraries."""
         return chardet.detect(self.content)['encoding']
 
     def iter_content(self, chunk_size=1, decode_unicode=False):
@@ -845,7 +845,7 @@ def text(self):
         """Content of the response, in unicode.
 
         If Response.encoding is None, encoding will be guessed using
-        ``chardet``.
+        ``charset_normalizer`` or ``chardet``.
 
         The encoding of the response content is determined based solely on HTTP
         headers, following RFC 2616 to the letter. If you can take advantage of
@@ -893,7 +893,7 @@ def json(self, **kwargs):
         if not self.encoding and self.content and len(self.content) > 3:
             # No encoding set. JSON RFC 4627 section 3 states we should expect
             # UTF-8, -16 or -32. Detect which one to use; If the detection or
-            # decoding fails, fall back to `self.text` (using chardet to make
+            # decoding fails, fall back to `self.text` (using charset_normalizer to make
             # a best guess).
             encoding = guess_json_utf(self.content)
             if encoding is not None:
diff --git a/requests/packages.py b/requests/packages.py
index 7232fe0ff7..00196bff25 100644
--- a/requests/packages.py
+++ b/requests/packages.py
@@ -1,9 +1,17 @@
 import sys
 
+try:
+    import chardet
+except ImportError:
+    import charset_normalizer as chardet
+    import warnings
+
+    warnings.filterwarnings('ignore', 'Trying to detect', module='charset_normalizer')
+
 # This code exists for backwards compatibility reasons.
 # I don't like it either. Just look the other way. :)
 
-for package in ('urllib3', 'idna', 'chardet'):
+for package in ('urllib3', 'idna'):
     locals()[package] = __import__(package)
     # This traversal is apparently necessary such that the identities are
     # preserved (requests.packages.urllib3.* is urllib3.*)
@@ -11,4 +19,8 @@
         if mod == package or mod.startswith(package + '.'):
             sys.modules['requests.packages.' + mod] = sys.modules[mod]
 
+target = chardet.__name__
+for mod in list(sys.modules):
+    if mod == target or mod.startswith(target + '.'):
+        sys.modules['requests.packages.' + target.replace(target, 'chardet')] = sys.modules[mod]
 # Kinda cool, though, right?
diff --git a/setup.py b/setup.py
index 552c66de69..27f3948c66 100755
--- a/setup.py
+++ b/setup.py
@@ -41,7 +41,8 @@ def run_tests(self):
 packages = ['requests']
 
 requires = [
-    'chardet>=3.0.2,<5',
+    'charset_normalizer~=2.0.0; python_version >= "3"',
+    'chardet>=3.0.2,<5; python_version < "3"',
     'idna>=2.5,<3',
     'urllib3>=1.21.1,<1.27',
     'certifi>=2017.4.17'
@@ -103,6 +104,7 @@ def run_tests(self):
         'security': ['pyOpenSSL >= 0.14', 'cryptography>=1.3.4'],
         'socks': ['PySocks>=1.5.6, !=1.5.7'],
         'socks:sys_platform == "win32" and python_version == "2.7"': ['win_inet_pton'],
+        'use_chardet_on_py3': ['chardet>=3.0.2,<5']
     },
     project_urls={
         'Documentation': 'https://requests.readthedocs.io',
diff --git a/tox.ini b/tox.ini
index 80454e0117..c8a63ee476 100644
--- a/tox.ini
+++ b/tox.ini
@@ -1,7 +1,18 @@
 [tox]
-envlist = py27,py35,py36,py37,py38
+envlist = py{27,35,36,37,38}-{default,use_chardet_on_py3}
 
 [testenv]
-
+deps = -rrequirements-dev.txt
+extras =
+    security
+    socks
 commands =
-    python setup.py test
+    pytest tests
+
+[testenv:default]
+
+[testenv:use_chardet_on_py3]
+extras =
+    security
+    socks
+    use_chardet_on_py3
