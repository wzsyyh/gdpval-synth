# Code Review - PR #30539: Default to One Shard

# Code Review - PR #30539: Default to One Shard

## Summary and Risk Assessment

This PR changes the default number of primary shards for new indices from 5 to 1 in Elasticsearch. The change addresses the well-documented problem of oversharding, where users create indices with too many small shards relative to their data volume, leading to unnecessary overhead. For users with time-based indices, index templates can be used to set a different default. For non-time-based indices, the split API provides a path to increase shard count without reindexing. The risk level is **medium-high** because this changes a fundamental default that affects every index created without explicit shard configuration. The change touches core indexing logic in `MetaDataCreateIndexService.java`, test infrastructure in 40+ files, and critical documentation. While the backward-compatibility logic preserves 5-shard behavior for pre-7.0 indices, the breadth of test changes required (43 files) indicates high surface area for regressions.

## Core Logic Review

The core change is in `server/src/main/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexService.java`. A new static method `getNumberOfShards()` has been added that returns 5 for indices with `SETTING_VERSION_CREATED` before `Version.V_7_0_0_alpha1` and 1 for 7.0+ indices. This is a reasonable approach for backward compatibility.

Critically, the `SETTING_VERSION_CREATED` assignment has been moved **before** the `SETTING_NUMBER_OF_SHARDS` check. Previously, version was set after shard count was determined, but now the version must be known first because `getNumberOfShards()` depends on it. This reordering is correct and necessary — without it, `indexSettingsBuilder.get(SETTING_VERSION_CREATED)` would return null in `getNumberOfShards()`, causing a `NumberFormatException` when calling `Integer.parseInt()`.

The method includes an assertion `assert Version.CURRENT.major == 7` with a TODO comment noting this logic can be removed when the current major version is 8. This is acceptable for now but creates a maintenance obligation for the 8.0 release cycle.

One concern: the `getNumberOfShards()` method retrieves the version via `Integer.parseInt(indexSettingsBuilder.get(SETTING_VERSION_CREATED))` and constructs a Version via `Version.fromId()`. If `SETTING_VERSION_CREATED` were somehow set to a non-numeric value, this would throw an uncaught `NumberFormatException`. However, in practice this value is always set from a valid Version object, so the risk is low.

## Test Infrastructure Review

The test infrastructure changes are in `test/framework/src/main/java/org/elasticsearch/test/rest/yaml/ESClientYamlSuiteTestCase.java` and `test/framework/src/main/java/org/elasticsearch/test/rest/yaml/Features.java`. A new boolean field `useDefaultNumberOfShards` is initialized in a `@BeforeClass` method using `usually()`, which returns true approximately 90% of the time.

When `useDefaultNumberOfShards` is false (roughly 10% of test runs) AND the test does not have the `default_shards` feature in its skip section, a global index template is created that sets `index.number_of_shards` to 2 for all indices (`index_patterns: ["*"]`). This ensures that multi-shard scenarios are still tested even though the default is now 1.

Tests that need to always run with the default single shard can add `default_shards` to their features skip list. This is used for documentation tests (via `RestTestsFromSnippetsTask.groovy`) and for tests like `cat.templates/10_basic.yml` that inspect cluster state templates and would be confused by the random global template.

The `default_shards` feature was added to the `SUPPORTED` list in `Features.java`. The randomization approach is sound — it maintains test coverage for multi-shard issues while not requiring every test to explicitly configure shard counts. However, the ~10% randomization rate means multi-shard-specific bugs could slip through in 90% of CI runs, potentially requiring multiple failures before detection.

## Test Updates Review

Numerous test files required updates due to the shard count change. Here are the key ones:

**1. `client/rest-high-level/src/test/java/org/elasticsearch/client/SearchIT.java`**: Statistical aggregation values changed (e.g., variance from `1830d` to `1830.0000000000002`, skewness from `0.09340198804973046` to `0.09340198804973039`). With a single shard, all documents reside on the same shard, which can cause minor floating-point differences in aggregation results due to different accumulation orders.

**2. `client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDocumentationIT.java`**: The rank evaluation test changed `hitsAndRatings.get(0)` to `hitsAndRatings.get(2)`. With a single shard, document ordering changes, so the rated search hit at index 2 now contains the expected document ID '3'.

**3. `distribution/archives/integ-test-zip/src/test/java/org/elasticsearch/test/rest/CreatedLocationHeaderIT.java`**: Added an explicit index deletion between routing tests. With a single shard, the second indexing request with `?routing=cat` routes to the same shard and would not produce a 201 Created response, so the index must be deleted first.

**4. `server/src/test/java/org/elasticsearch/cluster/allocation/FilteringAllocationIT.java`**: Added `index.number_of_shards: 2` to the test index creation to maintain the test's intent of testing shard allocation across nodes.

**5. `modules/reindex/src/test/resources/rest-api-spec/test/reindex/35_search_failures.yml` and `update_by_query/35_search_failure.yml`**: Both added explicit `index.number_of_shards: 2` settings and changed `failures.0.shard` from `is_true` to `match: 0`. With 2 shards, the failing shard is deterministically shard 0.

