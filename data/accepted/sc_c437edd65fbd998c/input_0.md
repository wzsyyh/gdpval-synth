# The diff for PR #30539 from elastic/elasticsearch, showing changes across 43 files, with focus on test infrastructure files like RestTestsFromSnippetsTask


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


## Diff (first 3000 chars)
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
+++ b/client/rest-high-level/src/test/java/org/elasticsearch/client/documentation/SearchDoc