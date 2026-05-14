# PR #3578 diff and description from vercel/next


# Seed Material: vercel/next.js#3578: Universal Webpack
Source: github_issue_pr
Identifier: pr:vercel/next.js#3578

Repository: vercel/next.js
PR Number: #3578
PR Title: Universal Webpack
Merged At: 2018-01-30T15:40:53Z
Changed Files: 60
Additions: +1219, Deletions: -1606

## PR Description
- Support for nearly all loaders in the webpack ecosystem. Fixes #1564, #1245, #3068, #3241, #3560, #3318, #3203, #3597
- CSS / SASS / LESS support, `css-modules` is also support with a flag. Fixes #3131, #3239, #2534, #3465, #1615, #3143, #2413, #3131, #3519, #3276, #3408
- Support for custom extensions. Pages are still restricted to the core defined extensions though, which are: `.js,.jsx,.ts,.tsx` Fixes #3445, #2391
- Typescript support. Fixes #3511, #2391, #3389, #3124 
- Support for `preact` and any other React clone that supports server side rendering. Fixes #1564
- External source maps opt-in in production.  Fixes #1903.
- Latest version of react-hot-loader

I'm going to add more issues here whenever I come across one fitting this pull request.

## Webpack for Client / Server Side
Webpack is now being used to transpile the server side code too. This new feature is mostly backwards compatible. The main user facing difference is that `webpack` in `next.config.js` is now being ran twice, once for the server and once for the client allowing configuration to differ for client and server rendering. This differentiation is marked by a new property `isServer` passed to the `webpack` function. All properties are outlined below:

```js
module.exports = {
  webpack: (config, {dir, dev, isServer, buildId, config, defaultLoaders}) => {
	  return config
  }
}
```

## CSS / SASS / LESS
For importing `.css` `.scss` or `.less`  we’ve created modules which have sane defaults for server side rendering.

```
# css support
yarn add @zeit/next-css
```

```
// next.config.js
const withCSS = require('@zeit/next-css')
module.exports = withCSS()
```


### CSS modules 

Optionally you can enable css modules using `cssModules: true` , which works with `withSass` and `withLess` too.

```js
// next.config.js
const withCSS = require('@zeit/next-css')
module.exports = withCSS({
	cssModules: true
})
```

### sass support

```
npm install --save @zeit/next-sass node-sass
```

```js
// next.config.js
const withSass = require('@zeit/next-sass')
module.exports = withSass()
```

### less support

```
npm install --save @zeit/next-less less
```

```js
// next.config.js
const withLess = require('@zeit/next-less')
module.exports = withSass()
```

## Typescript
`npm install --save @zeit/next-typescript typescript`

Create a `next.config.js`

```js
// next.config.js
const withTypescript = require('@zeit/next-typescript')
module.exports = withTypescript()
```

