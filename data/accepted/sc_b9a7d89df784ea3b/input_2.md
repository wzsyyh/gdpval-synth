# ChickenEvaluator


# Seed Material: elastic/elasticsearch#140645: 🐔 Add CHICKEN function to ES|QL
Source: github_issue_pr
Identifier: pr:elastic/elasticsearch#140645

Repository: elastic/elasticsearch
PR Number: #140645
PR Title: 🐔 Add CHICKEN function to ES|QL
Merged At: 2026-01-15T18:17:19Z
Changed Files: 9
Additions: +1240, Deletions: -0

## PR Description
## Summary
Over the past few months, various flavors of a "chicken" feature have been discussed in hallway conversations, Slack threads, design documents, and occasional late-night brainstorming sessions. Ideas ranged from chicken-based joins to poultry-powered predicates.

This PR changes that and introduce the CHICKEN function that finally unlocks the poultry power of ES|QL. 🐣

## What does it do?

The CHICKEN function wraps any text message in ASCII art of a chicken saying the message.

Example usage:

```
ROW CHICKEN("Hello from ES|QL!")
```

```
 ____________________
< Hello from ES|QL! >
 --------------------
         \
          \__//
          /.__.\
          \ \/ /
       '__/    \
        \-      )
         \_____/
      _____|_|____
           " "
```


It is also possible to use the emoji function driven pattern syntax:

```
ROW `🐔`("Hello from ES|QL!")
```

## Features

🎯 Single argument: Pass any keyword or text message
📏 Smart text wrapping: Long messages automatically wrap to fit the speech bubble
🎨 Authentic ASCII art: A lovingly crafted chicken ready to deliver your messages

"With great power comes great poultry." 🐔

## Diff (first 3000 chars)
diff --git a/docs/changelog/140645.yaml b/docs/changelog/140645.yaml
new file mode 100644
index 0000000000000..7c193bf4ef956
--- /dev/null
+++ b/docs/changelog/140645.yaml
@@ -0,0 +1,5 @@
+pr: 140645
+summary: 🐔 Add CHICKEN function to ES|QL
+area: ES|QL
+type: feature
+issues: []
diff --git a/x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java b/x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java
new file mode 100644
index 0000000000000..563d7c8528815
--- /dev/null
+++ b/x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java
@@ -0,0 +1,160 @@
+// Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
+// or more contributor license agreements. Licensed under the Elastic License
+// 2.0; you may not use this file except in compliance with the Elastic License
+// 2.0.
+package org.elasticsearch.xpack.esql.expression.function.scalar.string;
+
+import java.lang.IllegalArgumentException;
+import java.lang.Override;
+import java.lang.String;
+import java.util.function.Function;
+import org.apache.lucene.util.BytesRef;
+import org.apache.lucene.util.RamUsageEstimator;
+import org.elasticsearch.compute.data.Block;
+import org.elasticsearch.compute.data.BytesRefBlock;
+import org.elasticsearch.compute.data.BytesRefVector;
+import org.elasticsearch.compute.data.Page;
+import org.elasticsearch.compute.operator.BreakingBytesRefBuilder;
+import org.elasticsearch.compute.operator.DriverContext;
+import org.elasticsearch.compute.operator.EvalOperator;
+import org.elasticsearch.compute.operator.Warnings;
+import org.elasticsearch.core.Releasables;
+import org.elasticsearch.xpack.esql.core.tree.Source;
+
+/**
+ * {@link EvalOperator.ExpressionEvaluator} implementation for {@link Chicken}.
+ * This class is generated. Edit {@code EvaluatorImplementer} instead.
+ */
+public final class ChickenEvaluator implements EvalOperator.ExpressionEvaluator {
+  private static final long BASE_RAM_BYTES_USED = RamUsageEstimator.shallowSizeOfInstance(ChickenEvaluator.class);
+
+  private final Source source;
+
+  private final BreakingBytesRefBuilder scratch;
+
+  private final EvalOperator.ExpressionEvaluator message;
+
+  private final ChickenArtBuilder chickenStyle;
+
+  private final int width;
+
+  private final DriverContext driverContext;
+
+  private Warnings warnings;
+
+  public ChickenEvaluator(Source source, BreakingBytesRefBuilder scratch,
+      EvalOperator.ExpressionEvaluator message, ChickenArtBuilder chickenStyle, int width,
+      DriverContext driverContext) {
+    this.source = source;
+    this.scratch = scratch;
+    this.message = message;
+    this.chickenStyle = chickenStyle;
+    this.width = width;
+    this.driverContext = driverContext;
+  }
+
+  @Override
+  public Block eval(Page page) {
+    try (BytesRefBlock message