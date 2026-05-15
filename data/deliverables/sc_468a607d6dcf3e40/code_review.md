# Code Review: PR #2436 - Simplify Logging

## Summary of Changes

PR #2436 simplifies Flask's logging configuration by removing unnecessary interference with Python's standard logging system. The PR modifies 13 files with 404 additions and 456 deletions, reflecting a net reduction in logging-related code.

Configuration Removal: The `LOGGER_NAME` configuration key (previously defaulting to `None` and used to name the application logger) and `LOGGER_HANDLER_POLICY` (which controlled handler activation with values `'always'`, `'debug'`, `'production'`, or `'never'`, defaulting to `'always'`) are removed from `flask/app.py`'s default config dict and the `ConfigAttribute` descriptor `logger_name` is deleted. The CHANGES file and `docs/config.rst` document these removals with a `versionchanged:: 1.0` note.

Logging Module Rewrite: `flask/logging.py` is substantially rewritten. The old implementation defined custom subclasses `DebugLogger`, `DebugHandler`, and `ProductionHandler` inside `create_logger`, used two format constants `PROD_LOG_FORMAT` and `DEBUG_LOG_FORMAT`, and removed all existing handlers on every access. The new implementation defines a single `default_handler` (a `logging.StreamHandler` writing to `wsgi_errors_stream`) with one format: `[%(asctime)s] %(levelname)s in %(module)s: %(message)s`. The `has_level_handler` function checks whether any handler in the logger hierarchy can handle the logger's effective level. The `create_logger` function gets the `'flask.app'` logger, sets its level to `DEBUG` if `app.debug` is true and the level is `NOTSET`, and adds `default_handler` only if `has_level_handler` returns false.

Documentation: Logging documentation is split from `docs/errorhandling.rst` into a new `docs/logging.rst` file, registered in `docs/contents.rst.inc`. The error handling docs now contain a short cross-reference: `See :ref:\`logging\` for information on how to log exceptions`. The new logging docs cover basic configuration with `dictConfig`, default configuration behavior, removing the default handler, emailing errors with `SMTPHandler`, injecting request information with a custom `RequestFormatter`, and logging from other libraries.

Test Reorganization: Logging tests are moved from `tests/test_helpers.py` (the `TestLogging` class is deleted) into a new `tests/test_logging.py` module. Tests that were previously miscategorized in `test_basic.py` have `LOGGER_HANDLER_POLICY` configuration removed. The `test_processor_exceptions` test is moved to `test_basic.py` as `test_error_handler_after_processor_error`.

## Key Architectural Decisions

Removing `LOGGER_NAME` and `LOGGER_HANDLER_POLICY`: The old `LOGGER_NAME` config (default `None`) allowed users to override the logger name, and `logger_name = ConfigAttribute('LOGGER_NAME')` was a descriptor on the `Flask` class. `LOGGER_HANDLER_POLICY` (default `'always'`) controlled which handler (debug or production) was active based on `app.debug`. These are removed because they complicated the logging setup for marginal benefit. The new approach always uses the name `'flask.app'`, placing it under the `'flask'` namespace for future extensibility.

Changing from DebugLogger subclass to locked_cached_property: The old approach used a thread lock (`_logger_lock`) and a `DebugLogger` subclass that overrode `getEffectiveLevel` to return `DEBUG` when `app.debug` was true and the logger level was 0. This meant every log message triggered a debug flag check. The new approach uses `@locked_cached_property` on the `logger` property, calling `create_logger(self)` once and caching the result. The level is set explicitly via `logger.setLevel(logging.DEBUG)` on first access if `app.debug` is true, eliminating per-message overhead.

The `has_level_handler` function: This function walks the logger hierarchy from the current logger up through parents (via `current.parent`) as long as `current.propagate` is true. At each level, it checks if any handler has a level less than or equal to the logger's effective level. This ensures a default handler is only added when no existing handler would process the logger's messages, respecting user-configured logging setups.

Public exports `default_handler` and `wsgi_errors_stream`: `wsgi_errors_stream` is a `LocalProxy` that resolves to `request.environ['wsgi.errors']` during a request or `sys.stderr` outside one. `default_handler` is a module-level `logging.StreamHandler` instance using the standard format. Both are public so users can reference them: `default_handler` for `removeHandler` and `wsgi_errors_stream` for use in custom `StreamHandler` or `dictConfig` via `ext://flask.logging.wsgi_errors_stream`.

## Code Quality Assessment

Thread Safety: The `@locked_cached_property` decorator (imported from `flask.helpers`) provides thread-safe lazy initialization, replacing the manual `_logger_lock` that was previously used in the `logger` property. This is a cleaner approach since the lock is encapsulated in the decorator. The old code also held the lock while creating the logger, which is preserved in the cached property's implementation.

