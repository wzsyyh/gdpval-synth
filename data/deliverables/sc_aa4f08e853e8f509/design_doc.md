# Design Doc - Unflagging --experimental-strip-types

# Design Doc - Unflagging --experimental-strip-types

## Summary

This document details the design and rationale for PR #56350, merged on December 26, 2024. The change enables the `--experimental-strip-types` flag by default, allowing Node.js to execute TypeScript files without requiring users to pass the flag explicitly.

The PR modifies 22 files with 64 additions and 114 deletions, primarily removing explicit flag references from benchmarks, tests, and documentation, and adding the new `--no-experimental-strip-types` flag for users who need to opt out.

## Motivation

The primary motivation for this change is to enable TypeScript execution by default to catch more bugs in the wild. As noted in the PR description, there are currently no open issues blocking this step, and it is considered a semver minor change.

This decision addresses issue nodejs/typescript#17, which requested enabling the feature by default. By unflagging, the Node.js team aims to gather broader feedback and identify edge cases before considering full stabilization.

## Detailed Design

The PR modifies a total of 22 files across benchmarks, documentation, and source code. Key files changed include:

- `benchmark/ts/strip-typescript.js`: Removed the `--experimental-strip-types` flag from the benchmark flags array.

- `doc/api/cli.md`: Removed the `--experimental-strip-types` documentation section and added the `--no-experimental-strip-types` section.

- The documentation for `--experimental-transform-types` was updated to remove the implication of `--experimental-strip-types`, as it now implies only `--enable-source-maps`.

- The `--input-type` documentation was updated to reflect that `-typescript` values are not available when `--no-experimental-strip-types` is used.

- The stability classification for the feature remains "Stability: 1.1 - Active development", indicating it is still experimental.

The removed documentation section for `--experimental-strip-types` included the YAML metadata `added: v22.6.0` and the stability note. The new `--no-experimental-strip-types` section allows users to opt out, with its own YAML metadata showing `added: v22.6.0` and a `changes` entry for the current version.

## Migration Path

For the majority of users, no action is required. TypeScript files will now execute by default without any additional configuration.

Users who previously set the `--experimental-strip-types` flag explicitly can remove it from their scripts, configuration files, or CLI invocations, as it is now the default behavior.

Users who need to disable the feature must use the new `--no-experimental-strip-types` flag. This is necessary if they encounter issues or prefer not to use TypeScript support.

When `--no-experimental-strip-types` is used, the `-typescript` values for `--input-type` (e.g., `"module-typescript"`, `"commonjs-typescript"`) are not available. This means users opting out cannot use these input types to run TypeScript code.

## Risk Analysis

One risk is that enabling the flag by default may break existing workflows that depend on TypeScript execution being opt-in. For example, some environments might have relied on the absence of the flag to avoid parsing overhead or compatibility issues. The introduction of `--no-experimental-strip-types` mitigates this by providing an explicit opt-out mechanism.

Another significant risk is the experimental nature of the feature. As stated in the PR description: "This feature is experimental and is subject to change." This means that the behavior, supported syntax, or even the existence of the feature could be altered in future releases, potentially causing breaking changes for users who adopt it.

The PR notes that the supported syntax has limitations documented at https://nodejs.org/api/typescript.html#type-stripping, and users should be aware of these constraints to avoid unexpected errors.

## Open Questions

1. When will the TypeScript type-stripping feature be considered stable? The current stability is "1.1 - Active development", but a clear roadmap for moving to stability level 2 or 3 is needed for long-term planning.

2. What additional TypeScript syntax or features might be supported in the future? The current limitations may need to be addressed to improve usability and adoption.

3. How will user feedback be collected and prioritized? Given that the feature is now enabled by default, a process for triaging and responding to bug reports and feature requests is essential.
