# Linked Issue #593


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


## Diff
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
-        else:
-            self.blueprints[blueprint.name] = blueprint
-            first_registration = True
-
-        blueprint.register(self, options, first_registration)
+        blueprint.register(self, options)
 
     def iter_blueprints(self):
         """Iterates over all blueprints by the order they were registered.
@@ -1235,22 +1221,18 @@ def _find_error_handler(self, e):
         """
         exc_class, code = self._get_exc_class_and_code(type(e))
 
-        for name, c in (
-            (request.blueprint, code),
-            (None, code),
-            (request.blueprint, None),
-            (None, None),
-        ):
-            handler_map = self.error_handler_spec[name][c]
+        for c in [code, None]:
+            for name in chain(self._request_blueprints(), [None]):
+                handler_map = self.error_handler_spec[name][c]
 
-            if not handler_map:
-                continue
+                if not handler_map:
+                    continue
 
-            for cls in exc_class.__mro__:
-                handler = handler_map.get(cls)
+                for cls in exc_class.__mro__:
+                    handler = handler_map.get(cls)
 
-                if handler is not None:
-                    return handler
+                    if handler is not None:
+                        return handler
 
     def handle_http_exception(self, e):
         """Handles an HTTP exception.  By default this will invoke the
@@ -1749,17 +1731,17 @@ def preprocess_request(self):
         further request handling is stopped.
         """
 
-        bp = _request_ctx_stack.top.request.blueprint
-
         funcs = self.url_value_preprocessors[None]
-        if bp is not None and bp in self.url_value_preprocessors:
-            funcs = chain(funcs, self.url_value_preprocessors[bp])
+        for bp in self._request_blueprints():
+            if bp in self.url_value_preprocessors:
+                funcs = chain(funcs, self.url_value_preprocessors[bp])
         for func in funcs:
             func(request.endpoint, request.view_args)
 
         funcs = self.before_request_funcs[None]
-        if bp is not None and bp in self.before_request_funcs:
-            funcs = chain(funcs, self.before_request_funcs[bp])
+        for bp in self._request_blueprints():
+            if bp in self.before_request_funcs:
+                funcs = chain(funcs, self.before_request_funcs[bp])
         for func in funcs:
             rv = func()
             if rv is not None:
@@ -1779,10 +1761,10 @@ def process_response(self, response):
                  instance of :attr:`response_class`.
         """
         ctx = _request_ctx_stack.top
-        bp = ctx.request.blueprint
         funcs = ctx._after_request_functions
-        if bp is not None and bp in self.after_request_funcs:
-            funcs = chain(funcs, reversed(self.after_request_funcs[bp]))
+        for bp in self._request_blueprints():
+            if bp in self.after_request_funcs:
+                funcs = chain(funcs, reversed(self.after_request_funcs[bp]))
         if None in self.after_request_funcs:
             funcs = chain(funcs, reversed(self.after_request_funcs[None]))
         for handler in funcs:
@@ -1815,9 +1797,9 @@ def do_teardown_request(self, exc=_sentinel):
         if exc is _sentinel:
             exc = sys.exc_info()[1]
         funcs = reversed(self.teardown_request_funcs[None])
-        bp = _request_ctx_stack.top.request.blueprint
-        if bp is not None and bp in self.teardown_request_funcs:
-            funcs = chain(funcs, reversed(self.teardown_request_funcs[bp]))
+        for bp in self._request_blueprints():
+            if bp in self.teardown_request_funcs:
+                funcs = chain(funcs, reversed(self.teardown_request_funcs[bp]))
         for func in funcs:
             func(exc)
         request_tearing_down.send(self, exc=exc)
@@ -1985,3 +1967,9 @@ def __call__(self, environ, start_response):
         wrapped to apply middleware.
         """
         return self.wsgi_app(environ, start_response)
+
+    def _request_blueprints(self):
+        if _request_ctx_stack.top.request.blueprint is None:
+            return []
+        else:
+            return reversed(_request_ctx_stack.top.request.blueprint.split("."))
diff --git a/src/flask/blueprints.py b/src/flask/blueprints.py
index d769cd58e3..92345cf2ba 100644
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@ -45,6 +45,8 @@ def __init__(self, blueprint, app, options, first_registration):
         #: blueprint.
         self.url_prefix = url_prefix
 
+        self.name_prefix = self.options.get("name_prefix", "")
+
         #: A dictionary with URL defaults that is added to each and every
         #: URL that was defined with the blueprint.
         self.url_defaults = dict(self.blueprint.url_values_defaults)
