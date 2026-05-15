# PR description for elastic/elasticsearch#30539


# Seed Material: elastic/elasticsearch#30539: Default to one shard
Source: github_issue_pr
Identifier: pr:elastic/elasticsearch#30539

Repository: elastic/elasticsearch
PR Number: #30539
PR Title: Default to one shard
Merged At: 2018-05-14T16:22:36Z
Changed Files: 43
Additions: +232, Deletions: -157

## PR Description
This commit changes the default out-of-the-box configuration for the number of shards from five to one. We think this will help address a common problem of oversharding. For users with time-based indices that need a different default, this can be managed with index templates. For users with non-time-based indices that find they need to re-shard with the split API in place they no longer need to resort only to reindexing.

Since this has the impact of changing the default number of shards used in REST tests, we want to ensure that we still have coverage for issues that could arise from multiple shards. As such, we randomize (rarely) the default number of shards in REST tests to two. This is managed via a global index template. However, some tests check the templates that are in the cluster state during the test. Since this template is randomly  there, we need a way for tests to skip adding the template used to set  the number of shards to two. For this we add the default_shards feature skip. To avoid having to write our docs in a complicated way because sometimes they might be behind one shard, and sometimes they might be behind two shards we apply the default_shards feature skip to all docs tests. That is, these tests will always run with the default number of shards (one).


