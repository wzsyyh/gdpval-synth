# Design Doc - Universal Webpack for Next.js

# Design Doc - Universal Webpack for Next.js

# Design Doc - Universal Webpack for Next.js

**Author:** Next.js Core Team  
**Date:** January 2018  
**PR:** vercel/next.js#3578

## Abstract

This document describes the architectural changes introduced by PR #3578, which implements universal (isomorphic) webpack configuration in Next.js. Webpack is now used to transpile both client-side and server-side code, enabling a plugin-based ecosystem for CSS, Sass, LESS, TypeScript, and React alternatives such as Preact. The new `webpack` function in `next.config.js` accepts an `isServer` boolean, allowing developers to provide differentiated configurations for client and server builds. This change resolves over 30 community issues related to loader support, CSS preprocessing, TypeScript integration, and React alternative compatibility.

## Motivation

## Motivation

Prior to PR #3578, Next.js had limited support for custom webpack loaders and preprocessing pipelines. Server-side code was not transpiled through webpack, which meant that features like CSS imports, Sass/Less compilation, and TypeScript support required fragile workarounds or were entirely unsupported. Community issues accumulated across several categories:

- **Loader support:** Issues #1564, #1245, #3068, #3241, #3560, #3318, #3203, #3597 requested the ability to use nearly all loaders in the webpack ecosystem.
- **CSS/Sass/Less support:** Issues #3131, #3239, #2534, #3465, #1615, #3143, #2413, #3519, #3276, #3408 requested built-in support for stylesheet preprocessing and CSS modules.
- **Custom extensions:** Issues #3445, #2391 requested support for custom file extensions beyond `.js` and `.jsx`.
- **TypeScript support:** Issues #3511, #2391, #3389, #3124 requested first-class TypeScript integration.
- **Preact/React alternatives:** Issue #1564 specifically described a bundle bloat problem where React, Preact, and Preact-compat were all included in the final bundle despite aliasing, producing bundles over 100kb larger than expected.
- **Source maps:** Issue #1903 requested external source maps in production builds.

The universal webpack approach solves all of these issues by establishing a single, extensible build pipeline for both client and server code.

## Architecture Overview

## Architecture Overview

The core architectural change in PR #3578 is that webpack is now used to transpile server-side code in addition to client-side code. Previously, server-side code was handled by a separate mechanism; now, a single webpack-based pipeline processes both environments.

The user-facing interface for this change is the `webpack` function in `next.config.js`. The function signature is:

```js
module.exports = {
  webpack: (config, {dir, dev, isServer, buildId, config, defaultLoaders}) => {
    return config
  }
}
```

The `isServer` boolean is the key differentiator. The webpack function is called twice during a build: once with `isServer: true` for the server bundle, and once with `isServer: false` for the client bundle. This allows developers to apply different transformations, loaders, or optimizations to server code versus client code.

Other parameters provide build context:
- `dir`: The project directory
- `dev`: Whether the build is for development mode
- `buildId`: A unique identifier for the current build
- `defaultLoaders`: Pre-configured loader objects provided by Next.js

This dual-invocation pattern is the foundation for the plugin ecosystem described in the next section.

## Plugin Ecosystem

## Plugin Ecosystem

PR #3578 introduces a composable plugin pattern using `@zeit`-scoped npm packages. Each plugin wraps a webpack configuration modification and is applied via function composition in `next.config.js`.

### CSS Support

The `@zeit/next-css` plugin enables importing `.css` files with server-side rendering support:

```bash
yarn add @zeit/next-css
```

```js
// next.config.js
const withCSS = require('@zeit/next-css')
module.exports = withCSS()
```

CSS modules can be enabled with the `cssModules` option:

```js
// next.config.js
const withCSS = require('@zeit/next-css')
module.exports = withCSS({
  cssModules: true
})
```

### Sass Support

```bash
npm install --save @zeit/next-sass node-sass
```

```js
// next.config.js
const withSass = require('@zeit/next-sass')
module.exports = withSass()
```

### Less Support

```bash
npm install --save @zeit/next-less less
```

```js
// next.config.js
const withLess = require('@zeit/next-less')
module.exports = withLess()
```

Note: The PR description contains a typo where the Less example shows `module.exports = withSass()` instead of `withLess()`. The correct pattern uses `withLess()`.

### TypeScript Support

```bash
npm install --save @zeit/next-typescript typescript
```

```js
// next.config.js
const withTypescript = require('@zeit/next-typescript')
module.exports = withTypescript()
```

### Preact Support

```bash
npm install --save @zeit/next-preact
```

```js
// next.config.js
const withPreact = require('@zeit/next-preact')
module.exports = withPreact()
```

Preact also requires a server-side alias configuration:

