# Full PR diff for django/django#14843 showing changes to django/db/models/query


# Seed Material: django/django#14843: Fixed #33646 -- Added async-compatible interface to QuerySet.
Source: github_issue_pr
Identifier: pr:django/django#14843

Repository: django/django
PR Number: #14843
PR Title: Fixed #33646 -- Added async-compatible interface to QuerySet.
Merged At: 2022-04-27T06:53:35Z
Changed Files: 9
Additions: +747, Deletions: -22

## PR Description
This adds an async-compatible set of methods and special methods to the `QuerySet` class (and, via the generic pass-through, Managers as well).

Included are:
* Async versions of all methods that do not return a QuerySet themselves, with an `a` prefix: `aiterator`, `aaggregate`, `acount`, `aget`, `acreate`, `abulk_create`, `abulk_update`, `aget_or_create`, `aupdate_or_create`, `aearliest`, `alatest`, `afirst`, `alast`, `ain_bulk`, `aupdate`, `adelete`, `aexists`, `acontains`, `aexplain`. Most are just wrappers around the underlying sync version, though some have a few performance shortcuts added.
* Async iterator ability on the `BaseIterable` that propagates through to all QuerySets as well as the results of `values()`, `values_list()` etc. It's not terribly efficient, but we can improve this progressively once we teach `compiler.results_iter` the wonders of async.
* A new `alist()` utility function for turning async iterables into lists asynchronously, because we do use `list()` quite a bit.

As a nice example, this means you can now write this kind of view:

```
async def myview(request):
    results = []
    async for row in TestModel.objects.filter(good=True):
        results.append(row)

    user = await TestModel.objects.aget(name=Andrew)

    return render(request, "index.html", {"results": results, "user": user})
```

Remaining work:
* [x] Ensure transactions error properly (we'll get these in another pass)
* [x] Tests
* [x] Documentation

## Diff (first 3000 chars)
diff --git a/django/db/models/query.py b/django/db/models/query.py
index 5c78c6e31502..8e9eb78cd489 100644
--- a/django/db/models/query.py
+++ b/django/db/models/query.py
@@ -7,6 +7,8 @@
 import warnings
 from itertools import chain, islice
 
+from asgiref.sync import sync_to_async
+
 import django
 from django.conf import settings
 from django.core import exceptions
@@ -45,6 +47,33 @@ def __init__(
         self.chunked_fetch = chunked_fetch
         self.chunk_size = chunk_size
 
+    async def _async_generator(self):
+        # Generators don't actually start running until the first time you call
+        # next() on them, so make the generator object in the async thread and
+        # then repeatedly dispatch to it in a sync thread.
+        sync_generator = self.__iter__()
+
+        def next_slice(gen):
+            return list(islice(gen, self.chunk_size))
+
+        while True:
+            chunk = await sync_to_async(next_slice)(sync_generator)
+            for item in chunk:
+                yield item
+            if len(chunk) < self.chunk_size:
+                break
+
+    # __aiter__() is a *synchronous* method that has to then return an
+    # *asynchronous* iterator/generator. Thus, nest an async generator inside
+    # it.
+    # This is a generic iterable converter for now, and is going to suffer a
+    # performance penalty on large sets of items due to the cost of crossing
+    # over the sync barrier for each chunk. Custom __aiter__() methods should
+    # be added to each Iterable subclass, but that needs some work in the
+    # Compiler first.
+    def __aiter__(self):
+        return self._async_generator()
+
 
 class ModelIterable(BaseIterable):
     """Iterable that yields a model instance for each row."""
@@ -321,6 +350,16 @@ def __iter__(self):
         self._fetch_all()
         return iter(self._result_cache)
 
+    def __aiter__(self):
+        # Remember, __aiter__ itself is synchronous, it's the thing it returns
+        # that is async!
+        async def generator():
+            await self._async_fetch_all()
+            for item in self._result_cache:
+                yield item
+
+        return generator()
+
     def __bool__(self):
         self._fetch_all()
         return bool(self._result_cache)
@@ -460,6 +499,25 @@ def iterator(self, chunk_size=None):
         )
         return self._iterator(use_chunked_fetch, chunk_size)
 
+    async def aiterator(self, chunk_size=2000):
+        """
+        An asynchronous iterator over the results from applying this QuerySet
+        to the database.
+        """
+        if self._prefetch_related_lookups:
+            raise NotSupportedError(
+                "Using QuerySet.aiterator() after prefetch_related() is not supported."
+            )
+        if chunk_size <= 0:
+            raise ValueError("Chunk size must be strictly positive.")
+        use_chunked_fetch = not connections[self.db].settings_dict.get(
+            "DISABLE_SERVER_SIDE_CURSORS"
+     