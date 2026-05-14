# PR description explaining experimental


# Seed Material: vercel/next.js#65804: feat(next): experimental react compiler support
Source: github_issue_pr
Identifier: pr:vercel/next.js#65804

Repository: vercel/next.js
PR Number: #65804
PR Title: feat(next): experimental react compiler support
Merged At: 2024-05-16T09:22:28Z
Changed Files: 15
Additions: +538, Deletions: -89

## PR Description
### What

This PR exposes new experimental configuration for next.js, `experimental.reactCompiler`. Under the hood, this option configures to use new experimental react compiler (https://react.dev/learn/react-compiler#). `reactCompiler` value can be either boolean or an object contains partial set of compiler itself's configuration option.

For the webpack and turbopack both it is enabled by adding a babel plugin for the react compiler. If user have an existing .babelrc, plugin will be appended to the config. Otherwise, swc will still kicks in (for webpack) or turbopack for the general transform but only compiler babel plugin will run via babel. 


## Diff (first 3000 chars)
diff --git a/packages/next-swc/crates/next-core/src/next_config.rs b/packages/next-swc/crates/next-core/src/next_config.rs
index 93cf4bda13ae..490bbcdae34b 100644
--- a/packages/next-swc/crates/next-core/src/next_config.rs
+++ b/packages/next-swc/crates/next-core/src/next_config.rs
@@ -419,7 +419,7 @@ pub struct ExperimentalTurboConfig {
     pub use_swc_css: Option<bool>,
 }
 
-#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs)]
+#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, TraceRawVcs)]
 #[serde(rename_all = "camelCase")]
 pub struct RuleConfigItemOptions {
     pub loaders: Vec<LoaderItem>,
@@ -427,14 +427,14 @@ pub struct RuleConfigItemOptions {
     pub rename_as: Option<String>,
 }
 
-#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs)]
+#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, TraceRawVcs)]
 #[serde(rename_all = "camelCase", untagged)]
 pub enum RuleConfigItemOrShortcut {
     Loaders(Vec<LoaderItem>),
     Advanced(RuleConfigItem),
 }
 
-#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs)]
+#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, TraceRawVcs)]
 #[serde(rename_all = "camelCase", untagged)]
 pub enum RuleConfigItem {
     Options(RuleConfigItemOptions),
@@ -442,7 +442,7 @@ pub enum RuleConfigItem {
     Boolean(bool),
 }
 
-#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs)]
+#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, TraceRawVcs)]
 #[serde(untagged)]
 pub enum LoaderItem {
     LoaderName(String),
@@ -456,6 +456,36 @@ pub enum MdxRsOptions {
     Option(MdxTransformOptions),
 }
 
+#[turbo_tasks::value(shared)]
+#[derive(Clone, Debug)]
+#[serde(rename_all = "camelCase")]
+pub enum ReactCompilerMode {
+    Infer,
+    Annotation,
+    All,
+}
+
+/// Subset of react compiler options
+#[turbo_tasks::value(shared)]
+#[derive(Clone, Debug)]
+#[serde(rename_all = "camelCase")]
+pub struct ReactCompilerOptions {
+    #[serde(skip_serializing_if = "Option::is_none")]
+    pub compilation_mode: Option<ReactCompilerMode>,
+    #[serde(skip_serializing_if = "Option::is_none")]
+    pub panic_threshold: Option<String>,
+}
+
+#[derive(Clone, Debug, PartialEq, Serialize, Deserialize, TraceRawVcs)]
+#[serde(untagged)]
+pub enum ReactCompilerOptionsOrBoolean {
+    Boolean(bool),
+    Option(ReactCompilerOptions),
+}
+
+#[turbo_tasks::value(transparent)]
+pub struct OptionalReactCompilerOptions(Option<Vc<ReactCompilerOptions>>);
+
 #[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize, TraceRawVcs)]
 #[serde(rename_all = "camelCase")]
 pub struct ExperimentalConfig {
@@ -489,6 +519,7 @@ pub struct ExperimentalConfig {
     pub web_vitals_attribution: Option<Vec<String>>,
     pub server_actions: Option<ServerActionsOrLegacyBool>,
     pub sri: Option<SubResourceIntegrity>,
+    react_compiler: Option<ReactCompilerOptionsOrBoolean>,
 
     // ---
     // UNSUPPORTED
@@ -961,6 +992,29 @@ impl