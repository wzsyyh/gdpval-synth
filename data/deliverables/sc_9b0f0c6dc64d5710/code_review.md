# Code Review - PR #14679: Enable Hooks!

# Code Review - PR #14679: Enable Hooks!

## PR Summary

PR #14679, titled "Enable hooks!", was merged on January 23, 2019, in preparation for the upcoming React release. The PR unconditionally enables React hooks across the entire codebase by removing the `enableHooks` feature flag and all conditional logic that depended on it. The changes span 27 files with 32 additions and 107 deletions, reflecting a net reduction in code complexity.

The PR is organized into three atomic commits to simplify review: (1) commit 7c54bff turns hooks on everywhere by removing conditional guards, (2) commit 021844a removes test overrides and promotes internal tests that previously only overrode the hooks flag, and (3) commit d1ffc25 removes the hooks flag definition entirely from the shared feature flags module and all its forks.

## Scope of Changes

The changes in this PR fall into six distinct categories:

**Feature Flags** — The `enableHooks` constant is removed from the main flags file and all platform-specific forks: `packages/shared/ReactFeatureFlags.js`, `packages/shared/forks/ReactFeatureFlags.native-fb.js`, `packages/shared/forks/ReactFeatureFlags.native-oss.js`, `packages/shared/forks/ReactFeatureFlags.persistent.js`, `packages/shared/forks/ReactFeatureFlags.test-renderer.js`, `packages/shared/forks/ReactFeatureFlags.test-renderer.www.js`, and `packages/shared/forks/ReactFeatureFlags.www.js`.

**Reconciler Logic** — Conditional hooks code is removed from `packages/react-reconciler/src/ReactFiberHooks.js`, `packages/react-reconciler/src/ReactFiberCommitWork.js`, `packages/react-reconciler/src/ReactFiberScheduler.js`, and the `DispatcherWithoutHooks` export is removed from `packages/react-reconciler/src/ReactFiberDispatcher.js`.

**Server-Side Rendering** — The server renderer is updated in `packages/react-dom/src/server/ReactPartialRenderer.js` and `packages/react-dom/src/server/ReactPartialRendererHooks.js`, where `DispatcherWithoutHooks` is removed and the dispatcher assignment is simplified.

**Test Files** — Multiple test files have `ReactFeatureFlags.enableHooks = true` lines removed, and four test files are renamed from `.internal.js` to `.js` to promote them to non-internal status.

**Shallow Renderer** — `packages/react-test-renderer/src/ReactShallowRenderer.js` has the `enableHooks` conditional removed from constructor initialization and the render path.

**Public API** — `packages/react/src/React.js` is updated to unconditionally expose all hook functions on the React object.

## Flag Removal Analysis

The core change removes the `enableHooks` export from `packages/shared/ReactFeatureFlags.js`. Previously, this file exported `export const enableHooks = false;` (line 12 in the original). This line is deleted entirely.

All platform-specific fork files are similarly updated. In `packages/shared/forks/ReactFeatureFlags.www.js`, the line `export const enableHooks = true;` is removed. In `packages/shared/forks/ReactFeatureFlags.native-fb.js`, `export const enableHooks = true;` is removed. In `packages/shared/forks/ReactFeatureFlags.test-renderer.www.js`, `export const enableHooks = true;` is removed. The remaining forks (`ReactFeatureFlags.native-oss.js`, `ReactFeatureFlags.persistent.js`, `ReactFeatureFlags.test-renderer.js`) each had `export const enableHooks = false;` which is now removed.

In `packages/react-reconciler/src/ReactFiberHooks.js`, the function `renderWithHooks` previously contained a guard: `if (!enableHooks) { return Component(props, refOrContext); }` which would short-circuit hook rendering. This guard is removed, so the full hooks rendering path is always executed. Similarly, `resetHooks()` previously returned early if hooks were disabled; that early return is removed.

In `packages/react-reconciler/src/ReactFiberCommitWork.js`, the function `commitHookEffectList` previously returned early with `if (!enableHooks) { return; }`. This guard is removed so hook effects are always committed.

In `packages/react-reconciler/src/ReactFiberScheduler.js`, the conditional `if (enableHooks && effectTag & Passive)` is simplified to `if (effectTag & Passive)`, and the conditional block for passive effects scheduling is simplified from `if (enableHooks && firstEffect !== null && rootWithPendingPassiveEffects !== null)` to `if (firstEffect !== null && rootWithPendingPassiveEffects !== null)`.

## Dispatcher Consolidation

A key part of this refactor is the elimination of the `DispatcherWithoutHooks` fallback dispatcher. Previously, two dispatcher objects were exported: `Dispatcher` (with full hooks support) and `DispatcherWithoutHooks` (which only provided `readContext`).

