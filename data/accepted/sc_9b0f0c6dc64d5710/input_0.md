# PR #14679 diff and description from the React repository


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

## Diff (first 3000 chars)
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
rename from packages/react-dom/src/__