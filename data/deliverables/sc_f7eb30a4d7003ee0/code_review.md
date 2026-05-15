# Code Review: django/django#14843 — Async-Compatible QuerySet Interface

# Code Review: django/django#14843 — Async-Compatible QuerySet Interface

This review covers PR #14843, titled "Fixed #33646 -- Added async-compatible interface to QuerySet," merged on April 27, 2022. The PR adds asynchronous versions of all QuerySet methods that execute database queries, enabling developers to use Django's ORM directly from async views and code without wrapping calls in sync_to_async(). The implementation spans 9 files with 747 additions and 22 deletions, touching the core QuerySet class, documentation, and test infrastructure.

## Scope and Changed Files

The changes are concentrated in django/db/models/query.py, which contains all the async method implementations. This is the primary file of concern. Supporting documentation was added across four files: docs/ref/models/querysets.txt (reference docs for each new method), docs/releases/4.1.txt (release notes), docs/topics/async.txt (updated async topic guide), and docs/topics/db/queries.txt (new 'Asynchronous queries' section). A new test module was created at tests/async_queryset/ with models.py defining SimpleModel and RelatedModel, and tests.py containing the AsyncQuerySetTest class. Additionally, tests/basic/tests.py was updated to include the new async method names in the manager methods list.

The async methods added include: aiterator, aaggregate, acount, aget, acreate, abulk_create, abulk_update, aget_or_create, aupdate_or_create, aearliest, alatest, afirst, alast, ain_bulk, aupdate, adelete, aexists, acontains, and aexplain. These follow a consistent naming convention with an 'a' prefix on the synchronous method name.

## Architecture and Design Analysis

The PR employs two distinct implementation patterns. The first, and simpler, pattern wraps synchronous methods using asgiref.sync.sync_to_async. Nearly all async query methods (aget, acount, acreate, etc.) follow this pattern: they call the corresponding synchronous method via sync_to_async and return the result. This is straightforward but delegates all actual work to the sync context.

