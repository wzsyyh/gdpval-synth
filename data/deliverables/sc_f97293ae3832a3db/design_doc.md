# Technical Design Document: Experimental React Compiler Support in Next.js

# Technical Design Document: Experimental React Compiler Support in Next.js

This document describes the technical design of the experimental React compiler integration introduced in Next.js via PR #65804. The feature exposes a new `experimental.reactCompiler` configuration option that allows Next.js users to opt into using the React compiler (https://react.dev/learn/react-compiler) for automatic optimization of React components. This design document is intended for review by the React team at Meta to ensure architectural alignment and gather feedback before the feature graduates from experimental status.

PR #65804 was merged on 2024-05-16 and introduces 538 additions and 89 deletions across 15 changed files. The primary configuration changes are in the Rust-side Next.js SWC crate at `packages/next-swc/crates/next-core/src/next_config.rs`.

## Overview

The `experimental.reactCompiler` option in `next.config.js` allows users to enable the React compiler. This option can be set to either a simple boolean (`true` to enable with defaults) or an object containing a partial set of the React compiler's own configuration options. When enabled, the compiler is integrated at the build step through a Babel plugin, regardless of whether the user is using webpack or Turbopack as their bundler.

The React compiler itself is an experimental tool from the React team (documented at https://react.dev/learn/react-compiler). It automatically optimizes React components by memoizing values and reducing unnecessary re-renders, aiming to replace the need for manual `useMemo`, `useCallback`, and `React.memo` usage in many cases.

## Configuration Schema

The Rust-side configuration layer defines the schema for the React compiler options. Three new types are introduced in `next_config.rs`:

**`ReactCompilerMode`** is an enum with three variants: `Infer`, `Annotation`, and `All`. This enum is annotated with `#[turbo_tasks::value(shared)]`, derives `Clone` and `Debug`, and uses `#[serde(rename_all = "camelCase")]` for JSON serialization. The variants correspond to different modes the compiler can operate in.

**`ReactCompilerOptions`** is a struct with two optional fields:
- `compilation_mode: Option<ReactCompilerMode>` — selects the compiler's operating mode
- `panic_threshold: Option<String>` — controls the threshold at which the compiler panics on errors

Both fields use `#[serde(skip_serializing_if = "Option::is_none")]` to omit them from serialized output when not set. The struct also uses `#[turbo_tasks::value(shared)]` and derives `Clone` and `Debug`.

**`ReactCompilerOptionsOrBoolean`** is an untagged enum that allows the configuration to accept either a plain boolean or a `ReactCompilerOptions` object. This provides the flexible user-facing API where `reactCompiler: true` is equivalent to enabling with defaults, while `reactCompiler: { compilationMode: 'infer' }` allows fine-grained control.

Finally, **`OptionalReactCompilerOptions`** is defined as a transparent turbo-tasks value wrapping `Option<Vc<ReactCompilerOptions>>`, enabling the value to be passed through the turbo-tasks build graph.

The `ExperimentalConfig` struct is updated to include a new field: `react_compiler: Option<ReactCompilerOptionsOrBoolean>`. This field is optional, meaning the feature is disabled by default when the key is absent from the configuration.

## Integration Architecture

The React compiler is integrated into the Next.js build pipeline via a Babel plugin. This design choice applies uniformly to both the webpack and Turbopack bundlers, ensuring consistent behavior regardless of which bundler the user has configured.

When a user has an existing `.babelrc` configuration file in their project, the React compiler Babel plugin is appended to their existing Babel configuration. This preserves any custom Babel transforms the user has already set up while adding the compiler on top.

When no `.babelrc` exists, Next.js uses its default transform pipeline: SWC for webpack projects or Turbopack for Turbopack projects. In this case, the general JavaScript/TypeScript transformation is still handled by SWC or Turbopack for performance, but the React compiler Babel plugin runs as an additional pass through Babel. This is a hybrid approach — SWC or Turbopack handles the bulk of the transform work at high speed, and only the React compiler step is delegated to Babel.

This hybrid architecture means that even projects that have fully adopted SWC (and thus have no `.babelrc`) will still incur a Babel invocation for the React compiler step. This is a deliberate trade-off: the React compiler is an experimental tool and its Babel plugin is the officially supported integration point. Future work may move this into SWC or Turbopack natively once the compiler stabilizes.

## Type Safety and Serde Changes

As part of PR #65804, the `Eq` trait was added to the derive list of four existing configuration structs: `RuleConfigItemOptions`, `RuleConfigItemOrShortcut`, `RuleConfigItem`, and `LoaderItem`. Previously, these structs only derived `PartialEq`; the addition of `Eq` indicates a strengthening of the equality contract (from partial to total equality).

While the diff does not explicitly state the motivation, the likely reason is that new code introduced by this PR — or existing code that was refactored — requires total equality comparisons for these types. This is common when configuration values are used as keys in hash maps, compared in tests with `assert_eq!`, or validated against expected values in build pipelines. The `Eq` trait is a marker trait that extends `PartialEq` to assert that the equality relation is reflexive, symmetric, and transitive for all values of the type.

These structs use `#[serde(rename_all = "camelCase")]` and `#[serde(untagged)]` attributes for serialization, and they remain unchanged in their serialization behavior. The only change is the addition of `Eq` to their derive lists.

## Limitations and Open Questions

Several technical concerns arise from this design that would benefit from React team input:

**1. Babel dependency for SWC/Turbopack users.** The current design requires a Babel invocation even when the user has no `.babelrc` and is using SWC or Turbopack for all other transforms. This introduces a performance penalty and a dependency on Babel infrastructure that many Next.js users have deliberately moved away from. Questions for the React team: Is there a timeline for a native SWC or Turbopack plugin for the React compiler? Could the compiler expose a lower-level API that allows non-Babel integrations?

**2. Configuration schema alignment.** The `ReactCompilerOptions` struct in Next.js exposes only two fields: `compilation_mode` and `panic_threshold`. This is described as a "subset" of the compiler's options. However, the PR description does not specify which compiler options are intentionally excluded or why. Questions for the React team: Which additional compiler configuration options exist? Is this subset sufficient for most use cases? How should Next.js handle forward compatibility if new compiler options are added upstream?

**3. Error handling and `panic_threshold`.** The `panic_threshold` field is typed as `Option<String>` rather than a more constrained type (e.g., an enum of severity levels). This suggests the value is passed through to the compiler as a raw string. Questions: What are the valid values for `panic_threshold`? Should Next.js validate this field, or is pass-through to the compiler sufficient?