## Diff
diff --git a/buildSrc/src/main/groovy/org/elasticsearch/gradle/doc/RestTestsFromSnippetsTask.groovy b/buildSrc/src/main/groovy/org/elasticsearch/gradle/doc/RestTestsFromSnippetsTask.groovy
index 15a4f21b17543..adacc1863c595 100644
--- a/buildSrc/src/main/groovy/org/elasticsearch/gradle/doc/RestTestsFromSnippetsTask.groovy
+++ b/buildSrc/src/main/groovy/org/elasticsearch/gradle/doc/RestTestsFromSnippetsTask.groovy
@@ -225,6 +225,7 @@ public class RestTestsFromSnippetsTask extends SnippetsTask {
                  * warning every time. */
                 current.println("  - skip:")
                 current.println("      features: ")
+                current.println("        - default_shards")
                 current.println("        - stash_in_key")
                 current.println("        - stash_in_path")
                 current.println("        - stash_path_replace")
diff --git a/client/rest-high-level/src/test/java/org/elasticsearch/client/SearchIT.java b/client/rest-high-level/src/test/java/org/elasticsearch/client/SearchIT.java
index 9828041332b32..549b4ce0a85c5 100644
--- a/client/rest-high-level/src/test/java/org/elasticsearch/client/SearchIT.java
+++ b/client/rest-high-level/src/test/java/org/elasticsearch/client/SearchIT.java
@@ -312,14 +312,14 @@ public void testSearchWithMatrixStats() throws IOException {
         MatrixStats matrixStats = searchResponse.getAggregations().get("agg1");
         assertEquals(5, matrixStats.getFieldCount("num"));
         assertEquals(56d, matrixStats.getMean("num"), 0d);
-        assertEquals(1830d, matrixStats.getVariance("num"), 0d);
-        assertEquals(0.09340198804973046, matrixStats.getSkewness("num"), 0d);
+        assertEquals(1830.0000000000002, matrixStats.getVariance("num"), 0d);
+        assertEquals(0.09340198804973039, matrixStats.getSkewness("num"), 0d);
         assertEquals(1.2741646510794589, matrixStats.getKurtosis("num"), 0d);
         assertEquals(5, matrixStats.getFieldCount("num2"));
         assertEquals(29d, matrixStats.getMean("num2"), 0d);
         assertEquals(330d, matrixStats.getVariance("num2"), 0d);
         assertEquals(-0.13568039346585542, matrixStats.getSkewness("num2"), 1.0e-16);
-        assertEquals(1.3517561983471074, matrixStats.getKurtosis("num2"), 0d);
+        assertEquals(1.3517561983471071, matrixStats.getKurtosis("num2"), 0d);
         assertEquals(-767.5, matrixStats.getCovariance("num", "num2"), 0d);
         assertEquals(-0.9876336291667923, matrixStats.getCorrelation("num", "num2"), 0d);
     }
diff --git a/client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDocumentationIT.java b/client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDocumentationIT.java
index 4400d05a9f820..6fdc60fcb3394 100644
--- a/client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDocumentationIT.java
+++ b/client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDocumentationIT.java
@@ -800,7 +800,7 @@ public void testRankEval() throws Exception {
             double qualityLevel = evalQuality.getQualityLevel();        // <3>
             assertEquals(1.0 / 3.0, qualityLevel, 0.0);
             List<RatedSearchHit> hitsAndRatings = evalQuality.getHitsAndRatings();
-            RatedSearchHit ratedSearchHit = hitsAndRatings.get(0);
+            RatedSearchHit ratedSearchHit = hitsAndRatings.get(2);
             assertEquals("3", ratedSearchHit.getSearchHit().getId());   // <4>
             assertFalse(ratedSearchHit.getRating().isPresent());        // <5>
             MetricDetail metricDetails = evalQuality.getMetricDetails();
diff --git a/distribution/archives/integ-test-zip/src/test/java/org/elasticsearch/test/rest/CreatedLocationHeaderIT.java b/distribution/archives/integ-test-zip/src/test/java/org/elasticsearch/test/rest/CreatedLocationHeaderIT.java
index c61b736bf6db1..74cc251f52c2f 100644
--- a/distribution/archives/integ-test-zip/src/test/java/org/elasticsearch/test/rest/CreatedLocationHeaderIT.java
+++ b/distribution/archives/integ-test-zip/src/test/java/org/elasticsearch/test/rest/CreatedLocationHeaderIT.java
@@ -21,18 +21,22 @@
 
 import org.apache.http.entity.ContentType;
 import org.apache.http.entity.StringEntity;
+import org.elasticsearch.client.Request;
 import org.elasticsearch.client.Response;
+import org.junit.Before;
 
 import java.io.IOException;
 
 import static java.util.Collections.emptyMap;
 import static java.util.Collections.singletonMap;
+import static org.hamcrest.Matchers.equalTo;
 import static org.hamcrest.Matchers.startsWith;
 
 /**
  * Tests for the "Location" header returned when returning {@code 201 CREATED}.
  */
 public class CreatedLocationHeaderIT extends ESRestTestCase {
+
     public void testCreate() throws IOException {
         locationTestCase("PUT", "test/test/1");
     }
@@ -54,8 +58,11 @@ public void testUpsert() throws IOException {
     private void locationTestCase(String method, String url) throws IOException {
         locationTestCase(client().performRequest(method, url, emptyMap(),
             new StringEntity("{\"test\": \"test\"}", ContentType.APPLICATION_JSON)));
+        // we have to delete the index otherwise the second indexing request will route to the single shard and not produce a 201
+        final Response response = client().performRequest(new Request("DELETE", "test"));
+        assertThat(response.getStatusLine().getStatusCode(), equalTo(200));
         locationTestCase(client().performRequest(method, url + "?routing=cat", emptyMap(),
-            new StringEntity("{\"test\": \"test\"}", ContentType.APPLICATION_JSON)));
+                new StringEntity("{\"test\": \"test\"}", ContentType.APPLICATION_JSON)));
     }
 
     private void locationTestCase(Response response) throws IOException {
@@ -65,4 +72,5 @@ private void locationTestCase(Response response) throws IOException {
         Response getResponse = client().performRequest("GET", location);
         assertEquals(singletonMap("test", "test"), entityAsMap(getResponse).get("_source"));
     }
+
 }
diff --git a/docs/reference/aggregations/bucket/children-aggregation.asciidoc b/docs/reference/aggregations/bucket/children-aggregation.asciidoc
index e616359e8a818..3805b2e564ca4 100644
--- a/docs/reference/aggregations/bucket/children-aggregation.asciidoc
+++ b/docs/reference/aggregations/bucket/children-aggregation.asciidoc
@@ -137,8 +137,8 @@ Possible response:
   "took": 25,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
diff --git a/docs/reference/aggregations/metrics/geocentroid-aggregation.asciidoc b/docs/reference/aggregations/metrics/geocentroid-aggregation.asciidoc
index 59cadf1518eba..7dd5dca61b9e4 100644
--- a/docs/reference/aggregations/metrics/geocentroid-aggregation.asciidoc
+++ b/docs/reference/aggregations/metrics/geocentroid-aggregation.asciidoc
@@ -60,8 +60,8 @@ The response for the above aggregation:
     "aggregations": {
         "centroid": {
             "location": {
-                "lat": 51.00982963806018,
-                "lon": 3.9662131061777472
+                "lat": 51.009829603135586,
+                "lon": 3.9662130642682314
             },
             "count": 6
         }
@@ -113,8 +113,8 @@ The response for the above aggregation:
                    "doc_count": 3,
                    "centroid": {
                       "location": {
-                         "lat": 52.371655656024814,
-                         "lon": 4.909563297405839
+                         "lat": 52.371655642054975,
+                         "lon": 4.9095632415264845
                       },
                       "count": 3
                    }
@@ -125,7 +125,7 @@ The response for the above aggregation:
                    "centroid": {
                       "location": {
                          "lat": 48.86055548675358,
-                         "lon": 2.3316944623366
+                         "lon": 2.331694420427084
                       },
                       "count": 2
                    }
diff --git a/docs/reference/analysis/charfilters/pattern-replace-charfilter.asciidoc b/docs/reference/analysis/charfilters/pattern-replace-charfilter.asciidoc
index 6e881121a0f67..3da1c60db0552 100644
--- a/docs/reference/analysis/charfilters/pattern-replace-charfilter.asciidoc
+++ b/docs/reference/analysis/charfilters/pattern-replace-charfilter.asciidoc
@@ -235,8 +235,8 @@ The output from the above is:
   "timed_out": false,
   "took": $body.took,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
diff --git a/docs/reference/analysis/tokenizers/edgengram-tokenizer.asciidoc b/docs/reference/analysis/tokenizers/edgengram-tokenizer.asciidoc
index 3cf1f8403e230..9b6861627be40 100644
--- a/docs/reference/analysis/tokenizers/edgengram-tokenizer.asciidoc
+++ b/docs/reference/analysis/tokenizers/edgengram-tokenizer.asciidoc
@@ -294,8 +294,8 @@ GET my_index/_search
   "took": $body.took,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
diff --git a/docs/reference/api-conventions.asciidoc b/docs/reference/api-conventions.asciidoc
index e2824bb528584..42216a9a0fc14 100644
--- a/docs/reference/api-conventions.asciidoc
+++ b/docs/reference/api-conventions.asciidoc
@@ -300,11 +300,7 @@ Responds:
     "indices": {
       "twitter": {
         "shards": {
-          "0": [{"state": "STARTED"}, {"state": "UNASSIGNED"}],
-          "1": [{"state": "STARTED"}, {"state": "UNASSIGNED"}],
-          "2": [{"state": "STARTED"}, {"state": "UNASSIGNED"}],
-          "3": [{"state": "STARTED"}, {"state": "UNASSIGNED"}],
-          "4": [{"state": "STARTED"}, {"state": "UNASSIGNED"}]
+          "0": [{"state": "STARTED"}, {"state": "UNASSIGNED"}]
         }
       }
     }
diff --git a/docs/reference/cat/allocation.asciidoc b/docs/reference/cat/allocation.asciidoc
index 3719758ff58e9..a9de182e3c00e 100644
--- a/docs/reference/cat/allocation.asciidoc
+++ b/docs/reference/cat/allocation.asciidoc
@@ -16,7 +16,7 @@ Might respond with:
 [source,txt]
 --------------------------------------------------
 shards disk.indices disk.used disk.avail disk.total disk.percent host      ip        node
-     5         260b    47.3gb     43.4gb    100.7gb           46 127.0.0.1 127.0.0.1 CSUXak2
+     1         260b    47.3gb     43.4gb    100.7gb           46 127.0.0.1 127.0.0.1 CSUXak2
 --------------------------------------------------
 // TESTRESPONSE[s/\d+(\.\d+)?[tgmk]?b/\\d+(\\.\\d+)?[tgmk]?b/ s/46/\\d+/]
 // TESTRESPONSE[s/CSUXak2/.+/ _cat]
diff --git a/docs/reference/cat/health.asciidoc b/docs/reference/cat/health.asciidoc
index ca2a1838adb02..5f053edf30866 100644
--- a/docs/reference/cat/health.asciidoc
+++ b/docs/reference/cat/health.asciidoc
@@ -14,7 +14,7 @@ GET /_cat/health?v
 [source,txt]
 --------------------------------------------------
 epoch      timestamp cluster       status node.total node.data shards pri relo init unassign pending_tasks max_task_wait_time active_shards_percent
-1475871424 16:17:04  elasticsearch green           1         1      5   5    0    0        0             0                  -                100.0%
+1475871424 16:17:04  elasticsearch green           1         1      1   1    0    0        0             0                  -                100.0%
 --------------------------------------------------
 // TESTRESPONSE[s/1475871424 16:17:04/\\d+ \\d+:\\d+:\\d+/]
 // TESTRESPONSE[s/elasticsearch/[^ ]+/ s/0                  -/\\d+ (-|\\d+(\\.\\d+)?[ms]+)/ _cat]
@@ -33,7 +33,7 @@ which looks like:
 [source,txt]
 --------------------------------------------------
 cluster       status node.total node.data shards pri relo init unassign pending_tasks max_task_wait_time active_shards_percent
-elasticsearch green           1         1      5   5    0    0        0             0                  -                100.0%
+elasticsearch green           1         1      1   1    0    0        0             0                  -                100.0%
 --------------------------------------------------
 // TESTRESPONSE[s/elasticsearch/[^ ]+/ s/0                  -/\\d+ (-|\\d+(\\.\\d+)?[ms]+)/ _cat]
 
diff --git a/docs/reference/cat/indices.asciidoc b/docs/reference/cat/indices.asciidoc
index 3a50a836d0fdb..2a5b865fefa47 100644
--- a/docs/reference/cat/indices.asciidoc
+++ b/docs/reference/cat/indices.asciidoc
@@ -18,7 +18,7 @@ Might respond with:
 --------------------------------------------------
 health status index    uuid                   pri rep docs.count docs.deleted store.size pri.store.size
 yellow open   twitter  u8FNjxh8Rfy_awN11oDKYQ   1   1       1200            0     88.1kb         88.1kb
-green  open   twitter2 nYFWZEO7TUiOjLQXBaYJpA   5   0          0            0       260b           260b
+green  open   twitter2 nYFWZEO7TUiOjLQXBaYJpA   1   0          0            0       260b           260b
 --------------------------------------------------
 // TESTRESPONSE[s/\d+(\.\d+)?[tgmk]?b/\\d+(\\.\\d+)?[tgmk]?b/]
 // TESTRESPONSE[s/u8FNjxh8Rfy_awN11oDKYQ|nYFWZEO7TUiOjLQXBaYJpA/.+/ _cat]
@@ -81,7 +81,7 @@ Which looks like:
 --------------------------------------------------
 health status index    uuid                   pri rep docs.count docs.deleted store.size pri.store.size
 yellow open   twitter  u8FNjxh8Rfy_awN11oDKYQ   1   1       1200            0     88.1kb         88.1kb
-green  open   twitter2 nYFWZEO7TUiOjLQXBaYJpA   5   0          0            0       260b           260b
+green  open   twitter2 nYFWZEO7TUiOjLQXBaYJpA   1   0          0            0       260b           260b
 --------------------------------------------------
 // TESTRESPONSE[s/\d+(\.\d+)?[tgmk]?b/\\d+(\\.\\d+)?[tgmk]?b/]
 // TESTRESPONSE[s/u8FNjxh8Rfy_awN11oDKYQ|nYFWZEO7TUiOjLQXBaYJpA/.+/ _cat]
diff --git a/docs/reference/cat/segments.asciidoc b/docs/reference/cat/segments.asciidoc
index 88fb18b363745..a4c2c54d8eefd 100644
--- a/docs/reference/cat/segments.asciidoc
+++ b/docs/reference/cat/segments.asciidoc
@@ -17,8 +17,8 @@ might look like:
 ["source","txt",subs="attributes,callouts"]
 --------------------------------------------------
 index shard prirep ip        segment generation docs.count docs.deleted size size.memory committed searchable version compound
-test  4     p      127.0.0.1 _0               0          1            0  3kb        2042 false     true       {lucene_version}   true
-test1 4     p      127.0.0.1 _0               0          1            0  3kb        2042 false     true       {lucene_version}   true
+test  0     p      127.0.0.1 _0               0          1            0  3kb        2042 false     true       {lucene_version}   true
+test1 0     p      127.0.0.1 _0               0          1            0  3kb        2042 false     true       {lucene_version}   true
 --------------------------------------------------
 // TESTRESPONSE[s/3kb/\\d+(\\.\\d+)?[mk]?b/ s/2042/\\d+/ _cat]
 
diff --git a/docs/reference/cluster/health.asciidoc b/docs/reference/cluster/health.asciidoc
index 6cc99a25476d9..87c4e17f452ce 100644
--- a/docs/reference/cluster/health.asciidoc
+++ b/docs/reference/cluster/health.asciidoc
@@ -3,7 +3,7 @@
 
 The cluster health API allows to get a very simple status on the health
 of the cluster. For example, on a quiet single node cluster with a single index
-with 5 shards and one replica, this:
+with one shard and one replica, this:
 
 [source,js]
 --------------------------------------------------
@@ -22,11 +22,11 @@ Returns this:
   "timed_out" : false,
   "number_of_nodes" : 1,
   "number_of_data_nodes" : 1,
-  "active_primary_shards" : 5,
-  "active_shards" : 5,
+  "active_primary_shards" : 1,
+  "active_shards" : 1,
   "relocating_shards" : 0,
   "initializing_shards" : 0,
-  "unassigned_shards" : 5,
+  "unassigned_shards" : 1,
   "delayed_unassigned_shards": 0,
   "number_of_pending_tasks" : 0,
   "number_of_in_flight_fetch": 0,
diff --git a/docs/reference/getting-started.asciidoc b/docs/reference/getting-started.asciidoc
index 937917823f5a6..d684be80c00b8 100755
--- a/docs/reference/getting-started.asciidoc
+++ b/docs/reference/getting-started.asciidoc
@@ -95,7 +95,7 @@ Replication is important for two primary reasons:
 To summarize, each index can be split into multiple shards. An index can also be replicated zero (meaning no replicas) or more times. Once replicated, each index will have primary shards (the original shards that were replicated from) and replica shards (the copies of the primary shards).
 The number of shards and replicas can be defined per index at the time the index is created. After the index is created, you may change the number of replicas dynamically anytime but you cannot change the number of shards after-the-fact.
 
-By default, each index in Elasticsearch is allocated 5 primary shards and 1 replica which means that if you have at least two nodes in your cluster, your index will have 5 primary shards and another 5 replica shards (1 complete replica) for a total of 10 shards per index.
+By default, each index in Elasticsearch is allocated one primary shard and one replica which means that if you have at least two nodes in your cluster, your index will have one primary shard and another replica shard (one complete replica) for a total of two shards per index.
 
 NOTE: Each Elasticsearch shard is a Lucene index.  There is a maximum number of documents you can have in a single Lucene index.  As of https://issues.apache.org/jira/browse/LUCENE-5843[`LUCENE-5843`], the limit is `2,147,483,519` (= Integer.MAX_VALUE - 128) documents.
 You can monitor shard sizes using the {ref}/cat-shards.html[`_cat/shards`] API.
@@ -366,11 +366,11 @@ And the response:
 [source,txt]
 --------------------------------------------------
 health status index    uuid                   pri rep docs.count docs.deleted store.size pri.store.size
-yellow open   customer 95SQ4TSUT7mWBT7VNHH67A   5   1          0            0       260b           260b
+yellow open   customer 95SQ4TSUT7mWBT7VNHH67A   1   1          0            0       260b           260b
 --------------------------------------------------
 // TESTRESPONSE[s/95SQ4TSUT7mWBT7VNHH67A/.+/ s/260b/\\d+\\.?\\d?k?b/ _cat]
 
-The results of the second command tells us that we now have 1 index named customer and it has 5 primary shards and 1 replica (the defaults) and it contains 0 documents in it.
+The results of the second command tells us that we now have one index named customer and it has one primary shard and one replica (the defaults) and it contains zero documents in it.
 
 You might also notice that the customer index has a yellow health tagged to it. Recall from our previous discussion that yellow means that some replicas are not (yet) allocated. The reason this happens for this index is because Elasticsearch by default created one replica for this index. Since we only have one node running at the moment, that one replica cannot yet be allocated (for high availability) until a later point in time when another node joins the cluster. Once that replica gets allocated onto a second node, the health status for this index will turn to green.
 
diff --git a/docs/reference/glossary.asciidoc b/docs/reference/glossary.asciidoc
index 53164d366cd93..c6b9309fa3240 100644
--- a/docs/reference/glossary.asciidoc
+++ b/docs/reference/glossary.asciidoc
@@ -105,12 +105,13 @@
   you index a document, it is indexed first on the primary shard, then
   on all <<glossary-replica-shard,replicas>> of the primary shard.
   +
-  By default, an <<glossary-index,index>> has 5 primary shards. You can
-  specify fewer or more primary shards to scale the number of
-  <<glossary-document,documents>> that your index can handle.
+  By default, an <<glossary-index,index>> has one primary shard. You can specify
+  more primary shards to scale the number of <<glossary-document,documents>>
+  that your index can handle.
   +
-  You cannot change the number of primary shards in an index, once the
-  index is created.
+  You cannot change the number of primary shards in an index, once the index is
+  index is created. However, an index can be split into a new index using the
+  <<indices-split-index, split API>>.
   +
   See also <<glossary-routing,routing>>
 
diff --git a/docs/reference/how-to/recipes/stemming.asciidoc b/docs/reference/how-to/recipes/stemming.asciidoc
index 4e12dfd7ecad4..37901cb3abe62 100644
--- a/docs/reference/how-to/recipes/stemming.asciidoc
+++ b/docs/reference/how-to/recipes/stemming.asciidoc
@@ -78,31 +78,31 @@ GET index/_search
   "took": 2,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
   "hits": {
     "total": 2,
-    "max_score": 0.2876821,
+    "max_score": 0.18232156,
     "hits": [
       {
         "_index": "index",
         "_type": "_doc",
-        "_id": "2",
-        "_score": 0.2876821,
+        "_id": "1",
+        "_score": 0.18232156,
         "_source": {
-          "body": "A pair of skis"
+          "body": "Ski resort"
         }
       },
       {
         "_index": "index",
         "_type": "_doc",
-        "_id": "1",
-        "_score": 0.2876821,
+        "_id": "2",
+        "_score": 0.18232156,
         "_source": {
-          "body": "Ski resort"
+          "body": "A pair of skis"
         }
       }
     ]
@@ -136,20 +136,20 @@ GET index/_search
   "took": 1,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
   "hits": {
     "total": 1,
-    "max_score": 0.2876821,
+    "max_score": 0.80259144,
     "hits": [
       {
         "_index": "index",
         "_type": "_doc",
         "_id": "1",
-        "_score": 0.2876821,
+        "_score": 0.80259144,
         "_source": {
           "body": "Ski resort"
         }
@@ -193,20 +193,20 @@ GET index/_search
   "took": 2,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
   "hits": {
     "total": 1,
-    "max_score": 0.2876821,
+    "max_score": 0.80259144,
     "hits": [
       {
         "_index": "index",
         "_type": "_doc",
         "_id": "1",
-        "_score": 0.2876821,
+        "_score": 0.80259144,
         "_source": {
           "body": "Ski resort"
         }
diff --git a/docs/reference/indices/flush.asciidoc b/docs/reference/indices/flush.asciidoc
index db1f7c2fe00a9..8583afc96ab1f 100644
--- a/docs/reference/indices/flush.asciidoc
+++ b/docs/reference/indices/flush.asciidoc
@@ -106,11 +106,7 @@ which returns something similar to:
                    "num_docs" : 0
                  }
                }
-            ],
-            "1": ...,
-            "2": ...,
-            "3": ...,
-            "4": ...
+            ]
          }
       }
    }
@@ -120,10 +116,6 @@ which returns something similar to:
 // TESTRESPONSE[s/"translog_uuid" : "hnOG3xFcTDeoI_kvvvOdNA"/"translog_uuid": $body.indices.twitter.shards.0.0.commit.user_data.translog_uuid/]
 // TESTRESPONSE[s/"history_uuid" : "XP7KDJGiS1a2fHYiFL5TXQ"/"history_uuid": $body.indices.twitter.shards.0.0.commit.user_data.history_uuid/]
 // TESTRESPONSE[s/"sync_id" : "AVvFY-071siAOuFGEO9P"/"sync_id": $body.indices.twitter.shards.0.0.commit.user_data.sync_id/]
-// TESTRESPONSE[s/"1": \.\.\./"1": $body.indices.twitter.shards.1/]
-// TESTRESPONSE[s/"2": \.\.\./"2": $body.indices.twitter.shards.2/]
-// TESTRESPONSE[s/"3": \.\.\./"3": $body.indices.twitter.shards.3/]
-// TESTRESPONSE[s/"4": \.\.\./"4": $body.indices.twitter.shards.4/]
 <1> the `sync id` marker
 
 [float]
diff --git a/docs/reference/indices/shrink-index.asciidoc b/docs/reference/indices/shrink-index.asciidoc
index 496ae7253ce9c..34e90e6799d78 100644
--- a/docs/reference/indices/shrink-index.asciidoc
+++ b/docs/reference/indices/shrink-index.asciidoc
@@ -42,7 +42,7 @@ PUT /my_source_index/_settings
 }
 --------------------------------------------------
 // CONSOLE
-// TEST[s/^/PUT my_source_index\n/]
+// TEST[s/^/PUT my_source_index\n{"settings":{"index.number_of_shards":2}}\n/]
 <1> Forces the relocation of a copy of each shard to the node with name
     `shrink_node_name`.  See <<shard-allocation-filtering>> for more options.
 
@@ -119,7 +119,7 @@ POST my_source_index/_shrink/my_target_index?copy_settings=true
 }
 --------------------------------------------------
 // CONSOLE
-// TEST[s/^/PUT my_source_index\n{"settings": {"index.blocks.write": true}}\n/]
+// TEST[s/^/PUT my_source_index\n{"settings": {"index.number_of_shards":5,"index.blocks.write": true}}\n/]
 
 <1> The number of shards in the target index. This must be a factor of the
     number of shards in the source index.
diff --git a/docs/reference/mapping/params/normalizer.asciidoc b/docs/reference/mapping/params/normalizer.asciidoc
index 723f79c5dc499..3688a0e945414 100644
--- a/docs/reference/mapping/params/normalizer.asciidoc
+++ b/docs/reference/mapping/params/normalizer.asciidoc
@@ -83,31 +83,31 @@ both index and query time.
   "took": $body.took,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
   "hits": {
     "total": 2,
-    "max_score": 0.2876821,
+    "max_score": 0.47000363,
     "hits": [
       {
         "_index": "index",
         "_type": "_doc",
-        "_id": "2",
-        "_score": 0.2876821,
+        "_id": "1",
+        "_score": 0.47000363,
         "_source": {
-          "foo": "bar"
+          "foo": "BÀR"
         }
       },
       {
         "_index": "index",
         "_type": "_doc",
-        "_id": "1",
-        "_score": 0.2876821,
+        "_id": "2",
+        "_score": 0.47000363,
         "_source": {
-          "foo": "BÀR"
+          "foo": "bar"
         }
       }
     ]
@@ -144,8 +144,8 @@ returns
   "took": 43,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
diff --git a/docs/reference/mapping/types/percolator.asciidoc b/docs/reference/mapping/types/percolator.asciidoc
index b5226b53ba0c7..066d3ce1ac597 100644
--- a/docs/reference/mapping/types/percolator.asciidoc
+++ b/docs/reference/mapping/types/percolator.asciidoc
@@ -194,8 +194,8 @@ now returns matches from the new index:
   "took": 3,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -389,8 +389,8 @@ This results in a response like this:
   "took": 6,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -549,8 +549,8 @@ GET /my_queries1/_search
   "took": 6,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped": 0,
     "failed": 0
   },
diff --git a/docs/reference/query-dsl/percolate-query.asciidoc b/docs/reference/query-dsl/percolate-query.asciidoc
index b6e465e34dfd4..0d2661c37b862 100644
--- a/docs/reference/query-dsl/percolate-query.asciidoc
+++ b/docs/reference/query-dsl/percolate-query.asciidoc
@@ -83,8 +83,8 @@ The above request will yield the following response:
   "took": 13,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -227,8 +227,8 @@ GET /my-index/_search
   "took": 13,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -299,7 +299,7 @@ Index response:
     "failed": 0
   },
   "result": "created",
