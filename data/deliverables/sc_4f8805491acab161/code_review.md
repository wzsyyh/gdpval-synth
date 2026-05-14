# Code Review: PR #75624 - Add Node.js Runtime Support for Middleware

# PR #75624 Code Review: Add Node.js Runtime Support for Middleware

This document presents a comprehensive code review of PR #75624, which introduces Node.js runtime support for middleware in the Next.js build system. The review covers architectural changes, configuration flow, edge cases, and recommendations for the platform team.

## Summary

PR #75624, titled 'Add nodejs runtime support for middleware', was merged on February 4, 2025. The change removes the constraint that middleware must use only edge runtime APIs, allowing developers to set `runtime: 'nodejs'` in their middleware configuration. This addresses long-standing community requests referenced in discussions #71727 and #46722.

The PR modifies 18 files with 608 additions and 70 deletions. Key files include `packages/next/src/build/analysis/get-page-static-info.ts` for runtime resolution logic and `packages/next/src/build/entries.ts` for build entry point selection and validation. The middleware function signature `(req: NextRequest, event: NextFetchEvent) => Response` remains unchanged.

## Architecture Analysis

The core architectural change occurs in two files. In `get-page-static-info.ts`, the `getPagesPageStaticInfo` function was refactored to simplify runtime resolution. Previously, the `resolvedRuntime` variable was only set when the config specified edge runtime or when `getServerSideProps`/`getStaticProps` were present. The new logic unconditionally resolves `config.runtime ?? config.config?.runtime`, making runtime resolution more straightforward and removing conditional branching.

In `entries.ts`, the `runDependingOnPageType` function now checks if a middleware file uses Node.js runtime. When `params.pageRuntime === 'nodejs'`, it calls `params.onServer()` instead of `params.onEdgeServer()`. This is the critical branching point that routes Node.js middleware to the server compilation pipeline rather than the edge pipeline.

The `createEntrypoints` function adds validation logic: if a middleware file specifies `runtime: 'nodejs'` but `config.experimental.nodeMiddleware` is not enabled, a warning is logged via the new `Log.warn()` import, and the runtime is forced back to `'edge'`. This ensures backward compatibility while providing a clear migration path.

## Configuration Flow

The configuration flow begins when a developer sets `runtime: 'nodejs'` in their middleware configuration. During build analysis, `get-page-static-info.ts` extracts this setting as `config.runtime`. The simplified resolution logic passes this value through as `resolvedRuntime`.

In `entries.ts`, the `createEntrypoints` function checks two conditions: (1) whether the file is a middleware file via `isMiddlewareFile(page)`, and (2) whether `config.experimental.nodeMiddleware` is enabled. If the flag is missing and the runtime is set to `'nodejs'`, the system logs a warning message: 'nodejs runtime support for middleware requires experimental.nodeMiddleware be enabled in your next.config'. The runtime is then overridden to `'edge'` for safety.

When the experimental flag is enabled, the Node.js runtime setting is preserved. The `runDependingOnPageType` function then uses this value to determine whether to call `onServer()` (for Node.js) or `onEdgeServer()` (for edge), which routes the middleware through the appropriate webpack compilation pipeline. The final entry point configuration uses `getEdgeServerEntry` with the middleware's static info passed through.

## Edge Cases and Risks

1. **Backward Compatibility Risk**: Existing middleware that doesn't specify a runtime will continue to default to edge runtime. However, users who previously set `runtime: 'nodejs'` (perhaps incorrectly) may have experienced silent failures. The new warning mechanism surfaces this, but there's a risk of surprising users who didn't realize their configuration was being ignored.

2. **API Compatibility Differences**: The PR description states the middleware signature remains `(req: NextRequest, event: NextFetchEvent) => Response`, but Node.js middleware will have access to the full Node.js API surface. This could lead to developers using APIs that aren't available in edge runtime, creating portability issues if they later switch back to edge runtime.

3. **Feature Flag Requirement**: The requirement for `experimental.nodeMiddleware` creates a two-step migration path. Users must first enable the experimental flag, then set their middleware runtime. If users set the runtime without the flag, they'll get a warning but won't see an error, which could lead to confusion about why their Node.js middleware isn't working as expected.

4. **Bundle Size and Performance Implications**: Node.js middleware will be bundled differently than edge middleware. The `getEdgeServerEntry` function is used for both paths in the diff, but the actual webpack configuration may produce different bundle sizes. This could affect cold start times and memory usage in production deployments.

## Code Quality Observations

The refactoring in `get-page-static-info.ts` simplifies the runtime resolution logic by removing conditional checks for `isEdgeRuntime`, `getServerSideProps`, and `getStaticProps`. This makes the code more predictable and easier to maintain, as the runtime is now always resolved from the config when present.

The conditional branching in `runDependingOnPageType` is clear and follows the existing pattern for API routes. The use of early returns improves readability. However, the addition of a new `Log` import in `entries.ts` suggests this is the first warning in this module; consider whether this should be part of a more centralized logging strategy.

The validation logic in `createEntrypoints` correctly forces the runtime back to `'edge'` when the experimental flag is missing, but the warning message could be more actionable. It could include a link to the documentation for enabling the flag or explain the implications of the fallback.

## Recommendations

1. **Documentation**: Create migration documentation explaining the differences between edge and Node.js middleware, including performance characteristics and API availability. Reference discussions #71727 and #46722 for historical context.

2. **Testing Coverage**: Ensure integration tests cover both runtime paths (edge and Node.js) for middleware, including behavior with the experimental flag enabled and disabled. Test the warning mechanism to confirm it fires at the appropriate time during builds.

3. **Warning Enhancement**: Enhance the warning message in `entries.ts` to include a link to the configuration documentation or explain how to enable `experimental.nodeMiddleware`. This will reduce user confusion during the migration period.

4. **Performance Benchmarks**: Conduct performance benchmarks comparing edge and Node.js middleware for common use cases. Document any differences in cold start times, memory usage, and request latency to help users make informed decisions.

5. **Experimental Flag Timeline**: Define a clear timeline for graduating `experimental.nodeMiddleware` to a stable configuration option. Communicate this to users in release notes and documentation updates.
