# Design Doc - Async QuerySet Interface

# Design Doc - Async QuerySet Interface

Design Doc - Async QuerySet Interface

## Overview

Django's ORM has historically been synchronous, which limits developers building applications with async-capable frameworks like ASGI. This design document describes the architectural approach taken in PR #14843 to add async-compatible interfaces to Django's QuerySet class, addressing the long-standing need for async database operations. The work originates from Django ticket #33646, which requested native async support for query execution.

The implementation introduces async counterparts for all QuerySet methods that do not themselves return a QuerySet. These methods use an 'a' prefix convention (e.g., `acount`, `aget`) and wrap the underlying synchronous logic using `asgiref.sync.sync_to_async`. Additionally, async iteration support is added at both the BaseIterable and QuerySet levels, enabling `async for` loops over query results. A utility function `alist()` is also provided for asynchronously collecting iterables into lists.

## Motivation

As Django evolves to support asynchronous patterns through ASGI and async views, the ORM has remained a significant bottleneck. Developers using `async def` views must currently wrap every database call in `sync_to_async` or use `database_sync_to_async`, adding boilerplate and obscuring intent. Native async QuerySet support eliminates this friction and enables more natural, readable async code.

Two primary use cases drive this work: (1) Async views that perform database queries directly, such as `async def myview(request)` using `await TestModel.objects.aget(name='Andrew')` or `async for row in TestModel.objects.filter(good=True)` without manual sync wrappers. (2) Integration with async web frameworks and middleware that expect non-blocking database access, enabling better concurrency in high-throughput ASGI applications.

## Architecture

The design introduces async support through three complementary mechanisms: a-prefix async method wrappers, async iteration on BaseIterable, and a QuerySet-level async iterator override.

The a-prefix pattern provides async versions of all methods that do not return a QuerySet. The following methods are included: `aiterator`, `aaggregate`, `acount`, `aget`, `acreate`, `abulk_create`, `abulk_update`, `aget_or_create`, `aupdate_or_create`, `aearliest`, `alatest`, `afirst`, `alast`, `ain_bulk`, `aupdate`, `adelete`, `aexists`, `acontains`, `aexplain`. Most are thin wrappers around the synchronous version using `sync_to_async`, though some include performance optimizations.

For async iteration, `BaseIterable` gains a `_async_generator()` method and a `__aiter__()` method. The `_async_generator` creates the synchronous generator via `self.__iter__()` and then repeatedly calls it in chunks using `sync_to_async(next_slice)` where `next_slice` uses `islice(gen, self.chunk_size)`. This bridges the sync-async boundary by fetching chunks of results asynchronously while the generator remains synchronous internally. The `__aiter__()` method returns `self._async_generator()`.

At the QuerySet level, `__aiter__()` is overridden to provide a more efficient path. It defines an inner async generator that calls `await self._async_fetch_all()` and then yields from `self._result_cache`. This avoids the per-chunk sync overhead for QuerySets that support full materialization.

The `aiterator()` method on QuerySet provides an explicit asynchronous iterator with a default `chunk_size=2000`. It includes a guard that raises `NotSupportedError` if `prefetch_related` lookups are present, as prefetching is not yet supported with async iteration. It also validates that `chunk_size > 0`.

Finally, a new `alist()` utility function is added for converting async iterables into lists asynchronously, addressing the common pattern of needing to collect async iteration results.

## Implementation Details

The primary implementation resides in `django/db/models/query.py`. The file imports `sync_to_async` from `asgiref.sync` to handle the sync-to-async conversion of database operations. It also imports `islice` from `itertools` for chunked iteration in the async generator.

The async methods on QuerySet typically follow a pattern of calling the synchronous version within a `sync_to_async` wrapper. For example, `acount()` would wrap the synchronous `count()` method. Some methods like `aiterator()` have custom async implementations that manage cursor-based iteration asynchronously.

The BaseIterable `_async_generator()` method demonstrates the chunked bridge approach: it creates the sync generator, then in a loop fetches chunks via `sync_to_async(next_slice)(sync_generator)` where `next_slice` returns `list(islice(gen, self.chunk_size))`. It yields items from each chunk and breaks when a chunk is smaller than `self.chunk_size`, indicating exhaustion.

The `__aiter__()` on BaseIterable is a synchronous method that returns an asynchronous generator, as `__aiter__` must be synchronous per Python's async iteration protocol. This pattern is documented in the code comments explaining the design constraints.

## Limitations and Future Work

The current implementation has several known limitations. The BaseIterable async generator incurs a performance penalty on large result sets due to the cost of crossing the sync-to-async barrier for each chunk. The code comments note that custom `__aiter__()` methods should be added to each Iterable subclass to mitigate this, but this requires work in the Compiler first.

Specifically, the compiler's `results_iter` needs to be taught async capabilities to enable more efficient async iteration without per-chunk sync overhead. Until then, the generic BaseIterable approach provides a working but suboptimal solution.

The `aiterator()` method explicitly does not support `prefetch_related()`, raising `NotSupportedError` if used. This is because prefetching logic has not yet been adapted for async execution. Future work should enable async-aware prefetching.

Transaction handling is noted as remaining work in the PR description, with a plan to address it in another pass. Tests and documentation were completed as part of the PR, but broader integration testing with async views and ASGI applications is ongoing.

## Testing Strategy

The PR includes comprehensive tests for all new async methods. Testing should verify that each a-prefix method produces the same result as its synchronous counterpart, that async iteration yields the same objects as sync iteration, and that error conditions (like negative chunk_size in aiterator) raise appropriate exceptions.

The tests should also cover the async generator on BaseIterable to ensure correct chunked behavior, especially at boundaries where result sets are smaller than or exactly equal to the chunk size. Integration tests with async views demonstrate the end-to-end functionality.

Documentation updates were included to guide developers on using the new async interfaces, covering method signatures, usage examples, and known limitations. The testing approach ensures backward compatibility, as all synchronous interfaces remain unchanged.
