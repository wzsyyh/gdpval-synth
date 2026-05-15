# PR description with title 'Enable hooks!' and three atomic commit descriptions


# Seed Material: facebook/react#14679: Enable hooks!
Source: github_issue_pr
Identifier: pr:facebook/react#14679

Repository: facebook/react
PR Number: #14679
PR Title: Enable hooks!
Merged At: 2019-01-23T21:28:10Z
Changed Files: 27
Additions: +32, Deletions: -107

## PR Description
Turn hooks on everywhere in preparation for the upcoming release.

Commits are atomic to simplify the review:
* 7c54bff: Turn hooks on everywhere
* 021844a: Remove test overrides (and promote internal tests that only override the hooks flag)
* d1ffc25: Remove hooks flag entirely

## Diff
diff --git a/packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.internal.js b/packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.js
similarity index 97%
rename from packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.internal.js
rename to packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.js
index d84bd82fb278..b340779a74d1 100644
--- a/packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.internal.js
+++ b/packages/react-debug-tools/src/__tests__/ReactHooksInspection-test.js
@@ -16,9 +16,6 @@ let ReactDebugTools;
 describe('ReactHooksInspection', () => {
   beforeEach(() => {
     jest.resetModules();
-    let ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    // TODO: Switch this test to non-internal once the flag is on by default.
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     ReactDebugTools = require('react-debug-tools');
   });
diff --git a/packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.internal.js b/packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.js
similarity index 98%
rename from packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.internal.js
rename to packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.js
index 703db2af538d..33d7cec90ee6 100644
--- a/packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.internal.js
+++ b/packages/react-debug-tools/src/__tests__/ReactHooksInspectionIntegration-test.js
@@ -17,9 +17,6 @@ let ReactDebugTools;
 describe('ReactHooksInspectionIntergration', () => {
   beforeEach(() => {
     jest.resetModules();
-    let ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    // TODO: Switch this test to non-internal once the flag is on by default.
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     ReactTestRenderer = require('react-test-renderer');
     ReactDebugTools = require('react-debug-tools');
diff --git a/packages/react-dom/src/__tests__/ReactDOMServerIntegrationHooks-test.internal.js b/packages/react-dom/src/__tests__/ReactDOMServerIntegrationHooks-test.internal.js
index 97de8867b2bd..d69256c15ad5 100644
--- a/packages/react-dom/src/__tests__/ReactDOMServerIntegrationHooks-test.internal.js
+++ b/packages/react-dom/src/__tests__/ReactDOMServerIntegrationHooks-test.internal.js
@@ -38,7 +38,6 @@ function initModules() {
 
   ReactFeatureFlags = require('shared/ReactFeatureFlags');
   ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
-  ReactFeatureFlags.enableHooks = true;
   React = require('react');
   ReactDOM = require('react-dom');
   ReactDOMServer = require('react-dom/server');
diff --git a/packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.internal.js b/packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.js
similarity index 97%
rename from packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.internal.js
rename to packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.js
index 98069e2d9f40..bc2ae71673d2 100644
--- a/packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.internal.js
+++ b/packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.js
@@ -9,7 +9,6 @@
 
 'use strict';
 
-let ReactFeatureFlags;
 let React;
 let ReactDOM;
 let Suspense;
@@ -21,8 +20,6 @@ describe('ReactDOMSuspensePlaceholder', () => {
 
   beforeEach(() => {
     jest.resetModules();
-    ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     ReactDOM = require('react-dom');
     ReactCache = require('react-cache');
diff --git a/packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js b/packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
index 0ee2d601bd6c..d6ef0a1e4d4f 100644
--- a/packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
+++ b/packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
@@ -41,7 +41,6 @@ describe('ReactErrorBoundaries', () => {
     jest.resetModules();
     PropTypes = require('prop-types');
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    ReactFeatureFlags.enableHooks = true;
     ReactFeatureFlags.replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
     ReactDOM = require('react-dom');
     React = require('react');
diff --git a/packages/react-dom/src/server/ReactPartialRenderer.js b/packages/react-dom/src/server/ReactPartialRenderer.js
index 597abb4a6699..82d56f3a49e0 100644
--- a/packages/react-dom/src/server/ReactPartialRenderer.js
+++ b/packages/react-dom/src/server/ReactPartialRenderer.js
@@ -21,7 +21,6 @@ import describeComponentFrame from 'shared/describeComponentFrame';
 import ReactSharedInternals from 'shared/ReactSharedInternals';
 import {
   warnAboutDeprecatedLifecycles,
-  enableHooks,
   enableSuspenseServerRenderer,
 } from 'shared/ReactFeatureFlags';
 
@@ -55,7 +54,6 @@ import {
   prepareToUseHooks,
   finishHooks,
   Dispatcher,
-  DispatcherWithoutHooks,
   currentThreadID,
   setCurrentThreadID,
 } from './ReactPartialRendererHooks';
@@ -786,11 +784,7 @@ class ReactDOMServerRenderer {
     const prevThreadID = currentThreadID;
     setCurrentThreadID(this.threadID);
     const prevDispatcher = ReactCurrentDispatcher.current;
-    if (enableHooks) {
-      ReactCurrentDispatcher.current = Dispatcher;
-    } else {
-      ReactCurrentDispatcher.current = DispatcherWithoutHooks;
-    }
+    ReactCurrentDispatcher.current = Dispatcher;
     try {
       // Markup generated within <Suspense> ends up buffered until we know
       // nothing in that boundary suspended
diff --git a/packages/react-dom/src/server/ReactPartialRendererHooks.js b/packages/react-dom/src/server/ReactPartialRendererHooks.js
index 025b51a8c026..d8496b8a2629 100644
--- a/packages/react-dom/src/server/ReactPartialRendererHooks.js
+++ b/packages/react-dom/src/server/ReactPartialRendererHooks.js
@@ -423,6 +423,3 @@ export const Dispatcher: DispatcherType = {
   // Debugging effect
   useDebugValue: noop,
 };
-export const DispatcherWithoutHooks = {
-  readContext,
-};
diff --git a/packages/react-reconciler/src/ReactFiberCommitWork.js b/packages/react-reconciler/src/ReactFiberCommitWork.js
index 85cd0a5791ba..76e136dd7dbf 100644
--- a/packages/react-reconciler/src/ReactFiberCommitWork.js
+++ b/packages/react-reconciler/src/ReactFiberCommitWork.js
@@ -24,7 +24,6 @@ import type {Thenable} from './ReactFiberScheduler';
 
 import {unstable_wrap as Schedule_tracing_wrap} from 'scheduler/tracing';
 import {
-  enableHooks,
   enableSchedulerTracing,
   enableProfilerTimer,
 } from 'shared/ReactFeatureFlags';
@@ -312,9 +311,6 @@ function commitHookEffectList(
   mountTag: number,
   finishedWork: Fiber,
 ) {
-  if (!enableHooks) {
-    return;
-  }
   const updateQueue: FunctionComponentUpdateQueue | null = (finishedWork.updateQueue: any);
   let lastEffect = updateQueue !== null ? updateQueue.lastEffect : null;
   if (lastEffect !== null) {
diff --git a/packages/react-reconciler/src/ReactFiberDispatcher.js b/packages/react-reconciler/src/ReactFiberDispatcher.js
index ed2ed3b2f315..f1572072b3f6 100644
--- a/packages/react-reconciler/src/ReactFiberDispatcher.js
+++ b/packages/react-reconciler/src/ReactFiberDispatcher.js
@@ -34,6 +34,3 @@ export const Dispatcher = {
   useRef,
   useState,
 };
-export const DispatcherWithoutHooks = {
-  readContext,
-};
diff --git a/packages/react-reconciler/src/ReactFiberHooks.js b/packages/react-reconciler/src/ReactFiberHooks.js
index d2396cfdbec1..00cd8aa94039 100644
--- a/packages/react-reconciler/src/ReactFiberHooks.js
+++ b/packages/react-reconciler/src/ReactFiberHooks.js
@@ -13,7 +13,6 @@ import type {ExpirationTime} from './ReactFiberExpirationTime';
 import type {HookEffectTag} from './ReactHookEffectTags';
 
 import {NoWork} from './ReactFiberExpirationTime';
-import {enableHooks} from 'shared/ReactFeatureFlags';
 import {
   readContext,
   stashContextDependencies,
@@ -296,9 +295,6 @@ export function renderWithHooks(
   refOrContext: any,
   nextRenderExpirationTime: ExpirationTime,
 ): any {
-  if (!enableHooks) {
-    return Component(props, refOrContext);
-  }
   renderExpirationTime = nextRenderExpirationTime;
   currentlyRenderingFiber = workInProgress;
   firstCurrentHook = current !== null ? current.memoizedState : null;
@@ -397,9 +393,6 @@ export function bailoutHooks(
 }
 
 export function resetHooks(): void {
-  if (!enableHooks) {
-    return;
-  }
   if (__DEV__) {
     flushHookMismatchWarnings();
   }
diff --git a/packages/react-reconciler/src/ReactFiberScheduler.js b/packages/react-reconciler/src/ReactFiberScheduler.js
index bcc41fe3670a..1563f54b69a8 100644
--- a/packages/react-reconciler/src/ReactFiberScheduler.js
+++ b/packages/react-reconciler/src/ReactFiberScheduler.js
@@ -56,7 +56,6 @@ import {
   SimpleMemoComponent,
 } from 'shared/ReactWorkTags';
 import {
-  enableHooks,
   enableSchedulerTracing,
   enableProfilerTimer,
   enableUserTimingAPI,
@@ -165,7 +164,7 @@ import {
   commitDetachRef,
   commitPassiveHookEffects,
 } from './ReactFiberCommitWork';
-import {Dispatcher, DispatcherWithoutHooks} from './ReactFiberDispatcher';
+import {Dispatcher} from './ReactFiberDispatcher';
 
 export type Thenable = {
   then(resolve: () => mixed, reject?: () => mixed): mixed,
@@ -510,7 +509,7 @@ function commitAllLifeCycles(
       commitAttachRef(nextEffect);
     }
 
-    if (enableHooks && effectTag & Passive) {
+    if (effectTag & Passive) {
       rootWithPendingPassiveEffects = finishedRoot;
     }
 
@@ -784,11 +783,7 @@ function commitRoot(root: FiberRoot, finishedWork: Fiber): void {
     }
   }
 
-  if (
-    enableHooks &&
-    firstEffect !== null &&
-    rootWithPendingPassiveEffects !== null
-  ) {
+  if (firstEffect !== null && rootWithPendingPassiveEffects !== null) {
     // This commit included a passive effect. These do not need to fire until
     // after the next paint. Schedule an callback to fire them in an async
     // event. To ensure serial execution, the callback will be flushed early if
@@ -1221,11 +1216,7 @@ function renderRoot(root: FiberRoot, isYieldy: boolean): void {
   flushPassiveEffects();
 
   isWorking = true;
-  if (enableHooks) {
-    ReactCurrentDispatcher.current = Dispatcher;
-  } else {
-    ReactCurrentDispatcher.current = DispatcherWithoutHooks;
-  }
+  ReactCurrentDispatcher.current = Dispatcher;
 
   const expirationTime = root.nextExpirationTimeToWorkOn;
 
diff --git a/packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js b/packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js
index e7c43ce27423..76783087a45a 100644
--- a/packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js
@@ -25,7 +25,6 @@ describe('ReactHooks', () => {
 
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     ReactTestRenderer = require('react-test-renderer');
     ReactDOMServer = require('react-dom/server');
diff --git a/packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.internal.js b/packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.internal.js
index 74d69fac78de..fe67d1ab6234 100644
--- a/packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.internal.js
@@ -59,7 +59,6 @@ describe('ReactHooksWithNoopRenderer', () => {
 
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
-    ReactFeatureFlags.enableHooks = true;
     ReactFeatureFlags.enableSchedulerTracing = true;
     React = require('react');
     ReactNoop = require('react-noop-renderer');
diff --git a/packages/react-reconciler/src/__tests__/ReactNewContext-test.internal.js b/packages/react-reconciler/src/__tests__/ReactNewContext-test.internal.js
index 3b9873923a17..05c59d5f339b 100644
--- a/packages/react-reconciler/src/__tests__/ReactNewContext-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactNewContext-test.internal.js
@@ -21,7 +21,6 @@ describe('ReactNewContext', () => {
     jest.resetModules();
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     useContext = React.useContext;
     ReactNoop = require('react-noop-renderer');
diff --git a/packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js b/packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js
index b6ca5beba117..73a55370a187 100644
--- a/packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js
@@ -17,7 +17,6 @@ describe('ReactSuspense', () => {
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
     ReactFeatureFlags.replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     ReactTestRenderer = require('react-test-renderer');
     // JestReact = require('jest-react');
diff --git a/packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js b/packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js
index b3c46b7a2a80..ed3d9322ba1c 100644
--- a/packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js
@@ -23,7 +23,6 @@ describe('ReactSuspenseFuzz', () => {
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
     ReactFeatureFlags.replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
-    ReactFeatureFlags.enableHooks = true;
     React = require('react');
     Suspense = React.Suspense;
     ReactTestRenderer = require('react-test-renderer');
diff --git a/packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.internal.js b/packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.internal.js
index 9580c425a47b..daf898c6dfd2 100644
--- a/packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.internal.js
+++ b/packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.internal.js
@@ -17,7 +17,6 @@ describe('ReactSuspenseWithNoopRenderer', () => {
   beforeEach(() => {
     jest.resetModules();
     ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    ReactFeatureFlags.enableHooks = true;
     ReactFeatureFlags.debugRenderPhaseSideEffectsForStrictMode = false;
     ReactFeatureFlags.replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
     React = require('react');
diff --git a/packages/react-test-renderer/src/ReactShallowRenderer.js b/packages/react-test-renderer/src/ReactShallowRenderer.js
index 778e5943ec9c..815220efb7c1 100644
--- a/packages/react-test-renderer/src/ReactShallowRenderer.js
+++ b/packages/react-test-renderer/src/ReactShallowRenderer.js
@@ -15,7 +15,6 @@ import shallowEqual from 'shared/shallowEqual';
 import invariant from 'shared/invariant';
 import checkPropTypes from 'prop-types/checkPropTypes';
 import ReactSharedInternals from 'shared/ReactSharedInternals';
-import {enableHooks} from 'shared/ReactFeatureFlags';
 import warning from 'shared/warning';
 import is from 'shared/objectIs';
 
@@ -187,17 +186,15 @@ class ReactShallowRenderer {
     this._rendering = false;
     this._forcedUpdate = false;
     this._updater = new Updater(this);
-    if (enableHooks) {
-      this._dispatcher = this._createDispatcher();
-      this._workInProgressHook = null;
-      this._firstWorkInProgressHook = null;
-      this._isReRender = false;
-      this._didScheduleRenderPhaseUpdate = false;
-      this._renderPhaseUpdates = null;
-      this._currentlyRenderingComponent = null;
-      this._numberOfReRenders = 0;
-      this._previousComponentIdentity = null;
-    }
+    this._dispatcher = this._createDispatcher();
+    this._workInProgressHook = null;
+    this._firstWorkInProgressHook = null;
+    this._isReRender = false;
+    this._didScheduleRenderPhaseUpdate = false;
+    this._renderPhaseUpdates = null;
+    this._currentlyRenderingComponent = null;
+    this._numberOfReRenders = 0;
+    this._previousComponentIdentity = null;
   }
 
   _context: null | Object;
@@ -560,27 +557,19 @@ class ReactShallowRenderer {
 
         this._mountClassComponent(element, this._context);
       } else {
-        if (enableHooks) {
-          const prevDispatcher = ReactCurrentDispatcher.current;
-          ReactCurrentDispatcher.current = this._dispatcher;
-          this._prepareToUseHooks(element.type);
-          try {
-            this._rendered = element.type.call(
-              undefined,
-              element.props,
-              this._context,
-            );
-          } finally {
-            ReactCurrentDispatcher.current = prevDispatcher;
-          }
-          this._finishHooks(element, context);
-        } else {
+        const prevDispatcher = ReactCurrentDispatcher.current;
+        ReactCurrentDispatcher.current = this._dispatcher;
+        this._prepareToUseHooks(element.type);
+        try {
           this._rendered = element.type.call(
             undefined,
             element.props,
             this._context,
           );
+        } finally {
+          ReactCurrentDispatcher.current = prevDispatcher;
         }
+        this._finishHooks(element, context);
       }
     }
 
diff --git a/packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.internal.js b/packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.js
similarity index 97%
rename from packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.internal.js
rename to packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.js
index 2b1f3f56b823..60c79a12d702 100644
--- a/packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.internal.js
+++ b/packages/react-test-renderer/src/__tests__/ReactShallowRendererHooks-test.js
@@ -16,9 +16,6 @@ let React;
 describe('ReactShallowRenderer with hooks', () => {
   beforeEach(() => {
     jest.resetModules();
-    let ReactFeatureFlags = require('shared/ReactFeatureFlags');
-    // TODO: Switch this test to non-internal once the flag is on by default.
-    ReactFeatureFlags.enableHooks = true;
     createRenderer = require('react-test-renderer/shallow').createRenderer;
     React = require('react');
   });
diff --git a/packages/react/src/React.js b/packages/react/src/React.js
index 4b868feca9c8..78f72791eb02 100644
--- a/packages/react/src/React.js
+++ b/packages/react/src/React.js
@@ -13,7 +13,6 @@ import {
   REACT_STRICT_MODE_TYPE,
   REACT_SUSPENSE_TYPE,
 } from 'shared/ReactSymbols';
-import {enableHooks} from 'shared/ReactFeatureFlags';
 
 import {Component, PureComponent} from './ReactBaseClasses';
 import {createRef} from './ReactCreateRef';
@@ -66,6 +65,17 @@ const React = {
   lazy,
   memo,
 
+  useCallback,
+  useContext,
+  useEffect,
+  useImperativeHandle,
+  useDebugValue,
+  useLayoutEffect,
+  useMemo,
+  useReducer,
+  useRef,
+  useState,
+
   Fragment: REACT_FRAGMENT_TYPE,
   StrictMode: REACT_STRICT_MODE_TYPE,
   Suspense: REACT_SUSPENSE_TYPE,
@@ -95,17 +105,4 @@ if (enableStableConcurrentModeAPIs) {
   React.unstable_Profiler = undefined;
 }
 
-if (enableHooks) {
-  React.useCallback = useCallback;
-  React.useContext = useContext;
-  React.useEffect = useEffect;
-  React.useImperativeHandle = useImperativeHandle;
-  React.useDebugValue = useDebugValue;
-  React.useLayoutEffect = useLayoutEffect;
-  React.useMemo = useMemo;
-  React.useReducer = useReducer;
-  React.useRef = useRef;
-  React.useState = useState;
-}
-
 export default React;
diff --git a/packages/shared/ReactFeatureFlags.js b/packages/shared/ReactFeatureFlags.js
index 666205e7b304..af5241d1f28b 100644
--- a/packages/shared/ReactFeatureFlags.js
+++ b/packages/shared/ReactFeatureFlags.js
@@ -9,7 +9,6 @@
 
 export const enableUserTimingAPI = __DEV__;
 
-export const enableHooks = false;
 // Helps identify side effects in begin-phase lifecycle hooks and setState reducers:
 export const debugRenderPhaseSideEffects = false;
 
diff --git a/packages/shared/forks/ReactFeatureFlags.native-fb.js b/packages/shared/forks/ReactFeatureFlags.native-fb.js
index 943cef96e8a5..1a308519bad7 100644
--- a/packages/shared/forks/ReactFeatureFlags.native-fb.js
+++ b/packages/shared/forks/ReactFeatureFlags.native-fb.js
@@ -16,7 +16,6 @@ import typeof * as FeatureFlagsShimType from './ReactFeatureFlags.native-fb';
 export const {debugRenderPhaseSideEffects} = require('ReactFeatureFlags');
 
 // The rest of the flags are static for better dead code elimination.
-export const enableHooks = true;
 export const enableUserTimingAPI = __DEV__;
 export const enableProfilerTimer = __PROFILE__;
 export const enableSchedulerTracing = __PROFILE__;
diff --git a/packages/shared/forks/ReactFeatureFlags.native-oss.js b/packages/shared/forks/ReactFeatureFlags.native-oss.js
index 7e24ece36746..2e4918dc1e59 100644
--- a/packages/shared/forks/ReactFeatureFlags.native-oss.js
+++ b/packages/shared/forks/ReactFeatureFlags.native-oss.js
@@ -14,7 +14,6 @@ import typeof * as FeatureFlagsShimType from './ReactFeatureFlags.native-oss';
 
 export const debugRenderPhaseSideEffects = false;
 export const debugRenderPhaseSideEffectsForStrictMode = false;
-export const enableHooks = false;
 export const enableUserTimingAPI = __DEV__;
 export const replayFailedUnitOfWorkWithInvokeGuardedCallback = __DEV__;
 export const warnAboutDeprecatedLifecycles = false;
diff --git a/packages/shared/forks/ReactFeatureFlags.persistent.js b/packages/shared/forks/ReactFeatureFlags.persistent.js
index caa763c94c7e..34cce860a0d5 100644
--- a/packages/shared/forks/ReactFeatureFlags.persistent.js
+++ b/packages/shared/forks/ReactFeatureFlags.persistent.js
@@ -15,7 +15,6 @@ import typeof * as PersistentFeatureFlagsType from './ReactFeatureFlags.persiste
 export const debugRenderPhaseSideEffects = false;
 export const debugRenderPhaseSideEffectsForStrictMode = false;
 export const enableUserTimingAPI = __DEV__;
-export const enableHooks = false;
 export const warnAboutDeprecatedLifecycles = false;
 export const replayFailedUnitOfWorkWithInvokeGuardedCallback = __DEV__;
 export const enableProfilerTimer = __PROFILE__;
diff --git a/packages/shared/forks/ReactFeatureFlags.test-renderer.js b/packages/shared/forks/ReactFeatureFlags.test-renderer.js
index f55f419a6d49..d33865e96468 100644
--- a/packages/shared/forks/ReactFeatureFlags.test-renderer.js
+++ b/packages/shared/forks/ReactFeatureFlags.test-renderer.js
@@ -15,7 +15,6 @@ import typeof * as PersistentFeatureFlagsType from './ReactFeatureFlags.persiste
 export const debugRenderPhaseSideEffects = false;
 export const debugRenderPhaseSideEffectsForStrictMode = false;
 export const enableUserTimingAPI = __DEV__;
-export const enableHooks = false;
 export const warnAboutDeprecatedLifecycles = false;
 export const replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
 export const enableProfilerTimer = false;
diff --git a/packages/shared/forks/ReactFeatureFlags.test-renderer.www.js b/packages/shared/forks/ReactFeatureFlags.test-renderer.www.js
index 516f5738d5a3..09c63908f825 100644
--- a/packages/shared/forks/ReactFeatureFlags.test-renderer.www.js
+++ b/packages/shared/forks/ReactFeatureFlags.test-renderer.www.js
@@ -15,7 +15,6 @@ import typeof * as PersistentFeatureFlagsType from './ReactFeatureFlags.persiste
 export const debugRenderPhaseSideEffects = false;
 export const debugRenderPhaseSideEffectsForStrictMode = false;
 export const enableUserTimingAPI = __DEV__;
-export const enableHooks = true;
 export const warnAboutDeprecatedLifecycles = false;
 export const replayFailedUnitOfWorkWithInvokeGuardedCallback = false;
 export const enableProfilerTimer = false;
diff --git a/packages/shared/forks/ReactFeatureFlags.www.js b/packages/shared/forks/ReactFeatureFlags.www.js
index 40ea1ca5e0a9..56e563822b0f 100644
--- a/packages/shared/forks/ReactFeatureFlags.www.js
+++ b/packages/shared/forks/ReactFeatureFlags.www.js
@@ -21,9 +21,6 @@ export const {
   warnAboutShorthandPropertyCollision,
 } = require('ReactFeatureFlags');
 
-// The rest of the flags are static for better dead code elimination.
-export const enableHooks = true;
-
 // In www, we have experimental support for gathering data
 // from User Timing API calls in production. By default, we
 // only emit performance.mark/measure calls in __DEV__. But if
