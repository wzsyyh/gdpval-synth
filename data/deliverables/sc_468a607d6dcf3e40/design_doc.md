# Design Document: Simplify Logging - PR #2436

# Design Document: Simplify Logging - PR #2436

## Summary

This document details the changes proposed in pull request #2436, which simplifies the logging configuration and behavior in Flask. The primary goal is to reduce the level of interference Flask imposes on the standard Python logging system, making logging more predictable and easier for users to configure. The changes remove legacy configuration keys, standardize the logger name, and simplify handler management.

## Motivation

The motivation for these changes stems from discussions in issues #2023 and #641. The core problem identified is that Flask interferes too much with logging. The existing system uses configuration keys like `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` to control logger behavior in ways that often conflict with user expectations and make it difficult to integrate with application-specific logging setups. By simplifying this, Flask will adhere more closely to the standard Python logging best practices.

## Changes Overview

### Configuration

The following configuration keys have been removed: `LOGGER_NAME` and `LOGGER_HANDLER_POLICY`. Previously, `LOGGER_NAME` allowed customizing the logger's name, defaulting to the application's import name. Now, `app.logger` is always named `'flask.app'`. This uses the `'flask'` namespace to allow for other logging from Flask in the future. The `LOGGER_HANDLER_POLICY` key, which controlled when the handler was active (e.g., 'always', 'debug', 'production', 'never'), is no longer used.

### Logger Behavior

A custom `Logger` subclass was previously used to override `getEffectiveLevel`. This has been removed. Instead, the logger's level is set once when it is first accessed, based on the value of `app.debug`. This eliminates the need to check the debug setting for every message logged. Regarding handlers, the policy has been simplified: only one handler with one format is added, rather than different formats for production and development. A handler is only added if there are no existing handlers configured that would handle the logger's `getEffectiveLevel`. Importantly, handlers are never removed by Flask. The `default_handler` is made accessible so users can pass it to `removeHandler` if they wish to remove it themselves. The proxy stream to `environ['wsgi.errors']` is now exposed as `wsgi_errors_stream` for user configuration.

### Documentation

The logging documentation has been separated from the error handling documentation. It is now in a dedicated section to address key logging concepts more clearly. New documentation has been added for injecting request information into log messages. This reorganization aims to make it easier for users to find and understand logging configuration.

## Migration Guide

Users upgrading to this version need to update their application configuration. The `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` configuration keys are no longer recognized and should be removed from any configuration files or `app.config` settings. If you previously relied on `LOGGER_HANDLER_POLICY` to control handler activation, you will need to manage handlers manually using standard Python logging techniques. The logger name is now fixed to `'flask.app'`; if your logging configuration filters by logger name, update it accordingly. To remove the default handler provided by Flask, use `app.logger.removeHandler(app.logger.default_handler)`. If you were using the WSGI error stream directly, you can now access it via `app.wsgi_errors_stream`.

## Impact

These changes are intended to simplify logging but may require adjustments in existing applications. The removal of `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` is a breaking change for applications that used them. Applications that relied on the automatic handler removal or different log formats for debug vs. production will see different behavior. However, the new behavior is more aligned with standard logging practices, giving users more control. The exposure of `default_handler` and `wsgi_errors_stream` provides new hooks for advanced configuration.

## Testing

To ensure the changes work as expected and do not introduce regressions, the logging tests have been split into a separate, dedicated module. This improves test organization and makes it easier to maintain logging-specific tests. Some previously miscategorized tests have also been correctly organized within this new module. The test coverage validates the new logging behavior, including the level-setting logic, handler management, and the accessibility of the new stream and handler attributes.
