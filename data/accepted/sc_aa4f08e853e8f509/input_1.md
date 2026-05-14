# Issue nodejs/typescript#17 (motivation for unflagging)


# Seed Material: nodejs/node#56350: module: unflag --experimental-strip-types
Source: github_issue_pr
Identifier: pr:nodejs/node#56350

Repository: nodejs/node
PR Number: #56350
PR Title: module: unflag --experimental-strip-types
Merged At: 2024-12-26T18:46:06Z
Changed Files: 22
Additions: +64, Deletions: -114

## PR Description
It's time to enable it by default to catch some more bugs, currently there are no open issues.
I think it's a semver minor change.

Fixes: https://github.com/nodejs/typescript/issues/17

@nodejs/tsc for visibility

Notable change section:

This change enables the flag `--experimental-strip-types` by default.
Node.js will be able to execute TypeScript files without additional configuration. Note that there are some limitations in the supported syntax documented at https://nodejs.org/api/typescript.html#type-stripping
This feature is experimental and is subject to change.

## Diff (first 3000 chars)
diff --git a/benchmark/ts/strip-typescript.js b/benchmark/ts/strip-typescript.js
index 7a7155c568b613..29c81f5a750bae 100644
--- a/benchmark/ts/strip-typescript.js
+++ b/benchmark/ts/strip-typescript.js
@@ -12,7 +12,7 @@ const bench = common.createBenchmark(main, {
   filepath: [ts, js],
   n: [1e4],
 }, {
-  flags: ['--experimental-strip-types', '--disable-warning=ExperimentalWarning'],
+  flags: ['--disable-warning=ExperimentalWarning'],
 });
 
 async function main({ n, filepath }) {
diff --git a/doc/api/cli.md b/doc/api/cli.md
index 3e61b248b94fd9..87eda0deb66b46 100644
--- a/doc/api/cli.md
+++ b/doc/api/cli.md
@@ -780,7 +780,7 @@ Any query parameter or hash in the URL will be accessible via [`import.meta.url`
 
 ```bash
 node --entry-url 'file:///path/to/file.js?queryparams=work#and-hashes-too'
-node --entry-url --experimental-strip-types 'file.ts?query#hash'
+node --entry-url 'file.ts?query#hash'
 node --entry-url 'data:text/javascript,console.log("Hello")'
 ```
 
@@ -880,8 +880,8 @@ On Windows, using `cmd.exe` a single quote will not work correctly because it
 only recognizes double `"` for quoting. In Powershell or Git bash, both `'`
 and `"` are usable.
 
-It is possible to run code containing inline types by passing
-[`--experimental-strip-types`][].
+It is possible to run code containing inline types unless the
+[`--no-experimental-strip-types`][] flag is provided.
 
 ### `--experimental-addon-modules`
 
@@ -1008,17 +1008,6 @@ added:
 
 Use this flag to enable [ShadowRealm][] support.
 
-### `--experimental-strip-types`
-
-<!-- YAML
-added: v22.6.0
--->
-
-> Stability: 1.1 - Active development
-
-Enable experimental type-stripping for TypeScript files.
-For more information, see the [TypeScript type-stripping][] documentation.
-
 ### `--experimental-test-coverage`
 
 <!-- YAML
@@ -1059,7 +1048,7 @@ added: v22.7.0
 > Stability: 1.1 - Active development
 
 Enables the transformation of TypeScript-only syntax into JavaScript code.
-Implies `--experimental-strip-types` and `--enable-source-maps`.
+Implies `--enable-source-maps`.
 
 ### `--experimental-vm-modules`
 
@@ -1370,10 +1359,10 @@ added: v12.0.0
 
 This configures Node.js to interpret `--eval` or `STDIN` input as CommonJS or
 as an ES module. Valid values are `"commonjs"`, `"module"`, `"module-typescript"` and `"commonjs-typescript"`.
-The `"-typescript"` values are available only in combination with the flag `--experimental-strip-types`.
+The `"-typescript"` values are not available with the flag `--no-experimental-strip-types`.
 The default is `"commonjs"`.
 
-If `--experimental-strip-types` is enabled and `--input-type` is not provided,
+If `--input-type` is not provided,
 Node.js will try to detect the syntax with the following steps:
 
 1. Run the input as CommonJS.
@@ -1663,6 +1652,21 @@ changes:
 
 Disable the experimental [`node:sqlite`][] module.
 
+### `--no-experimental-strip-types`
+
+<!-- YAML
+added: v22.6.0
+changes:
+  - version: REPLACEME
+    pr-url: https://github