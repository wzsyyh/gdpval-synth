# Issue #593 excerpt describing the desired nested blueprint behavior


# Seed Material: pallets/flask#3923: Nested blueprints
Source: github_issue_pr
Identifier: pr:pallets/flask#3923

Repository: pallets/flask
PR Number: #3923
PR Title: Nested blueprints
Merged At: 2021-04-14T16:30:48Z
Changed Files: 5
Additions: +154, Deletions: -56

## PR Description
This allows blueprints to be nested within blueprints via a new
Blueprint.register_blueprint method. This should provide a use case
that has been desired for the past ~10 years.

This works by setting the endpoint name to be the blueprint names,
from parent to child delimeted by "." and then iterating over the
blueprint names in reverse order in the app (from most specific to
most general). This means that the expectation of nesting a blueprint
within a nested blueprint is met.

- fixes #593
- fixes #1548

Checklist:

- [x] Add tests that demonstrate the correct behavior of the change. Tests should fail without the change.
- [x] Add or update relevant docs, in the docs folder and in code.
- [x] Add an entry in `CHANGES.rst` summarizing the change and linking to the issue.
- [x] Add `.. versionchanged::` entries in any relevant code docs.
- [x] Run `pre-commit` hooks and fix any issues.
- [x] Run `pytest` and `tox`, no tests failed.


## Linked Issue #593
I'd like to be able to register "sub-blueprints" using `Blueprint.register_blueprint(*args, **kwargs)`. This would register the nested blueprints with an app when the "parent" is registered with it. All parameters are preserved, other than `url_prefix`, which is handled similarly to in `add_url_rule`. A naíve implementation could look like this:

``` python
class Blueprint(object):
    ...

    def register_blueprint(self, blueprint, **options):
        def deferred(state):
            url_prefix = options.get('url_prefix')
            if url_prefix is None:
                url_prefix = blueprint.url_prefix
            if 'url_prefix' in options:
                del options['url_prefix']

            state.app.register_blueprint(blueprint, url_prefix, **options)
        self.record(deferred)
```


## Diff (first 3000 chars)
diff --git a/CHANGES.rst b/CHANGES.rst
index 280a2dd5a5..8c615d5fb8 100644
--- a/CHANGES.rst
+++ b/CHANGES.rst
@@ -69,6 +69,7 @@ Unreleased
     ``@app.route("/login", methods=["POST"])``. :pr:`3907`
 -   Support async views, error handlers, before and after request, and
     teardown functions. :pr:`3412`
+-   Support nesting blueprints. :issue:`593, 1548`, :pr:`3923`
 
 
 Version 1.1.2
diff --git a/docs/blueprints.rst b/docs/blueprints.rst
index 3bc11893e4..6e8217abc9 100644
--- a/docs/blueprints.rst
+++ b/docs/blueprints.rst
@@ -120,6 +120,31 @@ On top of that you can register blueprints multiple times though not every
 blueprint might respond properly to that.  In fact it depends on how the
 blueprint is implemented if it can be mounted more than once.
 
+Nesting Blueprints
+------------------
+
+It is possible to register a blueprint on another blueprint.
+
+.. code-block:: python
+
+    parent = Blueprint("parent", __name__, url_prefix="/parent")
+    child = Blueprint("child", __name__, url_prefix="/child)
+    parent.register_blueprint(child)
+    app.register_blueprint(parent)
+
+The child blueprint will gain the parent's name as a prefix to its
+name, and child URLs will be prefixed with the parent's URL prefix.
+
+.. code-block:: python
+
+    url_for('parent.child.create')
+    /parent/child/create
+
+Blueprint-specific before request functions, etc. registered with the
+parent will trigger for the child. If a child does not have an error
+handler that can handle a given exception, the parent's will be tried.
+
+
 Blueprint Resources
 -------------------
 
diff --git a/src/flask/app.py b/src/flask/app.py
index 484881f45c..d6f15e8ce1 100644
--- a/src/flask/app.py
+++ b/src/flask/app.py
@@ -723,9 +723,9 @@ def update_template_context(self, context):
         funcs = self.template_context_processors[None]
         reqctx = _request_ctx_stack.top
         if reqctx is not None:
-            bp = reqctx.request.blueprint
-            if bp is not None and bp in self.template_context_processors:
-                funcs = chain(funcs, self.template_context_processors[bp])
+            for bp in self._request_blueprints():
+                if bp in self.template_context_processors:
+                    funcs = chain(funcs, self.template_context_processors[bp])
         orig_ctx = context.copy()
         for func in funcs:
             context.update(func())
@@ -987,21 +987,7 @@ def register_blueprint(self, blueprint, **options):
 
         .. versionadded:: 0.7
         """
-        first_registration = False
-
-        if blueprint.name in self.blueprints:
-            assert self.blueprints[blueprint.name] is blueprint, (
-                "A name collision occurred between blueprints"
-                f" {blueprint!r} and {self.blueprints[blueprint.name]!r}."
-                f" Both share the same name {blueprint.name!r}."
-                f" Blueprints that are created on the fly need unique"
-                f" names."
-            )
-   