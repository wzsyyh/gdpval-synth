# Code Review: PR #65804 - feat(next): experimental react compiler support

# Code Review: PR #65804 - feat(next): experimental react compiler support

## Summary

PR #65804, titled "feat(next): experimental react compiler support", introduces a new experimental configuration option `experimental.reactCompiler` to the Next.js framework in the vercel/next.js repository. The change spans 15 files with 538 additions and 89 deletions. The primary purpose is to expose configuration for the React compiler (https://react.dev/learn/react-compiler), allowing users to opt into automatic memoization through the build pipeline. The configuration value accepts either a boolean toggle or an object containing a partial set of the compiler's own configuration options.

A key file in this PR is `packages/next-swc/crates/next-core/src/next_config.rs`, which defines the Rust-side configuration types that Next.js uses to parse and validate user-provided configuration. For both webpack and turbopack build paths, the feature is enabled by adding a babel plugin for the React compiler. If a user has an existing `.babelrc`, the plugin is appended; otherwise, SWC (for webpack) or turbopack handles the general transform while only the compiler babel plugin runs through babel.

## Architecture and Design Review

The PR introduces three new types in `next_config.rs`: `ReactCompilerMode` (an enum with variants `Infer`, `Annotation`, and `All`), `ReactCompilerOptions` (a struct with optional `compilation_mode` and `panic_threshold` fields), and `ReactCompilerOptionsOrBoolean` (an untagged serde enum that accepts either a boolean or the options struct). This design mirrors existing patterns in the Next.js config surface, for example, `ServerActionsOrLegacyBool` appears nearby in the `ExperimentalConfig` struct. The use of `#[serde(untagged)]` on `ReactCompilerOptionsOrBoolean` is appropriate here because it allows users to write either `reactCompiler: true` or `reactCompiler: { compilationMode: 'all', panicThreshold: '...' }` in their `next.config.js` without discriminating tags.

Both `ReactCompilerMode` and `ReactCompilerOptions` are annotated with `#[turbo_tasks::value(shared)]`, meaning they are first-class values in the turbopack incremental computation graph. This is the correct approach for configuration data that turbopack will need to read during compilation. The `OptionalReactCompilerOptions` type is declared as a transparent turbo_tasks value wrapping `Option<Vc<ReactCompilerOptions>>`, enabling it to participate in turbo_tasks' memoization and dependency tracking.

The integration strategy is noteworthy: the React compiler is added as a babel plugin rather than a native SWC or turbopack transform. The PR description explains that if a user has an existing `.babelrc`, the plugin is appended to it; otherwise, the general transform still runs through SWC (webpack) or turbopack, but only the compiler babel plugin executes through babel. This hybrid approach introduces a babel dependency even for projects that previously relied entirely on SWC, which has performance implications worth monitoring.

## Type Safety and Derive Macro Changes

Four existing structs in `next_config.rs` had the `Eq` trait added to their derive list in this PR: `RuleConfigItemOptions`, `RuleConfigItemOrShortcut`, `RuleConfigItem`, and `LoaderItem`. Each of these previously derived `Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs` and now also derives `Eq`. The addition of `Eq` is likely required because these types are used in contexts that demand full equivalence checking, for example, as keys in hash maps or within turbo_tasks value comparisons.

All four types contain only `String`, `bool`, `Option<String>`, and `Vec<LoaderItem>` fields, which are types that naturally implement `Eq`. Since `Eq` is a marker trait extending `PartialEq` with the guarantee that `a == a` is always true, and none of the fields involve floating-point numbers or other non-reflexive types, the addition is safe. This is a low-risk, mechanically sound change that aligns with Rust's trait coherence requirements.

## Configuration Surface Area

The `ReactCompilerOptions` struct exposes exactly two fields from the broader React compiler configuration: `compilation_mode` (typed as `Option<ReactCompilerMode>`) and `panic_threshold` (typed as `Option<String>`). Both fields use `#[serde(skip_serializing_if = "Option::is_none")]`, ensuring that `None` values are omitted from serialized output rather than emitting null. This is the standard Next.js convention for optional configuration fields and is correctly applied here.

