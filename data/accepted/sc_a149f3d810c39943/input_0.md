# PR #14048 diff (3 changed files: src/Makefile, src/lolwut


# Seed Material: redis/redis#14048: LOLWUT for Redis 8.
Source: github_issue_pr
Identifier: pr:redis/redis#14048

Repository: redis/redis
PR Number: #14048
PR Title: LOLWUT for Redis 8.
Merged At: 2025-05-26T06:27:46Z
Changed Files: 3
Additions: +182, Deletions: -1

## PR Description
# Add LOLWUT 8: TAPE MARK I - Computer Poetry Generation

This PR introduces LOLWUT 8, implementing Nanni Balestrini's groundbreaking TAPE MARK I algorithm from 1962 - one of the first experiments in computer-generated poetry.

## Background

TAPE MARK I, created by Italian poet Nanni Balestrini and published in Almanacco Letterario Bompiani (1962), represents a [pioneering moment in computational creativity](https://en.wikipedia.org/wiki/Digital_poetry). Using an IBM 7090 mainframe, Balestrini developed an algorithm that combines verses from three different literary sources:

1. **Diary of Hiroshima** by Michihito Hachiya
2. **The Mystery of the Elevator** by Paul Goldwin  
3. **Tao Te Ching** by Lao Tse

The algorithm selects and arranges verses based on metrical compatibility rules and ensures alternation between different literary sources, creating unique poetic combinations with each execution.

## Implementation

This LOLWUT command faithfully reproduces Balestrini's original algorithm.
The main difference is that the default output is in English, and not in Italian. However it should be noted that Balestrini used three poems that were not in Italian anyway, so the translation process was already part of it. In the English versions, sometimes I operated minimal changes in order to preserve either the metric, or to make sure that the sentence stands on its own (like adding "it" before expands rapidly).

## Cultural Significance

TAPE MARK I predates most computational art experiments and demonstrates the early intersection of literature, technology, and algorithmic creativity. This implementation honors that pioneering work while making it accessible to a modern audience through Redis's LOLWUT tradition.

Each execution generates a unique poem, just as Balestrini intended.

Trivia: the original code, running on an IBM 7090, used six minutes to generate each verse :D

**IMPORTANT** This commit should be back-ported to Redis 8.


## Diff
diff --git a/src/Makefile b/src/Makefile
index 6cfac4aac13..4b86468b6a6 100644
--- a/src/Makefile
+++ b/src/Makefile
@@ -375,7 +375,7 @@ endif
 
 REDIS_SERVER_NAME=redis-server$(PROG_SUFFIX)
 REDIS_SENTINEL_NAME=redis-sentinel$(PROG_SUFFIX)
-REDIS_SERVER_OBJ=threads_mngr.o adlist.o quicklist.o ae.o anet.o dict.o ebuckets.o eventnotifier.o iothread.o mstr.o kvstore.o server.o sds.o zmalloc.o lzf_c.o lzf_d.o pqsort.o zipmap.o sha1.o ziplist.o release.o networking.o util.o object.o db.o replication.o rdb.o t_string.o t_list.o t_set.o t_zset.o t_hash.o config.o aof.o pubsub.o multi.o debug.o sort.o intset.o syncio.o cluster.o cluster_legacy.o crc16.o endianconv.o slowlog.o eval.o bio.o rio.o rand.o memtest.o syscheck.o crcspeed.o crccombine.o crc64.o bitops.o sentinel.o notify.o setproctitle.o blocked.o hyperloglog.o latency.o sparkline.o redis-check-rdb.o redis-check-aof.o geo.o lazyfree.o module.o evict.o expire.o geohash.o geohash_helper.o childinfo.o defrag.o siphash.o rax.o t_stream.o listpack.o localtime.o lolwut.o lolwut5.o lolwut6.o acl.o tracking.o socket.o tls.o sha256.o timeout.o setcpuaffinity.o monotonic.o mt19937-64.o resp_parser.o call_reply.o script_lua.o script.o functions.o function_lua.o commands.o strl.o connection.o unix.o logreqres.o
+REDIS_SERVER_OBJ=threads_mngr.o adlist.o quicklist.o ae.o anet.o dict.o ebuckets.o eventnotifier.o iothread.o mstr.o kvstore.o server.o sds.o zmalloc.o lzf_c.o lzf_d.o pqsort.o zipmap.o sha1.o ziplist.o release.o networking.o util.o object.o db.o replication.o rdb.o t_string.o t_list.o t_set.o t_zset.o t_hash.o config.o aof.o pubsub.o multi.o debug.o sort.o intset.o syncio.o cluster.o cluster_legacy.o crc16.o endianconv.o slowlog.o eval.o bio.o rio.o rand.o memtest.o syscheck.o crcspeed.o crccombine.o crc64.o bitops.o sentinel.o notify.o setproctitle.o blocked.o hyperloglog.o latency.o sparkline.o redis-check-rdb.o redis-check-aof.o geo.o lazyfree.o module.o evict.o expire.o geohash.o geohash_helper.o childinfo.o defrag.o siphash.o rax.o t_stream.o listpack.o localtime.o lolwut.o lolwut5.o lolwut6.o lolwut8.o acl.o tracking.o socket.o tls.o sha256.o timeout.o setcpuaffinity.o monotonic.o mt19937-64.o resp_parser.o call_reply.o script_lua.o script.o functions.o function_lua.o commands.o strl.o connection.o unix.o logreqres.o
 REDIS_CLI_NAME=redis-cli$(PROG_SUFFIX)
 REDIS_CLI_OBJ=anet.o adlist.o dict.o redis-cli.o zmalloc.o release.o ae.o redisassert.o crcspeed.o crccombine.o crc64.o siphash.o crc16.o monotonic.o cli_common.o mt19937-64.o strl.o cli_commands.o
 REDIS_BENCHMARK_NAME=redis-benchmark$(PROG_SUFFIX)
diff --git a/src/lolwut.c b/src/lolwut.c
index 3017f7aa5ff..8467c7803bb 100644
--- a/src/lolwut.c
+++ b/src/lolwut.c
@@ -19,6 +19,7 @@
 
 void lolwut5Command(client *c);
 void lolwut6Command(client *c);
+void lolwut8Command(client *c);
 
 /* The default target for LOLWUT if no matching version was found.
  * This is what unstable versions of Redis will display. */
@@ -54,6 +55,9 @@ void lolwutCommand(client *c) {
     else if ((v[0] == '6' && v[1] == '.' && v[2] != '9') ||
              (v[0] == '5' && v[1] == '.' && v[2] == '9'))
         lolwut6Command(c);
+    else if ((v[0] == '8' && v[1] == '.' && v[2] != '9') ||
+             (v[0] == '7' && v[1] == '.' && v[2] == '9'))
+        lolwut8Command(c);
     else
         lolwutUnstableCommand(c);
 
diff --git a/src/lolwut8.c b/src/lolwut8.c
new file mode 100644
index 00000000000..1be150e6e0c
--- /dev/null
+++ b/src/lolwut8.c
@@ -0,0 +1,177 @@
+/*
+ * Copyright (c) 2025-Present, Redis Ltd.
+ * All rights reserved.
+ *
+ * Licensed under your choice of (a) the Redis Source Available License 2.0
+ * (RSALv2); or (b) the Server Side Public License v1 (SSPLv1); or (c) the
+ * GNU Affero General Public License v3 (AGPLv3).
+ *
+ * Originally authored by: Salvatore Sanfilippo.
+ * Algorithm based on the Almanacco Bompiani description and the Python
+ * code written by Emiliano Russo.
+ */
+
+#include "server.h"
+#include <ctype.h>
+
+/* The LOLWUT 8 command:
+ *
+ * LOLWUT [EN|IT]
+ *
+ * By default the command produces verses in English language, in order for
+ * the output to be more universally accessible. However, passing IT as argument
+ * it is possible to reproduce the original output, exactly like done by
+ * Nanni Balestrini in TAPE MARK I, and described in the Almanacco Letterario
+ * Bompiani, 1962.
+ */
+
+// Structure to represent a verse with its metrical characteristics.
+typedef struct {
+    char text_en[100];    // English verse text.
+    char text_it[100];    // Italian verse text.
+    char fraction1[5];    // First fraction (rhythm/meter indicator).
+    char fraction2[5];    // Second fraction (rhythm/meter indicator).
+    char group[2];        // Group number (1-3 representing different
+                          // literary sources).
+} Verse;
+
+// Fisher-Yates shuffle algorithm to randomize verse order.
+static void shuffle(Verse *array, int size) {
+    for (int i = size - 1; i > 0; i--) {
+        int j = rand() % (i + 1);
+        Verse temp = array[j];
+        array[j] = array[i];
+        array[i] = temp;
+    }
+}
+
+void lolwut8Command(client *c) {
+    int en_lang = 1;  // Default to English.
+
+    /* Parse the optional arguments if any. */
+    if (c->argc > 1 && !strcasecmp(c->argv[1]->ptr,"IT"))
+        en_lang = 0;
+
+    // Define verses from three literary sources with their metrical fractions:
+    // Group 1: Diary of Hiroshima by Michihito Hachiya.
+    // Group 2: The Mystery of the Elevator by Paul Goldwin.
+    // Group 3: Tao Te Ching by Lao Tse.
+    Verse verses[] = {
+        // Group 1: Hiroshima verses.
+        {" The blinding / globe / of fire ",
+         " l accecante   /  globo  /  di fuoco  ", "1/4", "2/3", "1"},
+        {" It expands / rapidly ",
+         " si espande   /  rapidamente  ", "1/2", "3/4", "1"},
+        {" Thirty times / brighter / than the sun ",
+         " trenta volte  / piu luminoso  / del sole ", "2/3", "2/4", "1"},
+        {" When it reaches / the stratosphere ",
+         " quando  raggiunge / la stratosfera  ", "3/4", "1/2", "1"},
+        {" The summit / of the cloud ",
+         " la  sommita  /  della nuvola ", "1/3", "2/3", "1"},
+        {" Assumes / the well-known shape / of a mushroom ",
+         " assume   / la ben nota forma  / di fungo ", "2/4", "3/4", "1"},
+
+        // Group 2: Elevator mystery verses.
+        {" The head / pressed / upon the shoulder ",
+         " la testa / premuta  / sulla spalla  ", "1/4", "2/4", "2"},
+        {" The hair / between the lips ",
+         " i  capelli   /  tra le labbra ", "1/4", "2/4", "2"},
+        {" They lay / motionless / without speaking ",
+         " giacquero  /   immobili / senza parlare ", "2/3", "2/3", "2"},
+        {" Till he moved / his fingers / slowly ",
+         " finche non mosse  /  le dita  / lentamente    ", "3/4", "1/3", "2"},
+        {" Trying / to grasp ",
+         " cercando / di afferrare  ", "3/4", "1/2", "2"},
+
+        // Group 3: Tao Te Ching verses.
+        {" While the multitude / of things / comes into being ",
+         " mentre la moltitudine  /  delle cose  /   accade   ", "1/2", "1/2", "3"},
+        {" I envisage / their return ",
+         " io contemplo  /  il loro ritorno    ", "2/3", "3/4", "3"},
+        {" Although / things / flourish ",
+         " malgrado / che le cose  /  fioriscano    ", "1/2", "2/3", "3"},
+        {" They all return / to / their roots ",
+         " esse tornano  / tutte    / alla loro radice   ", "2/3", "1/4", "3"}
+    };
+
+    // Calculate the total number of verses.
+    int num_verses = sizeof(verses) / sizeof(verses[0]);
+
+    // Create a working copy of verses for manipulation.
+    Verse *working_verses = zmalloc(num_verses * sizeof(Verse));
+    memcpy(working_verses, verses, num_verses * sizeof(Verse));
+
+    // Step 1: Shuffle the verses randomly.
+    shuffle(working_verses, num_verses);
+
+    // Step 2: Build stanza by finding compatible verses
+    // Each subsequent verse must:
+    // - Have compatible metrical fractions (connecting criteria).
+    // - Belong to a different group than the previous verse.
+    Verse stanza[10];
+
+    int j; // At the end, it will contain the number of added stanzas.
+    for (j = 0; j < 10; j++) {
+        int i = 0;
+        int found = 0;
+
+        // Search for compatible verse among remaining verses.
+        while (i < num_verses) {
+            // Metrical compatibility check: this is used to select verses
+            // that go somewhat well together, if their fractions match.
+            // The algorithm checks if current verse's first fraction matches
+            // with previous verse's second fraction in various ways, and
+            // force successive verses to be of different groups.
+            if (j == 0 || // First stanza is always accepted.
+                ((working_verses[i].fraction1[0] == stanza[j-1].fraction2[0] ||
+                  working_verses[i].fraction1[2] == stanza[j-1].fraction2[0] ||
+                  working_verses[i].fraction1[2] == stanza[j-1].fraction2[2]) &&
+                 strcmp(working_verses[i].group, stanza[j-1].group) != 0))
+            {
+
+                // Add compatible verse to stanza.
+                stanza[j] = working_verses[i];
+
+                // Remove selected verse from working set, to avoid reuse.
+                for (int k = i; k < num_verses - 1; k++)
+                    working_verses[k] = working_verses[k + 1];
+                num_verses--;
+
+                found = 1;
+                break;
+            }
+            i++;
+        }
+
+        // Exit if there are no longer matching verses.
+        if (!found) break;
+    }
+    zfree(working_verses);
+
+    // Step 3: Combine all stanza verses into single SDS string.
+    sds combined = sdsempty();
+    for (int i = 0; i < j; i++) {
+        if (en_lang) {
+            combined = sdscat(combined, stanza[i].text_en);
+        } else {
+            combined = sdscat(combined, stanza[i].text_it);
+        }
+        combined = sdscat(combined, "\n");
+    }
+
+    // Step 4: Make uppercase, and strip the "/".
+    for (size_t j = 0; j < sdslen(combined); j++) {
+        combined[j] = toupper(combined[j]);
+        if (combined[j] == '/') combined[j] = ' ';
+    }
+
+    // Step 5: Add background info about what the user just saw.
+    combined = sdscat(combined,
+        "\nIn 1961, Nanni Balestrini created one of the first computer-generated poems, TAPE MARK I, using an IBM 7090 mainframe. Each execution combined verses from three literary sources following algorithmic rules based on metrical compatibility and group constraints. This LOLWUT command reproduces Balestrini's original algorithm, generating new stanzas through the same computational poetry process described in Almanacco Letterario Bompiani, 1962.\n\n"
+        "https://en.wikipedia.org/wiki/Digital_poetry\n"
+        "https://www.youtube.com/watch?v=8i7uFCK7G0o (English subs)\n\n"
+        "Use: LOLWUT IT for the original Italian output.\n\n");
+
+    addReplyVerbatim(c,combined,sdslen(combined),"txt");
+    sdsfree(combined);
+}
