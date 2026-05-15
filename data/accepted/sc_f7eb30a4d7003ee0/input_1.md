# PR description text for django/django#14843 describing the async-compatible interface additions


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

## Diff
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
+        )
+        async for item in self._iterable_class(
+            self, chunked_fetch=use_chunked_fetch, chunk_size=chunk_size
+        ):
+            yield item
+
     def aggregate(self, *args, **kwargs):
         """
         Return a dictionary containing the calculations (aggregation)
@@ -502,6 +560,9 @@ def aggregate(self, *args, **kwargs):
                     )
         return query.get_aggregation(self.db, kwargs)
 
+    async def aaggregate(self, *args, **kwargs):
+        return await sync_to_async(self.aggregate)(*args, **kwargs)
+
     def count(self):
         """
         Perform a SELECT COUNT() and return the number of records as an
@@ -515,6 +576,9 @@ def count(self):
 
         return self.query.get_count(using=self.db)
 
+    async def acount(self):
+        return await sync_to_async(self.count)()
+
     def get(self, *args, **kwargs):
         """
         Perform the query and return a single object matching the given
@@ -550,6 +614,9 @@ def get(self, *args, **kwargs):
             )
         )
 
+    async def aget(self, *args, **kwargs):
+        return await sync_to_async(self.get)(*args, **kwargs)
+
     def create(self, **kwargs):
         """
         Create a new object with the given kwargs, saving it to the database
@@ -560,6 +627,9 @@ def create(self, **kwargs):
         obj.save(force_insert=True, using=self.db)
         return obj
 
+    async def acreate(self, **kwargs):
+        return await sync_to_async(self.create)(**kwargs)
+
     def _prepare_for_bulk_create(self, objs):
         for obj in objs:
             if obj.pk is None:
