# The attached PR shows changes across 15 files with +538 additions and -89 deletions, introducing a new experimental configuration option for the React Compiler in Next


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


## Diff
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
@@ -961,6 +992,29 @@ impl NextConfig {
         Ok(options.cell())
     }
 
+    #[turbo_tasks::function]
+    pub async fn react_compiler(self: Vc<Self>) -> Result<Vc<OptionalReactCompilerOptions>> {
+        let options = &self.await?.experimental.react_compiler;
+
+        let options = match options {
+            Some(ReactCompilerOptionsOrBoolean::Boolean(true)) => {
+                OptionalReactCompilerOptions(Some(
+                    ReactCompilerOptions {
+                        compilation_mode: None,
+                        panic_threshold: None,
+                    }
+                    .cell(),
+                ))
+            }
+            Some(ReactCompilerOptionsOrBoolean::Option(options)) => OptionalReactCompilerOptions(
+                Some(ReactCompilerOptions { ..options.clone() }.cell()),
+            ),
+            _ => OptionalReactCompilerOptions(None),
+        };
+
+        Ok(options.cell())
+    }
+
     #[turbo_tasks::function]
     pub async fn sass_config(self: Vc<Self>) -> Result<Vc<JsonValue>> {
         Ok(Vc::cell(
diff --git a/packages/next/package.json b/packages/next/package.json
index 41226a700c72..cc6d2cdd2b6c 100644
--- a/packages/next/package.json
+++ b/packages/next/package.json
@@ -106,9 +106,13 @@
     "@playwright/test": "^1.41.2",
     "react": "19.0.0-beta-4508873393-20240430",
     "react-dom": "19.0.0-beta-4508873393-20240430",
-    "sass": "^1.3.0"
+    "sass": "^1.3.0",
+    "babel-plugin-react-compiler": "*"
   },
   "peerDependenciesMeta": {
+    "babel-plugin-react-compiler": {
+      "optional": true
+    },
     "sass": {
       "optional": true
     },
diff --git a/packages/next/src/build/babel/loader/get-config.ts b/packages/next/src/build/babel/loader/get-config.ts
index 7f6421e2ff58..abed82f147d3 100644
--- a/packages/next/src/build/babel/loader/get-config.ts
+++ b/packages/next/src/build/babel/loader/get-config.ts
@@ -70,7 +70,11 @@ function getPlugins(
   const { isServer, isPageFile, isNextDist, hasModuleExports } =
     cacheCharacteristics
 
-  const { hasReactRefresh, development } = loaderOptions
+  const { development } = loaderOptions
+  const hasReactRefresh =
+    loaderOptions.transformMode !== 'standalone'
+      ? loaderOptions.hasReactRefresh
+      : false
 
   const applyCommonJsItem = hasModuleExports
     ? createConfigItem(require('../plugins/commonjs'), { type: 'plugin' })
@@ -260,14 +264,7 @@ function getFreshConfig(
   filename: string,
   inputSourceMap?: object | null
 ) {
-  let { isServer, pagesDir, development, hasJsxRuntime, configFile, srcDir } =
-    loaderOptions
-
-  let customConfig: any = configFile
-    ? getCustomBabelConfig(configFile)
-    : undefined
-
-  checkCustomBabelConfigDeprecation(customConfig)
+  let { isServer, pagesDir, srcDir, development } = loaderOptions
 
   let options = {
     babelrc: false,
@@ -275,29 +272,75 @@ function getFreshConfig(
     filename,
     inputSourceMap: inputSourceMap || undefined,
 
-    // Set the default sourcemap behavior based on Webpack's mapping flag,
-    // but allow users to override if they want.
-    sourceMaps:
-      loaderOptions.sourceMaps === undefined
-        ? this.sourceMap
-        : loaderOptions.sourceMaps,
-
     // Ensure that Webpack will get a full absolute path in the sourcemap
     // so that it can properly map the module back to its internal cached
     // modules.
     sourceFileName: filename,
+    sourceMaps: this.sourceMap,
+  } as any
+
+  const baseCaller = {
+    name: 'next-babel-turbo-loader',
+    supportsStaticESM: true,
+    supportsDynamicImport: true,
+
+    // Provide plugins with insight into webpack target.
+    // https://github.com/babel/babel-loader/issues/787
+    target: target,
+
+    // Webpack 5 supports TLA behind a flag. We enable it by default
+    // for Babel, and then webpack will throw an error if the experimental
+    // flag isn't enabled.
+    supportsTopLevelAwait: true,
+
+    isServer,
+    srcDir,
+    pagesDir,
+    isDev: development,
+
+    ...loaderOptions.caller,
+  }
+
+  if (loaderOptions.transformMode === 'standalone') {
+    options.plugins = [
+      '@babel/plugin-syntax-jsx',
+      ...(loaderOptions.plugins ?? []),
+    ]
+    options.presets = [
+      [
+        require('next/dist/compiled/babel/preset-typescript'),
+        { allowNamespaces: true },
+      ],
+    ]
+    options.caller = baseCaller
+  } else {
+    let { configFile, plugins, hasJsxRuntime } = loaderOptions
+    let customConfig: any = configFile
+      ? getCustomBabelConfig(configFile)
+      : undefined
+
+    checkCustomBabelConfigDeprecation(customConfig)
 
-    plugins: [
+    // Set the default sourcemap behavior based on Webpack's mapping flag,
+    // but allow users to override if they want.
+    options.sourceMaps =
+      loaderOptions.sourceMaps === undefined
+        ? this.sourceMap
+        : loaderOptions.sourceMaps
+
+    options.plugins = [
       ...getPlugins(loaderOptions, cacheCharacteristics),
+      ...(plugins || []),
       ...(customConfig?.plugins || []),
-    ],
+    ]
 
     // target can be provided in babelrc
-    target: isServer ? undefined : customConfig?.target,
+    options.target = isServer ? undefined : customConfig?.target
+
     // env can be provided in babelrc
-    env: customConfig?.env,
+    options.env = customConfig?.env
 
-    presets: (() => {
+    options.presets = (() => {
       // If presets is defined the user will have next/babel in their babelrc
       if (customConfig?.presets) {
         return customConfig.presets
@@ -310,33 +353,15 @@ function getFreshConfig(
 
       // If no custom config is provided the default is to use next/babel
       return ['next/babel']
-    })(),
-
-    overrides: loaderOptions.overrides,
+    })()
 
-    caller: {
-      name: 'next-babel-turbo-loader',
-      supportsStaticESM: true,
-      supportsDynamicImport: true,
+    options.overrides = loaderOptions.overrides
 
-      // Provide plugins with insight into webpack target.
-      // https://github.com/babel/babel-loader/issues/787
-      target: target,
-
-      // Webpack 5 supports TLA behind a flag. We enable it by default
-      // for Babel, and then webpack will throw an error if the experimental
-      // flag isn't enabled.
-      supportsTopLevelAwait: true,
-
-      isServer,
-      srcDir,
-      pagesDir,
-      isDev: development,
+    options.caller = {
+      ...baseCaller,
       hasJsxRuntime,
-
-      ...loaderOptions.caller,
-    },
-  } as any
+    }
+  }
 
   // Babel does strict checks on the config so undefined is not allowed
   if (typeof options.target === 'undefined') {
@@ -405,7 +430,7 @@ export default function getConfig(
     filename
   )
 
-  if (loaderOptions.configFile) {
+  if (loaderOptions.transformMode === 'default' && loaderOptions.configFile) {
     // Ensures webpack invalidates the cache for this loader when the config file changes
     this.addDependency(loaderOptions.configFile)
   }
@@ -426,7 +451,11 @@ export default function getConfig(
     }
   }
 
-  if (loaderOptions.configFile && !configFiles.has(loaderOptions.configFile)) {
+  if (
+    loaderOptions.transformMode === 'default' &&
+    loaderOptions.configFile &&
+    !configFiles.has(loaderOptions.configFile)
+  ) {
     configFiles.add(loaderOptions.configFile)
     Log.info(
       `Using external babel configuration from ${loaderOptions.configFile}`
diff --git a/packages/next/src/build/babel/loader/types.d.ts b/packages/next/src/build/babel/loader/types.d.ts
index ddf223ac33ec..7115e5612631 100644
--- a/packages/next/src/build/babel/loader/types.d.ts
+++ b/packages/next/src/build/babel/loader/types.d.ts
@@ -6,16 +6,45 @@ export interface NextJsLoaderContext extends webpack.LoaderContext<{}> {
   target: string
 }
 
-export interface NextBabelLoaderOptions {
-  hasJsxRuntime: boolean
-  hasReactRefresh: boolean
+export interface NextBabelLoaderBaseOptions {
   isServer: boolean
-  development: boolean
+  distDir: string
   pagesDir: string
+  cwd: string
+  srcDir: string
+  caller: any
+  development: boolean
+
+  // Custom plugins to be added to the generated babel options.
+  plugins?: Array<any>
+}
+
+/**
+ * Options to create babel loader for the default transformations.
+ *
+ * This is primary usecase of babel-loader configuration for running
+ * all of the necessary transforms for the ecmascript instead of swc loader.
+ */
+export type NextBabelLoaderOptionDefaultPresets = NextBabelLoaderBaseOptions & {
+  transformMode: 'default'
+  hasJsxRuntime: boolean
+  hasReactRefresh: boolean
   sourceMaps?: any[]
   overrides: any
-  caller: any
   configFile: string | undefined
-  cwd: string
-  srcDir: string
 }
+
+/**
+ * Options to create babel loader for 'standalone' transformations.
+ *
+ * This'll create a babel loader does not enable any of the default presets or plugins,
+ * only the ones specified in the options where swc loader is enabled but need to inject
+ * a babel specific plugins like react compiler.
+ */
+export type NextBabelLoaderOptionStandalone = NextBabelLoaderBaseOptions & {
+  transformMode: 'standalone'
+}
+
+export type NextBabelLoaderOptions =
+  | NextBabelLoaderOptionDefaultPresets
+  | NextBabelLoaderOptionStandalone
diff --git a/packages/next/src/build/get-babel-loader-config.ts b/packages/next/src/build/get-babel-loader-config.ts
new file mode 100644
index 000000000000..3535100afd9c
--- /dev/null
+++ b/packages/next/src/build/get-babel-loader-config.ts
@@ -0,0 +1,86 @@
+import path from 'path'
+import type { ReactCompilerOptions } from '../server/config-shared'
+
+const getReactCompilerPlugins = (
+  options: boolean | ReactCompilerOptions | undefined,
+  isDev: boolean
+) => {
+  if (!options) {
+    return undefined
+  }
+
+  const compilerOptions = typeof options === 'boolean' ? {} : options
+  if (options) {
+    return [
+      [
+        'babel-plugin-react-compiler',
+        {
+          panicThreshold: isDev ? undefined : 'NONE',
+          ...compilerOptions,
+        },
+      ],
+    ]
+  }
+  return undefined
+}
+
+const getBabelLoader = (
+  useSWCLoader: boolean | undefined,
+  babelConfigFile: string | undefined,
+  isServer: boolean,
+  distDir: string,
+  pagesDir: string | undefined,
+  cwd: string,
+  srcDir: string,
+  dev: boolean,
+  isClient: boolean,
+  reactCompilerOptions: boolean | ReactCompilerOptions | undefined
+) => {
+  if (!useSWCLoader) {
+    return {
+      loader: require.resolve('./babel/loader/index'),
+      options: {
+        transformMode: 'default',
+        configFile: babelConfigFile,
+        isServer,
+        distDir,
+        pagesDir,
+        cwd,
+        srcDir: path.dirname(srcDir),
+        development: dev,
+        hasReactRefresh: dev && isClient,
+        hasJsxRuntime: true,
+        plugins: getReactCompilerPlugins(reactCompilerOptions, dev),
+      },
+    }
+  }
+
+  return undefined
+}
+
+/**
+ * Get a separate babel loader for the react compiler, only used if Babel is not
+ * configured through e.g. .babelrc. If user have babel config, this should be configured in the babel loader itself.
+ * Note from react compiler:
+ * > For best results, compiler must run as the first plugin in your Babel pipeline so it receives input as close to the original source as possible.
+ */
+const getReactCompilerLoader = (
+  options: boolean | ReactCompilerOptions | undefined,
+  cwd: string,
+  isDev: boolean
+) => {
+  if (!options) {
+    return undefined
+  }
+
+  return {
+    loader: require.resolve('./babel/loader/index'),
+    options: {
+      transformMode: 'standalone',
+      cwd,
+      plugins: getReactCompilerPlugins(options, isDev),
+    },
+  }
+}
+
+export { getBabelLoader, getReactCompilerLoader }
diff --git a/packages/next/src/build/swc/index.ts b/packages/next/src/build/swc/index.ts
index 8578d8a8b8e8..d6203ff7999f 100644
--- a/packages/next/src/build/swc/index.ts
+++ b/packages/next/src/build/swc/index.ts
@@ -16,10 +16,13 @@ import type {
   TurboRuleConfigItemOptions,
 } from '../../server/config-shared'
 import { isDeepStrictEqual } from 'util'
-import type { DefineEnvPluginOptions } from '../webpack/plugins/define-env-plugin'
-import { getDefineEnv } from '../webpack/plugins/define-env-plugin'
+import {
+  type DefineEnvPluginOptions,
+  getDefineEnv,
+} from '../webpack/plugins/define-env-plugin'
 import type { PageExtensions } from '../page-extensions-type'
 import type { __ApiPreviewProps } from '../../server/api-utils'
+import { getReactCompilerLoader } from '../get-babel-loader-config'
 
 const nextVersion = process.env.__NEXT_VERSION as string
 
@@ -1130,12 +1133,65 @@ function bindingToApi(
     }
   }
 
+  /**
+   * Returns a new copy of next.js config object to avoid mutating the original.
+   *
+   * Also it does some augmentation to the configuration as well, for example set the
+   * turbopack's rules if `experimental.reactCompilerOptions` is set.
+   */
+  function augmentNextConfig(
+    originalNextConfig: NextConfigComplete,
+    projectPath: string
+  ): Record<string, any> {
+    let nextConfig = { ...(originalNextConfig as any) }
+
+    const reactCompilerOptions = nextConfig.experimental?.reactCompiler
+
+    // It is not easy to set the rules inside of rust as resolving, and passing the context identical to the webpack
+    // config is bit hard, also we can reuse same codes between webpack config in here.
+    if (reactCompilerOptions) {
+      const ruleKeys = ['*.ts', '*.js', '*.jsx', '*.tsx']
+      if (
+        Object.keys(nextConfig?.experimental?.turbo?.rules ?? []).some((key) =>
+          ruleKeys.includes(key)
+        )
+      ) {
+        Log.warn(
+          `The React Compiler cannot be enabled automatically because 'experimental.turbo' contains a rule for '*.ts', '*.js', '*.jsx', and '*.tsx'. Remove this rule, or add 'babel-loader' and 'babel-plugin-react-compiler' to the Turbopack configuration manually.`
+        )
+      } else {
+        if (!nextConfig.experimental.turbo) {
+          nextConfig.experimental.turbo = {}
+        }
+
+        if (!nextConfig.experimental.turbo.rules) {
+          nextConfig.experimental.turbo.rules = {}
+        }
+
+        for (const key of ['*.ts', '*.js', '*.jsx', '*.tsx']) {
+          nextConfig.experimental.turbo.rules[key] = {
+            foreign: false,
+            loaders: [
+              getReactCompilerLoader(
+                originalNextConfig.experimental.reactCompiler,
+                projectPath,
+                nextConfig.dev
+              ),
+            ],
+          }
+        }
+      }
+    }
+
+    return nextConfig
+  }
+
   async function serializeNextConfig(
     nextConfig: NextConfigComplete,
     projectPath: string
   ): Promise<string> {
     // Avoid mutating the existing `nextConfig` object.
-    let nextConfigSerializable = { ...(nextConfig as any) }
+    let nextConfigSerializable = augmentNextConfig(nextConfig, projectPath)
 
     nextConfigSerializable.generateBuildId =
       await nextConfig.generateBuildId?.()
@@ -1144,8 +1200,10 @@ function bindingToApi(
     nextConfigSerializable.exportPathMap = {}
     nextConfigSerializable.webpack = nextConfig.webpack && {}
 
-    if (nextConfig.experimental?.turbo?.rules) {
-      ensureLoadersHaveSerializableOptions(nextConfig.experimental.turbo?.rules)
+    if (nextConfigSerializable.experimental?.turbo?.rules) {
+      ensureLoadersHaveSerializableOptions(
+        nextConfigSerializable.experimental.turbo?.rules
+      )
     }
 
     nextConfigSerializable.modularizeImports =
diff --git a/packages/next/src/build/webpack-config.ts b/packages/next/src/build/webpack-config.ts
index d0a5f322bc50..32cc8b9c751e 100644
--- a/packages/next/src/build/webpack-config.ts
+++ b/packages/next/src/build/webpack-config.ts
@@ -84,6 +84,10 @@ import {
 } from './create-compiler-aliases'
 import { hasCustomExportOutput } from '../export/utils'
 import { CssChunkingPlugin } from './webpack/plugins/css-chunking-plugin'
+import {
+  getBabelLoader,
+  getReactCompilerLoader,
+} from './get-babel-loader-config'
 
 type ExcludesFalse = <T>(x: T | false) => x is T
 type ClientEntries = {
@@ -405,23 +409,22 @@ export default async function getBaseWebpackConfig(
     loggedIgnoredCompilerOptions = true
   }
 
-  const babelLoader = (function getBabelLoader() {
-    if (useSWCLoader) return undefined
-    return {
-      loader: require.resolve('./babel/loader/index'),
-      options: {
-        configFile: babelConfigFile,
-        isServer: isNodeOrEdgeCompilation,
-        distDir,
-        pagesDir,
-        srcDir: path.dirname((appDir || pagesDir)!),
-        cwd: dir,
-        development: dev,
-        hasReactRefresh: dev && isClient,
-        hasJsxRuntime: true,
-      },
-    }
-  })()
+  const babelLoader = getBabelLoader(
+    useSWCLoader,
+    babelConfigFile,
+    isNodeOrEdgeCompilation,
+    distDir,
+    pagesDir,
+    dir,
+    (appDir || pagesDir)!,
+    dev,
+    isClient,
+    config.experimental?.reactCompiler
+  )
+
+  const reactCompilerLoader = babelLoader
+    ? undefined
+    : getReactCompilerLoader(config.experimental?.reactCompiler, dir, dev)
 
   let swcTraceProfilingInitialized = false
   const getSwcLoader = (extraOptions: Partial<SWCLoaderOptions>) => {
@@ -491,6 +494,7 @@ export default async function getBaseWebpackConfig(
         // acceptable as Babel will not be recommended.
         swcServerLayerLoader,
         babelLoader,
+        reactCompilerLoader,
       ].filter(Boolean)
     : []
 
@@ -540,6 +544,7 @@ export default async function getBaseWebpackConfig(
           // acceptable as Babel will not be recommended.
           isBrowserLayer ? swcBrowserLayerLoader : swcSSRLayerLoader,
           babelLoader,
+          reactCompilerLoader,
         ].filter(Boolean)
       : []),
   ]
diff --git a/packages/next/src/server/config-schema.ts b/packages/next/src/server/config-schema.ts
index 5a8613398798..97f16c1ef2d7 100644
--- a/packages/next/src/server/config-schema.ts
+++ b/packages/next/src/server/config-schema.ts
@@ -420,6 +420,19 @@ export const configSchema: zod.ZodType<NextConfig> = z.lazy(() =>
         testProxy: z.boolean().optional(),
         defaultTestRunner: z.enum(SUPPORTED_TEST_RUNNERS_LIST).optional(),
         allowDevelopmentBuild: z.literal(true).optional(),
+        reactCompiler: z.union([
+          z.boolean(),
+          z
+            .object({
+              compilationMode: z
+                .enum(['infer', 'annotation', 'all'])
+                .optional(),
+              panicThreshold: z
+                .enum(['ALL_ERRORS', 'CRITICAL_ERRORS', 'NONE'])
+                .optional(),
+            })
+            .optional(),
+        ]),
       })
       .optional(),
     exportPathMap: z
diff --git a/packages/next/src/server/config-shared.ts b/packages/next/src/server/config-shared.ts
index 2f46d3d53939..fec415e886d8 100644
--- a/packages/next/src/server/config-shared.ts
+++ b/packages/next/src/server/config-shared.ts
@@ -182,6 +182,18 @@ export interface NextJsWebpackConfig {
   ): any
 }
 
+/**
+ * Set of options for the react compiler next.js
+ * currently supports.
+ *
+ * This can be changed without breaking changes while supporting
+ * react compiler in the experimental phase.
+ */
+export interface ReactCompilerOptions {
+  compilationMode?: 'infer' | 'annotation' | 'all'
+  panicThreshold?: 'ALL_ERRORS' | 'CRITICAL_ERRORS' | 'NONE'
+}
+
 export interface ExperimentalConfig {
   flyingShuttle?: boolean
   prerenderEarlyExit?: boolean
@@ -446,6 +458,12 @@ export interface ExperimentalConfig {
    *
    */
   serverComponentsExternalPackages?: string[]
+  /**
+   * Enable experimental react compiler optimization.
+   * Configuration accepts partial config object to the compiler, if provided
+   * compiler will be enabled.
+   */
+  reactCompiler?: boolean | ReactCompilerOptions
 }
 
 export type ExportPathMap = {
diff --git a/pnpm-lock.yaml b/pnpm-lock.yaml
index 7737f803d91b..73d324c00840 100644
--- a/pnpm-lock.yaml
+++ b/pnpm-lock.yaml
@@ -815,6 +815,9 @@ importers:
       '@swc/helpers':
         specifier: 0.5.11
         version: 0.5.11
+      babel-plugin-react-compiler:
+        specifier: '*'
+        version: 0.0.0-experimental-c23de8d-20240515
       busboy:
         specifier: 1.6.0
         version: 1.6.0
@@ -1753,6 +1756,16 @@ packages:
       jsesc: 2.5.2
     dev: false
 
+  /@babel/generator@7.2.0:
+    resolution: {integrity: sha512-BA75MVfRlFQG2EZgFYIwyT1r6xSkwfP2bdkY/kLZusEYWiJs4xCowab/alaEaT0wSvmVuXGqiefeBlP+7V1yKg==}
+    dependencies:
+      '@babel/types': 7.22.5
+      jsesc: 2.5.2
+      lodash: 4.17.20
+      source-map: 0.5.7
+      trim-right: 1.0.1
+    dev: false
+
   /@babel/generator@7.22.5:
     resolution: {integrity: sha512-+lcUbnTRhd0jOewtFSedLyiPsD5tswKkbgcezOqqWFUVNEwoUTlpPOBmvhG7OXWLR4jMdv0czPGH5XbflnD1EA==}
     engines: {node: '>=6.9.0'}
@@ -4374,7 +4387,7 @@ packages:
       '@jest/types': 29.6.3
       '@types/node': 20.12.3
       ansi-escapes: 4.3.2
-      chalk: 4.0.0
+      chalk: 4.1.2
       ci-info: 3.8.0
       exit: 0.1.2
       graceful-fs: 4.2.11
@@ -4673,6 +4686,15 @@ packages:
       - supports-color
     dev: true
 
+  /@jest/types@24.9.0:
+    resolution: {integrity: sha512-XKK7ze1apu5JWQ5eZjHITP66AX+QsLlbaJRBGYr8pNzwcAE2JVkwnf0yqjHTsDRcjR0mujy/NmZMXw5kl+kGBw==}
+    engines: {node: '>= 6'}
+    dependencies:
+      '@types/istanbul-lib-coverage': 2.0.4
+      '@types/istanbul-reports': 1.1.2
+      '@types/yargs': 13.0.12
+    dev: false
+
   /@jest/types@27.5.1:
     resolution: {integrity: sha512-Cx46iJ9QpwQTjIdq5VJu2QTMMs3QlEjI0x1QbBP5W1+nMzyc2XmimiRR/CbX9TO0cPTeUlxWMOu8mslYsJ8DEw==}
     engines: {node: ^10.13.0 || ^12.13.0 || ^14.15.0 || >=15.0.0}
@@ -4704,7 +4726,7 @@ packages:
       '@types/istanbul-reports': 3.0.1
       '@types/node': 20.12.3
       '@types/yargs': 17.0.10
-      chalk: 4.0.0
+      chalk: 4.1.2
     dev: true
 
   /@jridgewell/gen-mapping@0.3.1:
@@ -7176,6 +7198,13 @@ packages:
     dependencies:
       '@types/istanbul-lib-coverage': 2.0.4
 
+  /@types/istanbul-reports@1.1.2:
+    resolution: {integrity: sha512-P/W9yOX/3oPZSpaYOCQzGqgCQRXn0FFO/V8bWrCQs+wLmvVVxk6CRBXALEvNs9OHIatlnlFokfhuDo2ug01ciw==}
+    dependencies:
+      '@types/istanbul-lib-coverage': 2.0.4
+      '@types/istanbul-lib-report': 3.0.0
+    dev: false
+
   /@types/istanbul-reports@3.0.0:
     resolution: {integrity: sha512-nwKNbvnwJ2/mndE9ItP/zc2TCzw6uuodnF4EHYWD+gCQDVBuRQL5UzbZD0/ezy1iKsFU2ZQiDqg4M9dN4+wZgA==}
     dependencies:
@@ -7494,6 +7523,12 @@ packages:
   /@types/yargs-parser@21.0.0:
     resolution: {integrity: sha512-iO9ZQHkZxHn4mSakYV0vFHAVDyEOIJQrV2uZ06HxEPcx+mt8swXoZHIbaaJ2crJYFfErySgktuTZ3BeLz+XmFA==}
 
+  /@types/yargs@13.0.12:
+    resolution: {integrity: sha512-qCxJE1qgz2y0hA4pIxjBR+PelCH0U5CK1XJXFwCNqfmliatKp47UCXXE9Dyk1OXBDLvsCF57TqQEJaeLfDYEOQ==}
+    dependencies:
+      '@types/yargs-parser': 21.0.0
+    dev: false
+
   /@types/yargs@16.0.9:
     resolution: {integrity: sha512-tHhzvkFXZQeTECenFoRljLBYPZJ7jAVxqqtEI0qTLOmuultnFp4I9yKE17vTuhf7BkhCu7I4XuemPgikDVuYqA==}
     dependencies:
@@ -8227,7 +8262,6 @@ packages:
   /ansi-regex@4.1.0:
     resolution: {integrity: sha512-1apePfXM1UOSqw0o9IiFAovVz9M5S1Dg+4TrDwfMewQ6p/rmMueb7tWZjQ1rx4Loy1ArBggoqGpfqqdI4rondg==}
     engines: {node: '>=6'}
-    dev: true
 
   /ansi-regex@5.0.1:
     resolution: {integrity: sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==}
@@ -8808,6 +8842,18 @@ packages:
     transitivePeerDependencies:
       - supports-color
 
+  /babel-plugin-react-compiler@0.0.0-experimental-c23de8d-20240515:
+    resolution: {integrity: sha512-0XN2gmpT55QtAz5n7d5g91y1AuO9tRhWBaLgCRyc4ExHrlr7+LfxW+YTb3mOwxngkkiggwM8HyYsaEK9MqhnlQ==}
+    dependencies:
+      '@babel/generator': 7.2.0
+      '@babel/types': 7.22.5
+      chalk: 4.1.2
+      invariant: 2.2.4
+      pretty-format: 24.9.0
+      zod: 3.23.8
+      zod-validation-error: 2.1.0(zod@3.23.8)
+    dev: false
+
   /babel-plugin-transform-async-to-promises@0.8.15:
     resolution: {integrity: sha512-fDXP68ZqcinZO2WCiimCL9zhGjGXOnn3D33zvbh+yheZ/qOrNVVDDIBtAaM3Faz8TRvQzHiRKsu3hfrBAhEncQ==}
     dev: true
@@ -14086,7 +14132,7 @@ packages:
       '@sidvind/better-ajv-errors': 0.6.10(ajv@6.12.6)
       acorn-walk: 8.2.0
       ajv: 6.12.6
-      chalk: 4.0.0
+      chalk: 4.1.2
       deepmerge: 4.2.2
       eslint: 7.24.0
       espree: 7.3.1
@@ -14579,7 +14625,6 @@ packages:
     resolution: {integrity: sha512-phJfQVBuaJM5raOpJjSfkiD6BpbCE4Ns//LaXl6wGYtUBY83nWS6Rf9tXm2e8VaK60JEjYldbPif/A2B1C2gNA==}
     dependencies:
       loose-envify: 1.4.0
-    dev: true
 
   /ip@2.0.0:
     resolution: {integrity: sha512-WKa+XuLG1A1R0UWhl2+1XQSi+fZWMsYKffMZTTYsiZaUD8k2yDAj5atimTUD2TZkyCkNEeYE5NhFZmupOGtjYQ==}
@@ -15432,7 +15477,7 @@ packages:
       '@jest/core': 29.7.0
       '@jest/test-result': 29.7.0
       '@jest/types': 29.6.3
-      chalk: 4.0.0
+      chalk: 4.1.2
       create-jest: 29.7.0(@types/node@20.12.3)
       exit: 0.1.2
       import-local: 3.0.2
@@ -15500,7 +15545,7 @@ packages:
     resolution: {integrity: sha512-LMIgiIrhigmPrs03JHpxUh2yISK3vLFPkAodPeo0+BuF7wA2FoQbkEg1u8gBYBThncu7e1oEDUfIXVuTqLRUjw==}
     engines: {node: ^14.15.0 || ^16.10.0 || >=18.0.0}
     dependencies:
-      chalk: 4.0.0
+      chalk: 4.1.2
       diff-sequences: 29.6.3
       jest-get-type: 29.6.3
       pretty-format: 29.7.0
@@ -16028,7 +16073,7 @@ packages:
     dependencies:
       '@jest/types': 29.6.3
       '@types/node': 20.12.3
-      chalk: 4.0.0
+      chalk: 4.1.2
       ci-info: 3.8.0
       graceful-fs: 4.2.11
       picomatch: 2.3.1
@@ -20886,6 +20931,16 @@ packages:
     engines: {node: '>=6'}
     dev: true
 
+  /pretty-format@24.9.0:
+    resolution: {integrity: sha512-00ZMZUiHaJrNfk33guavqgvfJS30sLYf0f8+Srklv0AMPodGGHcoHgksZ3OThYnIvOd+8yMCn0YiEOogjlgsnA==}
+    engines: {node: '>= 6'}
+    dependencies:
+      '@jest/types': 24.9.0
+      ansi-regex: 4.1.0
+      ansi-styles: 3.2.1
+      react-is: 19.0.0-beta-4508873393-20240430
+    dev: false
+
   /pretty-format@27.5.1:
     resolution: {integrity: sha512-Qb1gy5OrP5+zDf2Bvnzdl3jsTf1qXVMazbvCoKhtKqVs4/YK4ozX4gKQJJVyNe+cajNPn0KoC0MC3FUmaHWEmQ==}
     engines: {node: ^10.13.0 || ^12.13.0 || ^14.15.0 || >=15.0.0}
@@ -24153,6 +24208,11 @@ packages:
     engines: {node: '>=0.10.0'}
     dev: true
 
+  /trim-right@1.0.1:
+    resolution: {integrity: sha512-WZGXGstmCWgeevgTL54hrCuw1dyMQIzWy7ZfqRJfSmJZBwklI15egmQytFP6bPidmw3M8d5yEowl1niq4vmqZw==}
+    engines: {node: '>=0.10.0'}
+    dev: false
+
   /trim-trailing-lines@1.1.2:
     resolution: {integrity: sha512-MUjYItdrqqj2zpcHFTkMa9WAv4JHTI6gnRQGPFLrt5L9a6tRMiDnIqYl8JBvu2d2Tc3lWJKQwlGCp0K8AvCM+Q==}
     dev: true
@@ -25752,10 +25812,23 @@ packages:
     resolution: {integrity: sha512-N+d4UJSJbt/R3wqY7Coqs5pcV0aUj2j9IaQ3rNj9bVCLld8tTGKRa2USARjnvZJWVx1NDmQev8EknoczaOQDOA==}
     dev: true
 
+  /zod-validation-error@2.1.0(zod@3.23.8):
+    resolution: {integrity: sha512-VJh93e2wb4c3tWtGgTa0OF/dTt/zoPCPzXq4V11ZjxmEAFaPi/Zss1xIZdEB5RD8GD00U0/iVXgqkF77RV7pdQ==}
+    engines: {node: '>=18.0.0'}
+    peerDependencies:
+      zod: ^3.18.0
+    dependencies:
+      zod: 3.23.8
+    dev: false
+
   /zod@3.22.3:
     resolution: {integrity: sha512-EjIevzuJRiRPbVH4mGc8nApb/lVLKVpmUhAaR5R5doKGfAnGJ6Gr3CViAVjP+4FWSxCsybeWQdcgCtbX+7oZug==}
     dev: true
 
+  /zod@3.23.8:
+    resolution: {integrity: sha512-XBx9AXhXktjUqnepgTiE5flcKIYWi/rme0Eaj+5Y0lftuGBq+jyRu/md4WnuxqgP1ubdpNCsYEYPxrzVHD8d6g==}
+    dev: false
+
   /zwitch@1.0.5:
     resolution: {integrity: sha512-V50KMwwzqJV0NpZIZFwfOD5/lyny3WlSzRiXgA0G7VUnRlqttta1L6UQIHzd6EuBY/cHGfwTIck7w1yH6Q5zUw==}
     dev: true
diff --git a/test/e2e/react-compiler/.babelrc b/test/e2e/react-compiler/.babelrc
new file mode 100644
index 000000000000..1ff94f7ed28e
--- /dev/null
+++ b/test/e2e/react-compiler/.babelrc
@@ -0,0 +1,3 @@
+{
+  "presets": ["next/babel"]
+}
diff --git a/test/e2e/react-compiler/app/layout.tsx b/test/e2e/react-compiler/app/layout.tsx
new file mode 100644
index 000000000000..af824ab0611d
--- /dev/null
+++ b/test/e2e/react-compiler/app/layout.tsx
@@ -0,0 +1,13 @@
+'use client'
+
+export default function RootLayout({
+  children,
+}: {
+  children: React.ReactNode
+}) {
+  return (
+    <html>
+      <body>{children}</body>
+    </html>
+  )
+}
diff --git a/test/e2e/react-compiler/app/page.tsx b/test/e2e/react-compiler/app/page.tsx
new file mode 100644
index 000000000000..e5c502bd1ae8
--- /dev/null
+++ b/test/e2e/react-compiler/app/page.tsx
@@ -0,0 +1,25 @@
+'use client'
+
+export default function Page() {
+  let heading: any = null
+  // eslint-disable-next-line no-eval
+  const $_ = eval('$')
+  if (Array.isArray($_)) {
+    // console.log("useMemoCache", $_);
+    heading = (
+      <h1 className="text-9xl">
+        {/* @ts-ignore */}
+        React compiler is enabled with <strong>{$_.length}</strong> memo slots
+      </h1>
+    )
+  }
+
+  return (
+    <>
+      <div>
+        {heading}
+        <p>hello world</p>
+      </div>
+    </>
+  )
+}
diff --git a/test/e2e/react-compiler/next.config.js b/test/e2e/react-compiler/next.config.js
new file mode 100644
index 000000000000..f230258c1322
--- /dev/null
+++ b/test/e2e/react-compiler/next.config.js
@@ -0,0 +1,12 @@
+/**
+ * @type {import('next').NextConfig}
+ */
+const nextConfig = {
+  experimental: {
+    // Forces nextjs to use experimental react which has the useMemoCache hook.
+    taint: true,
+    reactCompiler: true,
+  },
+}
+
+module.exports = nextConfig
diff --git a/test/e2e/react-compiler/react-compiler.test.ts b/test/e2e/react-compiler/react-compiler.test.ts
new file mode 100644
index 000000000000..bc03fa4eaf91
--- /dev/null
+++ b/test/e2e/react-compiler/react-compiler.test.ts
@@ -0,0 +1,27 @@
+import { nextTestSetup, FileRef } from 'e2e-utils'
+import { join } from 'path'
+
+describe.each(
+  ['default', process.env.TURBOPACK ? undefined : 'babelrc'].filter(Boolean)
+)('react-compiler %s', (variant) => {
+  const { next } = nextTestSetup({
+    files:
+      variant === 'babelrc'
+        ? __dirname
+        : {
+            app: new FileRef(join(__dirname, 'app')),
+            'next.config.js': new FileRef(join(__dirname, 'next.config.js')),
+          },
+
+    dependencies: {
+      'babel-plugin-react-compiler': '0.0.0-experimental-4690415-20240515',
+    },
+  })
+
+  it('should render', async () => {
+    const $ = await next.render$('/')
+    expect($('h1').text()).toMatch(
+      /React compiler is enabled with .+ memo slots/
+    )
+  })
+})