Then create a `tsconfig.json` in your project

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
    "typeRoots": [
      "./node_modules/@types"
    ],
    "lib": [
      "dom",
      "es2015",
      "es2016"
    ]
  }
}
```

Create pages in the `pages` directory

```js
// pages/index.tsx
export default () => <div>Hello World</div>
```

## preact
With universal webpack and the upgrade to react-hot-loader v4 `preact` is now easily configured

```js
// next.config.js
const withPreact = require('@zeit/next-preact')
module.exports = withPreact()
```

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

## Source Maps
Next is configured to serve the `.js.map` route for bundled files. You

## Linked Issue #1564
Sorry, I seem to be a nag... 😞

I'm not sure at what point it was, but the latest few `beta` releases (and current `2.0` release 🎉) lost the ability to fully alias React.

Even with a `next.config.js` fully configured for aliasing React to Preact or Inferno, the `react` and `react-dom`still need to be installed, or else an error is thrown instantly. Not all that reassuring to begin with.

After installing those two, the final bundle (`.next/commons.js` in beta, `.next/app.js` in 2.0) is over 100kb. I recognize this to be larger than what the `using-{preact|inferno}` examples produced in the past. 

So, suspiciously, I combed through the output code and, sure enough, `preact`, `preact-compat` **and** `react` are all there.

I tested with Preact, but Inferno would operate exactly the same. 

For combing, search for `expected a ReactNode`.  Neither of the "compat" packages include this error message.

## Diff (first 3000 chars)
diff --git a/asset.js b/asset.js
new file mode 100644
index 000000000000..fd0bd5dbb15e
--- /dev/null
+++ b/asset.js
@@ -0,0 +1 @@
+module.exports = require('./dist/lib/asset')
diff --git a/bin/next-dev b/bin/next-dev
index bfdfc29c2780..edf2255b85ba 100755
--- a/bin/next-dev
+++ b/bin/next-dev
@@ -1,11 +1,9 @@
 #!/usr/bin/env node
-import 'source-map-support/register'
 import { resolve, join } from 'path'
 import parseArgs from 'minimist'
 import { existsSync, readFileSync } from 'fs'
 import Server from '../server'
 import { printAndExit } from '../lib/utils'
-import pkgUp from 'pkg-up'
 
 const argv = parseArgs(process.argv.slice(2), {
   alias: {
@@ -64,7 +62,7 @@ srv.start(argv.port, argv.hostname)
 .catch((err) => {
   if (err.code === 'EADDRINUSE') {
     let errorMessage = `Port ${argv.port} is already in use.`
-    const pkgAppPath = pkgUp.sync('.')
+    const pkgAppPath = require('pkg-up').sync('.')
     const appPackage = JSON.parse(readFileSync(pkgAppPath, 'utf8'))
     const nextScript = Object.entries(appPackage.scripts).find(scriptLine => scriptLine[1] === 'next')
     if (nextScript) errorMessage += `\nUse \`npm run ${nextScript[0]} -- -p <some other port>\`.`
diff --git a/client/index.js b/client/index.js
index 0283d98197fd..78d953e5ae28 100644
--- a/client/index.js
+++ b/client/index.js
@@ -6,6 +6,7 @@ import EventEmitter from '../lib/EventEmitter'
 import App from '../lib/app'
 import { loadGetInitialProps, getURL } from '../lib/utils'
 import PageLoader from '../lib/page-loader'
+import * as asset from '../lib/asset'
 
 // Polyfill Promise globally
 // This is needed because Webpack2's dynamic loading(common chunks) code
@@ -29,6 +30,9 @@ const {
   location
 } = window
 
+// With this, static assets will work across zones
+asset.setAssetPrefix(assetPrefix)
+
 const asPath = getURL()
 
 const pageLoader = new PageLoader(buildId, assetPrefix)
@@ -93,10 +97,7 @@ export default async ({ ErrorDebugComponent: passedDebugComponent, stripAnsi: pa
 }
 
 export async function render (props) {
-  // There are some errors we should ignore.
-  // Next.js rendering logic knows how to handle them.
-  // These are specially 404 errors
-  if (props.err && !props.err.ignore) {
+  if (props.err) {
     await renderError(props.err)
     return
   }
@@ -159,7 +160,8 @@ async function doRender ({ Component, props, hash, err, emitter: emitterProp = e
 
 let isInitialRender = true
 function renderReactElement (reactEl, domEl) {
-  if (isInitialRender) {
+  // The check for `.hydrate` is there to support React alternatives like preact
+  if (isInitialRender && typeof ReactDOM.hydrate === 'function') {
     ReactDOM.hydrate(reactEl, domEl)
     isInitialRender = false
   } else {
diff --git a/client/next-dev.js b/client/next-dev.js
index ef771c32c615..7f5e13e0005f 100644
--- a/client/next-dev.js
+++ b/client/next-dev.js
@@ -1,10 +1,11 @@
-import 'react-hot-loader/patch'
 import stripAnsi from 'strip-ansi'
 import initNext, * as next from './'
 import E