The `has_level_handler` function correctly traverses the logger hierarchy. It starts at the given logger and checks each logger's handlers for a level <= the effective level. If `propagate` is `False`, it stops. The function uses `logger.getEffectiveLevel()` which already walks up the hierarchy to find the first explicitly set level, so the effective level is computed once and then each logger is checked for handlers at or below that level. One edge case: if no handlers are found anywhere and the root logger has no handlers, the function returns `False`, triggering addition of the default handler.

The use of `logging.NOTSET` (value 0) as a sentinel is standard Python logging practice. In `create_logger`, the check `if app.debug and logger.level == logging.NOTSET` ensures the level is only set once on first access, preventing overwriting a user-configured level. The `test_logger` test verifies this by asserting `app.logger.level == logging.NOTSET` when debug is false, and `test_logger_debug` asserts `app.logger.level == logging.DEBUG` when debug is true.

The removal of `del logger.handlers[:]` (which cleared all handlers on every access) is a significant improvement. The old code aggressively removed handlers, which could break user configurations. The new code only adds a handler if none exist that would handle the logger's messages, respecting existing configurations.

## Risk Analysis

Risk 1: Users who relied on `LOGGER_NAME` to customize the logger name will find their configuration ignored. The logger is now always named `'flask.app'`. If users configured handlers or filters based on the old logger name (which was the import name by default), their logging setup will break. They must update their configuration to reference `'flask.app'` or `'flask'`.

Risk 2: Users who set `LOGGER_HANDLER_POLICY` to values like `'never'` to suppress Flask's default logging behavior will no longer have that option. The policy is removed entirely. The new approach only adds a handler if no handlers are configured, so users must ensure their logging configuration is set up before accessing `app.logger`, or they will get the default handler added.

Risk 3: The removal of the `DebugLogger` subclass means the `getEffectiveLevel` behavior changed. Previously, `getEffectiveLevel` returned `DEBUG` dynamically when `app.debug` was true, even if the logger level was not explicitly set. Now, the level is set once on first access. If code relies on checking `app.logger.getEffectiveLevel()` after changing `app.debug` at runtime, it will no longer see the change reflected in the logger's effective level.

Risk 4: The removal of separate debug and production log formats means users who relied on the verbose debug format (`DEBUG_LOG_FORMAT` with line of dashes and pathname:lineno) will now get the simpler production format (`[%(asctime)s] %(levelname)s in %(module)s: %(message)s`) in all modes. They must configure their own formatter if they want different formatting.

Risk 5: Tests in `test_basic.py` that set `LOGGER_HANDLER_POLICY` to `'never'` (e.g., `test_teardown_request_handler_error`, `test_error_handling`, `test_error_handling_processing`, `test_baseexception_error_handling`, `test_exception_propagation`) had those lines removed. While the tests still pass because the new logging doesn't interfere with error handling, users who copied these patterns into their own test code will need to remove the config setting.

## Documentation and Test Review

The new `docs/logging.rst` is well-structured and covers the essential topics: basic configuration with `dictConfig`, default configuration, removing the default handler, emailing errors, injecting request information, and logging from other libraries. The `dictConfig` example correctly uses `ext://flask.logging.wsgi_errors_stream` for the stream, which matches the new public API. The documentation includes a `RequestFormatter` example that subclasses `logging.Formatter` to inject `request.url` and `request.remote_addr`.

The `tests/test_logging.py` module contains focused tests: `test_logger` verifies the logger name is `'flask.app'`, level is `NOTSET`, and the default handler is added. `test_logger_debug` verifies the level is set to `DEBUG` when `app.debug` is true. `test_existing_handler` verifies no handler is added when the root logger already has one. `test_wsgi_errors_stream` verifies the stream proxies correctly during requests and outside requests. `test_has_level_handler` tests the hierarchy traversal logic with propagate and handler level scenarios. `test_log_view_exception` verifies exception logging during requests.

Gap: The documentation does not mention the `has_level_handler` function or explain the logic for when a default handler is added versus when user-configured handlers are respected. This is an important behavior change that users upgrading need to understand.

Gap: There is no test for the scenario where a user configures logging after accessing `app.logger` and then removes the default handler using `from flask.logging import default_handler` followed by `app.logger.removeHandler(default_handler)`, which is documented in `docs/logging.rst`.

Gap: The `test_template_loader_debugging` test in `tests/test_templating.py` was updated to use `monkeypatch.setattr(logging.getLogger('flask'), 'handlers', [_TestHandler()])` instead of directly modifying `app.logger.handlers`. This is correct but tests the `'flask'` logger namespace rather than `'flask.app'`, which could mask issues if the logger hierarchy changes.
