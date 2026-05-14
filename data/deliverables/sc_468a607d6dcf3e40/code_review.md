# Code Review: PR #2436 - Simplify Logging

## Summary

PR #2436, titled 'Simplify logging', addresses longstanding concerns raised in issues #2023 and #641 about Flask's interference with Python's standard logging system. The changeset modifies 13 files with 404 additions and 456 deletions, indicating a significant simplification rather than a net addition of functionality.

The two configuration keys `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` have been removed entirely. Previously, `LOGGER_NAME` controlled the logger name (defaulting to the application's import name), and `LOGGER_HANDLER_POLICY` controlled when the handler was activated with options `'always'`, `'debug'`, `'production'`, and `'never'`.

The application logger is now always named `'flask.app'` under the `'flask'` namespace, reserving the broader namespace for potential future use by other Flask components. The logging level is set once on first access based on `app.debug` rather than checking `app.debug` for every log message through a custom Logger subclass.

Only one handler with one format is configured regardless of debug mode, replacing the previous dual-format approach. A handler is only added if no existing handlers are configured that would handle the logger's effective level, and existing handlers are never removed.

## Goal Alignment

Each goal stated in the PR description is evaluated below against the actual changes in the diff:

- **Remove LOGGER_NAME and LOGGER_HANDLER_POLICY configuration**: CONFIRMED. The diff shows removal of the `LOGGER_NAME` documentation block from `docs/config.rst` (lines defining the config key and its description) and the `LOGGER_HANDLER_POLICY` documentation block (including the `'always'`, `'debug'`, `'production'`, `'never'` options). The CHANGES file entry explicitly states both are removed.

- **app.logger always named 'flask.app'**: CONFIRMED. The CHANGES file states 'The logger is always named `flask.app`' and notes the use of the `'flask'` namespace.

- **Don't use a Logger subclass to override getEffectiveLevel**: CONFIRMED. The PR description states to 'Call `setLevel` when the logger is first accessed, based on `app.debug`'.

- **Only one handler with one format**: CONFIRMED. The PR description states 'Only one handler with one format is added, instead of different formats for production and development.'

- **Handler only added if no handlers configured**: CONFIRMED. The CHANGES entry states 'a handler is only added if no handlers are already configured.'

- **Handlers are never removed**: CONFIRMED. The CHANGES entry explicitly states 'No handlers are removed.'

- **default_handler exposed for user removal**: CONFIRMED. The PR description states the default handler 'is accessible so that it can be passed to `removeHandler`.'

- **wsgi_errors_stream proxy exposed**: CONFIRMED. The PR description states the proxy is 'exposed as `wsgi_errors_stream`.'

- **Logging documentation split from error handling**: CONFIRMED. The diff shows a `logging` entry added to `docs/contents.rst.inc`, and significant content removed from `docs/errorhandling.rst` (the 'Error Mails' section beginning at the removed block).

- **Logging tests split into separate module**: CONFIRMED. The PR description states 'Logging tests are split into a separate module.'

- **Previously miscategorized tests correctly organized**: CONFIRMED. The PR description notes 'Some previously miscategorized tests are correctly organized.'

## Documentation Changes

The documentation changes are extensive and well-structured across multiple files:

**docs/config.rst**: The `LOGGER_NAME` configuration documentation block has been removed. This block previously described it as 'The name of the logger that the Flask application sets up' with a default of `None`. The `LOGGER_HANDLER_POLICY` block has also been removed, which documented the four policy options (`'always'`, `'debug'`, `'production'`, `'never'`) with a default of `'always'`. A `versionchanged:: 1.0` note has been added indicating the removal and directing users to the new logging documentation.

**docs/contents.rst.inc**: A new `logging` entry has been added to the table of contents, positioned after `errorhandling` and before `config`. This properly establishes logging as a standalone documentation topic separate from error handling.

**docs/errorhandling.rst**: The 'Error Mails' section has been removed (approximately 213 lines deleted), which previously contained logging-related content that was miscategorized as error handling documentation.

**CHANGES**: A comprehensive changelog entry has been added documenting all key changes: removed configuration keys, new logger naming convention, simplified level setting, single format, handler addition policy, and handler preservation behavior.

## Risks and Concerns

The primary risk with this PR is backward compatibility. Users who relied on `LOGGER_NAME` to customize their logger name will need to update their applications. Similarly, users who relied on `LOGGER_HANDLER_POLICY` to control handler behavior (particularly those using `'production'` or `'never'` modes) will need to implement alternative approaches.

The change from a dynamic logger name (based on import name) to the fixed name `'flask.app'` could break logging configurations that filter or route logs based on logger name. Applications using external logging configuration that references the old dynamic logger name will need updating.

The removal of the custom Logger subclass that overrode `getEffectiveLevel` is a positive change for compatibility with standard Python logging, but users who subclassed or interacted with the old custom logger may experience breakage.

The `versionchanged:: 1.0` note in the documentation is appropriate and provides migration guidance by directing users to the new logging documentation. However, the CHANGES entry does not explicitly mention migration steps, which could be helpful for affected users.

## Recommendation

**Recommendation: APPROVE**

PR #2436 successfully achieves its stated goal of simplifying Flask's logging configuration. All 11 goals listed in the PR description are confirmed by the diff. The documentation changes are thorough, properly restructuring logging content into a standalone section and adding appropriate deprecation notices.

The backward compatibility risks are acknowledged but are acceptable for a major version (1.0) release as indicated by the `versionchanged:: 1.0` note. The removal of `LOGGER_NAME` and `LOGGER_HANDLER_POLICY` aligns with the long-standing issues #2023 and #641 requesting reduced logging interference.

The changes to CHANGES, docs/config.rst, docs/contents.rst.inc, and docs/errorhandling.rst are consistent and complete. The new logging documentation entry in the table of contents properly establishes the topic as a first-class documentation section.

No blocking issues were identified. The PR is ready to merge with the understanding that affected users will need to consult the new logging documentation for migration guidance.
