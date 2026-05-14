# Design Document: Node.js Runtime Support for Middleware

# Design Document: Node.js Runtime Support for Middleware

## Overview

This design document details the implementation of Node.js runtime support for Next.js middleware, as introduced in PR #75624. The feature addresses long-standing developer requests to use full Node.js APIs within middleware functions, removing the previous constraint that limited middleware to only Edge Runtime APIs. The change enables setting `runtime: 'nodejs'` in middleware configuration.

The pull request was merged on 2025-02-04 and directly responds to the feature requests and discussions outlined in issues #71727 and #46722. By supporting the Node.js runtime, middleware gains access to the broader Node.js ecosystem, allowing for more complex operations that were previously impossible under the Edge Runtime limitations.

## Technical Implementation Details

The core implementation involves modifications to the middleware runtime resolution and entry point creation logic. In `packages/next/src/build/analysis/get-page-static-info.ts`, the logic for determining the `resolvedRuntime` was simplified. Previously, the runtime was only resolved if the page used Edge Runtime, `getServerSideProps`, or `getStaticProps`. The new logic unconditionally sets `resolvedRuntime` to `config.runtime ?? config.config?.runtime`, making the runtime configuration directly available for all pages, including middleware.

In `packages/next/src/build/entries.ts`, the `runDependingOnPageType` function was updated to handle the new middleware runtime option. Previously, middleware files were unconditionally handled by calling `params.onEdgeServer()`. The updated function now checks if `params.pageRuntime === 'nodejs'`. If true, it calls `params.onServer()` to route the middleware through the Node.js server compilation path instead of the edge server path.

A critical safeguard was added in the `createEntrypoints` function. If the middleware file is detected and `config.experimental.nodeMiddleware` is not enabled while `pageRuntime` is set to `'nodejs'`, the build system logs a warning: 'nodejs runtime support for middleware requires experimental.nodeMiddleware be enabled in your next.config'. In this case, the runtime is forcibly reset to `'edge'` to maintain backward compatibility and prevent silent failures.

## Developer Impact and Migration

For developers, this change introduces a new configuration option. Middleware can now explicitly specify `runtime: 'nodejs'` in its configuration. However, to activate this feature, developers must also enable the experimental flag `nodeMiddleware` in their `next.config.js` file. Without this flag, the build will revert to using the Edge Runtime and issue a warning.

Importantly, the public API and signature of the middleware function remain unchanged. Middleware functions still receive `(req: NextRequest, event: NextFetchEvent) => Response`. This ensures backward compatibility and allows existing edge-based middleware to continue functioning without modification, while new middleware can opt into the Node.js runtime as needed.

## Rationale and Tradeoffs

The primary rationale for this change is to provide developers with more flexibility and power in their middleware functions. The previous constraint to Edge Runtime APIs, while offering performance benefits for certain use cases, limited the functionality of middleware. This change was motivated by direct community feedback, as evidenced by the discussions in #71727 and #46722, which highlighted the need for Node.js compatibility.

By supporting the Node.js runtime, middleware can now leverage the full Node.js standard library and npm packages. This removes constraints related to API availability, allowing for more complex authentication flows, database interactions, or other operations that require Node.js-specific modules. The tradeoff is potentially different performance characteristics compared to the Edge Runtime, which is why the feature is initially gated behind an experimental flag.

## Testing and Rollout Considerations

Testing this feature requires verifying both the runtime selection logic and the guard conditions. Key test scenarios include: ensuring middleware with `runtime: 'nodejs'` is correctly bundled for the Node.js server when the experimental flag is enabled; confirming that a warning is logged and the runtime falls back to 'edge' when the flag is disabled; and validating that middleware without an explicit runtime setting continues to use the Edge Runtime.

The feature is rolled out as experimental via the `nodeMiddleware` flag in `next.config.js`. This allows the team to gather real-world usage data and feedback before making it generally available. The flag gating also serves as a clear signal to developers that the feature may have breaking changes in future releases, setting appropriate expectations during the experimental phase.
