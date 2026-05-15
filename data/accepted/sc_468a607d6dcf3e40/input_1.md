# PR description for pallets/flask#2436


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

## Diff
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
-(depending on what's available).  Where this ends up is sometimes hard to
-find.  Often it's in your webserver's log files.
-
-I can pretty much promise you however that if you only use a logfile for
-the application errors you will never look at it except for debugging an
-issue when a user reported it for you.  What you probably want instead is
-a mail the second the exception happened.  Then you get an alert and you
-can do something about it.
-
-Flask uses the Python builtin logging system, and it can actually send
-you mails for errors which is probably what you want.  Here is how you can
-configure the Flask logger to send you mails for exceptions::
-
-    ADMINS = ['yourname@example.com']
-    if not app.debug:
-        import logging
-        from logging.handlers import SMTPHandler
-        mail_handler = SMTPHandler('127.0.0.1',
-                                   'server-error@example.com',
-                                   ADMINS, 'YourApplication Failed')
-        mail_handler.setLevel(logging.ERROR)
-        app.logger.addHandler(mail_handler)
-
-So what just happened?  We created a new
-:class:`~logging.handlers.SMTPHandler` that will send mails with the mail
-server listening on ``127.0.0.1`` to all the `ADMINS` from the address
-*server-error@example.com* with the subject "YourApplication Failed".  If
-your mail server requires credentials, these can also be provided.  For
-that check out the documentation for the
-:class:`~logging.handlers.SMTPHandler`.
-
-We also tell the handler to only send errors and more critical messages.
-Because we certainly don't want to get a mail for warnings or other
-useless logs that might happen during request handling.
-
-Before you run that in production, please also look at :ref:`logformat` to
-put more information into that error mail.  That will save you from a lot
-of frustration.
-
-
-Logging to a File
------------------
-
-Even if you get mails, you probably also want to log warnings.  It's a
-good idea to keep as much information around that might be required to
-debug a problem.  By default as of Flask 0.11, errors are logged to your
-webserver's log automatically.  Warnings however are not.  Please note
-that Flask itself will not issue any warnings in the core system, so it's
-your responsibility to warn in the code if something seems odd.
-
-There are a couple of handlers provided by the logging system out of the
-box but not all of them are useful for basic error logging.  The most
-interesting are probably the following:
-
--   :class:`~logging.FileHandler` - logs messages to a file on the
-    filesystem.
--   :class:`~logging.handlers.RotatingFileHandler` - logs messages to a file
-    on the filesystem and will rotate after a certain number of messages.
--   :class:`~logging.handlers.NTEventLogHandler` - will log to the system
-    event log of a Windows system.  If you are deploying on a Windows box,
-    this is what you want to use.
--   :class:`~logging.handlers.SysLogHandler` - sends logs to a UNIX
-    syslog.
-
-Once you picked your log handler, do like you did with the SMTP handler
-above, just make sure to use a lower setting (I would recommend
-`WARNING`)::
-
-    if not app.debug:
-        import logging
-        from themodule import TheHandlerYouWant
-        file_handler = TheHandlerYouWant(...)
-        file_handler.setLevel(logging.WARNING)
-        app.logger.addHandler(file_handler)
-
-.. _logformat:
-
-Controlling the Log Format
---------------------------
-
-By default a handler will only write the message string into a file or
-send you that message as mail.  A log record stores more information,
-and it makes a lot of sense to configure your logger to also contain that
-information so that you have a better idea of why that error happened, and
-more importantly, where it did.
-
-A formatter can be instantiated with a format string.  Note that
-tracebacks are appended to the log entry automatically.  You don't have to
-do that in the log formatter format string.
-
-Here are some example setups:
-
-Email
-`````
-
-::
-
-    from logging import Formatter
-    mail_handler.setFormatter(Formatter('''
-    Message type:       %(levelname)s
-    Location:           %(pathname)s:%(lineno)d
-    Module:             %(module)s
-    Function:           %(funcName)s
-    Time:               %(asctime)s
-
-    Message:
-
-    %(message)s
-    '''))
-
-File logging
-````````````
-
-::
-
-    from logging import Formatter
-    file_handler.setFormatter(Formatter(
-        '%(asctime)s %(levelname)s: %(message)s '
-        '[in %(pathname)s:%(lineno)d]'
-    ))
-
-
-Complex Log Formatting
-``````````````````````
-
-Here is a list of useful formatting variables for the format string.  Note
-that this list is not complete, consult the official documentation of the
-:mod:`logging` package for a full list.
-
-.. tabularcolumns:: |p{3cm}|p{12cm}|
-
-+------------------+----------------------------------------------------+
-| Format           | Description                                        |
-+==================+====================================================+
-| ``%(levelname)s``| Text logging level for the message                 |
-|                  | (``'DEBUG'``, ``'INFO'``, ``'WARNING'``,           |
-|                  | ``'ERROR'``, ``'CRITICAL'``).                      |
-+------------------+----------------------------------------------------+
-| ``%(pathname)s`` | Full pathname of the source file where the         |
-|                  | logging call was issued (if available).            |
-+------------------+----------------------------------------------------+
-| ``%(filename)s`` | Filename portion of pathname.                      |
-+------------------+----------------------------------------------------+
-| ``%(module)s``   | Module (name portion of filename).                 |
-+------------------+----------------------------------------------------+
-| ``%(funcName)s`` | Name of function containing the logging call.      |
-+------------------+----------------------------------------------------+
-| ``%(lineno)d``   | Source line number where the logging call was      |
-|                  | issued (if available).                             |
-+------------------+----------------------------------------------------+
-| ``%(asctime)s``  | Human-readable time when the                       |
-|                  | :class:`~logging.LogRecord` was created.           |
-|                  | By default this is of the form                     |
-|                  | ``"2003-07-08 16:49:45,896"`` (the numbers after   |
-|                  | the comma are millisecond portion of the time).    |
-|                  | This can be changed by subclassing the formatter   |
-|                  | and overriding the                                 |
-|                  | :meth:`~logging.Formatter.formatTime` method.      |
-+------------------+----------------------------------------------------+
-| ``%(message)s``  | The logged message, computed as ``msg % args``     |
-+------------------+----------------------------------------------------+
-
-If you want to further customize the formatting, you can subclass the
-formatter.  The formatter has three interesting methods:
-
-:meth:`~logging.Formatter.format`:
-    handles the actual formatting.  It is passed a
-    :class:`~logging.LogRecord` object and has to return the formatted
-    string.
-:meth:`~logging.Formatter.formatTime`:
-    called for `asctime` formatting.  If you want a different time format
-    you can override this method.
-:meth:`~logging.Formatter.formatException`
-    called for exception formatting.  It is passed an :attr:`~sys.exc_info`
-    tuple and has to return a string.  The default is usually fine, you
-    don't have to override it.
-
-For more information, head over to the official documentation.
-
-
-Other Libraries
----------------
-
-So far we only configured the logger your application created itself.
-Other libraries might log themselves as well.  For example, SQLAlchemy uses
-logging heavily in its core.  While there is a method to configure all
-loggers at once in the :mod:`logging` package, I would not recommend using
-it.  There might be a situation in which you want to have multiple
-separate applications running side by side in the same Python interpreter
-and then it becomes impossible to have different logging setups for those.
-
-Instead, I would recommend figuring out which loggers you are interested
-in, getting the loggers with the :func:`~logging.getLogger` function and
-iterating over them to attach handlers::
-
-    from logging import getLogger
-    loggers = [app.logger, getLogger('sqlalchemy'),
-               getLogger('otherlibrary')]
-    for logger in loggers:
-        logger.addHandler(mail_handler)
-        logger.addHandler(file_handler)
+Logging
+-------
+
+See :ref:`logging` for information on how to log exceptions, such as by
+emailing them to admins.
 
 
 Debugging Application Errors
diff --git a/docs/logging.rst b/docs/logging.rst
new file mode 100644
index 0000000000..6bd9266c79
--- /dev/null
+++ b/docs/logging.rst
@@ -0,0 +1,175 @@
+.. _logging:
+
+Logging
+=======
+
+Flask uses standard Python :mod:`logging`. All Flask-related messages are
+logged under the ``'flask'`` logger namespace.
+:meth:`Flask.logger <flask.Flask.logger>` returns the logger named
+``'flask.app'``, and can be used to log messages for your application. ::
+
+    @app.route('/login', methods=['POST'])
+    def login():
+        user = get_user(request.form['username'])
+
+        if user.check_password(request.form['password']):
+            login_user(user)
+            app.logger.info('%s logged in successfully', user.username)
+            return redirect(url_for('index'))
+        else:
+            app.logger.info('%s failed to log in', user.username)
+            abort(401)
+
+
+Basic Configuration
+-------------------
+
+When you want to configure logging for your project, you should do it as soon
+as possible when the program starts. If :meth:`app.logger <flask.Flask.logger>`
+is accessed before logging is configured, it will add a default handler. If
+possible, configure logging before creating the application object.
+
+This example uses :func:`~logging.config.dictConfig` to create a logging
+configuration similar to Flask's default, except for all logs::
+
+    from logging.config import dictConfig
+
+    dictConfig({
+        'version': 1,
+        'formatters': {'default': {
+            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
+        }},
+        'handlers': {'wsgi': {
+            'class': 'logging.StreamHandler',
+            'stream': 'ext://flask.logging.wsgi_errors_stream',
+            'formatter': 'default'
+        }},
+        'root': {
+            'level': 'INFO',
+            'handlers': ['wsgi']
+        }
+    })
+
+    app = Flask(__name__)
+
+
+Default Configuration
+`````````````````````
+
+If you do not configure logging yourself, Flask will add a
+:class:`~logging.StreamHandler` to :meth:`app.logger <flask.Flask.logger>`
+automatically. During requests, it will write to the stream specified by the
+WSGI server in ``environ['wsgi.errors']`` (which is usually
+:data:`sys.stderr`). Outside a request, it will log to :data:`sys.stderr`.
+
+
+Removing the Default Handler
+````````````````````````````
+
+If you configured logging after accessing
+:meth:`app.logger <flask.Flask.logger>`, and need to remove the default
+handler, you can import and remove it::
+
+    from flask.logging import default_handler
+
+    app.logger.removeHandler(default_handler)
+
+
+Email Errors to Admins
+----------------------
+
+When running the application on a remote server for production, you probably
+won't be looking at the log messages very often. The WSGI server will probably
+send log messages to a file, and you'll only check that file if a user tells
+you something went wrong.
+
+To be proactive about discovering and fixing bugs, you can configure a
+:class:`logging.handlers.SMTPHandler` to send an email when errors and higher
+are logged. ::
+
+    import logging
+    from logging.handlers import SMTPHandler
+
+    mail_handler = SMTPHandler(
+        mailhost='127.0.0.1',
+        fromaddr='server-error@example.com',
+        toaddrs=['admin@example.com'],
+        subject='Application Error'
+    )
+    mail_handler.setLevel(logging.ERROR)
+    mail_handler.setFormatter(logging.Formatter(
+        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
+    ))
+
+    if not app.debug:
+        app.logger.addHandler(mail_handler)
+
+This requires that you have an SMTP server set up on the same server. See the
+Python docs for more information about configuring the handler.
+
+
+Injecting Request Information
+-----------------------------
+
+Seeing more information about the request, such as the IP address, may help
+debugging some errors. You can subclass :class:`logging.Formatter` to inject
+your own fields that can be used in messages. You can change the formatter for
+Flask's default handler, the mail handler defined above, or any other
+handler. ::
+
+    from flask import request
+    from flask.logging import default_handler
+
+    class RequestFormatter(logging.Formatter):
+        def format(self, record):
+            record.url = request.url
+            record.remote_addr = request.remote_addr
+            return super().format(record)
+
+    formatter = RequestFormatter(
+        '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
+        '%(levelname)s in %(module)s: %(message)s'
+    ))
+    default_handler.setFormatter(formatter)
+    mail_handler.setFormatter(formatter)
+
+
+Other Libraries
+---------------
+
+Other libraries may use logging extensively, and you want to see relevant
+messages from those logs too. The simplest way to do this is to add handlers
+to the root logger instead of only the app logger. ::
+
+    from flask.logging import default_handler
+
+    root = logging.getLogger()
+    root.addHandler(default_handler)
+    root.addHandler(mail_handler)
+
+Depending on your project, it may be more useful to configure each logger you
+care about separately, instead of configuring only the root logger. ::
+
+    for logger in (
+        app.logger,
+        logging.getLogger('sqlalchemy'),
+        logging.getLogger('other_package'),
+    ):
+        logger.addHandler(default_handler)
+        logger.addHandler(mail_handler)
+
+
+Werkzeug
+````````
+
+Werkzeug logs basic request/response information to the ``'werkzeug'`` logger.
+If the root logger has no handlers configured, Werkzeug adds a
+:class:`~logging.StreamHandler` to its logger.
+
+
+Flask Extensions
+````````````````
+
+Depending on the situation, an extension may choose to log to
+:meth:`app.logger <flask.Flask.logger>` or its own named logger. Consult each
+extension's documentation for details.
diff --git a/flask/app.py b/flask/app.py
index afa5fd1cf2..88ca433c65 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -16,10 +16,9 @@
 from itertools import chain
 from threading import Lock
 
