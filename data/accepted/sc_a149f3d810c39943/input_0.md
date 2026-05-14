# PR #14048 diff showing changes to src/Makefile, src/lolwut


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


## Diff (first 3000 chars)
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
@@ -54,6 +55,9 @@ void lolwut