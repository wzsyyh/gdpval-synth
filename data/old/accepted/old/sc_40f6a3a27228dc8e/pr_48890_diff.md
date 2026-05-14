**Repository:** nodejs/node

**PR:** #48890

## Diff Excerpt

```diff
diff --git a/doc/api/cli.md b/doc/api/cli.md
index b2d860ba500166..6cd0a795c216e7 100644
--- a/doc/api/cli.md
+++ b/doc/api/cli.md
@@ -984,6 +984,41 @@ surface on other platforms, but the performance impact may be severe.
 This flag is inherited from V8 and is subject to change upstream. It may
 disappear in a non-semver-major release.
 
+### `--env-file=config`
+
+> Stability: 1.1 - Active development
+
+<!-- YAML
+added: REPLACEME
+-->
+
+Loads environment variables from a file relative to the current directory,
+making them available to applications on `process.env`. The [environment
+variables which configure Node.js][environment_variables], such as `NODE_OPTIONS`,
+are parsed and applied. If the same variable is defined in the environment and
+in the file, the value from the environment takes precedence.
+
+The format of the file should be one line per key-value pair of environment
+variable name and value separated by `=`:
+
+```text
+PORT=3000
+```
+
+Any text after a `#` is treated as a comment:
+
+```text
+# This is a comment
+PORT=3000 # This is also a comment
+```
+
+Values can start and end with the following quotes: `\`, `"` or `'`.
+They are omitted from the values.
+
+```text
+USERNAME="nodejs" # will result in `nodejs` as the value.
+```
+
 ### `--max-http-header-size=size`
 
 <!-- YAML
@@ -2647,6 +2682,7 @@ done
 [debugger]: debugger.md
 [debugging security implications]: https://nodejs.org/en/docs/guides/debugging-getting-started/#security-implications
 [emit_warning]: process.md#processemitwarningwarning-options
```
