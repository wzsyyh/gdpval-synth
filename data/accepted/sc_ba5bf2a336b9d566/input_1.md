# PR description with benchmark results and ratios


# Seed Material: numpy/numpy#22315: ENH: Vectorize quicksort for 16-bit and 64-bit dtype using AVX512
Source: github_issue_pr
Identifier: pr:numpy/numpy#22315

Repository: numpy/numpy
PR Number: #22315
PR Title: ENH: Vectorize quicksort for 16-bit and 64-bit dtype using AVX512
Merged At: 2023-02-15T12:01:17Z
Changed Files: 19
Additions: +390, Deletions: -941

## PR Description
This patch adds AVX512 based 64-bit on AVX512-SKX and 16-bit sorting on AVX512-ICL. All the AVX512 sorting code has been reformatted as a separate header files and put in a separate folder. The AVX512 64-bit sorting is nearly 10x faster and AVX512 16-bit sorting is nearly 16x faster when compared to `std::sort`. ~~Still working on running NumPy benchmarks to get exact benchmark numbers~~

16-bit int sped up by **17x** and float64 by nearly **10x** for random arrays. Benchmarked on a 11th Gen Tigerlake i7-1165G7. 

```
      before           after         ratio
     [41b6ac0e]       [2b384ac6]
     <main>           <avxsort> 
-        44.2±1μs       41.8±0.5μs     0.95  bench_function_base.Sort.time_sort('quick', 'float32', ('sorted_block', 100))
-      39.7±0.1μs      37.1±0.02μs     0.93  bench_function_base.Sort.time_sort('quick', 'int32', ('sorted_block', 1000))
-        45.7±3μs       42.6±0.4μs     0.93  bench_function_base.Sort.time_sort('quick', 'float32', ('random',))
-      39.8±0.1μs       37.1±0.4μs     0.93  bench_function_base.Sort.time_sort('quick', 'int32', ('random',))
-     39.1±0.03μs      36.4±0.03μs     0.93  bench_function_base.Sort.time_sort('quick', 'int32', ('sorted_block', 100))
-      39.9±0.1μs       37.1±0.2μs     0.93  bench_function_base.Sort.time_sort('quick', 'int32', ('reversed',))
-      39.4±0.2μs       36.3±0.2μs     0.92  bench_function_base.Sort.time_sort('quick', 'int32', ('ordered',))
-     40.6±0.03μs       37.1±0.3μs     0.91  bench_function_base.Sort.time_sort('quick', 'uint32', ('sorted_block', 100))
-      46.4±0.7μs       41.8±0.4μs     0.90  bench_function_base.Sort.time_sort('quick', 'float32', ('ordered',))
-      40.5±0.4μs       36.4±0.1μs     0.90  bench_function_base.Sort.time_sort('quick', 'int32', ('sorted_block', 10))
-        42.5±1μs      37.5±0.08μs     0.88  bench_function_base.Sort.time_sort('quick', 'uint32', ('sorted_block', 1000))
-        42.4±1μs       36.8±0.4μs     0.87  bench_function_base.Sort.time_sort('quick', 'uint32', ('ordered',))
-        43.4±3μs       37.4±0.2μs     0.86  bench_function_base.Sort.time_sort('quick', 'uint32', ('sorted_block', 10))
-        44.5±1μs         38.0±1μs     0.85  bench_function_base.Sort.time_sort('quick', 'uint32', ('reversed',))
-        81.7±4μs       67.9±0.2μs     0.83  bench_function_base.Sort.time_sort('quick', 'float64', ('ordered',))
-        45.7±1μs       37.6±0.2μs     0.82  bench_function_base.Sort.time_sort('quick', 'uint32', ('random',))
-       119±0.6μs       77.7±0.2μs     0.65  bench_function_base.Sort.time_sort('quick', 'int64', ('reversed',))
-         136±5μs       67.1±0.3μs     0.49  bench_function_base.Sort.time_sort('quick', 'float64', ('reversed',))
-     70.6±0.03μs      33.9±0.07μs     0.48  bench_function_base.Sort.time_sort('quick', 'int16', ('ordered',))
-         113±1μs       34.8±0.1μs     0.31  bench_function_base.Sort.time_sort('quick', 'int16', ('reversed',))
-         325±9μs      80.9±0.07μs     0.25  bench_function_base.Sort.time_sort('quick', 'int64', ('sorted_block', 1000))
-         452±8μs         85.7±4μs     0.19  bench_function_base.Sort.time_sort('quick', 'int64', ('sorted_block', 100))
-         386±5μs       70.3±0.6μs     0.18  bench_function_base.Sort.time_sort('quick', 'float64', ('sorted_block', 1000))
-         460±5μs         82.0±3μs     0.18  bench_function_base.Sort.time_sort('quick', 'int64', ('sorted_block', 10))
-      94.5±0.5ms       14.2±0.4ms     0.15  bench_function_base.Sort.time_sort_worst
-        537±10μs         80.8±2μs     0.15  bench_function_base.Sort.time_sort('quick', 'int64', ('random',))
-        518±10μs         73.9±3μs     0.14  bench_function_base.Sort.time_sort('quick', 'float64', ('sorted_block', 100))
-        533±20μs       74.5±0.3μs     0.14  bench_function_base.Sort.time_sort('quick', 'float64', ('sorted_block', 10))
-        70.3±1μs       8.54±0.2μs     0.12  bench_function_base.Sort.time_sort('

## Diff (first 3000 chars)
diff --git a/.gitmodules b/.gitmodules
index 1ea274daf3b9..d849a3caf5c2 100644
--- a/.gitmodules
+++ b/.gitmodules
@@ -4,3 +4,6 @@
 [submodule "numpy/core/src/umath/svml"]
 	path = numpy/core/src/umath/svml
 	url = https://github.com/numpy/SVML.git
+[submodule "numpy/core/src/npysort/x86-simd-sort"]
+	path = numpy/core/src/npysort/x86-simd-sort
+	url = https://github.com/intel/x86-simd-sort
diff --git a/azure-pipelines.yml b/azure-pipelines.yml
index 18b72f49081c..7657ab87f996 100644
--- a/azure-pipelines.yml
+++ b/azure-pipelines.yml
@@ -184,6 +184,9 @@ stages:
     - script: /bin/bash -c "! vulture . --min-confidence 100 --exclude doc/,numpy/distutils/ | grep 'unreachable'"
       displayName: 'Check for unreachable code paths in Python modules'
 
+    - script: git submodule update --init
+      displayName: 'Fetch submodules'
+
     # prefer usage of clang over gcc proper
     # to match likely scenario on many user mac machines
     - script: python setup.py build -j 4 build_src --verbose-cfg install
diff --git a/azure-steps-windows.yml b/azure-steps-windows.yml
index 318f4639880d..a147ffd7ab6d 100644
--- a/azure-steps-windows.yml
+++ b/azure-steps-windows.yml
@@ -1,4 +1,6 @@
 steps:
+- script: git submodule update --init
+  displayName: 'Fetch submodules'
 - task: UsePythonVersion@0
   inputs:
     versionSpec: $(PYTHON_VERSION)
diff --git a/benchmarks/benchmarks/bench_function_base.py b/benchmarks/benchmarks/bench_function_base.py
index 2e44ff76b6b2..cc37bef3994b 100644
--- a/benchmarks/benchmarks/bench_function_base.py
+++ b/benchmarks/benchmarks/bench_function_base.py
@@ -248,7 +248,7 @@ class Sort(Benchmark):
         # In NumPy 1.17 and newer, 'merge' can be one of several
         # stable sorts, it isn't necessarily merge sort.
         ['quick', 'merge', 'heap'],
-        ['float64', 'int64', 'float32', 'uint32', 'int32', 'int16'],
+        ['float64', 'int64', 'float32', 'uint32', 'int32', 'int16', 'float16'],
         [
             ('random',),
             ('ordered',),
diff --git a/numpy/core/meson.build b/numpy/core/meson.build
index 27d7ab851e1d..eea31faace96 100644
--- a/numpy/core/meson.build
+++ b/numpy/core/meson.build
@@ -453,6 +453,11 @@ if cc.get_id() == 'msvc'
      staticlib_cflags +=  '-d2VolatileMetadata-'
    endif
 endif
+# TODO: change to "feature" option in meson_options.txt? See
+# https://mesonbuild.com/Build-options.html#build-options
+if get_option('disable-simd-optimizations')
+  staticlib_cflags += '-DNPY_DISABLE_OPTIMIZATION'
+endif
 
 npy_math_internal_h = custom_target(
   output: 'npy_math_internal.h',
@@ -594,7 +599,8 @@ np_core_dep = declare_dependency(
     '.',
     'include',
     'src/common',
-  ]
+  ],
+  compile_args: disable_simd_optimizations
 )
 
 
@@ -718,7 +724,8 @@ src_multiarray = [
   'src/multiarray/usertypes.c',
   'src/multiarray/vdot.c',
   src_file.process('src/common/npy_sort.h.src'),
-  'src/npysort/x86-qsort.dispatch.cpp',
+  'src/npysort/simd_qsort.dispatch.cpp',
+  'src/npys