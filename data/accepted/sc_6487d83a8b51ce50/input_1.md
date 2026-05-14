# PR description with follow-up checklist and missing features list


# Seed Material: nodejs/node#48890: src: add built-in `.env` file support
Source: github_issue_pr
Identifier: pr:nodejs/node#48890

Repository: nodejs/node
PR Number: #48890
PR Title: src: add built-in `.env` file support
Merged At: 2023-08-17T14:08:05Z
Changed Files: 19
Additions: +508, Deletions: -16

## PR Description
> Follow-ups in https://github.com/nodejs/node/issues/49148

## Follow-up from the comments:

@cjihrig:

- [x] Using a custom path instead of .env file in the current working directory.
- [ ] The option to augment vs. overwrite the existing process.env with the values from the .env file. If we support augmenting, what happens on conflict (overwrite, don’t overwrite, throw, etc.)?
- [ ] ~~Programmatic API~~.
- [ ] ~~The ability to put the loaded values in an object other than process.env.~~
- [ ] ~~Multiline values.~~
- [x] Comments in the .env files.
- [ ] ~~Variable expansion.~~

@KhafraDev 

- [x] regarding testing and validation, you can take dotenv’s test suite https://github.com/motdotla/dotenv/tree/master/tests

@GeoffreyBooth 

- [x] the flag should be –env-file [path-to-file] so like –env-file .env or –env-file .env.development or whatever.
- [x] fix and support windows newline character
- [x] Support `NODE_OPTIONS`

## Missing features

The following features are not implemented in this current context. And can be implemented in a separate PR.

- Respect newline character in values with `"`
- Multiline values
- Variable expansion
- Incremental env support (.env.development overrides .env on NODE_ENV=development)

Ref: https://github.com/orgs/nodejs/discussions/44975


## Diff (first 3000 chars)
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
+[environment_variables]: #environment-variables
 [filtering tests by name]: test.md#filtering-tests-by-name
 [jitless]: https://v8.dev/blog/jitless
 [libuv threadpool documentation]: https://docs.libuv.org/en/latest/threadpool.html
diff --git a/node.gyp b/node.gyp
index db6d7455bf1dbd..f145bcaf398005 100644
--- a/node.gyp
+++ b/node.gyp
@@ -100,6 +100,7 @@
       'src/node_contextify.cc',
       'src/node_credentials.cc',
       'src/node_dir.cc',
+      'src/node_dotenv.cc',
       'src/node_env_var.cc',
       'src/node_errors.cc',
       'src/node_external_reference.cc',
@@ -214,6 +215,7 @@
       'src/node_context_data.h',
       'src/node_contextify.h',
       'src/node_dir.h',
+      'src/node_dotenv.h',
       'src/node_errors.h',
       'src/node_exit_code.h',
       'src/node_external_reference.h',
diff --git a/src/env.cc b/src/env.cc
index 6b0aba44a36eba..7e3d3aca2d5f96 100644
--- a/src/env.cc
+++ b/src/env.cc
@@ -683,7 +683,7 @@ void Environment::TryLoadAddon(
   }
 }
 
-std::string Environment::GetCwd() {
+std::string Environment::GetCwd(const std::string& exec_path) {
   char cwd[PATH_MAX_BYTES];
   size_t size = PATH_MAX_BYTES;
   const int err = uv_cwd(cwd, &size);
@@ -695,7 +695,6 @@ std::string Environment::GetCwd() {
 
   // This can fail if the cwd is deleted. In that case, fall back to
   // exec_path.
-  const std::string& exec_path = exec_path_;
   return exec_path.substr(0, exec_path.find_last_of