# Code Review: PR #63209 - Stabilize async_await in Rust 1.39.0

## Review Summary

This review covers PR #63209, which stabilizes the `async/await` syntax for inclusion in Rust 1.39.0. The PR represents the culmination of extensive work to bring first-class async/await support to stable Rust.

Three language features are being stabilized in this PR: free and inherent `async fn`s, the `<expr>.await` expression form, and the `async move? { ... }` block form. This PR closes issue #62149 (the primary stabilization tracking issue) and issue #50547.

## Scope of Changes

The PR modifies 181 files with +271 additions and -605 deletions. The net reduction of 334 lines reflects the removal of now-unnecessary feature gate attributes and unstable annotations across the codebase.

The predominant pattern of changes involves removing `#![feature(async_await)]` attributes from test files, documentation examples, and error code illustrations. Additionally, `#[unstable]` attributes marking the `async` and `await` keywords as unstable are removed from the standard library keyword documentation.

## Technical Analysis

The diff reveals a systematic and consistent pattern of feature gate removal across multiple compiler and standard library components. In `src/librustc/error_codes.rs`, the `#![feature(async_await)]` line is removed from erroneous and corrected code examples for error E0698, which documents issues with type inference in async contexts.

In `src/librustc_typeck/check/mod.rs`, the feature gate is removed from the documentation comment on the `FnCtxt` type that illustrates a common error of forgetting `.await` when using futures. This change ensures the documentation example reflects stable Rust syntax.

The changes in `src/librustc_typeck/error_codes.rs` are particularly noteworthy. The feature gate is removed from examples for error E0733 (recursion in async fns requiring boxing) and the desugared alternative example. Additionally, a pre-existing typo is corrected: `foo_desugered` is fixed to `foo_desugared` in both the function name and its recursive call. This is a valuable incidental cleanup that improves documentation quality.

In `src/libstd/keyword_docs.rs`, the `#[unstable(feature = "async_await", issue = "50547")]` attribute is removed from both the `async` and `await` keyword documentation modules. This marks these keywords as fully stable in the standard library documentation.

## Documentation Updates

Three error codes have their documentation updated in this PR. Error E0698 in `src/librustc/error_codes.rs` has its code examples updated to remove the async_await feature gate, making the examples valid for stable Rust. Error E0733 in `src/librustc_typeck/error_codes.rs` similarly has its examples updated, covering the async recursion documentation. The related E0720 desugared example is also updated.

The keyword documentation in `src/libstd/keyword_docs.rs` undergoes a structural change: the `#[unstable(feature = "async_await", issue = "50547")]` annotation is removed from both the `async` keyword module and the `await` keyword module. This is the change that will cause these keywords to appear as stable in the generated Rust documentation for 1.39.0. The issue number 50547 referenced in these annotations corresponds to the original tracking issue for async/await stabilization.

## Risk Assessment

The risk level of this stabilization PR is low. The changes are predominantly mechanical removals of feature gate attributes and unstable annotations. There are no changes to compiler logic, type checking rules, or runtime behavior. The actual implementation of async/await was completed in prior PRs; this PR simply removes the feature gates that previously restricted async/await to nightly builds.

The PR description confirms that all identified blockers have been resolved. These include issue #61949 (addressed by PR #62849), issue #62517 (addressed by PR #63376), issue #63225 (addressed by PR #63501), issue #63388 (addressed by PR #63499), and issue #63500 (addressed by PR #63501). Additionally, control flow tests for `?`, `return` in async blocks, and `break` were added in PR #63387. The FCP (Final Comment Period) in issue #62149 has been completed.

## Recommendation

Recommendation: **Approve**. The changes are clean, consistent, and mechanically sound. All feature gate removals follow the established pattern for stabilizing language features in the Rust compiler. The incidental typo correction in `src/librustc_typeck/error_codes.rs` is a welcome bonus. With all blockers resolved and the FCP completed, this PR is ready for merge to enable async/await in Rust 1.39.0.