```js
// server.js
require('@zeit/next-preact/alias')()
const { createServer } = require('http')
const next = require('next')

const app = next({ dev: process.env.NODE_ENV !== 'production' })
const handle = app.getRequestHandler()

app.prepare()
.then(() => {
  createServer(handle)
  .listen(port, () => {
    console.log(`> Ready on http://localhost:${port}`)
  })
})
```

## Client-Side Changes

## Client-Side Changes

### Asset Prefix Support

The `client/index.js` diff introduces a new import of `* as asset` from `'../lib/asset'` and calls `asset.setAssetPrefix(assetPrefix)` during client initialization. This enables static assets to work correctly across zones (multi-zone deployments), as noted in the source comment: "With this, static assets will work across zones."

### Simplified Error Handling

The error handling in the `render` function was simplified. Previously, the code checked `if (props.err && !props.err.ignore)` before rendering an error. The `ignore` property was used by Next.js rendering logic to handle certain 404 errors internally. PR #3578 removes this check, simplifying the condition to `if (props.err)`:

```js
// Before
if (props.err && !props.err.ignore) {
  await renderError(props.err)
  return
}

// After
if (props.err) {
  await renderError(props.err)
  return
}
```

### React Alternative Hydration Support

The `renderReactElement` function now checks whether `ReactDOM.hydrate` is a function before calling it. This change supports React alternatives like Preact that may not implement the `hydrate` method:

```js
// Before
if (isInitialRender) {
  ReactDOM.hydrate(reactEl, domEl)
  isInitialRender = false
} else {
  ReactDOM.render(reactEl, domEl)
}

// After (with comment: "The check for `.hydrate` is there to support React alternatives like preact")
if (isInitialRender && typeof ReactDOM.hydrate === 'function') {
  ReactDOM.hydrate(reactEl, domEl)
  isInitialRender = false
} else {
  ReactDOM.render(reactEl, domEl)
}
```

This ensures that Preact and other React alternatives that do not support `ReactDOM.hydrate` will fall back to `ReactDOM.render`.

## TypeScript Configuration

## TypeScript Configuration

The `@zeit/next-typescript` plugin requires a `tsconfig.json` in the project root. The recommended configuration from the PR description is:

```json
{
  "compileOnSave": false,
  "compilerOptions": {
    "target": "esnext",
    "module": "esnext",
    "jsx": "preserve",
    "allowJs": true,
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "removeComments": false,
    "preserveConstEnums": true,
    "sourceMap": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "typeRoots": ["./node_modules/@types"],
    "lib": ["dom", "es2015", "es2016"]
  }
}
```

Key compiler options explained:
- **`target: esnext`**: Emits the latest ECMAScript features, relying on webpack for further transpilation if needed.
- **`module: esnext`**: Uses ES module syntax, which webpack can process natively.
- **`jsx: preserve`**: Keeps JSX syntax intact so that Babel (via webpack) can handle JSX transformation.
- **`allowSyntheticDefaultImports`**: Allows default imports from modules without a default export, necessary for interop with CommonJS modules.
- **`allowJs: true`**: Allows mixing TypeScript and JavaScript files in the same project.
- **`skipLibCheck: true`**: Skips type checking of declaration files for faster compilation.

Pages are created using `.tsx` extensions in the `pages` directory:

```tsx
// pages/index.tsx
export default () => <div>Hello World</div>
```

## Backward Compatibility and Migration

## Backward Compatibility and Migration

According to the PR description, the new universal webpack system is "mostly backwards compatible." Existing `next.config.js` files that define a `webpack` function will continue to work without modification.

The main user-facing difference is that the `webpack` function in `next.config.js` is now called twice—once for the client build and once for the server build. The `isServer` boolean parameter allows developers to differentiate between these two invocations. Any existing webpack configuration that makes assumptions about running only once will need to be updated.

For custom extensions, while webpack now supports nearly all loaders, pages are still restricted to the core defined extensions: `.js`, `.jsx`, `.ts`, and `.tsx`. This restriction ensures consistent behavior for the file-system based routing mechanism.

The removal of the `source-map-support/register` import in `bin/next-dev` and the change from top-level `import` of `pkgUp` to a dynamic `require('pkg-up').sync('.')` are internal implementation details that do not affect user-facing configuration.

## Linked Issues Resolved

## Linked Issues Resolved

PR #3578 resolves issues across the following categories:

1. **Webpack ecosystem loader support:** #1564, #1245, #3068, #3241, #3560, #3318, #3203, #3597
2. **CSS/SASS/LESS support and CSS modules:** #3131, #3239, #2534, #3465, #1615, #3143, #2413, #3519, #3276, #3408
3. **Custom file extensions:** #3445, #2391
4. **TypeScript support:** #3511, #2391, #3389, #3124
5. **Preact and React clone support:** #1564
6. **External source maps in production:** #1903

Notable specific issues include:
- **#1564**: Described the problem of React, Preact, and Preact-compat all being included in the final bundle despite aliasing, producing bundles over 100kb. The issue title refers to "fully aliasing React" being broken in beta releases.
- **#3131**: Referenced twice in the PR description in the CSS/SASS/LESS category.
- **#2391**: Referenced in both custom extensions and TypeScript categories.
- **#1903**: Requested external source maps opt-in in production.
- **#3511**: A TypeScript-specific issue.
- **#3445**: A custom extensions issue.