The choice of `panic_threshold` as a `String` rather than a typed enum (for example, a `PanicThreshold` enum with variants like `None`, `Critical`, `All`) is a pragmatic decision because it forwards the value directly to the React compiler's own configuration without needing to track upstream changes. However, it does shift validation responsibility to the compiler itself, meaning invalid values will not be caught at the Next.js config parsing stage. This is an acceptable tradeoff for an experimental feature but should be revisited if the feature moves out of experimental status.

The `ReactCompilerMode` enum provides three modes: `Infer`, `Annotation`, and `All`, which correspond to the React compiler's own compilation modes. This subset appears sufficient for initial experimental use. Future iterations may need to expose additional options such as custom component filters or module-level granularity.

## Risks and Concerns

**1. Babel dependency for all users:** The PR adds a babel plugin even for projects that do not have a `.babelrc`. This means enabling `reactCompiler: true` forces babel into the build pipeline, potentially negating SWC's performance advantages. Users expecting a pure-SWC build will encounter unexpected babel invocations. This should be clearly documented, and benchmarks should be provided comparing build times with and without the compiler enabled.

**2. Untagged enum error messages:** The `#[serde(untagged)]` attribute on `ReactCompilerOptionsOrBoolean` can produce confusing deserialization error messages when users provide invalid configuration. If a user writes `reactCompiler: "invalid"`, serde will attempt to parse it as a boolean (fail), then as `ReactCompilerOptions` (fail), and return a generic error. Next.js should add custom validation or error handling to surface actionable messages.

**3. Experimental compiler stability:** The React compiler itself is experimental (as noted by the https://react.dev/learn/react-compiler reference). Shipping experimental compiler support as a Next.js configuration option means users may encounter compiler bugs that manifest as Next.js issues. Clear communication about the experimental status and a way to disable the compiler without reverting configuration are essential.

**4. `panic_threshold` validation gap:** As noted above, `panic_threshold` is an untyped `String`. Invalid values will pass Next.js config validation silently and only fail at compile time within the React compiler. A typed enum or at least a regex validation would improve the user experience.

**5. Eq trait additions:** While the addition of `Eq` to `RuleConfigItemOptions`, `RuleConfigItemOrShortcut`, `RuleConfigItem`, and `LoaderItem` is safe for current field types, it sets a precedent. If a floating-point field is ever added to any of these structs, the `Eq` derive will fail to compile, which is actually the correct behavior. However, if someone removes the `Eq` derive to unblock compilation, they may introduce subtle equality bugs. This is a minor concern but worth noting for future maintainers.

## Recommendations

**Add integration tests** for the new configuration surface. Specifically, test that `reactCompiler: true`, `reactCompiler: false`, and `reactCompiler: { compilationMode: 'all', panicThreshold: '...' }` all parse correctly from `next.config.js` and produce the expected babel plugin configuration. Test edge cases such as `reactCompiler: {}` (empty object) and `reactCompiler: 42` (invalid type).

**Improve error messages** for invalid `reactCompiler` values. Consider adding a custom serde deserializer or post-parse validation step that produces actionable error messages rather than serde's generic "data did not match any variant" error for `ReactCompilerOptionsOrBoolean`.

**Document the babel requirement** prominently in the Next.js documentation for this feature. Users should understand that enabling the React compiler introduces a babel dependency and may impact build performance. Include a benchmark comparing build times with and without `reactCompiler` enabled on a representative Next.js application.

**Add a configuration guide** explaining the three `ReactCompilerMode` variants (`Infer`, `Annotation`, `All`) and when to use each. Since `panic_threshold` is a free-form string, document the valid values that the React compiler accepts.

**Consider typed validation** for `panic_threshold`. Even if the React compiler's upstream configuration changes, a validation step at the Next.js layer would catch obvious mistakes (for example, empty string or numeric values) before they reach the compiler.

**Track upstream React compiler changes.** As the React compiler evolves from experimental to stable, the `ReactCompilerOptions` struct should be expanded to expose additional configuration options. Create a tracking issue for this follow-up work.
