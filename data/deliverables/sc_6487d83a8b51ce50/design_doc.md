# Design Document: Built-in .env File Support

# Design Document: Built-in .env File Support

# Design Document: Built-in .env File Support

**Status:** Merged (PR #48890, 2023-08-17)
**Stability:** 1.1 - Active development
**Feature:** `--env-file` command-line flag

This document describes the design and current implementation of built-in `.env` file support in Node.js, introduced via PR #48890. It serves as a reference for the feature's capabilities, limitations, and planned future enhancements.

## Overview

The `--env-file` flag provides a built-in mechanism for loading environment variables from a specified file. As described in the documentation diff, it "loads environment variables from a file relative to the current directory, making them available to applications on `process.env`." This eliminates the need for external packages like `dotenv` for common use cases.

The flag parses and applies Node.js-specific environment variables, such as `NODE_OPTIONS`, which are "parsed and applied" during startup. The feature is currently at Stability 1.1, indicating active development and potential for change in non-semver-major releases.

The implementation supports basic `.env` file formatting: one key-value pair per line, comments prefixed with `#`, and the ability to quote values using backslash, double quote, or single quote characters, which are omitted from the final value.

## Current Implementation Details

### File Format Specification

The `.env` file follows a simple line-oriented format. Each line contains a single environment variable assignment in the form `KEY=VALUE`. The format supports:
- **Comments:** Any text after a `#` character is treated as a comment and ignored.
- **Quoted Values:** Values can be enclosed in backslash (`\`), double quote (`"`), or single quote (`'`) characters. The enclosing quotes are omitted from the final value stored in `process.env`.
- **Line Structure:** Each line defines one variable; there is no support for multiline values in this implementation.

### Modified Files

The PR introduced changes to three key areas of the codebase:
1. **`doc/api/cli.md`**: Added documentation for the new `--env-file=config` flag, including usage examples, format specification, and stability information.
2. **`node.gyp`**: Added the new source files `src/node_dotenv.cc` and `src/node_dotenv.h` to the build configuration.
3. **`src/env.cc`**: Modified the `Environment::GetCwd` function. The signature was changed from `std::string Environment::GetCwd()` to `std::string Environment::GetCwd(const std::string& exec_path)`, allowing the working directory resolution to use a provided path as a fallback.

### Variable Precedence

As specified in the documentation, "if the same variable is defined in the environment and in the file, the value from the environment takes precedence." This ensures that existing environment configurations are not inadvertently overridden by the `.env` file.

## Supported and Missing Features

The following table summarizes the feature requests from the PR discussion and their implementation status. Features marked with [x] are implemented in PR #48890.

| Feature | Status | Notes |
| :--- | :--- | :--- |
| Custom path instead of .env in cwd | ✅ Implemented | Supported via `--env-file [path-to-file]` flag |
| Comments in .env files | ✅ Implemented | Text after `#` is treated as a comment |
| `--env-file` flag naming | ✅ Implemented | Flag uses `--env-file` format as requested |
| Windows newline character support | ✅ Implemented | Fixed and supported |
| Support for `NODE_OPTIONS` | ✅ Implemented | Parsed and applied from the .env file |
| Augment vs. overwrite process.env | ❌ Not Implemented | Future work: determine conflict resolution |
| Programmatic API | ❌ Not Implemented | Explicitly excluded from this PR |
| Load values into object other than process.env | ❌ Not Implemented | Explicitly excluded from this PR |
| Multiline values | ❌ Not Implemented | Explicitly excluded from this PR |
| Variable expansion | ❌ Not Implemented | Explicitly excluded from this PR |

### Missing Features (from PR Description)

The PR description explicitly lists the following features as not implemented and reserved for future separate PRs:
- Respect newline character in values with quotes
- Multiline values
- Variable expansion
- Incremental env support (e.g., `.env.development` overrides `.env` on `NODE_ENV=development`)

## Open Questions and Future Work

### Unresolved Follow-up Items

The following items from the PR comments remain unresolved and require design decisions before implementation:
1. **Augment vs. Overwrite Behavior** (@cjihrig): The core question is whether the `.env` file should add to `process.env` or replace it. If augmenting, the conflict resolution strategy (overwrite, don't overwrite, throw, etc.) must be defined.
2. **Respecting Newlines in Quoted Values** (Missing Feature): Currently, values with embedded newlines are not supported. This requires parsing logic to handle multiline strings within quotes.
3. **Variable Expansion** (Missing Feature): Supporting syntax like `${VAR}` to reference other variables within the `.env` file. This is a common feature in dotenv packages but adds complexity to the parser.

### Proposed Prioritization

Based on the discussion context and common usage patterns, the following prioritization for future work is recommended:
1. **High Priority: Augment vs. Overwrite Behavior** - This is a fundamental design decision that affects all users of the feature. Resolving this first establishes the correct default behavior and prevents breaking changes later.
2. **Medium Priority: Respecting Newlines in Quoted Values** - This addresses a basic limitation in the current parser and would improve compatibility with common `.env` file formats.
3. **Low Priority: Variable Expansion and Incremental Support** - While useful, these are more advanced features that can be added later without disrupting the core functionality. They are commonly handled by external packages in the meantime.

## References

- **dotenv Test Suite:** https://github.com/motdotla/dotenv/tree/master/tests (reference for testing and validation)
- **Node.js Discussions:** https://github.com/orgs/nodejs/discussions/44975 (context for missing features)
- **Related Issue:** https://github.com/nodejs/node/issues/49148 (follow-ups tracking)
