# Full diff of PR redis/redis#14661 (19 files changed, +600 additions, -3995 deletions)


# Seed Material: redis/redis#14661: Replace fast_float C++ library with pure C implementation
Source: github_issue_pr
Identifier: pr:redis/redis#14661

Repository: redis/redis
PR Number: #14661
PR Title: Replace fast_float C++ library with pure C implementation
Merged At: 2026-04-15T12:33:55Z
Changed Files: 19
Additions: +600, Deletions: -3995

## PR Description
The fast_float dependency required C++ (libstdc++) to build Redis. This commit replaces the 3800-line C++ template library with a minimal pure C implementation (~360 lines) that provides the same functionality needed by Redis.

This is **very important** because Redis build process would fail without g++ installed, a common situation in Linux distributions even after installing the basic build tools: we want the build process of Redis to be the simplest possible. Also Redis sometimes is compiled in embedded systems lacking the g++ toolchain. There is no reason to depend on C++ in a project written in C.

## The C implementation uses
1. Fast path (Clinger's algorithm) for numbers with mantissa <= 2^53 and exponent in [-22, 22], covering ~99% of real-world cases.
2. Fallback to strtod() for complex cases to ensure correctly-rounded results.

## Changes
- Move new fast_float_strtod.c(C implementation) from deps into Redis core since it is now a single file and no longer needs a separate directory.
- Remove all c++ dependencies

The implementation was tested against both strtod and the original C++ implementation with 10,000+ test cases including edge cases, special values (inf/nan), and random inputs.


<!-- CURSOR_SUMMARY -->
---

> [!NOTE]
> **Medium Risk**
> Replaces core floating-point parsing and build/link settings to remove C++/`libstdc++` dependencies; parsing correctness and edge-case behavior could affect command semantics and tests across platforms.
> 
> **Overview**
> Replaces the bundled `deps/fast_float` C++ library with a new in-tree C implementation (`src/fast_float_strtod.c`/`.h`) that parses common decimal floats via a fast path and falls back to `strtod` for complex cases.
> 
> Updates all call sites to use the new length-based `fast_float_strtod(const char*, size_t, ...)` API (including RESP double parsing, zset score parsing, and `DEBUG SLEEP`), tightens `string2d` to reject partial parses, and adds a dedicated `fastfloat` unit test plus a SORT regression test.
> 
> Simplifies builds by removing `fast_float` from dependency targets, dropping `-lstdc++` and the `deps/fast_float` static library, cleaning up `.gitignore`/deps `Makefile`, and adjusting CI workflows to no longer install `g++`/`gcc-c++`.
> 
> <sup>Reviewed by [Cursor Bugbot](https://cursor.com/bugbot) for commit 605c2a22fab4d71256582fa69b368408e6a6281c. Bugbot is set up for automated code reviews on this repo. Configure [here](https://www.cursor.com/dashboard/bugbot).</sup>
<!-- /CURSOR_SUMMARY -->

## Diff (first 3000 chars)
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 4fe75a6fa2d..75a8ff62da5 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -62,7 +62,7 @@ jobs:
     - uses: actions/checkout@v4
     - name: make
       run: |
-        sudo apt-get update && sudo apt-get install libc6-dev-i386 gcc-multilib g++-multilib
+        sudo apt-get update && sudo apt-get install libc6-dev-i386 gcc-multilib
         make REDIS_CFLAGS='-Werror' 32bit
 
   build-libc-malloc:
@@ -79,7 +79,7 @@ jobs:
     - uses: actions/checkout@v4
     - name: make
       run: |
-        dnf -y install which gcc gcc-c++ make
+        dnf -y install which gcc make
         make REDIS_CFLAGS='-Werror'
 
   build-old-chain-jemalloc:
@@ -96,7 +96,6 @@ jobs:
         apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 40976EAF437D05B5
         apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32
         apt-get update
-        apt-get install -y make gcc-4.8 g++-4.8
+        apt-get install -y make gcc-4.8
         update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.8 100
-        update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.8 100
         make CC=gcc REDIS_CFLAGS='-Werror'
diff --git a/.github/workflows/daily.yml b/.github/workflows/daily.yml
index fdac6d994c7..36edb75296b 100644
--- a/.github/workflows/daily.yml
+++ b/.github/workflows/daily.yml
@@ -240,7 +240,7 @@ jobs:
         ref: ${{ env.GITHUB_HEAD_REF }}
     - name: make
       run: |
-        apt-get update && apt-get install -y make gcc g++
+        apt-get update && apt-get install -y make gcc
         make CC=gcc REDIS_CFLAGS='-Werror -DREDIS_TEST -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=3'
     - name: testprep
       run: sudo apt-get install -y tcl8.6 tclx procps
@@ -347,7 +347,7 @@ jobs:
         ref: ${{ env.GITHUB_HEAD_REF }}
     - name: make
       run: |
-        sudo apt-get update && sudo apt-get install libc6-dev-i386 g++ gcc-multilib g++-multilib
+        sudo apt-get update && sudo apt-get install libc6-dev-i386 gcc-multilib
         make 32bit REDIS_CFLAGS='-Werror -DREDIS_TEST'
         make -C tests/modules 32bit # the script below doesn't have an argument, we must build manually ahead of time
     - name: testprep
@@ -580,7 +580,7 @@ jobs:
     - name: testprep
       run: |
         sudo apt-get update
-        sudo apt-get install tcl8.6 tclx valgrind g++ -y
+        sudo apt-get install tcl8.6 tclx valgrind -y
     - name: test
       if: true && !contains(github.event.inputs.skiptests, 'redis')
       # Note that valgrind's overhead doesn't pair well with io-threads so we
@@ -645,7 +645,7 @@ jobs:
     - name: testprep
       run: |
         sudo apt-get update
-        sudo apt-get install tcl8.6 tclx valgrind g++ -y
+        sudo apt-get install tcl8.6 tclx valgrind -y
     - name: test
       if: true && !contains(github.event.inputs.skiptests, 'redis')
       run: ./runtest --valgrind --tags -iothreads --no-latency