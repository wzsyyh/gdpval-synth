# PR description text from the author regarding chardet 4


# Seed Material: psf/requests#5688: Upgrade to chardet 4.x
Source: github_issue_pr
Identifier: pr:psf/requests#5688

Repository: psf/requests
PR Number: #5688
PR Title: Upgrade to chardet 4.x
Merged At: 2020-12-14T17:29:11Z
Changed Files: 2
Additions: +3, Deletions: -5

## PR Description
I just released [chardet 4.0.0](https://github.com/chardet/chardet/releases/tag/4.0.0) today, and it's faster and fully backward compatible with chardet 3.x (as long as you aren't mucking around in the models it uses under-the-hood directly). The next major release will be Python 3.6+, but seeing as it took me three years to put out this one, that's unlikely to be soon.

## Diff (first 3000 chars)
diff --git a/requests/__init__.py b/requests/__init__.py
index c00f556bbc..f8f94295f9 100644
--- a/requests/__init__.py
+++ b/requests/__init__.py
@@ -65,10 +65,8 @@ def check_compatibility(urllib3_version, chardet_version):
     # Check chardet for compatibility.
     major, minor, patch = chardet_version.split('.')[:3]
     major, minor, patch = int(major), int(minor), int(patch)
-    # chardet >= 3.0.2, < 3.1.0
-    assert major == 3
-    assert minor < 1
-    assert patch >= 2
+    # chardet >= 3.0.2, < 5.0.0
+    assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
 
 
 def _check_cryptography(cryptography_version):
diff --git a/setup.py b/setup.py
index e714bfa441..7ba4b2a25f 100755
--- a/setup.py
+++ b/setup.py
@@ -42,7 +42,7 @@ def run_tests(self):
 packages = ['requests']
 
 requires = [
-    'chardet>=3.0.2,<4',
+    'chardet>=3.0.2,<5',
     'idna>=2.5,<3',
     'urllib3>=1.21.1,<1.27',
     'certifi>=2017.4.17'