**6. `x-pack/qa/sql/security/src/test/java/org/elasticsearch/xpack/qa/sql/security/RestSqlSecurityIT.java`**: The `testHijackScrollFails` test reduced from 4 expected `access_denied` audit log entries to 1. With the old default of 5 shards, there was one scroll access denial per shard (4 non-primary shards); with 1 shard, there are zero additional shards but one denial still occurs for the single shard's scroll request.

**7. `rest-api-spec/src/main/resources/rest-api-spec/test/search.aggregation/240_max_buckets.yml`**: Added additional documents (IDs 5-8) with different keywords to ensure sufficient unique buckets exist for the max_buckets aggregation test, since with a single shard, document distribution changes.

## Documentation Review

The documentation updates are extensive and appear to be thorough. Key files updated include:

**1. `docs/reference/getting-started.asciidoc`**: Updated the introductory explanation to state 'one primary shard' instead of '5 primary shards' and adjusted the `_cat/indices` response example accordingly. The text now correctly states a total of 'two shards per index' (one primary + one replica).

**2. `docs/reference/glossary.asciidoc`**: The primary shard glossary entry was updated from '5 primary shards' to 'one primary shard'. Importantly, the text about not being able to change shards was updated to mention the split API: 'However, an index can be split into a new index using the <<indices-split-index, split API>>.' This is a valuable addition given the new default.

**3. `docs/reference/cluster/health.asciidoc`**: Updated from '5 shards and one replica' to 'one shard and one replica' and changed `active_primary_shards`, `active_shards`, and `unassigned_shards` from 5 to 1.

**4. `docs/reference/cat/allocation.asciidoc`, `cat/health.asciidoc`, `cat/indices.asciidoc`, `cat/segments.asciidoc`**: All `_cat` API documentation examples updated shard counts from 5 to 1. The segments doc also changed shard numbers from 4 to 0 in examples.

**5. Multiple aggregation, query, and search documentation files**: Files including `children-aggregation.asciidoc`, `geocentroid-aggregation.asciidoc`, `percolate-query.asciidoc`, `terms-set-query.asciidoc`, `completion-suggest.asciidoc`, `count.asciidoc`, `validate.asciidoc`, and others all had `_shards.total` and `_shards.successful` updated from 5 to 1.

**6. `docs/reference/indices/shrink-index.asciidoc`**: The shrink index documentation added explicit `index.number_of_shards:2` and `index.number_of_shards:5` settings in TEST directives to ensure shrink operations still work with sufficient source shards.

**7. `docs/reference/search/search-shards.asciidoc`**: Added explicit `index.number_of_shards:5` in TEST directives since this API's examples require multiple shards to be meaningful.

The documentation coverage appears comprehensive. All `_shards` response examples were updated, and search score values were recalculated where they changed due to single-shard IDF calculations (e.g., stemming.asciidoc scores changed from `0.2876821` to `0.18232156` or `0.80259144`).

## Backward Compatibility Assessment

The backward compatibility approach is implemented through the `getNumberOfShards()` method in `MetaDataCreateIndexService.java`. For indices where `SETTING_VERSION_CREATED` indicates a version before `V_7_0_0_alpha1`, the default remains 5 shards. For version 7.0.0-alpha1 and later, the default is 1 shard.

This means that existing indices are unaffected — the change only applies to newly created indices on 7.x clusters. Rolling upgrade scenarios are handled correctly because `SETTING_VERSION_CREATED` is set to the minimum version of the non-client nodes in the cluster during index creation.

The approach is **sufficient** for the stated goals. The version-based guard ensures that indices created during mixed-version rolling upgrades (with some 6.x nodes still present) will use the old 5-shard default, preventing inconsistency. Only when all nodes are upgraded to 7.x will new indices use the 1-shard default.

One potential gap: the `getNumberOfShards()` method uses `Version.fromId(Integer.parseInt(...))` which could fail if `SETTING_VERSION_CREATED` is malformed. However, this value is always set programmatically from a valid Version object, so this is a theoretical rather than practical concern.

## Recommendations

**1. Add monitoring for index creation patterns**: After release, monitor the distribution of `number_of_shards` settings on newly created indices. If a significant percentage of users are overriding the default back to 5, this may indicate the default should be re-evaluated or that migration documentation needs enhancement.

**2. Increase multi-shard test randomization frequency**: The current `usually()` call returns true ~90% of the time, meaning multi-shard scenarios are only tested ~10% of CI runs. For the 7.0 release cycle, consider increasing this to 25-30% to catch shard-distribution-related regressions earlier. The risk of missed bugs from only 10% coverage is non-trivial for a change of this magnitude.

**3. Add explicit upgrade documentation**: Create a specific section in the migration guide explaining the default change and its implications. Users upgrading from 6.x should understand that new indices will have 1 shard by default, how to use index templates to preserve the old behavior, and when to use the split API. The glossary already mentions the split API, but a dedicated migration section would be more discoverable.
