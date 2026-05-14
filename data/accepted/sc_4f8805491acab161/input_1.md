# PR description with feature explanation and discussion references


# Seed Material: vercel/next.js#75624: Add nodejs runtime support for middleware
Source: github_issue_pr
Identifier: pr:vercel/next.js#75624

Repository: vercel/next.js
PR Number: #75624
PR Title: Add nodejs runtime support for middleware
Merged At: 2025-02-04T18:51:57Z
Changed Files: 18
Additions: +608, Deletions: -70

## PR Description
This allows setting `runtime: 'nodejs'` in middleware, which removes the constraint of only using edge runtime APIs for middleware. This doesn't change the signature of middleware and it still receives `(req: NextRequest, event: NextFetchEvent) => Response`. 

x-ref: https://github.com/vercel/next.js/discussions/71727
x-ref: https://github.com/vercel/next.js/discussions/46722

## Diff (first 3000 chars)
diff --git a/packages/next/src/build/analysis/get-page-static-info.ts b/packages/next/src/build/analysis/get-page-static-info.ts
index 084da67283a1..8b269ceecf24 100644
--- a/packages/next/src/build/analysis/get-page-static-info.ts
+++ b/packages/next/src/build/analysis/get-page-static-info.ts
@@ -614,12 +614,7 @@ export async function getPagesPageStaticInfo({
   const config = parsePagesSegmentConfig(exportedConfig, route)
   const isAnAPIRoute = isAPIRoute(route)
 
-  const resolvedRuntime =
-    isEdgeRuntime(config.runtime ?? config.config?.runtime) ||
-    getServerSideProps ||
-    getStaticProps
-      ? config.runtime ?? config.config?.runtime
-      : undefined
+  const resolvedRuntime = config.runtime ?? config.config?.runtime
 
   if (resolvedRuntime === SERVER_RUNTIME.experimentalEdge) {
     warnAboutExperimentalEdge(isAnAPIRoute ? page! : null)
diff --git a/packages/next/src/build/entries.ts b/packages/next/src/build/entries.ts
index 00dd62b4134c..7cd1348305cf 100644
--- a/packages/next/src/build/entries.ts
+++ b/packages/next/src/build/entries.ts
@@ -9,6 +9,7 @@ import type {
   MiddlewareMatcher,
   PageStaticInfo,
 } from './analysis/get-page-static-info'
+import * as Log from './output/log'
 import type { LoadedEnvFiles } from '@next/env'
 import type { AppLoaderOptions } from './webpack/loaders/next-app-loader'
 
@@ -517,9 +518,15 @@ export function runDependingOnPageType<T>(params: {
   }
 
   if (isMiddlewareFile(params.page)) {
-    params.onEdgeServer()
-    return
+    if (params.pageRuntime === 'nodejs') {
+      params.onServer()
+      return
+    } else {
+      params.onEdgeServer()
+      return
+    }
   }
+
   if (isAPIRoute(params.page)) {
     if (isEdgeRuntime(params.pageRuntime)) {
       params.onEdgeServer()
@@ -650,6 +657,20 @@ export async function createEntrypoints(
 
       const isInstrumentation =
         isInstrumentationHookFile(page) && pagesType === PAGE_TYPES.ROOT
+
+      let pageRuntime = staticInfo?.runtime
+
+      if (
+        isMiddlewareFile(page) &&
+        !config.experimental.nodeMiddleware &&
+        pageRuntime === 'nodejs'
+      ) {
+        Log.warn(
+          'nodejs runtime support for middleware requires experimental.nodeMiddleware be enabled in your next.config'
+        )
+        pageRuntime = 'edge'
+      }
+
       runDependingOnPageType({
         page,
         pageRuntime: staticInfo.runtime,
@@ -692,6 +713,20 @@ export async function createEntrypoints(
                 isEdgeServer: false,
                 isDev: false,
               })
+          } else if (isMiddlewareFile(page)) {
+            server[serverBundlePath] = getEdgeServerEntry({
+              ...params,
+              rootDir,
+              absolutePagePath: absolutePagePath,
+              bundlePath: clientBundlePath,
+              isDev: false,
+              isServerComponent,
+              page,
+              middleware: staticInfo?.middleware,
+              pagesType,
+              prefe