@@ -68,7 +70,7 @@ def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
             defaults = dict(defaults, **options.pop("defaults"))
         self.app.add_url_rule(
             rule,
-            f"{self.blueprint.name}.{endpoint}",
+            f"{self.name_prefix}{self.blueprint.name}.{endpoint}",
             view_func,
             defaults=defaults,
             **options,
@@ -168,6 +170,7 @@ def __init__(
 
         self.url_values_defaults = url_defaults
         self.cli_group = cli_group
+        self._blueprints = []
 
     def _is_setup_finished(self):
         return self.warn_on_modifications and self._got_registered_once
@@ -210,7 +213,16 @@ def make_setup_state(self, app, options, first_registration=False):
         """
         return BlueprintSetupState(self, app, options, first_registration)
 
-    def register(self, app, options, first_registration=False):
+    def register_blueprint(self, blueprint, **options):
+        """Register a :class:`~flask.Blueprint` on this blueprint. Keyword
+        arguments passed to this method will override the defaults set
+        on the blueprint.
+
+        .. versionadded:: 2.0
+        """
+        self._blueprints.append((blueprint, options))
+
+    def register(self, app, options):
         """Called by :meth:`Flask.register_blueprint` to register all
         views and callbacks registered on the blueprint with the
         application. Creates a :class:`.BlueprintSetupState` and calls
@@ -223,6 +235,20 @@ def register(self, app, options, first_registration=False):
         :param first_registration: Whether this is the first time this
             blueprint has been registered on the application.
         """
+        first_registration = False
+
+        if self.name in app.blueprints:
+            assert app.blueprints[self.name] is self, (
+                "A name collision occurred between blueprints"
+                f" {self!r} and {app.blueprints[self.name]!r}."
+                f" Both share the same name {self.name!r}."
+                f" Blueprints that are created on the fly need unique"
+                f" names."
+            )
+        else:
+            app.blueprints[self.name] = self
+            first_registration = True
+
         self._got_registered_once = True
         state = self.make_setup_state(app, options, first_registration)
 
@@ -278,19 +304,28 @@ def extend(bp_dict, parent_dict, ensure_sync=False):
         for deferred in self.deferred_functions:
             deferred(state)
 
-        if not self.cli.commands:
-            return
-
         cli_resolved_group = options.get("cli_group", self.cli_group)
 
-        if cli_resolved_group is None:
-            app.cli.commands.update(self.cli.commands)
-        elif cli_resolved_group is _sentinel:
-            self.cli.name = self.name
-            app.cli.add_command(self.cli)
-        else:
-            self.cli.name = cli_resolved_group
-            app.cli.add_command(self.cli)
+        if self.cli.commands:
+            if cli_resolved_group is None:
+                app.cli.commands.update(self.cli.commands)
+            elif cli_resolved_group is _sentinel:
+                self.cli.name = self.name
+                app.cli.add_command(self.cli)
+            else:
+                self.cli.name = cli_resolved_group
+                app.cli.add_command(self.cli)
+
+        for blueprint, bp_options in self._blueprints:
+            url_prefix = options.get("url_prefix", "")
+            if "url_prefix" in bp_options:
+                url_prefix = (
+                    url_prefix.rstrip("/") + "/" + bp_options["url_prefix"].lstrip("/")
+                )
+
+            bp_options["url_prefix"] = url_prefix
+            bp_options["name_prefix"] = options.get("name_prefix", "") + self.name + "."
+            blueprint.register(app, bp_options)
 
     def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
         """Like :meth:`Flask.add_url_rule` but for a blueprint.  The endpoint for
diff --git a/tests/test_blueprints.py b/tests/test_blueprints.py
index 903c7421bf..b986ca022d 100644
--- a/tests/test_blueprints.py
+++ b/tests/test_blueprints.py
@@ -850,3 +850,52 @@ def about():
 
     assert client.get("/de/").data == b"/de/about"
     assert client.get("/de/about").data == b"/de/"
+
+
+def test_nested_blueprint(app, client):
+    parent = flask.Blueprint("parent", __name__)
+    child = flask.Blueprint("child", __name__)
+    grandchild = flask.Blueprint("grandchild", __name__)
+
+    @parent.errorhandler(403)
+    def forbidden(e):
+        return "Parent no", 403
+
+    @parent.route("/")
+    def parent_index():
+        return "Parent yes"
+
+    @parent.route("/no")
+    def parent_no():
+        flask.abort(403)
+
+    @child.route("/")
+    def child_index():
+        return "Child yes"
+
+    @child.route("/no")
+    def child_no():
+        flask.abort(403)
+
+    @grandchild.errorhandler(403)
+    def grandchild_forbidden(e):
+        return "Grandchild no", 403
+
+    @grandchild.route("/")
+    def grandchild_index():
+        return "Grandchild yes"
+
+    @grandchild.route("/no")
+    def grandchild_no():
+        flask.abort(403)
+
+    child.register_blueprint(grandchild, url_prefix="/grandchild")
+    parent.register_blueprint(child, url_prefix="/child")
+    app.register_blueprint(parent, url_prefix="/parent")
+
+    assert client.get("/parent/").data == b"Parent yes"
+    assert client.get("/parent/child/").data == b"Child yes"
+    assert client.get("/parent/child/grandchild/").data == b"Grandchild yes"
+    assert client.get("/parent/no").data == b"Parent no"
+    assert client.get("/parent/child/no").data == b"Parent no"
+    assert client.get("/parent/child/grandchild/no").data == b"Grandchild no"
