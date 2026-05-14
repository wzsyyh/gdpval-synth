# PR #4721 diff: src/pubsub


# Seed Material: redis/redis#4721: Boost up performance for redis PUB-SUB patterns matching
Source: github_issue_pr
Identifier: pr:redis/redis#4721

Repository: redis/redis
PR Number: #4721
PR Title: Boost up performance for redis PUB-SUB patterns matching
Merged At: 2020-03-31T10:42:19Z
Changed Files: 3
Additions: +48, Deletions: -12

## PR Description
If lots of clients `PSUBSCRIBE` to same patterns, multiple patterns matching will take place. This commit change it into just one single pattern matching by using a `dict *` to store the unique pattern and which clients subscribe to it.

For example, if there are two clients `PSUBSCRIBE f*o` and one clients `PSUBSCRIBE b*r`, redis will perform pattern match 3 times:

![7](https://user-images.githubusercontent.com/3157740/36828546-78d6d2fe-1d55-11e8-86ab-e99b5c1c4bcc.png)

After the modification by this commit, it will only perform 2 times of pattern match:

![8](https://user-images.githubusercontent.com/3157740/36828569-96709750-1d55-11e8-8b8b-0b01a73a0f49.png)

So when there is 100 clients subscribe the same pattern, this commit will reduce the pattern match time from 100 to 1. **This feature is already tested and run in production environment at Alibaba Group without any issue for about 2 months.**

## Diff (first 3000 chars)
diff --git a/src/pubsub.c b/src/pubsub.c
index d1fffa20a72..bbcfc1f43b5 100644
--- a/src/pubsub.c
+++ b/src/pubsub.c
@@ -125,6 +125,8 @@ int pubsubUnsubscribeChannel(client *c, robj *channel, int notify) {
 
 /* Subscribe a client to a pattern. Returns 1 if the operation succeeded, or 0 if the client was already subscribed to that pattern. */
 int pubsubSubscribePattern(client *c, robj *pattern) {
+    dictEntry *de;
+    list *clients;
     int retval = 0;
 
     if (listSearchKey(c->pubsub_patterns,pattern) == NULL) {
@@ -136,6 +138,16 @@ int pubsubSubscribePattern(client *c, robj *pattern) {
         pat->pattern = getDecodedObject(pattern);
         pat->client = c;
         listAddNodeTail(server.pubsub_patterns,pat);
+        /* Add the client to the pattern -> list of clients hash table */
+        de = dictFind(server.pubsub_patterns_dict,pattern);
+        if (de == NULL) {
+            clients = listCreate();
+            dictAdd(server.pubsub_patterns_dict,pattern,clients);
+            incrRefCount(pattern);
+        } else {
+            clients = dictGetVal(de);
+        }
+        listAddNodeTail(clients,c);
     }
     /* Notify the client */
     addReply(c,shared.mbulkhdr[3]);
@@ -148,6 +160,8 @@ int pubsubSubscribePattern(client *c, robj *pattern) {
 /* Unsubscribe a client from a channel. Returns 1 if the operation succeeded, or
  * 0 if the client was not subscribed to the specified channel. */
 int pubsubUnsubscribePattern(client *c, robj *pattern, int notify) {
+    dictEntry *de;
+    list *clients;
     listNode *ln;
     pubsubPattern pat;
     int retval = 0;
@@ -160,6 +174,18 @@ int pubsubUnsubscribePattern(client *c, robj *pattern, int notify) {
         pat.pattern = pattern;
         ln = listSearchKey(server.pubsub_patterns,&pat);
         listDelNode(server.pubsub_patterns,ln);
+        /* Remove the client from the pattern -> clients list hash table */
+        de = dictFind(server.pubsub_patterns_dict,pattern);
+        serverAssertWithInfo(c,NULL,de != NULL);
+        clients = dictGetVal(de);
+        ln = listSearchKey(clients,c);
+        serverAssertWithInfo(c,NULL,ln != NULL);
+        listDelNode(clients,ln);
+        if (listLength(clients) == 0) {
+            /* Free the list and associated hash entry at all if this was
+             * the latest client. */
+            dictDelete(server.pubsub_patterns_dict,pattern);
+        }
     }
     /* Notify the client */
     if (notify) {
@@ -225,6 +251,7 @@ int pubsubUnsubscribeAllPatterns(client *c, int notify) {
 int pubsubPublishMessage(robj *channel, robj *message) {
     int receivers = 0;
     dictEntry *de;
+    dictIterator *di;
     listNode *ln;
     listIter li;
 
@@ -247,25 +274,32 @@ int pubsubPublishMessage(robj *channel, robj *message) {
         }
     }
     /* Send to clients listening to matching channels */
-    if (listLength(server.pubsub_patterns)) {
-        listRewind(server.pubsub_patterns,&li);
+    di = dictGetIterator(server.pub