-from werkzeug.datastructures import ImmutableDict, Headers
-from werkzeug.exceptions import BadRequest, HTTPException, \
-    InternalServerError, MethodNotAllowed, default_exceptions, \
-    BadRequestKeyError
+from werkzeug.datastructures import Headers, ImmutableDict
+from werkzeug.exceptions import BadRequest, BadRequestKeyError, HTTPException, \
+    InternalServerError, MethodNotAllowed, default_exceptions
 from werkzeug.routing import BuildError, Map, RequestRedirect, Rule
 
 from . import cli, json
@@ -30,6 +29,7 @@
 from .helpers import _PackageBoundObject, \
     _endpoint_from_view_func, find_package, get_debug_flag, \
     get_flashed_messages, locked_cached_property, url_for
+from .logging import create_logger
 from .sessions import SecureCookieSessionInterface
 from .signals import appcontext_tearing_down, got_request_exception, \
     request_finished, request_started, request_tearing_down
@@ -37,9 +37,6 @@
     _default_template_ctx_processor
 from .wrappers import Request, Response
 
-# a lock used for logger initialization
-_logger_lock = Lock()
-
 # a singleton sentinel value for parameter defaults
 _sentinel = object()
 
@@ -264,12 +261,6 @@ class Flask(_PackageBoundObject):
     #: ``USE_X_SENDFILE`` configuration key.  Defaults to ``False``.
     use_x_sendfile = ConfigAttribute('USE_X_SENDFILE')
 