In `packages/react-reconciler/src/ReactFiberDispatcher.js`, the export `export const DispatcherWithoutHooks = { readContext };` is removed entirely. The corresponding import in `packages/react-reconciler/src/ReactFiberScheduler.js` is updated from `import {Dispatcher, DispatcherWithoutHooks} from './ReactFiberDispatcher';` to `import {Dispatcher} from './ReactFiberDispatcher';`. The conditional assignment `if (enableHooks) { ReactCurrentDispatcher.current = Dispatcher; } else { ReactCurrentDispatcher.current = DispatcherWithoutHooks; }` is simplified to `ReactCurrentDispatcher.current = Dispatcher;`.

In `packages/react-dom/src/server/ReactPartialRendererHooks.js`, the export `export const DispatcherWithoutHooks = { readContext };` is removed. In `packages/react-dom/src/server/ReactPartialRenderer.js`, the import of `DispatcherWithoutHooks` is removed, and the conditional dispatcher assignment is simplified from `if (enableHooks) { ReactCurrentDispatcher.current = Dispatcher; } else { ReactCurrentDispatcher.current = DispatcherWithoutHooks; }` to `ReactCurrentDispatcher.current = Dispatcher;`.

This consolidation means that hooks are always available through the dispatcher, and there is no longer a code path where components run with a restricted dispatcher that lacks hook implementations.

## Test File Cleanup

Four test files are renamed from `.internal.js` to `.js`, promoting them from internal-only tests to standard tests: `packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.js` (was `.internal.js`), `packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.js` (was `.internal.js`), `packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.js` (was `.internal.js`), and `packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.js` (was `.internal.js`).

These renamed files also have the `ReactFeatureFlags.enableHooks = true` lines removed from their `beforeEach` blocks, along with TODO comments that read `// TODO: Switch this test to non-internal once the flag is on by default.`

Several additional test files that remain as `.internal.js` also have `ReactFeatureFlags.enableHooks = true` removed: `packages/react-dom/src/__tests__/ReactDOMServerIntegrationHooks-test.internal.js`, `packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js`, `packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js`, `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.internal.js`, `packages/react-reconciler/src/__tests__/ReactNewContext-test.internal.js`, `packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js`, `packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js`, and `packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.internal.js`.

## Public API Impact

In `packages/react/src/React.js`, the hook functions are moved from a conditional block into the main React object literal. Previously, hooks were added to the React object inside an `if (enableHooks) { ... }` block that was placed after the object definition. Now, the following hooks are included directly in the object definition: `useCallback`, `useContext`, `useEffect`, `useImperativeHandle`, `useDebugValue`, `useLayoutEffect`, `useMemo`, `useReducer`, `useRef`, and `useState`.

The import of `enableHooks` from `'shared/ReactFeatureFlags'` is also removed from this file. This means that hooks are now part of the stable public API of React and are always available to consumers, which is the intended behavior for the 16.8 release.

## Risk Assessment

The primary risk of this change is that any code path that previously relied on hooks being disabled would now execute with hooks enabled. However, since the `enableHooks` flag was already `true` in the `www` and `native-fb` forks (the production builds for Facebook), the only environments where hooks were previously disabled were the default open-source build, the test renderer, and the persistent renderer. In practice, these environments were already testing with hooks enabled via test overrides.

The `DispatcherWithoutHooks` fallback previously provided only `readContext`, meaning that if hooks were somehow invoked when disabled, they would fail. Removing this fallback and always using the full `Dispatcher` is safe because hooks are now unconditionally enabled.

The shallow renderer (`ReactShallowRenderer.js`) previously had an `enableHooks` guard around dispatcher initialization and the hook-based rendering path. Removing this guard means the shallow renderer will always support hooks, which aligns with the public API change. The constructor now always initializes `_dispatcher`, `_workInProgressHook`, and related state.

Server-side rendering in `ReactPartialRenderer.js` similarly simplifies to always use the full `Dispatcher`, ensuring hooks are supported during SSR. This is consistent with the reconciler changes.

Overall, the PR achieves a clean removal of the feature flag with no functional regression risk, as the flag was already enabled in all production environments.

## Conclusion

PR #14679 achieves a clean and complete removal of the `enableHooks` feature flag. The three atomic commits systematically enable hooks in production code, clean up test overrides, and remove the flag definition. The net reduction of 75 lines (32 additions, 107 deletions) reflects the elimination of conditional logic and redundant dispatcher implementations. The changes are well-scoped and the PR is ready for the upcoming release.
