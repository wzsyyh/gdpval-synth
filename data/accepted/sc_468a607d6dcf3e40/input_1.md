# pr_description


# Seed Material: pallets/flask#2436: Simplify logging
Source: github_issue_pr
Identifier: pr:pallets/flask#2436

Repository: pallets/flask
PR Number: #2436
PR Title: Simplify logging
Merged At: 2017-07-31T20:23:45Z
Changed Files: 13
Additions: +404, Deletions: -456

## PR Description
Based on discussion in #2023 and #641, Flask interferes too much with logging. This patch greatly reduces the logging configuration that Flask does.

* Remove `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` configuration.
* `app.logger` is always named `'flask.app'`. Use the `'flask'` namespace to allow other logging from Flask in the future.
* Don't use a `Logger` subclass to override `getEffectiveLevel`. Call `setLevel` when the logger is first accessed, based on `app.debug`, instead of checking `debug` for every message.
* Only one handler with one format is added, instead of different formats for production and development.
* A handler is only added if there are no handlers configured that would handle the logger's `getEffectiveLevel`.
* Handlers are never removed.
* The `default_handler` is accessible so that it can be passed to `removeHandler` in case the user wants to get rid of the default handler after it is configured.
* The proxy stream to `environ['wsgi.errors']` is exposed as `wsgi_errors_stream`, in case the user wants to use it in their own configuration.
* Logging documentation is split from error handling documentation and reorganized to address the key concepts.
* Added documentation for injecting request information into messages.
* Logging tests are split into a separate module.
* Some previously miscategorized tests are correctly organized.

## Diff (first 3000 chars)
diff --git a/CHANGES b/CHANGES
index b44334db55..fe48808f32 100644
--- a/CHANGES
+++ b/CHANGES
@@ -106,6 +106,12 @@ Major release, unreleased
   (`#2416`_)
 - When passing a full URL to the test client, use the scheme in the URL instead
   of the ``PREFERRED_URL_SCHEME``. (`#2436`_)
+- ``app.logger`` has been simplified. ``LOGGER_NAME`` and
+  ``LOGGER_HANDLER_POLICY`` config was removed. The logger is always named
+  ``flask.app``. The level is only set on first access, it doesn't check
+  ``app.debug`` each time. Only one format is used, not different ones
+  depending on ``app.debug``. No handlers are removed, and a handler is only
+  added if no handlers are already configured. (`#2436`_)
 
 .. _#1421: https://github.com/pallets/flask/issues/1421
 .. _#1489: https://github.com/pallets/flask/pull/1489
diff --git a/docs/config.rst b/docs/config.rst
index 223bd6a87b..cf119cba82 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -199,21 +199,6 @@ The following configuration values are used internally by Flask:
 
     Default: ``timedelta(hours=12)`` (``43200`` seconds)
 
-.. py:data:: LOGGER_NAME
-
-    The name of the logger that the Flask application sets up. If not set,
-    it will take the import name passed to ``Flask.__init__``.
-
-    Default: ``None``
-
-.. py:data:: LOGGER_HANDLER_POLICY
-
-    When to activate the application's logger handler. ``'always'`` always
-    enables it, ``'debug'`` only activates it in debug mode, ``'production'``
-    only activates it when not in debug mode, and ``'never'`` never enables it.
-
-    Default: ``'always'``
-
 .. py:data:: SERVER_NAME
 
     Inform the application what host and port it is bound to. Required for
@@ -329,6 +314,11 @@ The following configuration values are used internally by Flask:
    ``SESSION_REFRESH_EACH_REQUEST``, ``TEMPLATES_AUTO_RELOAD``,
    ``LOGGER_HANDLER_POLICY``, ``EXPLAIN_TEMPLATE_LOADING``
 
+.. versionchanged:: 1.0
+
+    ``LOGGER_NAME`` and ``LOGGER_HANDLER_POLICY`` were removed. See
+    :ref:`logging` for information about configuration.
+
 Configuring from Files
 ----------------------
 
diff --git a/docs/contents.rst.inc b/docs/contents.rst.inc
index e77f7b60ee..de4d7a918b 100644
--- a/docs/contents.rst.inc
+++ b/docs/contents.rst.inc
@@ -16,6 +16,7 @@ instructions for web development with Flask.
    templating
    testing
    errorhandling
+   logging
    config
    signals
    views
diff --git a/docs/errorhandling.rst b/docs/errorhandling.rst
index 84c649ce3e..413680dd6a 100644
--- a/docs/errorhandling.rst
+++ b/docs/errorhandling.rst
@@ -143,213 +143,11 @@ determined.
    Handlers are prioritized by specificity of the exception classes they are
    registered for instead of the order they are registered in.
 
-Error Mails
------------
-
-If the application runs in production mode (which it will do on your
-server) you might not see any log messages.  The reason for that is that
-Flask by default will just report to the WSGI error stream or stderr
-(depen