The second pattern handles async iteration and is more architecturally interesting. In BaseIterable, a new _async_generator method creates a synchronous iterator via self.__iter__(), then repeatedly fetches chunks using sync_to_async with the chunk_size parameter. The __aiter__ method is synchronous (as required by Python's async iteration protocol) and returns the async generator object. The code comments explicitly note that this approach 'is going to suffer a performance penalty on large sets of items due to the cost of crossing over the sync barrier for each chunk' and that custom __aiter__() methods should be added to each Iterable subclass once the Compiler is updated.

The QuerySet class overrides __aiter__ with a different approach: it calls a new _async_fetch_all method that iterates over the iterable class with 'async for' and populates _result_cache, then yields from the cache. This means that for standard QuerySet iteration, all results are fetched asynchronously into the cache first, then yielded synchronously from the cache. Both synchronous and asynchronous iteration share the same _result_cache.

The aiterator method on QuerySet takes a different path — it iterates directly over self._iterable_class using 'async for', preserving streaming behavior without caching. This is important for memory efficiency with large result sets.

## Risk Assessment

The most significant risk is the performance overhead introduced by the sync-to-async boundary crossing. Every async operation requires at least one context switch between async and sync execution. For methods like aget() that wrap a single synchronous call, this overhead is minimal. However, for iteration via BaseIterable._async_generator, the cost scales with result set size since a sync_to_async call occurs for every chunk. The chunk size defaults to 2000 in aiterator, but the comment in the code acknowledges this penalty and notes that optimization requires changes to the compiler's results_iter.

Transaction support is explicitly absent in the async interface. The documentation in docs/topics/async.txt states: 'Transactions do not yet work in async mode. If you have a piece of code that needs transactions behavior, we recommend you write that piece as a single synchronous function and call it using sync_to_async.' Similarly, docs/topics/db/queries.txt confirms that 'Transactions are not currently supported with asynchronous queries and updates. You will find that trying to use one raises SynchronousOnlyOperation.' This is a major limitation for any workflow requiring atomic multi-operation transactions.

The aiterator method raises NotSupportedError when used after prefetch_related(), as shown in the code and tested in test_aiterator_prefetch_related. This is documented in docs/ref/models/querysets.txt but could surprise developers who expect seamless parity between sync and async iteration.

Deferred fields (from defer() and only()) will raise SynchronousOnlyOperation if accessed from async code, because the lazy-loading mechanism cannot cross the sync barrier. This is documented in the queryset reference but represents a subtle footgun for developers migrating existing code to async.

## Documentation Quality Review

The documentation is comprehensive and well-structured. The new 'Asynchronous queries' section in docs/topics/db/queries.txt provides excellent guidance, clearly distinguishing between methods that return QuerySets (non-blocking, no async version needed) and methods that execute queries (blocking, with async versions). The practical example showing User.objects.filter(username=my_input).afirst() effectively demonstrates the pattern of mixing sync queryset-building methods with async terminal methods.

The docs/topics/async.txt update replaces the generic sync_to_async wrapping example with a more specific ORM example showing async for iteration and afirst() usage. The section now links to the new async-queries reference and notes the transaction limitation explicitly.

Each method in docs/ref/models/querysets.txt received consistent treatment: a method signature line for the async version, a note stating '*Asynchronous version*', and a versionchanged:: 4.1 entry. The documentation also adds notes about deferred field access limitations near the defer() and only() sections, and a note that refinement methods like filter() are safe to use in async code since they do not execute queries.

The release notes in docs/releases/4.1.txt include a new 'Asynchronous ORM interface' subsection under the 4.1 features, with a code example and a forward-looking statement about ongoing work to push async support into the SQL compiler and database drivers.

## Test Coverage Assessment

The new tests/async_queryset/tests.py file contains a well-structured AsyncQuerySetTest class with setUpTestData creating three SimpleModel instances (s1, s2, s3) with sequential field values (1, 2, 3) and distinct created timestamps. Tests cover all 19 async methods: test_async_iteration, test_aiterator, test_aiterator_prefetch_related, test_aiterator_invalid_chunk_size, test_acount, test_acount_cached_result, test_aget, test_acreate, test_aget_or_create, test_aupdate_or_create, test_abulk_create, test_abulk_update, test_ain_bulk, test_alatest, test_aearliest, test_afirst, test_alast, test_aaggregate, test_aexists, test_acontains, test_aupdate, test_adelete, and test_aexplain.

Notable edge cases tested include: aiterator raising NotSupportedError after prefetch_related() (test_aiterator_prefetch_related), aiterator raising ValueError for chunk_size of 0 or -1 (test_aiterator_invalid_chunk_size), and acount using cached results when the queryset was already evaluated (test_acount_cached_result). The test for acontains also tests with an unsaved instance whose ID does not exist.

The abulk_create and aexplain tests are wrapped with @async_to_sync and @skipUnlessDBFeature decorators, appropriately handling database-specific features. The _get_db_feature static method avoids accessing connection attributes across sync/async boundaries, which is a good pattern.

A gap worth noting is the lack of error-path tests for most async methods — for example, testing aget() with no matching object (expected ObjectDoesNotExist), or acreate() with an integrity error. The test_acount_cached_result test demonstrates cache-sharing behavior but could be expanded. Additionally, the RelatedModel defined in tests/async_queryset/models.py is never used in any test, suggesting planned but unimplemented related-object testing.

## Recommendations for Team Adoption

Adopt the async ORM interface for simple read operations in async views where the sync-to-async overhead is negligible relative to database query time. Methods like aget(), afirst(), acount(), and aexists() are straightforward wrappers and carry minimal risk. Use these to replace manual sync_to_async wrapping of individual ORM calls.

Avoid using aiterator() for performance-critical code paths that process large result sets, as the chunked sync barrier crossing adds overhead proportional to result set size. The default chunk size of 2000 is reasonable for moderate result sets, but monitor performance. For truly high-throughput scenarios, continue using synchronous iteration within a sync_to_async wrapper for now, pending future compiler-level async support.

Do not use async ORM operations within transactions. The documentation is explicit that transactions are not supported. Instead, encapsulate transactional logic in a synchronous function and call it via sync_to_async, as recommended in docs/topics/async.txt. This pattern should be enforced through code review.

Be cautious with defer() and only() in async contexts. Deferred fields will raise SynchronousOnlyOperation on access. Ensure that all fields accessed in async code are included in select_related() or only() calls, or avoid deferred field loading entirely in async code paths.

Plan for future improvements: the PR comments and documentation indicate that async support will be extended into the SQL compiler and database drivers. The current sync_to_async wrapping is an interim solution. Avoid tightly coupling business logic to the current implementation patterns, and structure code so that async ORM calls can benefit from future optimizations transparently.
