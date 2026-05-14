# PR #96878 diff and description from kubernetes/kubernetes repository


# Seed Material: kubernetes/kubernetes#96878: Enable kubectl-get to strip managed fields
Source: github_issue_pr
Identifier: pr:kubernetes/kubernetes#96878

Repository: kubernetes/kubernetes
PR Number: #96878
PR Title: Enable kubectl-get to strip managed fields
Merged At: 2021-02-17T00:39:06Z
Changed Files: 8
Additions: +183, Deletions: -9

## PR Description
**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

Enable `kubectl get` to strip managed fields to make the output less verbose.

**Which issue(s) this PR fixes**:
<!--
*Automatically closes linked issue when PR is merged.
Usage: `Fixes #<issue number>`, or `Fixes (paste link of issue)`.
_If PR is about `failing-tests or flakes`, please post the related issues/tests in a comment and do not use `Fixes`_*
-->
xref #90066

**Special notes for your reviewer**:

**Does this PR introduce a user-facing change?**:
<!--
If no, just write "NONE" in the release-note block below.
If yes, a release note is required:
Enter your extended release note in the block below. If the PR requires additional action from users switching to the new release, include the string "action required".

For more information on release notes see: https://git.k8s.io/community/contributors/guide/release-notes.md
-->
```release-note
kubectl: `kubectl get` will omit managed fields by default now. Users could set `--show-managed-fields` to true to show managedFields when the output format is either `json` or `yaml`.
```

**Additional documentation e.g., KEPs (Kubernetes Enhancement Proposals), usage docs, etc.**:

<!--
This section can be blank if this pull request does not require a release note.

When adding links which point to resources within git repositories, like
KEPs or supporting documentation, please reference a specific commit and avoid
linking directly to the master branch. This ensures that links reference a
specific point in time, rather than a document that may change over time.

See here for guidance on getting permanent links to files: https://help.github.com/en/articles/getting-permanent-links-to-files

Please use the following format for linking documentation:
- [KEP]: <link>
- [Usage]: <link>
- [Other doc]: <link>
-->
```docs

```


## Diff (first 3000 chars)
diff --git a/staging/src/k8s.io/cli-runtime/pkg/genericclioptions/json_yaml_flags.go b/staging/src/k8s.io/cli-runtime/pkg/genericclioptions/json_yaml_flags.go
index e207fd8742b7b..cd1d039f853ae 100644
--- a/staging/src/k8s.io/cli-runtime/pkg/genericclioptions/json_yaml_flags.go
+++ b/staging/src/k8s.io/cli-runtime/pkg/genericclioptions/json_yaml_flags.go
@@ -36,6 +36,7 @@ func (f *JSONYamlPrintFlags) AllowedFormats() []string {
 // Given the following flag values, a printer can be requested that knows
 // how to handle printing based on these values.
 type JSONYamlPrintFlags struct {
+	showManagedFields bool
 }
 
 // ToPrinter receives an outputFormat and returns a printer capable of
@@ -55,12 +56,17 @@ func (f *JSONYamlPrintFlags) ToPrinter(outputFormat string) (printers.ResourcePr
 		return nil, NoCompatiblePrinterError{OutputFormat: &outputFormat, AllowedFormats: f.AllowedFormats()}
 	}
 
+	if !f.showManagedFields {
+		printer = &printers.OmitManagedFieldsPrinter{Delegate: printer}
+	}
 	return printer, nil
 }
 
 // AddFlags receives a *cobra.Command reference and binds
 // flags related to JSON or Yaml printing to it
-func (f *JSONYamlPrintFlags) AddFlags(c *cobra.Command) {}
+func (f *JSONYamlPrintFlags) AddFlags(c *cobra.Command) {
+	c.Flags().BoolVar(&f.showManagedFields, "show-managed-fields", f.showManagedFields, "If true, keep the managedFields when printing objects in JSON or YAML format.")
+}
 
 // NewJSONYamlPrintFlags returns flags associated with
 // yaml or json printing, with default values set.
diff --git a/staging/src/k8s.io/cli-runtime/pkg/printers/BUILD b/staging/src/k8s.io/cli-runtime/pkg/printers/BUILD
index 16d012c12e1d3..1a72354e1543b 100644
--- a/staging/src/k8s.io/cli-runtime/pkg/printers/BUILD
+++ b/staging/src/k8s.io/cli-runtime/pkg/printers/BUILD
@@ -8,6 +8,7 @@ go_library(
         "interface.go",
         "json.go",
         "jsonpath.go",
+        "managedfields.go",
         "name.go",
         "sourcechecker.go",
         "tableprinter.go",
@@ -39,6 +40,7 @@ go_test(
     srcs = [
         "json_test.go",
         "jsonpath_test.go",
+        "managedfields_test.go",
         "sourcechecker_test.go",
         "tableprinter_test.go",
         "template_test.go",
@@ -54,6 +56,7 @@ go_test(
         "//staging/src/k8s.io/apimachinery/pkg/util/json:go_default_library",
         "//staging/src/k8s.io/apimachinery/pkg/util/sets:go_default_library",
         "//staging/src/k8s.io/client-go/kubernetes/scheme:go_default_library",
+        "//vendor/github.com/stretchr/testify/require:go_default_library",
         "//vendor/sigs.k8s.io/yaml:go_default_library",
     ],
 )
diff --git a/staging/src/k8s.io/cli-runtime/pkg/printers/managedfields.go b/staging/src/k8s.io/cli-runtime/pkg/printers/managedfields.go
new file mode 100644
index 0000000000000..cab54d0584de8
--- /dev/null
+++ b/staging/src/k8s.io/cli-runtime/pkg/printers/managedfields.go
@@ -0,0 +1,59 @@
+/*
+Copyright 2021 The Kubernetes Authors.
+
+Licensed under the