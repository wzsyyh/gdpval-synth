# PR description from moby/moby#34263 explaining the --chown flag feature and its supported formats


# Seed Material: moby/moby#34263: Add --chown flag to ADD/COPY commands
Source: github_issue_pr
Identifier: pr:moby/moby#34263

Repository: moby/moby
PR Number: #34263
PR Title: Add --chown flag to ADD/COPY commands
Merged At: 2017-08-28T16:50:45Z
Changed Files: 7
Additions: +293, Deletions: -15

## PR Description
Carry #28499 (which was a carry of #27303)

This adds `--chown` function to the `ADD` and `COPY` commands in `Dockerfile`. The format of the `--chown` flag allows any uid/username and gid/groupname combination separated by a colon, e.g.:
```
--chown=someuser:555
--chown=anyuser:anygroup
--chown=1001:1002
--chown=333:agroupname
```

Lookups (to translate name -> ID integer) will use the `/etc/passwd` and `/etc/group` files found in the container filesystem. Currently if they do not exist, then the `docker build` will fail. This PR probably needs a way to fail gracefully (or ignore failures) on Windows as those containers will not have these files. If only numeric IDs are used, no lookups will be performed.

User namespaces are supported and IDs will be shifted (after translated names to integers) based on the user namespace mappings set in the daemon.

I also think a few more tests are necessary to fully test the behavior, but wanted to get the rebased code available for review initially.

## Diff (first 3000 chars)
diff --git a/builder/dockerfile/copy.go b/builder/dockerfile/copy.go
index c7db943f5c08f..223623ccd6be9 100644
--- a/builder/dockerfile/copy.go
+++ b/builder/dockerfile/copy.go
@@ -56,6 +56,7 @@ type copyInstruction struct {
 	cmdName                 string
 	infos                   []copyInfo
 	dest                    string
+	chownStr                string
 	allowLocalDecompression bool
 }
 
@@ -369,6 +370,7 @@ func downloadSource(output io.Writer, stdout io.Writer, srcURL string) (remote b
 type copyFileOptions struct {
 	decompress bool
 	archiver   *archive.Archiver
+	chownPair  idtools.IDPair
 }
 
 func performCopyForInfo(dest copyInfo, source copyInfo, options copyFileOptions) error {
@@ -388,7 +390,7 @@ func performCopyForInfo(dest copyInfo, source copyInfo, options copyFileOptions)
 		return errors.Wrapf(err, "source path not found")
 	}
 	if src.IsDir() {
-		return copyDirectory(archiver, srcPath, destPath)
+		return copyDirectory(archiver, srcPath, destPath, options.chownPair)
 	}
 	if options.decompress && archive.IsArchivePath(srcPath) && !source.noDecompress {
 		return archiver.UntarPath(srcPath, destPath)
@@ -405,26 +407,28 @@ func performCopyForInfo(dest copyInfo, source copyInfo, options copyFileOptions)
 		// is a symlink
 		destPath = filepath.Join(destPath, filepath.Base(source.path))
 	}
-	return copyFile(archiver, srcPath, destPath)
+	return copyFile(archiver, srcPath, destPath, options.chownPair)
 }
 
-func copyDirectory(archiver *archive.Archiver, source, dest string) error {
+func copyDirectory(archiver *archive.Archiver, source, dest string, chownPair idtools.IDPair) error {
+	destExists, err := isExistingDirectory(dest)
+	if err != nil {
+		return errors.Wrapf(err, "failed to query destination path")
+	}
 	if err := archiver.CopyWithTar(source, dest); err != nil {
 		return errors.Wrapf(err, "failed to copy directory")
 	}
-	return fixPermissions(source, dest, archiver.IDMappings.RootPair())
+	return fixPermissions(source, dest, chownPair, !destExists)
 }
 
-func copyFile(archiver *archive.Archiver, source, dest string) error {
-	rootIDs := archiver.IDMappings.RootPair()
-
-	if err := idtools.MkdirAllAndChownNew(filepath.Dir(dest), 0755, rootIDs); err != nil {
+func copyFile(archiver *archive.Archiver, source, dest string, chownPair idtools.IDPair) error {
+	if err := idtools.MkdirAllAndChownNew(filepath.Dir(dest), 0755, chownPair); err != nil {
 		return errors.Wrapf(err, "failed to create new directory")
 	}
 	if err := archiver.CopyFileWithTar(source, dest); err != nil {
 		return errors.Wrapf(err, "failed to copy file")
 	}
-	return fixPermissions(source, dest, rootIDs)
+	return fixPermissions(source, dest, chownPair, false)
 }
 
 func endsInSlash(path string) bool {
diff --git a/builder/dockerfile/copy_unix.go b/builder/dockerfile/copy_unix.go
index 326d95bb39dfd..a4a5e05235d59 100644
--- a/builder/dockerfile/copy_unix.go
+++ b/builder/dockerfile/copy_unix.go
@@ -9,10 +9,16 @@ import (
 	"github.com/docker/docker/