@@ -720,6 +790,13 @@ def bulk_create(
 
         return objs
 
+    async def abulk_create(self, objs, batch_size=None, ignore_conflicts=False):
+        return await sync_to_async(self.bulk_create)(
+            objs=objs,
+            batch_size=batch_size,
+            ignore_conflicts=ignore_conflicts,
+        )
+
     def bulk_update(self, objs, fields, batch_size=None):
         """
         Update the given fields in each of the given objects in the database.
@@ -774,6 +851,15 @@ def bulk_update(self, objs, fields, batch_size=None):
 
     bulk_update.alters_data = True
 
+    async def abulk_update(self, objs, fields, batch_size=None):
+        return await sync_to_async(self.bulk_update)(
+            objs=objs,
+            fields=fields,
+            batch_size=batch_size,
+        )
+
+    abulk_update.alters_data = True
+
     def get_or_create(self, defaults=None, **kwargs):
         """
         Look up an object with the given kwargs, creating one if necessary.
@@ -799,6 +885,12 @@ def get_or_create(self, defaults=None, **kwargs):
                     pass
                 raise
 
+    async def aget_or_create(self, defaults=None, **kwargs):
+        return await sync_to_async(self.get_or_create)(
+            defaults=defaults,
+            **kwargs,
+        )
+
     def update_or_create(self, defaults=None, **kwargs):
         """
         Look up an object with the given kwargs, updating one with defaults
@@ -819,6 +911,12 @@ def update_or_create(self, defaults=None, **kwargs):
             obj.save(using=self.db)
         return obj, False
 
+    async def aupdate_or_create(self, defaults=None, **kwargs):
+        return await sync_to_async(self.update_or_create)(
+            defaults=defaults,
+            **kwargs,
+        )
+
     def _extract_model_params(self, defaults, **kwargs):
         """
         Prepare `params` for creating a model instance based on the given
@@ -873,21 +971,37 @@ def earliest(self, *fields):
             raise TypeError("Cannot change a query once a slice has been taken.")
         return self._earliest(*fields)
 
+    async def aearliest(self, *fields):
+        return await sync_to_async(self.earliest)(*fields)
+
     def latest(self, *fields):
+        """
+        Return the latest object according to fields (if given) or by the
+        model's Meta.get_latest_by.
+        """
         if self.query.is_sliced:
             raise TypeError("Cannot change a query once a slice has been taken.")
         return self.reverse()._earliest(*fields)
 
+    async def alatest(self, *fields):
+        return await sync_to_async(self.latest)(*fields)
+
     def first(self):
         """Return the first object of a query or None if no match is found."""
         for obj in (self if self.ordered else self.order_by("pk"))[:1]:
             return obj
 
+    async def afirst(self):
+        return await sync_to_async(self.first)()
+
     def last(self):
         """Return the last object of a query or None if no match is found."""
         for obj in (self.reverse() if self.ordered else self.order_by("-pk"))[:1]:
             return obj
 
+    async def alast(self):
+        return await sync_to_async(self.last)()
+
     def in_bulk(self, id_list=None, *, field_name="pk"):
         """
         Return a dictionary mapping each of the given IDs to the object with
@@ -930,6 +1044,12 @@ def in_bulk(self, id_list=None, *, field_name="pk"):
             qs = self._chain()
         return {getattr(obj, field_name): obj for obj in qs}
 
+    async def ain_bulk(self, id_list=None, *, field_name="pk"):
+        return await sync_to_async(self.in_bulk)(
+            id_list=id_list,
+            field_name=field_name,
+        )
+
     def delete(self):
         """Delete the records in the current QuerySet."""
         self._not_support_combined_queries("delete")
@@ -963,6 +1083,12 @@ def delete(self):
     delete.alters_data = True
     delete.queryset_only = True
 
+    async def adelete(self):
+        return await sync_to_async(self.delete)()
+
+    adelete.alters_data = True
+    adelete.queryset_only = True
+
     def _raw_delete(self, using):
         """
         Delete objects found from the given queryset in single direct SQL
@@ -998,6 +1124,11 @@ def update(self, **kwargs):
 
     update.alters_data = True
 
+    async def aupdate(self, **kwargs):
+        return await sync_to_async(self.update)(**kwargs)
+
+    aupdate.alters_data = True
+
     def _update(self, values):
         """
         A version of update() that accepts field objects instead of field names.
@@ -1018,12 +1149,21 @@ def _update(self, values):
     _update.queryset_only = False
 
     def exists(self):
+        """
+        Return True if the QuerySet would have any results, False otherwise.
+        """
         if self._result_cache is None:
             return self.query.has_results(using=self.db)
         return bool(self._result_cache)
 
+    async def aexists(self):
+        return await sync_to_async(self.exists)()
+
     def contains(self, obj):
-        """Return True if the queryset contains an object."""
+        """
+        Return True if the QuerySet contains the provided obj,
+        False otherwise.
+        """
         self._not_support_combined_queries("contains")
         if self._fields is not None:
             raise TypeError(
@@ -1040,14 +1180,24 @@ def contains(self, obj):
             return obj in self._result_cache
         return self.filter(pk=obj.pk).exists()
 
+    async def acontains(self, obj):
+        return await sync_to_async(self.contains)(obj=obj)
+
     def _prefetch_related_objects(self):
         # This method can only be called once the result cache has been filled.
         prefetch_related_objects(self._result_cache, *self._prefetch_related_lookups)
         self._prefetch_done = True
 
     def explain(self, *, format=None, **options):
+        """
+        Runs an EXPLAIN on the SQL query this QuerySet would perform, and
+        returns the results.
+        """
         return self.query.explain(using=self.db, format=format, **options)
 
+    async def aexplain(self, *, format=None, **options):
+        return await sync_to_async(self.explain)(format=format, **options)
+
     ##################################################
     # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
     ##################################################
@@ -1648,6 +1798,12 @@ def _fetch_all(self):
         if self._prefetch_related_lookups and not self._prefetch_done:
             self._prefetch_related_objects()
 
+    async def _async_fetch_all(self):
+        if self._result_cache is None:
+            self._result_cache = [result async for result in self._iterable_class(self)]
+        if self._prefetch_related_lookups and not self._prefetch_done:
+            sync_to_async(self._prefetch_related_objects)()
+
     def _next_is_sticky(self):
         """
         Indicate that the next filter call and the one following that should
diff --git a/docs/ref/models/querysets.txt b/docs/ref/models/querysets.txt
index 94614aad7205..a9da1dcf7eab 100644
--- a/docs/ref/models/querysets.txt
+++ b/docs/ref/models/querysets.txt
@@ -34,6 +34,19 @@ You can evaluate a ``QuerySet`` in the following ways:
   Note: Don't use this if all you want to do is determine if at least one
   result exists. It's more efficient to use :meth:`~QuerySet.exists`.
 
+* **Asynchronous iteration.**. A ``QuerySet`` can also be iterated over using
+  ``async for``::
+
+      async for e in Entry.objects.all():
+        results.append(e)
+
+  Both synchronous and asynchronous iterators of QuerySets share the same
+  underlying cache.
+
+  .. versionchanged:: 4.1
+
+    Support for asynchronous iteration was added.
+
 * **Slicing.** As explained in :ref:`limiting-querysets`, a ``QuerySet`` can
   be sliced, using Python's array-slicing syntax. Slicing an unevaluated
   ``QuerySet`` usually returns another unevaluated ``QuerySet``, but Django
@@ -176,6 +189,12 @@ Django provides a range of ``QuerySet`` refinement methods that modify either
 the types of results returned by the ``QuerySet`` or the way its SQL query is
 executed.
 
+.. note::
+
+    These methods do not run database queries, therefore they are **safe to**
+    **run in asynchronous code**, and do not have separate asynchronous
+    versions.
+
 ``filter()``
 ~~~~~~~~~~~~
 
@@ -1581,6 +1600,13 @@ A queryset that has deferred fields will still return model instances. Each
 deferred field will be retrieved from the database if you access that field
 (one at a time, not all the deferred fields at once).
 
+.. note::
+
+    Deferred fields will not lazy-load like this from asynchronous code.
+    Instead, you will get a ``SynchronousOnlyOperation`` exception. If you are
+    writing asynchronous code, you should not try to access any fields that you
+    ``defer()``.
+
 You can make multiple calls to ``defer()``. Each call adds new fields to the
 deferred set::
 
@@ -1703,6 +1729,11 @@ options.
 Using :meth:`only` and omitting a field requested using :meth:`select_related`
 is an error as well.
 
+As with ``defer()``, you cannot access the non-loaded fields from asynchronous
+code and expect them to load. Instead, you will get a
+``SynchronousOnlyOperation`` exception. Ensure that all fields you might access
+are in your ``only()`` call.
+
 .. note::
 
     When calling :meth:`~django.db.models.Model.save()` for instances with
@@ -1946,10 +1977,25 @@ something *other than* a ``QuerySet``.
 These methods do not use a cache (see :ref:`caching-and-querysets`). Rather,
 they query the database each time they're called.
 
+Because these methods evaluate the QuerySet, they are blocking calls, and so
+their main (synchronous) versions cannot be called from asynchronous code. For
+this reason, each has a corresponding asynchronous version with an ``a`` prefix
+- for example, rather than ``get(…)`` you can ``await aget(…)``.
+
+There is usually no difference in behavior apart from their asynchronous
+nature, but any differences are noted below next to each method.
+
+.. versionchanged:: 4.1
+
+    The asynchronous versions of each method, prefixed with ``a`` was added.
+
 ``get()``
 ~~~~~~~~~
 
 .. method:: get(*args, **kwargs)
+.. method:: aget(*args, **kwargs)
+
+*Asynchronous version*: ``aget()``
 
 Returns the object matching the given lookup parameters, which should be in
 the format described in `Field lookups`_. You should use lookups that are
@@ -1989,10 +2035,17 @@ can use :exc:`django.core.exceptions.ObjectDoesNotExist`  to handle
     except ObjectDoesNotExist:
         print("Either the blog or entry doesn't exist.")
 
+.. versionchanged:: 4.1
+
+    ``aget()`` method was added.
+
 ``create()``
 ~~~~~~~~~~~~
 
 .. method:: create(**kwargs)
+.. method:: acreate(*args, **kwargs)
+
+*Asynchronous version*: ``acreate()``
 
 A convenience method for creating an object and saving it all in one step.  Thus::
 
@@ -2013,10 +2066,17 @@ database, a call to ``create()`` will fail with an
 :exc:`~django.db.IntegrityError` since primary keys must be unique. Be
 prepared to handle the exception if you are using manual primary keys.
 
+.. versionchanged:: 4.1
+
+    ``acreate()`` method was added.
+
 ``get_or_create()``
 ~~~~~~~~~~~~~~~~~~~
 
 .. method:: get_or_create(defaults=None, **kwargs)
+.. method:: aget_or_create(defaults=None, **kwargs)
+
+*Asynchronous version*: ``aget_or_create()``
 
 A convenience method for looking up an object with the given ``kwargs`` (may be
 empty if your model has defaults for all fields), creating one if necessary.
@@ -2138,10 +2198,17 @@ whenever a request to a page has a side effect on your data. For more, see
   chapter because it isn't related to that book, but it can't create it either
   because ``title`` field should be unique.
 
+.. versionchanged:: 4.1
+
+    ``aget_or_create()`` method was added.
+
 ``update_or_create()``
 ~~~~~~~~~~~~~~~~~~~~~~
 
 .. method:: update_or_create(defaults=None, **kwargs)
+.. method:: aupdate_or_create(defaults=None, **kwargs)
+
+*Asynchronous version*: ``aupdate_or_create()``
 
 A convenience method for updating an object with the given ``kwargs``, creating
 a new one if necessary. The ``defaults`` is a dictionary of (field, value)
@@ -2188,10 +2255,17 @@ Like :meth:`get_or_create` and :meth:`create`, if you're using manually
 specified primary keys and an object needs to be created but the key already
 exists in the database, an :exc:`~django.db.IntegrityError` is raised.
 
+.. versionchanged:: 4.1
+
+    ``aupdate_or_create()`` method was added.
+
 ``bulk_create()``
 ~~~~~~~~~~~~~~~~~
 
 .. method:: bulk_create(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None)
+.. method:: abulk_create(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None)
+
+*Asynchronous version*: ``abulk_create()``
 
 This method inserts the provided list of objects into the database in an
 efficient manner (generally only 1 query, no matter how many objects there
@@ -2267,10 +2341,15 @@ support it).
     parameters were added to support updating fields when a row insertion fails
     on conflict.
 
+    ``abulk_create()`` method was added.
+
 ``bulk_update()``
 ~~~~~~~~~~~~~~~~~
 
 .. method:: bulk_update(objs, fields, batch_size=None)
+.. method:: abulk_update(objs, fields, batch_size=None)
+
+*Asynchronous version*: ``abulk_update()``
 
 This method efficiently updates the given fields on the provided model
 instances, generally with one query, and returns the number of objects
@@ -2313,10 +2392,17 @@ The ``batch_size`` parameter controls how many objects are saved in a single
 query. The default is to update all objects in one batch, except for SQLite
 and Oracle which have restrictions on the number of variables used in a query.
 
+.. versionchanged:: 4.1
+
+    ``abulk_update()`` method was added.
+
 ``count()``
 ~~~~~~~~~~~
 
 .. method:: count()
+.. method:: acount()
+
+*Asynchronous version*: ``acount()``
 
 Returns an integer representing the number of objects in the database matching
 the ``QuerySet``.
@@ -2342,10 +2428,17 @@ database query like ``count()`` would.
 If the queryset has already been fully retrieved, ``count()`` will use that
 length rather than perform an extra database query.
 
+.. versionchanged:: 4.1
+
+    ``acount()`` method was added.
+
 ``in_bulk()``
 ~~~~~~~~~~~~~
 
 .. method:: in_bulk(id_list=None, *, field_name='pk')
+.. method:: ain_bulk(id_list=None, *, field_name='pk')
+
+*Asynchronous version*: ``ain_bulk()``
 
 Takes a list of field values (``id_list``) and the ``field_name`` for those
 values, and returns a dictionary mapping each value to an instance of the
@@ -2374,19 +2467,29 @@ Example::
 
 If you pass ``in_bulk()`` an empty list, you'll get an empty dictionary.
 
+.. versionchanged:: 4.1
+
+    ``ain_bulk()`` method was added.
+
 ``iterator()``
 ~~~~~~~~~~~~~~
 
 .. method:: iterator(chunk_size=None)
+.. method:: aiterator(chunk_size=None)
+
+*Asynchronous version*: ``aiterator()``
 
 Evaluates the ``QuerySet`` (by performing the query) and returns an iterator
-(see :pep:`234`) over the results. A ``QuerySet`` typically caches its results
-internally so that repeated evaluations do not result in additional queries. In
-contrast, ``iterator()`` will read results directly, without doing any caching
-at the ``QuerySet`` level (internally, the default iterator calls ``iterator()``
-and caches the return value). For a ``QuerySet`` which returns a large number of
-objects that you only need to access once, this can result in better
-performance and a significant reduction in memory.
+(see :pep:`234`) over the results, or an asynchronous iterator (see :pep:`492`)
+if you call its asynchronous version ``aiterator``.
+
+A ``QuerySet`` typically caches its results internally so that repeated
+evaluations do not result in additional queries. In contrast, ``iterator()``
+will read results directly, without doing any caching at the ``QuerySet`` level
+(internally, the default iterator calls ``iterator()`` and caches the return
+value). For a ``QuerySet`` which returns a large number of objects that you
+only need to access once, this can result in better performance and a
+significant reduction in memory.
 
 Note that using ``iterator()`` on a ``QuerySet`` which has already been
 evaluated will force it to evaluate again, repeating the query.
@@ -2395,6 +2498,11 @@ evaluated will force it to evaluate again, repeating the query.
 long as ``chunk_size`` is given. Larger values will necessitate fewer queries
 to accomplish the prefetching at the cost of greater memory usage.
 
+.. note::
+
+    ``aiterator()`` is *not* compatible with previous calls to
+    ``prefetch_related()``.
+
 On some databases (e.g. Oracle, `SQLite
 <https://www.sqlite.org/limits.html#max_variable_number>`_), the maximum number
 of terms in an SQL ``IN`` clause might be limited. Hence values below this
@@ -2411,7 +2519,9 @@ once or streamed from the database using server-side cursors.
 
 .. versionchanged:: 4.1
 
-    Support for prefetching related objects was added.
+    Support for prefetching related objects was added to ``iterator()``.
+
+    ``aiterator()`` method was added.
 
 .. deprecated:: 4.1
 
@@ -2471,6 +2581,9 @@ value for ``chunk_size`` will result in Django using an implicit default of
 ~~~~~~~~~~~~
 
 .. method:: latest(*fields)
+.. method:: alatest(*fields)
+
+*Asynchronous version*: ``alatest()``
 
 Returns the latest object in the table based on the given field(s).
 
@@ -2512,18 +2625,32 @@ readability.
 
         Entry.objects.filter(pub_date__isnull=False).latest('pub_date')
 
+.. versionchanged:: 4.1
+
+    ``alatest()`` method was added.
+
 ``earliest()``
 ~~~~~~~~~~~~~~
 
 .. method:: earliest(*fields)
+.. method:: aearliest(*fields)
+
+*Asynchronous version*: ``aearliest()``
 
 Works otherwise like :meth:`~django.db.models.query.QuerySet.latest` except
 the direction is changed.
 
+.. versionchanged:: 4.1
+
+    ``aearliest()`` method was added.
+
 ``first()``
 ~~~~~~~~~~~
 
 .. method:: first()
+.. method:: afirst()
+
+*Asynchronous version*: ``afirst()``
 
 Returns the first object matched by the queryset, or ``None`` if there
 is no matching object. If the ``QuerySet`` has no ordering defined, then the
@@ -2542,17 +2669,31 @@ equivalent to the above example::
     except IndexError:
         p = None
 
+.. versionchanged:: 4.1
+
+    ``afirst()`` method was added.
+
 ``last()``
 ~~~~~~~~~~
 
 .. method:: last()
+.. method:: alast()
+
+*Asynchronous version*: ``alast()``
 
 Works like  :meth:`first()`, but returns the last object in the queryset.
 
+.. versionchanged:: 4.1
+
+    ``alast()`` method was added.
+
 ``aggregate()``
 ~~~~~~~~~~~~~~~
 
 .. method:: aggregate(*args, **kwargs)
+.. method:: aaggregate(*args, **kwargs)
+
+*Asynchronous version*: ``aaggregate()``
 
 Returns a dictionary of aggregate values (averages, sums, etc.) calculated over
 the ``QuerySet``. Each argument to ``aggregate()`` specifies a value that will
@@ -2585,10 +2726,17 @@ control the name of the aggregation value that is returned::
 For an in-depth discussion of aggregation, see :doc:`the topic guide on
 Aggregation </topics/db/aggregation>`.
 
+.. versionchanged:: 4.1
+
+    ``aaggregate()`` method was added.
+
 ``exists()``
 ~~~~~~~~~~~~
 
 .. method:: exists()
+.. method:: aexists()
+
+*Asynchronous version*: ``aexists()``
 
 Returns ``True`` if the :class:`.QuerySet` contains any results, and ``False``
 if not. This tries to perform the query in the simplest and fastest way
@@ -2618,10 +2766,17 @@ more overall work (one query for the existence check plus an extra one to later
 retrieve the results) than using ``bool(some_queryset)``, which retrieves the
 results and then checks if any were returned.
 
+.. versionchanged:: 4.1
+
+    ``aexists()`` method was added.
+
 ``contains()``
 ~~~~~~~~~~~~~~
 
 .. method:: contains(obj)
+.. method:: acontains(obj)
+
+*Asynchronous version*: ``acontains()``
 
 .. versionadded:: 4.0
 
@@ -2647,10 +2802,17 @@ know that it will be at some point, then using ``some_queryset.contains(obj)``
 will make an additional database query, generally resulting in slower overall
 performance.
 
+.. versionchanged:: 4.1
+
+    ``acontains()`` method was added.
+
 ``update()``
 ~~~~~~~~~~~~
 
 .. method:: update(**kwargs)
+.. method:: aupdate(**kwargs)
+
+*Asynchronous version*: ``aupdate()``
 
 Performs an SQL update query for the specified fields, and returns
 the number of rows matched (which may not be equal to the number of rows
@@ -2721,6 +2883,10 @@ update a bunch of records for a model that has a custom
         e.comments_on = False
         e.save()
 
+.. versionchanged:: 4.1
+
+    ``aupdate()`` method was added.
+
 Ordered queryset
 ^^^^^^^^^^^^^^^^
 
@@ -2739,6 +2905,9 @@ unique field in the order that is specified without conflicts. For example::
 ~~~~~~~~~~~~
 
 .. method:: delete()
+.. method:: adelete()
+
+*Asynchronous version*: ``adelete()``
 
 Performs an SQL delete query on all rows in the :class:`.QuerySet` and
 returns the number of objects deleted and a dictionary with the number of
@@ -2789,6 +2958,10 @@ ForeignKeys which are set to :attr:`~django.db.models.ForeignKey.on_delete`
 Note that the queries generated in object deletion is an implementation
 detail subject to change.
 
+.. versionchanged:: 4.1
+
+    ``adelete()`` method was added.
+
 ``as_manager()``
 ~~~~~~~~~~~~~~~~
 
@@ -2798,10 +2971,16 @@ Class method that returns an instance of :class:`~django.db.models.Manager`
 with a copy of the ``QuerySet``’s methods. See
 :ref:`create-manager-with-queryset-methods` for more details.
 
+Note that unlike the other entries in this section, this does not have an
+asynchronous variant as it does not execute a query.
+
 ``explain()``
 ~~~~~~~~~~~~~
 
 .. method:: explain(format=None, **options)
+.. method:: aexplain(format=None, **options)
+
+*Asynchronous version*: ``aexplain()``
 
 Returns a string of the ``QuerySet``’s execution plan, which details how the
 database would execute the query, including any indexes or joins that would be
@@ -2841,6 +3020,10 @@ adverse effects on your database. For example, the ``ANALYZE`` flag supported
 by MariaDB, MySQL 8.0.18+, and PostgreSQL could result in changes to data if
 there are triggers or if a function is called, even for a ``SELECT`` query.
 
+.. versionchanged:: 4.1
+
+    ``aexplain()`` method was added.
+
 .. _field-lookups:
 
 ``Field`` lookups
diff --git a/docs/releases/4.1.txt b/docs/releases/4.1.txt
index 0de527447bf3..b564a325a9b2 100644
--- a/docs/releases/4.1.txt
+++ b/docs/releases/4.1.txt
@@ -43,6 +43,28 @@ View subclasses may now define async HTTP method handlers::
 
 See :ref:`async-class-based-views` for more details.
 
+Asynchronous ORM interface
+--------------------------
+
+``QuerySet`` now provides an asynchronous interface for all data access
+operations. These are named as-per the existing synchronous operations but with
+an ``a`` prefix, for example ``acreate()``, ``aget()``, and so on.
+
+The new interface allows you to write asynchronous code without needing to wrap
+ORM operations in ``sync_to_async()``::
+
+    async for author in Author.objects.filter(name__startswith="A"):
+        book = await author.books.afirst()
+
+Note that, at this stage, the underlying database operations remain
+synchronous, with contributions ongoing to push asynchronous support down into
+the SQL compiler, and integrate asynchronous database drivers. The new
+asynchronous queryset interface currently encapsulates the necessary
+``sync_to_async()`` operations for you, and will allow your code to take
+advantage of developments in the ORM's asynchronous support as it evolves.
+
+See :ref:`async-queries` for details and limitations.
+
 .. _csrf-cookie-masked-usage:
 
 ``CSRF_COOKIE_MASKED`` setting
diff --git a/docs/topics/async.txt b/docs/topics/async.txt
index 101bbeeabb66..9e2785c351f9 100644
--- a/docs/topics/async.txt
+++ b/docs/topics/async.txt
@@ -61,27 +61,39 @@ In both ASGI and WSGI mode, you can still safely use asynchronous support to
 run code concurrently rather than serially. This is especially handy when
 dealing with external APIs or data stores.
 
-If you want to call a part of Django that is still synchronous, like the ORM,
-you will need to wrap it in a :func:`sync_to_async` call. For example::
+If you want to call a part of Django that is still synchronous, you will need
+to wrap it in a :func:`sync_to_async` call. For example::
 
     from asgiref.sync import sync_to_async
 
-    results = await sync_to_async(Blog.objects.get, thread_sensitive=True)(pk=123)
+    results = await sync_to_async(sync_function, thread_sensitive=True)(pk=123)
 
-You may find it easier to move any ORM code into its own function and call that
-entire function using :func:`sync_to_async`. For example::
+If you accidentally try to call a part of Django that is synchronous-only
+from an async view, you will trigger Django's
+:ref:`asynchronous safety protection <async-safety>` to protect your data from
+corruption.
 
-    from asgiref.sync import sync_to_async
+Queries & the ORM
+-----------------
 
-    def _get_blog(pk):
-        return Blog.objects.select_related('author').get(pk=pk)
+.. versionadded:: 4.1
 
-    get_blog = sync_to_async(_get_blog, thread_sensitive=True)
+With some exceptions, Django can run ORM queries asynchronously as well::
 
-If you accidentally try to call a part of Django that is still synchronous-only
-from an async view, you will trigger Django's
-:ref:`asynchronous safety protection <async-safety>` to protect your data from
-corruption.
+    async for author in Author.objects.filter(name__startswith="A"):
+        book = await author.books.afirst()
+
+Detailed notes can be found in :ref:`async-queries`, but in short:
+
+* All ``QuerySet`` methods that cause a SQL query to occur have an
+  ``a``-prefixed asynchronous variant.
+
+* ``async for`` is supported on all QuerySets (including the output of
+  ``values()`` and ``values_list()``.)
+
+Transactions do not yet work in async mode. If you have a piece of code that
+needs transactions behavior, we recommend you write that piece as a single
+synchronous function and call it using :func:`sync_to_async`.
 
 Performance
 -----------
diff --git a/docs/topics/db/queries.txt b/docs/topics/db/queries.txt
index 811853251392..af264623673e 100644
--- a/docs/topics/db/queries.txt
+++ b/docs/topics/db/queries.txt
@@ -849,6 +849,102 @@ being evaluated and therefore populate the cache::
     Simply printing the queryset will not populate the cache. This is because
     the call to ``__repr__()`` only returns a slice of the entire queryset.
 
+.. _async-queries:
+
+Asynchronous queries
+====================
+
+.. versionadded:: 4.1
+
+If you are writing asynchronous views or code, you cannot use the ORM for
+queries in quite the way we have described above, as you cannot call *blocking*
+synchronous code from asynchronous code - it will block up the event loop
+(or, more likely, Django will notice and raise a ``SynchronousOnlyOperation``
+to stop that from happening).
+
+Fortunately, you can do many queries using Django's asynchronous query APIs.
+Every method that might block - such as ``get()`` or ``delete()`` - has an
+asynchronous variant (``aget()`` or ``adelete()``), and when you iterate over
+results, you can use asynchronous iteration (``async for``) instead.
+
+Query iteration
+---------------
+
+.. versionadded:: 4.1
+
+The default way of iterating over a query - with ``for`` - will result in a
+blocking database query behind the scenes as Django loads the results at
+iteration time. To fix this, you can swap to ``async for``::
+
+    async for entry in Authors.objects.filter(name__startswith="A"):
+        ...
+
+Be aware that you also can't do other things that might iterate over the
+queryset, such as wrapping ``list()`` around it to force its evaluation (you
+can use ``async for`` in a comprehension, if you want it).
+
+Because ``QuerySet`` methods like ``filter()`` and ``exclude()`` do not
+actually run the query - they set up the queryset to run when it's iterated
+over - you can use those freely in asynchronous code. For a guide to which
+methods can keep being used like this, and which have asynchronous versions,
+read the next section.
+
+``QuerySet`` and manager methods
+--------------------------------
+
+.. versionadded:: 4.1
+
+Some methods on managers and querysets - like ``get()`` and ``first()`` - force
+execution of the queryset and are blocking. Some, like ``filter()`` and
+``exclude()``, don't force execution and so are safe to run from asynchronous
+code. But how are you supposed to tell the difference?
+
+While you could poke around and see if there is an ``a``-prefixed version of
+the method (for example, we have ``aget()`` but not ``afilter()``), there is a
+more logical way - look up what kind of method it is in the
+:doc:`QuerySet reference </ref/models/querysets>`.
+
+In there, you'll find the methods on QuerySets grouped into two sections:
+
+* *Methods that return new querysets*: These are the non-blocking ones,
+  and don't have asynchronous versions. You're free to use these in any
+  situation, though read the notes on ``defer()`` and ``only()`` before you use
+  them.
+
+* *Methods that do not return querysets*: These are the blocking ones, and
+  have asynchronous versions - the asynchronous name for each is noted in its
+  documentation, though our standard pattern is to add an ``a`` prefix.
+
+Using this distinction, you can work out when you need to use asynchronous
+versions, and when you don't. For example, here's a valid asynchronous query::
+
+    user = await User.objects.filter(username=my_input).afirst()
+
+``filter()`` returns a queryset, and so it's fine to keep chaining it inside an
+asynchronous environment, whereas ``first()`` evaluates and returns a model
+instance - thus, we change to ``afirst()``, and use ``await`` at the front of
+the whole expression in order to call it in an asynchronous-friendly way.
+
+.. note::
+
+    If you forget to put the ``await`` part in, you may see errors like
+    *"coroutine object has no attribute x"* or *"<coroutine …>"* strings in
+    place of your model instances. If you ever see these, you are missing an
+    ``await`` somewhere to turn that coroutine into a real value.
+
+Transactions
+------------
+
+.. versionadded:: 4.1
+
+Transactions are **not** currently supported with asynchronous queries and
+updates. You will find that trying to use one raises
+``SynchronousOnlyOperation``.
+
+If you wish to use a transaction, we suggest you write your ORM code inside a
+separate, synchronous function and then call that using sync_to_async - see
+:doc:/topics/async` for more.
+
 .. _querying-jsonfield:
 
 Querying ``JSONField``
diff --git a/tests/async_queryset/__init__.py b/tests/async_queryset/__init__.py
new file mode 100644
index 000000000000..e69de29bb2d1
diff --git a/tests/async_queryset/models.py b/tests/async_queryset/models.py
new file mode 100644
index 000000000000..8cb051258c10
--- /dev/null
+++ b/tests/async_queryset/models.py
@@ -0,0 +1,11 @@
+from django.db import models
+from django.utils import timezone
+
+
+class RelatedModel(models.Model):
+    simple = models.ForeignKey("SimpleModel", models.CASCADE, null=True)
+
+
+class SimpleModel(models.Model):
+    field = models.IntegerField()
+    created = models.DateTimeField(default=timezone.now)
diff --git a/tests/async_queryset/tests.py b/tests/async_queryset/tests.py
new file mode 100644
index 000000000000..f600cfe392f5
--- /dev/null
+++ b/tests/async_queryset/tests.py
@@ -0,0 +1,227 @@
+import json
+import xml.etree.ElementTree
+from datetime import datetime
+
+from asgiref.sync import async_to_sync, sync_to_async
+
+from django.db import NotSupportedError, connection
+from django.db.models import Sum
+from django.test import TestCase, skipUnlessDBFeature
+
+from .models import SimpleModel
+
+
+class AsyncQuerySetTest(TestCase):
+    @classmethod
+    def setUpTestData(cls):
+        cls.s1 = SimpleModel.objects.create(
+            field=1,
+            created=datetime(2022, 1, 1, 0, 0, 0),
+        )
+        cls.s2 = SimpleModel.objects.create(
+            field=2,
+            created=datetime(2022, 1, 1, 0, 0, 1),
+        )
+        cls.s3 = SimpleModel.objects.create(
+            field=3,
+            created=datetime(2022, 1, 1, 0, 0, 2),
+        )
+
+    @staticmethod
+    def _get_db_feature(connection_, feature_name):
+        # Wrapper to avoid accessing connection attributes until inside
+        # coroutine function. Connection access is thread sensitive and cannot
+        # be passed across sync/async boundaries.
+        return getattr(connection_.features, feature_name)
+
+    async def test_async_iteration(self):
+        results = []
+        async for m in SimpleModel.objects.order_by("pk"):
+            results.append(m)
+        self.assertEqual(results, [self.s1, self.s2, self.s3])
+
+    async def test_aiterator(self):
+        qs = SimpleModel.objects.aiterator()
+        results = []
+        async for m in qs:
+            results.append(m)
+        self.assertCountEqual(results, [self.s1, self.s2, self.s3])
+
+    async def test_aiterator_prefetch_related(self):
+        qs = SimpleModel.objects.prefetch_related("relatedmodels").aiterator()
+        msg = "Using QuerySet.aiterator() after prefetch_related() is not supported."
+        with self.assertRaisesMessage(NotSupportedError, msg):
+            async for m in qs:
+                pass
+
+    async def test_aiterator_invalid_chunk_size(self):
+        msg = "Chunk size must be strictly positive."
+        for size in [0, -1]:
+            qs = SimpleModel.objects.aiterator(chunk_size=size)
+            with self.subTest(size=size), self.assertRaisesMessage(ValueError, msg):
+                async for m in qs:
+                    pass
+
+    async def test_acount(self):
+        count = await SimpleModel.objects.acount()
+        self.assertEqual(count, 3)
+
+    async def test_acount_cached_result(self):
+        qs = SimpleModel.objects.all()
+        # Evaluate the queryset to populate the query cache.
+        [x async for x in qs]
+        count = await qs.acount()
+        self.assertEqual(count, 3)
+
+        await sync_to_async(SimpleModel.objects.create)(
+            field=4,
+            created=datetime(2022, 1, 1, 0, 0, 0),
+        )
+        # The query cache is used.
+        count = await qs.acount()
+        self.assertEqual(count, 3)
+
+    async def test_aget(self):
+        instance = await SimpleModel.objects.aget(field=1)
+        self.assertEqual(instance, self.s1)
+
+    async def test_acreate(self):
+        await SimpleModel.objects.acreate(field=4)
+        self.assertEqual(await SimpleModel.objects.acount(), 4)
+
+    async def test_aget_or_create(self):
+        instance, created = await SimpleModel.objects.aget_or_create(field=4)
+        self.assertEqual(await SimpleModel.objects.acount(), 4)
+        self.assertIs(created, True)
+
+    async def test_aupdate_or_create(self):
+        instance, created = await SimpleModel.objects.aupdate_or_create(
+            id=self.s1.id, defaults={"field": 2}
+        )
+        self.assertEqual(instance, self.s1)
+        self.assertIs(created, False)
+        instance, created = await SimpleModel.objects.aupdate_or_create(field=4)
+        self.assertEqual(await SimpleModel.objects.acount(), 4)
+        self.assertIs(created, True)
+
+    @skipUnlessDBFeature("has_bulk_insert")
+    @async_to_sync
+    async def test_abulk_create(self):
+        instances = [SimpleModel(field=i) for i in range(10)]
+        qs = await SimpleModel.objects.abulk_create(instances)
+        self.assertEqual(len(qs), 10)
+
+    async def test_abulk_update(self):
+        instances = SimpleModel.objects.all()
+        async for instance in instances:
+            instance.field = instance.field * 10
+
+        await SimpleModel.objects.abulk_update(instances, ["field"])
+
+        qs = [(o.pk, o.field) async for o in SimpleModel.objects.all()]
+        self.assertCountEqual(
+            qs,
+            [(self.s1.pk, 10), (self.s2.pk, 20), (self.s3.pk, 30)],
+        )
+
+    async def test_ain_bulk(self):
+        res = await SimpleModel.objects.ain_bulk()
+        self.assertEqual(
+            res,
+            {self.s1.pk: self.s1, self.s2.pk: self.s2, self.s3.pk: self.s3},
+        )
+
+        res = await SimpleModel.objects.ain_bulk([self.s2.pk])
+        self.assertEqual(res, {self.s2.pk: self.s2})
+
+        res = await SimpleModel.objects.ain_bulk([self.s2.pk], field_name="id")
+        self.assertEqual(res, {self.s2.pk: self.s2})
+
+    async def test_alatest(self):
+        instance = await SimpleModel.objects.alatest("created")
+        self.assertEqual(instance, self.s3)
+
+        instance = await SimpleModel.objects.alatest("-created")
+        self.assertEqual(instance, self.s1)
+
+    async def test_aearliest(self):
+        instance = await SimpleModel.objects.aearliest("created")
+        self.assertEqual(instance, self.s1)
+
+        instance = await SimpleModel.objects.aearliest("-created")
+        self.assertEqual(instance, self.s3)
+
+    async def test_afirst(self):
+        instance = await SimpleModel.objects.afirst()
+        self.assertEqual(instance, self.s1)
+
+        instance = await SimpleModel.objects.filter(field=4).afirst()
+        self.assertIsNone(instance)
+
+    async def test_alast(self):
+        instance = await SimpleModel.objects.alast()
+        self.assertEqual(instance, self.s3)
+
+        instance = await SimpleModel.objects.filter(field=4).alast()
+        self.assertIsNone(instance)
+
+    async def test_aaggregate(self):
+        total = await SimpleModel.objects.aaggregate(total=Sum("field"))
+        self.assertEqual(total, {"total": 6})
+
+    async def test_aexists(self):
+        check = await SimpleModel.objects.filter(field=1).aexists()
+        self.assertIs(check, True)
+
+        check = await SimpleModel.objects.filter(field=4).aexists()
+        self.assertIs(check, False)
+
+    async def test_acontains(self):
+        check = await SimpleModel.objects.acontains(self.s1)
+        self.assertIs(check, True)
+        # Unsaved instances are not allowed, so use an ID known not to exist.
+        check = await SimpleModel.objects.acontains(
+            SimpleModel(id=self.s3.id + 1, field=4)
+        )
+        self.assertIs(check, False)
+
+    async def test_aupdate(self):
+        await SimpleModel.objects.aupdate(field=99)
+        qs = [o async for o in SimpleModel.objects.all()]
+        values = [instance.field for instance in qs]
+        self.assertEqual(set(values), {99})
+
+    async def test_adelete(self):
+        await SimpleModel.objects.filter(field=2).adelete()
+        qs = [o async for o in SimpleModel.objects.all()]
+        self.assertCountEqual(qs, [self.s1, self.s3])
+
+    @skipUnlessDBFeature("supports_explaining_query_execution")
+    @async_to_sync
+    async def test_aexplain(self):
+        supported_formats = await sync_to_async(self._get_db_feature)(
+            connection, "supported_explain_formats"
+        )
+        all_formats = (None, *supported_formats)
+        for format_ in all_formats:
+            with self.subTest(format=format_):
+                # TODO: Check the captured query when async versions of
+                # self.assertNumQueries/CaptureQueriesContext context
+                # processors are available.
+                result = await SimpleModel.objects.filter(field=1).aexplain(
+                    format=format_
+                )
+                self.assertIsInstance(result, str)
+                self.assertTrue(result)
+                if not format_:
+                    continue
+                if format_.lower() == "xml":
+                    try:
+                        xml.etree.ElementTree.fromstring(result)
+                    except xml.etree.ElementTree.ParseError as e:
+                        self.fail(f"QuerySet.aexplain() result is not valid XML: {e}")
+                elif format_.lower() == "json":
+                    try:
+                        json.loads(result)
+                    except json.JSONDecodeError as e:
+                        self.fail(f"QuerySet.aexplain() result is not valid JSON: {e}")
diff --git a/tests/basic/tests.py b/tests/basic/tests.py
index 7be1595be595..e27fb66e3d93 100644
--- a/tests/basic/tests.py
+++ b/tests/basic/tests.py
@@ -702,6 +702,24 @@ class ManagerTest(SimpleTestCase):
         "union",
         "intersection",
         "difference",
+        "aaggregate",
+        "abulk_create",
+        "abulk_update",
+        "acontains",
+        "acount",
+        "acreate",
+        "aearliest",
+        "aexists",
+        "aexplain",
+        "afirst",
+        "aget",
+        "aget_or_create",
+        "ain_bulk",
+        "aiterator",
+        "alast",
+        "alatest",
+        "aupdate",
+        "aupdate_or_create",
     ]
 
     def test_manager_methods(self):
