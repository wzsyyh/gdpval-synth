# docs/async-await


# Seed Material: pallets/flask#3412: Add `async` support
Source: github_issue_pr
Identifier: pr:pallets/flask#3412

Repository: pallets/flask
PR Number: #3412
PR Title: Add `async` support
Merged At: 2021-04-07T12:32:20Z
Changed Files: 13
Additions: +380, Deletions: -23

## PR Description
This will require Python 2 support to be dropped, which as I understand isn't likely to happen till 2020. Which is a bonus as it gives time to consider this change and the implications of it. (I also need to spend some time cleaning up this implementation, yet it serves as a proof of concept).

I've written [this blog post](https://pgjones.dev/blog/flask-async-quart-sync-2019/) to add some extra context, but I see a key aspect to this change is that whilst it adds `async` support it does not do so throughout and specifically does not support ASGI. This means that Flask is constrained (when using `async`) to have worse performance than the ASGI equivalents. This is necessary as I don't think Flask can be `async` throughout (or support ASGI) whilst being backwards compatible. Yet this change is good overall, in that users would be able to add some async usage to their existing codebases. I would also like to note that they can switch to Quart if their usage becomes mostly async. 

This allows for async functions to be passed to the Flask class
instance, for example as a view function,

    @app.route("/")
    async def index():
        return "Async hello"

this comes with a cost though of poorer performance than using the
sync equivalent.


## Diff (first 3000 chars)
diff --git a/CHANGES.rst b/CHANGES.rst
index d98d91fe60..280a2dd5a5 100644
--- a/CHANGES.rst
+++ b/CHANGES.rst
@@ -67,6 +67,8 @@ Unreleased
 -   Add route decorators for common HTTP methods. For example,
     ``@app.post("/login")`` is a shortcut for
     ``@app.route("/login", methods=["POST"])``. :pr:`3907`
+-   Support async views, error handlers, before and after request, and
+    teardown functions. :pr:`3412`
 
 
 Version 1.1.2
diff --git a/docs/async-await.rst b/docs/async-await.rst
new file mode 100644
index 0000000000..c8981f886a
--- /dev/null
+++ b/docs/async-await.rst
@@ -0,0 +1,81 @@
+.. _async_await:
+
+Using ``async`` and ``await``
+=============================
+
+.. versionadded:: 2.0
+
+Routes, error handlers, before request, after request, and teardown
+functions can all be coroutine functions if Flask is installed with the
+``async`` extra (``pip install flask[async]``). This allows views to be
+defined with ``async def`` and use ``await``.
+
+.. code-block:: python
+
+    @app.route("/get-data")
+    async def get_data():
+        data = await async_db_query(...)
+        return jsonify(data)
+
+
+Performance
+-----------
+
+Async functions require an event loop to run. Flask, as a WSGI
+application, uses one worker to handle one request/response cycle.
+When a request comes in to an async view, Flask will start an event loop
+in a thread, run the view function there, then return the result.
+
+Each request still ties up one worker, even for async views. The upside
+is that you can run async code within a view, for example to make
+multiple concurrent database queries, HTTP requests to an external API,
+etc. However, the number of requests your application can handle at one
+time will remain the same.
+
+**Async is not inherently faster than sync code.** Async is beneficial
+when performing concurrent IO-bound tasks, but will probably not improve
+CPU-bound tasks. Traditional Flask views will still be appropriate for
+most use cases, but Flask's async support enables writing and using
+code that wasn't possible natively before.
+
+
+When to use Quart instead
+-------------------------
+
+Flask's async support is less performant than async-first frameworks due
+to the way it is implemented. If you have a mainly async codebase it
+would make sense to consider `Quart`_. Quart is a reimplementation of
+Flask based on the `ASGI`_ standard instead of WSGI. This allows it to
+handle many concurrent requests, long running requests, and websockets
+without requiring individual worker processes or threads.
+
+It has also already been possible to run Flask with Gevent or Eventlet
+to get many of the benefits of async request handling. These libraries
+patch low-level Python functions to accomplish this, whereas ``async``/
+``await`` and ASGI use standard, modern Python capabilities. Deciding
+whether you should use Flask, Quart, or something else is ultimately up
+to understanding the specific needs of your project.
+
+.. _Quart: https:/