-    #: The name of the logger to use.  By default the logger name is the
-    #: package name passed to the constructor.
-    #:
-    #: .. versionadded:: 0.4
-    logger_name = ConfigAttribute('LOGGER_NAME')
-
     #: The JSON encoder class to use.  Defaults to :class:`~flask.json.JSONEncoder`.
     #:
     #: .. versionadded:: 0.10
@@ -294,8 +285,6 @@ class Flask(_PackageBoundObject):
         'SECRET_KEY':                           None,
         'PERMANENT_SESSION_LIFETIME':           timedelta(days=31),
         'USE_X_SENDFILE':                       False,
-        'LOGGER_NAME':                          None,
-        'LOGGER_HANDLER_POLICY':               'always',
         'SERVER_NAME':                          None,
         'APPLICATION_ROOT':                     '/',
         'SESSION_COOKIE_NAME':                  'session',
@@ -392,10 +381,6 @@ def __init__(
         #: to load a config from files.
         self.config = self.make_config(instance_relative_config)
 
-        # Prepare the deferred setup of the logger.
-        self._logger = None
-        self.logger_name = self.import_name
-
         #: A dictionary of all view functions registered.  The keys will
         #: be function names which are also used to generate URLs and
         #: the values are the function objects themselves.
@@ -613,27 +598,28 @@ def preserve_context_on_exception(self):
             return rv
         return self.debug
 
-    @property
+    @locked_cached_property
     def logger(self):
-        """A :class:`logging.Logger` object for this application.  The
-        default configuration is to log to stderr if the application is
-        in debug mode.  This logger can be used to (surprise) log messages.
-        Here some examples::
+        """The ``'flask.app'`` logger, a standard Python
+        :class:`~logging.Logger`.
+
+        In debug mode, the logger's :attr:`~logging.Logger.level` will be set
+        to :data:`~logging.DEBUG`.
 
-            app.logger.debug('A value for debugging')
-            app.logger.warning('A warning occurred (%d apples)', 42)
-            app.logger.error('An error occurred')
+        If there are no handlers configured, a default handler will be added.
+        See :ref:`logging` for more information.
+
+        .. versionchanged:: 1.0
+            Behavior was simplified. The logger is always named
+            ``flask.app``. The level is only set during configuration, it
+            doesn't check ``app.debug`` each time. Only one format is used,
+            not different ones depending on ``app.debug``. No handlers are
+            removed, and a handler is only added if no handlers are already
+            configured.
 
         .. versionadded:: 0.3
         """
-        if self._logger and self._logger.name == self.logger_name:
-            return self._logger
-        with _logger_lock:
-            if self._logger and self._logger.name == self.logger_name:
-                return self._logger
-            from flask.logging import create_logger
-            self._logger = rv = create_logger(self)
-            return rv
+        return create_logger(self)
 
     @locked_cached_property
     def jinja_env(self):
diff --git a/flask/logging.py b/flask/logging.py
index 3f888a756b..86a3fa33ac 100644
--- a/flask/logging.py
+++ b/flask/logging.py
@@ -1,94 +1,69 @@
-# -*- coding: utf-8 -*-
-"""
-    flask.logging
-    ~~~~~~~~~~~~~
-
-    Implements the logging support for Flask.
-
-    :copyright: (c) 2015 by Armin Ronacher.
-    :license: BSD, see LICENSE for more details.
-"""
-
 from __future__ import absolute_import
 
+import logging
 import sys
 
 from werkzeug.local import LocalProxy
-from logging import getLogger, StreamHandler, Formatter, getLoggerClass, \
-     DEBUG, ERROR
-from .globals import _request_ctx_stack
-
 
-PROD_LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
-DEBUG_LOG_FORMAT = (
-    '-' * 80 + '\n' +
-    '%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n' +
-    '%(message)s\n' +
-    '-' * 80
-)
+from .globals import request
 
 
 @LocalProxy
-def _proxy_stream():
-    """Finds the most appropriate error stream for the application.  If a
-    WSGI request is in flight we log to wsgi.errors, otherwise this resolves
-    to sys.stderr.
+def wsgi_errors_stream():
+    """Find the most appropriate error stream for the application. If a request
+    is active, log to ``wsgi.errors``, otherwise use ``sys.stderr``.
+
+    If you configure your own :class:`logging.StreamHandler`, you may want to
+    use this for the stream. If you are using file or dict configuration and
+    can't import this directly, you can refer to it as
+    ``ext://flask.logging.wsgi_errors_stream``.
     """
-    ctx = _request_ctx_stack.top
-    if ctx is not None:
-        return ctx.request.environ['wsgi.errors']
-    return sys.stderr
+    return request.environ['wsgi.errors'] if request else sys.stderr
+
+
+def has_level_handler(logger):
+    """Check if there is a handler in the logging chain that will handle the
+    given logger's :meth:`effective level <~logging.Logger.getEffectiveLevel>`.
+    """
+    level = logger.getEffectiveLevel()
+    current = logger
+
+    while current:
+        if any(handler.level <= level for handler in current.handlers):
+            return True
 
+        if not current.propagate:
+            break
+
+        current = current.parent
 
-def _should_log_for(app, mode):
-    policy = app.config['LOGGER_HANDLER_POLICY']
-    if policy == mode or policy == 'always':
-        return True
     return False
 
 
+#: Log messages to :func:`~flask.logging.wsgi_errors_stream` with the format
+#: ``[%(asctime)s] %(levelname)s in %(module)s: %(message)s``.
+default_handler = logging.StreamHandler(wsgi_errors_stream)
+default_handler.setFormatter(logging.Formatter(
+    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
+))
+
+
 def create_logger(app):
-    """Creates a logger for the given application.  This logger works
-    similar to a regular Python logger but changes the effective logging
-    level based on the application's debug flag.  Furthermore this
-    function also removes all attached handlers in case there was a
-    logger with the log name before.
+    """Get the ``'flask.app'`` logger and configure it if needed.
+
+    When :attr:`~flask.Flask.debug` is enabled, set the logger level to
+    :data:`logging.DEBUG` if it is not set.
+
+    If there is no handler for the logger's effective level, add a
+    :class:`~logging.StreamHandler` for
+    :func:`~flask.logging.wsgi_errors_stream` with a basic format.
     """
-    Logger = getLoggerClass()
-
-    class DebugLogger(Logger):
-        def getEffectiveLevel(self):
-            if self.level == 0 and app.debug:
-                return DEBUG
-            return Logger.getEffectiveLevel(self)
-
-    class DebugHandler(StreamHandler):
-        def emit(self, record):
-            if app.debug and _should_log_for(app, 'debug'):
-                StreamHandler.emit(self, record)
-
-    class ProductionHandler(StreamHandler):
-        def emit(self, record):
-            if not app.debug and _should_log_for(app, 'production'):
-                StreamHandler.emit(self, record)
-
-    debug_handler = DebugHandler()
-    debug_handler.setLevel(DEBUG)
-    debug_handler.setFormatter(Formatter(DEBUG_LOG_FORMAT))
-
-    prod_handler = ProductionHandler(_proxy_stream)
-    prod_handler.setLevel(ERROR)
-    prod_handler.setFormatter(Formatter(PROD_LOG_FORMAT))
-
-    logger = getLogger(app.logger_name)
-    # just in case that was not a new logger, get rid of all the handlers
-    # already attached to it.
-    del logger.handlers[:]
-    logger.__class__ = DebugLogger
-    logger.addHandler(debug_handler)
-    logger.addHandler(prod_handler)
-
-    # Disable propagation by default
-    logger.propagate = False
+    logger = logging.getLogger('flask.app')
+
+    if app.debug and logger.level == logging.NOTSET:
+        logger.setLevel(logging.DEBUG)
+
+    if not has_level_handler(logger):
+        logger.addHandler(default_handler)
 
     return logger
diff --git a/tests/test_basic.py b/tests/test_basic.py
index a46bfbfc90..0e3076df0e 100644
--- a/tests/test_basic.py
+++ b/tests/test_basic.py
@@ -738,7 +738,6 @@ def root():
 
 def test_teardown_request_handler_error(app, client):
     called = []
-    app.config['LOGGER_HANDLER_POLICY'] = 'never'
     app.testing = False
 
     @app.teardown_request
@@ -814,7 +813,6 @@ def index():
 
 
 def test_error_handling(app, client):
-    app.config['LOGGER_HANDLER_POLICY'] = 'never'
     app.testing = False
 
     @app.errorhandler(404)
@@ -860,7 +858,6 @@ def test_error_handler_unknown_code(app):
 
 
 def test_error_handling_processing(app, client):
-    app.config['LOGGER_HANDLER_POLICY'] = 'never'
     app.testing = False
 
     @app.errorhandler(500)
@@ -882,7 +879,6 @@ def after_request(resp):
 
 
 def test_baseexception_error_handling(app, client):
-    app.config['LOGGER_HANDLER_POLICY'] = 'never'
     app.testing = False
 
     @app.route('/')
@@ -1021,6 +1017,34 @@ def fail():
         client.get('/fail')
 
 
+def test_error_handler_after_processor_error(app, client):
+    app.testing = False
+
+    @app.before_request
+    def before_request():
+        if trigger == 'before':
+            1 // 0
+
+    @app.after_request
+    def after_request(response):
+        if trigger == 'after':
+            1 // 0
+        return response
+
+    @app.route('/')
+    def index():
+        return 'Foo'
+
+    @app.errorhandler(500)
+    def internal_server_error(e):
+        return 'Hello Server Error', 500
+
+    for trigger in 'before', 'after':
+        rv = client.get('/')
+        assert rv.status_code == 500
+        assert rv.data == b'Hello Server Error'
+
+
 def test_enctype_debug_helper(app, client):
     from flask.debughelpers import DebugFilesKeyError
     app.debug = True
@@ -1425,7 +1449,6 @@ def subdomain():
 
 def test_exception_propagation(app, client):
     def apprunner(config_key):
-        app.config['LOGGER_HANDLER_POLICY'] = 'never'
 
         @app.route('/')
         def index():
diff --git a/tests/test_helpers.py b/tests/test_helpers.py
index 73c6bee728..cc480c26fa 100644
--- a/tests/test_helpers.py
+++ b/tests/test_helpers.py
@@ -9,20 +9,19 @@
     :license: BSD, see LICENSE for more details.
 """
 
-import pytest
-
+import datetime
 import os
 import uuid
-import datetime
 
-import flask
-from logging import StreamHandler
+import pytest
 from werkzeug.datastructures import Range
 from werkzeug.exceptions import BadRequest, NotFound
-from werkzeug.http import parse_cache_control_header, parse_options_header
-from werkzeug.http import http_date
+from werkzeug.http import http_date, parse_cache_control_header, \
+    parse_options_header
+
+import flask
 from flask._compat import StringIO, text_type
-from flask.helpers import get_debug_flag, make_response
+from flask.helpers import get_debug_flag
 
 
 def has_encoding(name):
@@ -660,94 +659,7 @@ def test_send_from_directory_bad_request(self, app, req_ctx):
             flask.send_from_directory('static', 'bad\x00')
 
 
-class TestLogging(object):
-    def test_logger_cache(self):
-        app = flask.Flask(__name__)
-        logger1 = app.logger
-        assert app.logger is logger1
-        assert logger1.name == __name__
-        app.logger_name = __name__ + '/test_logger_cache'
-        assert app.logger is not logger1
-
-    def test_debug_log(self, capsys, app, client):
-        app.debug = True
-
-        @app.route('/')
-        def index():
-            app.logger.warning('the standard library is dead')
-            app.logger.debug('this is a debug statement')
-            return ''
-
-        @app.route('/exc')
-        def exc():
-            1 // 0
-
-        with client:
-            client.get('/')
-            out, err = capsys.readouterr()
-            assert 'WARNING in test_helpers [' in err
-            assert os.path.basename(__file__.rsplit('.', 1)[0] + '.py') in err
-            assert 'the standard library is dead' in err
-            assert 'this is a debug statement' in err
-
-            with pytest.raises(ZeroDivisionError):
-                client.get('/exc')
-
-    def test_debug_log_override(self, app):
-        app.debug = True
-        app.logger_name = 'flask_tests/test_debug_log_override'
-        app.logger.level = 10
-        assert app.logger.level == 10
-
-    def test_exception_logging(self, app, client):
-        out = StringIO()
-        app.config['LOGGER_HANDLER_POLICY'] = 'never'
-        app.logger_name = 'flask_tests/test_exception_logging'
-        app.logger.addHandler(StreamHandler(out))
-        app.testing = False
-
-        @app.route('/')
-        def index():
-            1 // 0
-
-        rv = client.get('/')
-        assert rv.status_code == 500
-        assert b'Internal Server Error' in rv.data
-
-        err = out.getvalue()
-        assert 'Exception on / [GET]' in err
-        assert 'Traceback (most recent call last):' in err
-        assert '1 // 0' in err
-        assert 'ZeroDivisionError:' in err
-
-    def test_processor_exceptions(self, app, client):
-        app.config['LOGGER_HANDLER_POLICY'] = 'never'
-        app.testing = False
-
-        @app.before_request
-        def before_request():
-            if trigger == 'before':
-                1 // 0
-
-        @app.after_request
-        def after_request(response):
-            if trigger == 'after':
-                1 // 0
-            return response
-
-        @app.route('/')
-        def index():
-            return 'Foo'
-
-        @app.errorhandler(500)
-        def internal_server_error(e):
-            return 'Hello Server Error', 500
-
-        for trigger in 'before', 'after':
-            rv = client.get('/')
-            assert rv.status_code == 500
-            assert rv.data == b'Hello Server Error'
-
+class TestUrlFor(object):
     def test_url_for_with_anchor(self, app, req_ctx):
 
         @app.route('/')
diff --git a/tests/test_logging.py b/tests/test_logging.py
new file mode 100644
index 0000000000..1a0105693c
--- /dev/null
+++ b/tests/test_logging.py
@@ -0,0 +1,91 @@
+import logging
+import sys
+
+import pytest
+
+from flask._compat import StringIO
+from flask.logging import default_handler, has_level_handler, \
+    wsgi_errors_stream
+
+
+@pytest.fixture(autouse=True)
+def reset_logging(monkeypatch):
+    root_handlers = logging.root.handlers[:]
+    root_level = logging.root.level
+
+    logger = logging.getLogger('flask.app')
+    logger.handlers = []
+    logger.setLevel(logging.NOTSET)
+
+    yield
+
+    logging.root.handlers[:] = root_handlers
+    logging.root.setLevel(root_level)
+
+    logger.handlers = []
+    logger.setLevel(logging.NOTSET)
+
+
+def test_logger(app):
+    assert app.logger.name == 'flask.app'
+    assert app.logger.level == logging.NOTSET
+    assert app.logger.handlers == [default_handler]
+
+
+def test_logger_debug(app):
+    app.debug = True
+    assert app.logger.level == logging.DEBUG
+    assert app.logger.handlers == [default_handler]
+
+
+def test_existing_handler(app):
+    logging.root.addHandler(logging.StreamHandler())
+    assert app.logger.level == logging.NOTSET
+    assert not app.logger.handlers
+
+
+def test_wsgi_errors_stream(app, client):
+    @app.route('/')
+    def index():
+        app.logger.error('test')
+        return ''
+
+    stream = StringIO()
+    client.get('/', errors_stream=stream)
+    assert 'ERROR in test_logging: test' in stream.getvalue()
+
+    assert wsgi_errors_stream._get_current_object() is sys.stderr
+
+    with app.test_request_context(errors_stream=stream):
+        assert wsgi_errors_stream._get_current_object() is stream
+
+
+def test_has_level_handler():
+    logger = logging.getLogger('flask.app')
+    assert not has_level_handler(logger)
+
+    handler = logging.StreamHandler()
+    logging.root.addHandler(handler)
+    assert has_level_handler(logger)
+
+    logger.propagate = False
+    assert not has_level_handler(logger)
+    logger.propagate = True
+
+    handler.setLevel(logging.ERROR)
+    assert not has_level_handler(logger)
+
+
+def test_log_view_exception(app, client):
+    @app.route('/')
+    def index():
+        raise Exception('test')
+
+    app.testing = False
+    stream = StringIO()
+    rv = client.get('/', errors_stream=stream)
+    assert rv.status_code == 500
+    assert rv.data
+    err = stream.getvalue()
+    assert 'Exception on / [GET]' in err
+    assert 'Exception: test' in err
diff --git a/tests/test_subclassing.py b/tests/test_subclassing.py
index 3f81ecd81e..82739a7e4a 100644
--- a/tests/test_subclassing.py
+++ b/tests/test_subclassing.py
@@ -9,8 +9,8 @@
     :copyright: (c) 2015 by Armin Ronacher.
     :license: BSD, see LICENSE for more details.
 """
+
 import flask
-from logging import StreamHandler
 
 from flask._compat import StringIO
 
@@ -22,16 +22,12 @@ def log_exception(self, exc_info):
 
     out = StringIO()
     app = SuppressedFlask(__name__)
-    app.logger_name = 'flask_tests/test_suppressed_exception_logging'
-    app.logger.addHandler(StreamHandler(out))
 
     @app.route('/')
     def index():
-        1 // 0
+        raise Exception('test')
 
-    rv = app.test_client().get('/')
+    rv = app.test_client().get('/', errors_stream=out)
     assert rv.status_code == 500
     assert b'Internal Server Error' in rv.data
-
-    err = out.getvalue()
-    assert err == ''
+    assert not out.getvalue()
diff --git a/tests/test_templating.py b/tests/test_templating.py
index c41bcda8b1..d871ca4ddc 100644
--- a/tests/test_templating.py
+++ b/tests/test_templating.py
@@ -399,7 +399,7 @@ def run_simple_mock(*args, **kwargs):
     assert app.jinja_env.auto_reload == True
 
 
-def test_template_loader_debugging(test_apps):
+def test_template_loader_debugging(test_apps, monkeypatch):
     from blueprintapp import app
 
     called = []
@@ -419,19 +419,15 @@ def handle(x, record):
             assert 'See http://flask.pocoo.org/docs/blueprints/#templates' in text
 
     with app.test_client() as c:
-        try:
-            old_load_setting = app.config['EXPLAIN_TEMPLATE_LOADING']
-            old_handlers = app.logger.handlers[:]
-            app.logger.handlers = [_TestHandler()]
-            app.config['EXPLAIN_TEMPLATE_LOADING'] = True
-
-            with pytest.raises(TemplateNotFound) as excinfo:
-                c.get('/missing')
-
-            assert 'missing_template.html' in str(excinfo.value)
-        finally:
-            app.logger.handlers[:] = old_handlers
-            app.config['EXPLAIN_TEMPLATE_LOADING'] = old_load_setting
+        monkeypatch.setitem(app.config, 'EXPLAIN_TEMPLATE_LOADING', True)
+        monkeypatch.setattr(
+            logging.getLogger('flask'), 'handlers', [_TestHandler()]
+        )
+
+        with pytest.raises(TemplateNotFound) as excinfo:
+            c.get('/missing')
+
+        assert 'missing_template.html' in str(excinfo.value)
 
     assert len(called) == 1
 
diff --git a/tests/test_testing.py b/tests/test_testing.py
index c25a03055e..a673c2e128 100644
--- a/tests/test_testing.py
+++ b/tests/test_testing.py
@@ -207,7 +207,6 @@ def test_session_transaction_needs_cookies(app):
 
 
 def test_test_client_context_binding(app, client):
-    app.config['LOGGER_HANDLER_POLICY'] = 'never'
     app.testing = False
 
     @app.route('/')
