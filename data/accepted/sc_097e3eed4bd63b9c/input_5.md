# mkdocs


# Seed Material: pydantic/pydantic#3099: Added support for Rich Repr protocol
Source: github_issue_pr
Identifier: pr:pydantic/pydantic#3099

Repository: pydantic/pydantic
PR Number: #3099
PR Title: Added support for Rich Repr protocol
Merged At: 2022-08-04T13:47:42Z
Changed Files: 6
Additions: +49, Deletions: -0

## PR Description
## Change Summary

Adds support for the [Rich Repr Protocol](https://rich.readthedocs.io/en/latest/pretty.html#rich-repr-protocol) so that Rich can pretty print PyDantic objects.

<img width="838" alt="Screen Shot 2021-08-15 at 14 13 35" src="https://user-images.githubusercontent.com/554369/129479888-8f001b49-2d0b-47a5-a7c7-d7b913fb0e40.png">

Note that Rich does not need to be added a dependency. If PyDantic objects are printed with Rich you will get the formatting above, otherwise there are no changes.

## Related issue number

<!-- Are there any issues opened that will be resolved by merging this change? -->

## Checklist

* [x] Unit tests for the changes exist
* [x] Tests pass on CI and coverage remains at 100%
* [x] Documentation reflects the changes where applicable
* [x] `changes/<pull request or issue id>-<github username>.md` file added describing change
  (see [changes/README.md](https://github.com/samuelcolvin/pydantic/blob/master/changes/README.md) for details)
* [x] My PR is ready to review, **please add a comment including the phrase "please review" to assign reviewers**


## Diff (first 3000 chars)
diff --git a/changes/3099-willmcgugan.md b/changes/3099-willmcgugan.md
new file mode 100644
index 00000000000..c4380b11e9f
--- /dev/null
+++ b/changes/3099-willmcgugan.md
@@ -0,0 +1 @@
+Adds a `__rich_repr__` method to `Representation` class which enables pretty printing with [Rich](https://github.com/willmcgugan/rich)
\ No newline at end of file
diff --git a/docs/usage/rich.md b/docs/usage/rich.md
new file mode 100644
index 00000000000..8d601d5c754
--- /dev/null
+++ b/docs/usage/rich.md
@@ -0,0 +1,5 @@
+Pydantic models may be printed with the [Rich](https://github.com/willmcgugan/rich) library which will add additional formatting and color to the output. Here's an example:
+
+![Printing Pydantic models with Rich](./rich_pydantic.png)
+
+See the Rich documentation on [pretty printing](https://rich.readthedocs.io/en/latest/pretty.html) for more information.
diff --git a/docs/usage/rich_pydantic.png b/docs/usage/rich_pydantic.png
new file mode 100644
index 00000000000..365f7b8e94c
Binary files /dev/null and b/docs/usage/rich_pydantic.png differ
diff --git a/mkdocs.yml b/mkdocs.yml
index 1db3fb7ca84..bc460dedc16 100644
--- a/mkdocs.yml
+++ b/mkdocs.yml
@@ -55,6 +55,7 @@ nav:
   - usage/postponed_annotations.md
   - 'Usage with mypy': usage/mypy.md
   - 'Usage with devtools': usage/devtools.md
+  - 'Usage with rich': usage/rich.md
 - Contributing to pydantic: contributing.md
 - 'Mypy plugin': mypy_plugin.md
 - 'PyCharm plugin': pycharm_plugin.md
diff --git a/pydantic/utils.py b/pydantic/utils.py
index f9c4ec16022..31e74771387 100644
--- a/pydantic/utils.py
+++ b/pydantic/utils.py
@@ -50,6 +50,8 @@
     from .main import BaseModel
     from .typing import AbstractSetIntStr, DictIntStrAny, IntStr, MappingIntStrAny, ReprArgs
 
+    RichReprResult = Iterable[Union[Any, Tuple[Any], Tuple[str, Any], Tuple[str, Any, Any]]]
+
 __all__ = (
     'import_string',
     'sequence_like',
@@ -388,6 +390,14 @@ def __str__(self) -> str:
     def __repr__(self) -> str:
         return f'{self.__repr_name__()}({self.__repr_str__(", ")})'
 
+    def __rich_repr__(self) -> 'RichReprResult':
+        """Get fields for Rich library"""
+        for name, field_repr in self.__repr_args__():
+            if name is None:
+                yield field_repr
+            else:
+                yield name, field_repr
+
 
 class GetterDict(Representation):
     """
diff --git a/tests/test_rich_repr.py b/tests/test_rich_repr.py
new file mode 100644
index 00000000000..ed3015c2a2b
--- /dev/null
+++ b/tests/test_rich_repr.py
@@ -0,0 +1,32 @@
+from datetime import datetime
+from typing import List, Optional
+
+from pydantic import BaseModel
+from pydantic.color import Color
+
+
+class User(BaseModel):
+    id: int
+    name: str = 'John Doe'
+    signup_ts: Optional[datetime] = None
+    friends: List[int] = []
+
+
+def test_rich_repr() -> None:
+    user = User(id=22)
+    rich_repr = list(user.__rich_repr__())
+
+    assert rich_repr == [
+        ('id', 22),
+        ('name', 'John D