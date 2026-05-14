# Code Review: PR #14679 - Enable hooks!

## Summary

PR #14679, titled 'Enable hooks!', merges a series of atomic commits that prepare the React codebase for the upcoming release by enabling the hooks feature flag everywhere. The PR changes 27 files with +32 additions and -107 deletions, resulting in a net reduction of 75 lines. The changes are clean and focused, removing the `enableHooks` feature flag and its test overrides, which indicates hooks are now considered stable and ready for general use.

This PR is a critical step in the release process, as it removes the conditional logic that previously required developers to opt-in to hooks via a feature flag. By turning hooks on everywhere, the team is signaling confidence in the feature's stability and preparing for a public release.

## Atomic Commit Analysis

The PR is structured into three atomic commits, each with a clear, focused purpose:

1. **Commit 7c54bff: Turn hooks on everywhere**
   This commit modifies `shared/ReactFeatureFlags` to set `enableHooks = true` by default. This is the foundational change that activates hooks across all environments. The change is minimal and isolated, making it easy to revert if necessary.

2. **Commit 021844a: Remove test overrides (and promote internal tests that only override the hooks flag)**
   This commit removes explicit overrides of `ReactFeatureFlags.enableHooks = true` from test files, since the flag is now on by default. It also renames test files from `.internal.js` to `.js` to reflect their promoted status. For example:
   ```
   ReactHooksInspection-test.internal.js -> ReactHooksInspection-test.js
   ReactHooksInspectionIntegration-test.internal.js -> ReactHooksInspectionIntegration-test.js
   ReactDOMSuspensePlaceholder-test.internal.js -> ReactDOMSuspensePlaceholder-test.js
   ```
   This commit ensures tests run with the default configuration, reducing maintenance overhead.

3. **Commit d1ffc25: Remove hooks flag entirely**
   This commit removes the `enableHooks` flag from `shared/ReactFeatureFlags` entirely, cleaning up the codebase. Since hooks are now always enabled, the flag is no longer needed. This reduces complexity and prevents accidental re-introduction of the conditional logic.

Each commit is atomic and self-contained, making the PR easy to review and bisect if issues arise.

## File Rename Review

The PR renames several test files from `.internal.js` to `.js`, which indicates these tests are no longer internal-only and can run in the standard test suite. The renames include:
- `packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.internal.js` to `ReactHooksInspection-test.js`
- `packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.internal.js` to `ReactHooksInspectionIntegration-test.js`
- `packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.internal.js` to `ReactDOMSuspensePlaceholder-test.js`

These renames are safe because the test content remains unchanged, and the removal of the `enableHooks` override from the `beforeEach` block is the only code change. The tests will now run with the default feature flags, which include hooks enabled. No functionality is altered, and the test coverage remains the same.

## Feature Flag Removal Analysis

The core change in this PR is the removal of the `enableHooks` feature flag from `shared/ReactFeatureFlags`. Initially, the flag was set to `true` by default (commit 7c54bff), and later removed entirely (commit d1ffc25). This indicates that hooks are now a permanent, non-optional feature of React.

Removing the flag simplifies the codebase by eliminating conditional logic that checked `ReactFeatureFlags.enableHooks`. For example, in test files like `ReactDOMServerIntegrationHooks-test.internal.js`, the line `ReactFeatureFlags.enableHooks = true` was removed, as it is no longer needed. This cleanup reduces technical debt and makes the code easier to maintain.

The removal also ensures that hooks are always available in all environments, including production, development, and test. This is consistent with the PR's goal of enabling hooks everywhere for the upcoming release.

## Risk Assessment

The risk of regression from this PR is low. The changes are minimal and well-scoped, focusing only on feature flag removal and test file cleanup. The atomic commit structure allows for easy bisection if issues arise.

One potential risk is that some code paths may have relied on `enableHooks` being false, but this is unlikely since the flag was already set to true in many test environments. The PR ensures that hooks are enabled everywhere, which aligns with the intended release behavior.

Another consideration is that renaming test files could break CI/CD pipelines if they depend on specific file paths. However, this is mitigated by the fact that the renames are part of a coordinated cleanup, and the test framework should handle the changes transparently.

Overall, the risk is minimal, and the benefits of simplifying the codebase outweigh any potential issues.

## Conclusion

PR #14679 is a clean, well-structured change that prepares React for the upcoming release by enabling hooks everywhere. The three atomic commits are logical and easy to follow, and the file renames and feature flag removal are safe and beneficial. The risk of regression is low, and the changes align with the goal of stabilizing hooks for public use.

Based on this review, I recommend that PR #14679 is ready for release. The changes are minimal, focused, and well-tested, with no significant concerns or blocking issues. The team can proceed with confidence.