-  "_seq_no" : 0,
+  "_seq_no" : 1,
   "_primary_term" : 1
 }
 --------------------------------------------------
@@ -407,8 +407,8 @@ This will yield the following response.
   "took": 7,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -512,8 +512,8 @@ The slightly different response:
   "took": 13,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
@@ -608,8 +608,8 @@ The above search request returns a response similar to this:
   "took": 13,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
diff --git a/docs/reference/query-dsl/terms-set-query.asciidoc b/docs/reference/query-dsl/terms-set-query.asciidoc
index 35bc17e1f0fac..29b349c3b7adb 100644
--- a/docs/reference/query-dsl/terms-set-query.asciidoc
+++ b/docs/reference/query-dsl/terms-set-query.asciidoc
@@ -68,20 +68,20 @@ Response:
   "took": 13,
   "timed_out": false,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "skipped" : 0,
     "failed": 0
   },
   "hits": {
     "total": 1,
-    "max_score": 0.5753642,
+    "max_score": 0.87546873,
     "hits": [
       {
         "_index": "my-index",
         "_type": "_doc",
         "_id": "2",
-        "_score": 0.5753642,
+        "_score": 0.87546873,
         "_source": {
           "codes": ["def", "ghi"],
           "required_matches": 2
diff --git a/docs/reference/search/count.asciidoc b/docs/reference/search/count.asciidoc
index f1c6cf7c573f9..5c01fa53d45ec 100644
--- a/docs/reference/search/count.asciidoc
+++ b/docs/reference/search/count.asciidoc
@@ -37,8 +37,8 @@ tweets from the `twitter` index for a certain user. The result is:
 {
     "count" : 1,
     "_shards" : {
-        "total" : 5,
-        "successful" : 5,
+        "total" : 1,
+        "successful" : 1,
         "skipped" : 0,
         "failed" : 0
     }
diff --git a/docs/reference/search/search-shards.asciidoc b/docs/reference/search/search-shards.asciidoc
index 1a7c45545769a..90ee35afa6172 100644
--- a/docs/reference/search/search-shards.asciidoc
+++ b/docs/reference/search/search-shards.asciidoc
@@ -18,7 +18,7 @@ Full example:
 GET /twitter/_search_shards
 --------------------------------------------------
 // CONSOLE
-// TEST[s/^/PUT twitter\n/]
+// TEST[s/^/PUT twitter\n{"settings":{"index.number_of_shards":5}}\n/]
 
 This will yield the following result:
 
@@ -103,7 +103,7 @@ And specifying the same request, this time with a routing value:
 GET /twitter/_search_shards?routing=foo,bar
 --------------------------------------------------
 // CONSOLE
-// TEST[s/^/PUT twitter\n/]
+// TEST[s/^/PUT twitter\n{"settings":{"index.number_of_shards":5}}\n/]
 
 This will yield the following result:
 
diff --git a/docs/reference/search/suggesters/completion-suggest.asciidoc b/docs/reference/search/suggesters/completion-suggest.asciidoc
index e3101a5dfb438..9f9833bde9d5c 100644
--- a/docs/reference/search/suggesters/completion-suggest.asciidoc
+++ b/docs/reference/search/suggesters/completion-suggest.asciidoc
@@ -177,8 +177,8 @@ returns this response:
 --------------------------------------------------
 {
   "_shards" : {
-    "total" : 5,
-    "successful" : 5,
+    "total" : 1,
+    "successful" : 1,
     "skipped" : 0,
     "failed" : 0
   },
@@ -251,8 +251,8 @@ Which should look like:
     "took": 6,
     "timed_out": false,
     "_shards" : {
-        "total" : 5,
-        "successful" : 5,
+        "total" : 1,
+        "successful" : 1,
         "skipped" : 0,
         "failed" : 0
     },
diff --git a/docs/reference/search/validate.asciidoc b/docs/reference/search/validate.asciidoc
index 2c0c8821355a7..20894e5773a37 100644
--- a/docs/reference/search/validate.asciidoc
+++ b/docs/reference/search/validate.asciidoc
@@ -218,8 +218,8 @@ Response:
 {
   "valid": true,
   "_shards": {
-    "total": 5,
-    "successful": 5,
+    "total": 1,
+    "successful": 1,
     "failed": 0
   },
   "explanations": [
@@ -227,31 +227,7 @@ Response:
       "index": "twitter",
       "shard": 0,
       "valid": true,
-      "explanation": "user:kimchy~2"
-    },
-    {
-      "index": "twitter",
-      "shard": 1,
-      "valid": true,
-      "explanation": "user:kimchy~2"
-    },
-    {
-      "index": "twitter",
-      "shard": 2,
-      "valid": true,
-      "explanation": "user:kimchy~2"
-    },
-    {
-      "index": "twitter",
-      "shard": 3,
-      "valid": true,
-      "explanation": "(user:kimchi)^0.8333333"
-    },
-    {
-      "index": "twitter",
-      "shard": 4,
-      "valid": true,
-      "explanation": "user:kimchy"
+      "explanation": "(user:kimchi)^0.8333333 user:kimchy"
     }
   ]
 }
diff --git a/modules/reindex/src/test/resources/rest-api-spec/test/reindex/35_search_failures.yml b/modules/reindex/src/test/resources/rest-api-spec/test/reindex/35_search_failures.yml
index 605891d2b32d3..70e78f7e36b37 100644
--- a/modules/reindex/src/test/resources/rest-api-spec/test/reindex/35_search_failures.yml
+++ b/modules/reindex/src/test/resources/rest-api-spec/test/reindex/35_search_failures.yml
@@ -1,5 +1,12 @@
 ---
 "Response format for search failures":
+  - do:
+      indices.create:
+        index: source
+        body:
+          settings:
+            index.number_of_shards: 2
+
   - do:
       index:
         index:   source
@@ -26,7 +33,7 @@
   - match: {updated: 0}
   - match: {version_conflicts: 0}
   - match: {batches: 0}
-  - is_true: failures.0.shard
+  - match: {failures.0.shard: 0}
   - match: {failures.0.index:  source}
   - is_true: failures.0.node
   - match: {failures.0.reason.type:   script_exception}
diff --git a/modules/reindex/src/test/resources/rest-api-spec/test/update_by_query/35_search_failure.yml b/modules/reindex/src/test/resources/rest-api-spec/test/update_by_query/35_search_failure.yml
index 8ace77eee59eb..17f422453ce18 100644
--- a/modules/reindex/src/test/resources/rest-api-spec/test/update_by_query/35_search_failure.yml
+++ b/modules/reindex/src/test/resources/rest-api-spec/test/update_by_query/35_search_failure.yml
@@ -1,5 +1,12 @@
 ---
 "Response format for search failures":
+  - do:
+      indices.create:
+        index: source
+        body:
+          settings:
+            index.number_of_shards: 2
+
   - do:
       index:
         index:   source
@@ -22,7 +29,7 @@
   - match: {updated: 0}
   - match: {version_conflicts: 0}
   - match: {batches: 0}
-  - is_true: failures.0.shard
+  - match: {failures.0.shard: 0}
   - match: {failures.0.index:  source}
   - is_true: failures.0.node
   - match: {failures.0.reason.type:   script_exception}
diff --git a/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/multi_cluster/10_basic.yml b/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/multi_cluster/10_basic.yml
index 7726a1df0b10d..8617ecc1fe28a 100644
--- a/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/multi_cluster/10_basic.yml
+++ b/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/multi_cluster/10_basic.yml
@@ -161,7 +161,7 @@
       search:
         index: my_remote_cluster:aliased_test_index,my_remote_cluster:field_caps_index_1
 
-  - match: { _shards.total: 8 }
+  - match: { _shards.total: 4 }
   - match: { hits.total: 2 }
   - match: { hits.hits.0._source.filter_field: 1 }
   - match: { hits.hits.0._index: "my_remote_cluster:test_index" }
diff --git a/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/remote_cluster/10_basic.yml b/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/remote_cluster/10_basic.yml
index d37bb5a182586..c2840c1ce98e8 100644
--- a/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/remote_cluster/10_basic.yml
+++ b/qa/multi-cluster-search/src/test/resources/rest-api-spec/test/remote_cluster/10_basic.yml
@@ -27,6 +27,8 @@
         indices.create:
           index: field_caps_index_1
           body:
+              settings:
+                index.number_of_shards: 1
               mappings:
                 t:
                   properties:
@@ -51,6 +53,8 @@
         indices.create:
           index: field_caps_index_3
           body:
+              settings:
+                index.number_of_shards: 1
               mappings:
                 t:
                   properties:
diff --git a/rest-api-spec/src/main/resources/rest-api-spec/test/cat.templates/10_basic.yml b/rest-api-spec/src/main/resources/rest-api-spec/test/cat.templates/10_basic.yml
index 403b0b740c533..78b7a4277570a 100644
--- a/rest-api-spec/src/main/resources/rest-api-spec/test/cat.templates/10_basic.yml
+++ b/rest-api-spec/src/main/resources/rest-api-spec/test/cat.templates/10_basic.yml
@@ -14,6 +14,8 @@
 
 ---
 "No templates":
+    - skip:
+        features: default_shards
     - do:
         cat.templates: {}
 
@@ -174,6 +176,8 @@
 
 ---
 "Sort templates":
+    - skip:
+        features: default_shards
     - do:
         indices.put_template:
           name: test
@@ -222,6 +226,8 @@
 
 ---
 "Multiple template":
+    - skip:
+        features: default_shards
     - do:
         indices.put_template:
           name: test_1
diff --git a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/10_basic.yml b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/10_basic.yml
index 4d98eade8f709..a88b37ead3154 100644
--- a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/10_basic.yml
+++ b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/10_basic.yml
@@ -24,7 +24,8 @@
           settings:
             # ensure everything is allocated on a single node
             index.routing.allocation.include._id: $master
-            number_of_replicas: 0
+            index.number_of_shards: 2
+            index.number_of_replicas: 0
   - do:
       index:
         index: source
diff --git a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/20_source_mapping.yml b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/20_source_mapping.yml
index 07b3515b50c9e..ee7b2215d2187 100644
--- a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/20_source_mapping.yml
+++ b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/20_source_mapping.yml
@@ -20,7 +20,8 @@
             settings:
               # ensure everything is allocated on a single node
               index.routing.allocation.include._id: $master
-              number_of_replicas: 0
+              index.number_of_shards: 2
+              index.number_of_replicas: 0
             mappings:
               test:
                 properties:
diff --git a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/30_copy_settings.yml b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/30_copy_settings.yml
index 6e595921d7f6e..50438384b3ab0 100644
--- a/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/30_copy_settings.yml
+++ b/rest-api-spec/src/main/resources/rest-api-spec/test/indices.shrink/30_copy_settings.yml
@@ -19,6 +19,7 @@
           settings:
             # ensure everything is allocated on the master node
             index.routing.allocation.include._id: $master
+            index.number_of_shards: 2
             index.number_of_replicas: 0
             index.merge.scheduler.max_merge_count: 4
 
diff --git a/rest-api-spec/src/main/resources/rest-api-spec/test/search.aggregation/240_max_buckets.yml b/rest-api-spec/src/main/resources/rest-api-spec/test/search.aggregation/240_max_buckets.yml
index 86c6c632d5e94..f8d960e0c2597 100644
--- a/rest-api-spec/src/main/resources/rest-api-spec/test/search.aggregation/240_max_buckets.yml
+++ b/rest-api-spec/src/main/resources/rest-api-spec/test/search.aggregation/240_max_buckets.yml
@@ -17,14 +17,14 @@ setup:
         index: test
         type:  doc
         id:    1
-        body:  { "date": "2014-03-03T00:00:00", "keyword": "foo" }
+        body:  { "date": "2014-03-03T00:00:00", "keyword": "dgx" }
 
   - do:
       index:
         index: test
         type:  doc
         id:    2
-        body:  { "date": "2015-03-03T00:00:00", "keyword": "bar" }
+        body:  { "date": "2015-03-03T00:00:00", "keyword": "dfs" }
 
   - do:
       index:
@@ -38,7 +38,36 @@ setup:
         index: test
         type:  doc
         id:    4
-        body:  { "date": "2017-03-03T00:00:00" }
+        body:  { "date": "2017-03-03T00:00:00", "keyword": "foo" }
+
+  - do:
+      index:
+        index: test
+        type:  doc
+        id:    5
+        body:  { "date": "2018-03-03T00:00:00", "keyword": "bar" }
+
+  - do:
+      index:
+        index: test
+        type:  doc
+        id:    6
+        body:  { "date": "2019-03-03T00:00:00", "keyword": "baz" }
+
+  - do:
+      index:
+        index: test
+        type:  doc
+        id:    7
+        body:  { "date": "2020-03-03T00:00:00", "keyword": "qux" }
+
+  - do:
+      index:
+        index: test
+        type:  doc
+        id:    8
+        body:  { "date": "2021-03-03T00:00:00", "keyword": "quux" }
+
 
   - do:
       indices.refresh:
diff --git a/server/src/main/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexService.java b/server/src/main/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexService.java
index 166aad3ecaa12..0d8a374e66d42 100644
--- a/server/src/main/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexService.java
+++ b/server/src/main/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexService.java
@@ -366,8 +366,14 @@ public ClusterState execute(ClusterState currentState) throws Exception {
                 }
                 // now, put the request settings, so they override templates
                 indexSettingsBuilder.put(request.settings());
+                if (indexSettingsBuilder.get(SETTING_VERSION_CREATED) == null) {
+                    DiscoveryNodes nodes = currentState.nodes();
+                    final Version createdVersion = Version.min(Version.CURRENT, nodes.getSmallestNonClientNodeVersion());
+                    indexSettingsBuilder.put(SETTING_VERSION_CREATED, createdVersion);
+                }
                 if (indexSettingsBuilder.get(SETTING_NUMBER_OF_SHARDS) == null) {
-                    indexSettingsBuilder.put(SETTING_NUMBER_OF_SHARDS, settings.getAsInt(SETTING_NUMBER_OF_SHARDS, 5));
+                    final int numberOfShards = getNumberOfShards(indexSettingsBuilder);
+                    indexSettingsBuilder.put(SETTING_NUMBER_OF_SHARDS, settings.getAsInt(SETTING_NUMBER_OF_SHARDS, numberOfShards));
                 }
                 if (indexSettingsBuilder.get(SETTING_NUMBER_OF_REPLICAS) == null) {
                     indexSettingsBuilder.put(SETTING_NUMBER_OF_REPLICAS, settings.getAsInt(SETTING_NUMBER_OF_REPLICAS, 1));
@@ -376,12 +382,6 @@ public ClusterState execute(ClusterState currentState) throws Exception {
                     indexSettingsBuilder.put(SETTING_AUTO_EXPAND_REPLICAS, settings.get(SETTING_AUTO_EXPAND_REPLICAS));
                 }
 
-                if (indexSettingsBuilder.get(SETTING_VERSION_CREATED) == null) {
-                    DiscoveryNodes nodes = currentState.nodes();
-                    final Version createdVersion = Version.min(Version.CURRENT, nodes.getSmallestNonClientNodeVersion());
-                    indexSettingsBuilder.put(SETTING_VERSION_CREATED, createdVersion);
-                }
-
                 if (indexSettingsBuilder.get(SETTING_CREATION_DATE) == null) {
                     indexSettingsBuilder.put(SETTING_CREATION_DATE, new DateTime(DateTimeZone.UTC).getMillis());
                 }
@@ -573,6 +573,18 @@ public ClusterState execute(ClusterState currentState) throws Exception {
             }
         }
 
+        static int getNumberOfShards(final Settings.Builder indexSettingsBuilder) {
+            // TODO: this logic can be removed when the current major version is 8
+            assert Version.CURRENT.major == 7;
+            final int numberOfShards;
+            if (Version.fromId(Integer.parseInt(indexSettingsBuilder.get(SETTING_VERSION_CREATED))).before(Version.V_7_0_0_alpha1)) {
+                numberOfShards = 5;
+            } else {
+                numberOfShards = 1;
+            }
+            return numberOfShards;
+        }
+
         @Override
         public void onFailure(String source, Exception e) {
             if (e instanceof ResourceAlreadyExistsException) {
diff --git a/server/src/test/java/org/elasticsearch/cluster/allocation/FilteringAllocationIT.java b/server/src/test/java/org/elasticsearch/cluster/allocation/FilteringAllocationIT.java
index d887387d43fe9..ccdc1d6ab3323 100644
--- a/server/src/test/java/org/elasticsearch/cluster/allocation/FilteringAllocationIT.java
+++ b/server/src/test/java/org/elasticsearch/cluster/allocation/FilteringAllocationIT.java
@@ -96,7 +96,7 @@ public void testDisablingAllocationFiltering() throws Exception {
 
         logger.info("--> creating an index with no replicas");
         client().admin().indices().prepareCreate("test")
-                .setSettings(Settings.builder().put("index.number_of_replicas", 0))
+                .setSettings(Settings.builder().put("index.number_of_shards", 2).put("index.number_of_replicas", 0))
                 .execute().actionGet();
 
         ensureGreen();
diff --git a/server/src/test/java/org/elasticsearch/cluster/metadata/IndexCreationTaskTests.java b/server/src/test/java/org/elasticsearch/cluster/metadata/IndexCreationTaskTests.java
index ad36457bde505..de8251ece255f 100644
--- a/server/src/test/java/org/elasticsearch/cluster/metadata/IndexCreationTaskTests.java
+++ b/server/src/test/java/org/elasticsearch/cluster/metadata/IndexCreationTaskTests.java
@@ -185,7 +185,7 @@ public void testRequestDataHavePriorityOverTemplateData() throws Exception {
     public void testDefaultSettings() throws Exception {
         final ClusterState result = executeTask();
 
-        assertThat(result.getMetaData().index("test").getSettings().get(SETTING_NUMBER_OF_SHARDS), equalTo("5"));
+        assertThat(result.getMetaData().index("test").getSettings().get(SETTING_NUMBER_OF_SHARDS), equalTo("1"));
     }
 
     public void testSettingsFromClusterState() throws Exception {
diff --git a/server/src/test/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexServiceTests.java b/server/src/test/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexServiceTests.java
index d5f3d71d7ee26..24f5a69656114 100644
--- a/server/src/test/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexServiceTests.java
+++ b/server/src/test/java/org/elasticsearch/cluster/metadata/MetaDataCreateIndexServiceTests.java
@@ -56,6 +56,7 @@
 import java.util.stream.Stream;
 
 import static java.util.Collections.emptyMap;
+import static org.elasticsearch.cluster.metadata.IndexMetaData.SETTING_VERSION_CREATED;
 import static org.hamcrest.Matchers.endsWith;
 import static org.hamcrest.Matchers.equalTo;
 
@@ -92,6 +93,21 @@ public static boolean isSplitable(int source, int target) {
         return source * x == target;
     }
 
+    public void testNumberOfShards() {
+        {
+            final Version versionCreated = VersionUtils.randomVersionBetween(
+                    random(),
+                    Version.V_6_0_0_alpha1, VersionUtils.getPreviousVersion(Version.V_7_0_0_alpha1));
+            final Settings.Builder indexSettingsBuilder = Settings.builder().put(SETTING_VERSION_CREATED, versionCreated);
+            assertThat(MetaDataCreateIndexService.IndexCreationTask.getNumberOfShards(indexSettingsBuilder), equalTo(5));
+        }
+        {
+            final Version versionCreated = VersionUtils.randomVersionBetween(random(), Version.V_7_0_0_alpha1, Version.CURRENT);
+            final Settings.Builder indexSettingsBuilder = Settings.builder().put(SETTING_VERSION_CREATED, versionCreated);
+            assertThat(MetaDataCreateIndexService.IndexCreationTask.getNumberOfShards(indexSettingsBuilder), equalTo(1));
+        }
+    }
+
     public void testValidateShrinkIndex() {
         int numShards = randomIntBetween(2, 42);
         ClusterState state = createClusterState("source", numShards, randomIntBetween(0, 10),
diff --git a/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/ESClientYamlSuiteTestCase.java b/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/ESClientYamlSuiteTestCase.java
index 950bb14eed9af..ab99bc0d97ba4 100644
--- a/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/ESClientYamlSuiteTestCase.java
+++ b/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/ESClientYamlSuiteTestCase.java
@@ -21,7 +21,10 @@
 
 import com.carrotsearch.randomizedtesting.RandomizedTest;
 import org.apache.http.HttpHost;
+import org.apache.http.entity.StringEntity;
+import org.apache.http.message.BasicHeader;
 import org.elasticsearch.Version;
+import org.elasticsearch.client.Request;
 import org.elasticsearch.client.Response;
 import org.elasticsearch.client.ResponseException;
 import org.elasticsearch.client.RestClient;
@@ -29,6 +32,7 @@
 import org.elasticsearch.common.collect.Tuple;
 import org.elasticsearch.common.io.PathUtils;
 import org.elasticsearch.common.xcontent.NamedXContentRegistry;
+import org.elasticsearch.common.xcontent.XContentType;
 import org.elasticsearch.test.rest.ESRestTestCase;
 import org.elasticsearch.test.rest.yaml.restspec.ClientYamlSuiteRestApi;
 import org.elasticsearch.test.rest.yaml.restspec.ClientYamlSuiteRestSpec;
@@ -38,6 +42,7 @@
 import org.elasticsearch.test.rest.yaml.section.ExecutableSection;
 import org.junit.AfterClass;
 import org.junit.Before;
+import org.junit.BeforeClass;
 
 import java.io.IOException;
 import java.nio.file.Files;
@@ -94,6 +99,13 @@ protected ESClientYamlSuiteTestCase(ClientYamlTestCandidate testCandidate) {
         this.testCandidate = testCandidate;
     }
 
+    private static boolean useDefaultNumberOfShards;
+
+    @BeforeClass
+    public static void initializeUseDefaultNumberOfShards() {
+        useDefaultNumberOfShards = usually();
+    }
+
     @Before
     public void initAndResetContext() throws Exception {
         if (restTestExecutionContext == null) {
@@ -318,6 +330,14 @@ public void test() throws IOException {
             throw new IllegalArgumentException("No executable sections loaded for [" + testCandidate.getTestPath() + "]");
         }
 
+        if (useDefaultNumberOfShards == false
+                && testCandidate.getTestSection().getSkipSection().getFeatures().contains("default_shards") == false) {
+            final Request request = new Request("PUT", "/_template/global");
+            request.setHeaders(new BasicHeader("Content-Type", XContentType.JSON.mediaTypeWithoutParameters()));
+            request.setEntity(new StringEntity("{\"index_patterns\":[\"*\"],\"settings\":{\"index.number_of_shards\":2}}"));
+            adminClient().performRequest(request);
+        }
+
         if (!testCandidate.getSetupSection().isEmpty()) {
             logger.debug("start setup test [{}]", testCandidate.getTestPath());
             for (DoSection doSection : testCandidate.getSetupSection().getDoSections()) {
diff --git a/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/Features.java b/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/Features.java
index ab9be65514a96..d074dd82af7a6 100644
--- a/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/Features.java
+++ b/test/framework/src/main/java/org/elasticsearch/test/rest/yaml/Features.java
@@ -37,6 +37,7 @@
 public final class Features {
     private static final List<String> SUPPORTED = unmodifiableList(Arrays.asList(
             "catch_unauthorized",
+            "default_shards",
             "embedded_stash_key",
             "headers",
             "stash_in_key",
diff --git a/x-pack/qa/sql/security/src/test/java/org/elasticsearch/xpack/qa/sql/security/RestSqlSecurityIT.java b/x-pack/qa/sql/security/src/test/java/org/elasticsearch/xpack/qa/sql/security/RestSqlSecurityIT.java
index 5833ef6dae5a1..f7abb6f64f63c 100644
--- a/x-pack/qa/sql/security/src/test/java/org/elasticsearch/xpack/qa/sql/security/RestSqlSecurityIT.java
+++ b/x-pack/qa/sql/security/src/test/java/org/elasticsearch/xpack/qa/sql/security/RestSqlSecurityIT.java
@@ -236,11 +236,7 @@ public void testHijackScrollFails() throws Exception {
         createAuditLogAsserter()
             .expectSqlCompositeAction("test_admin", "test")
             .expect(true, SQL_ACTION_NAME, "full_access", empty())
-            // One scroll access denied per shard
-            .expect("access_denied", SQL_ACTION_NAME, "full_access", "default_native", empty(), "InternalScrollSearchRequest")
-            .expect("access_denied", SQL_ACTION_NAME, "full_access", "default_native", empty(), "InternalScrollSearchRequest")
-            .expect("access_denied", SQL_ACTION_NAME, "full_access", "default_native", empty(), "InternalScrollSearchRequest")
-            .expect("access_denied", SQL_ACTION_NAME, "full_access", "default_native", empty(), "InternalScrollSearchRequest")
+            // one scroll access denied per shard
             .expect("access_denied", SQL_ACTION_NAME, "full_access", "default_native", empty(), "InternalScrollSearchRequest")
             .assertLogs();
     }
