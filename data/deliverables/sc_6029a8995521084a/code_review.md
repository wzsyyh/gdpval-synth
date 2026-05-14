# Code Review: PR #14661 — Replace fast_float C++ Library with Pure C Implementation

# Code Review: PR #14661 — Replace fast_float C++ Library with Pure C Implementation

## Executive Summary

PR #14661, merged on 2026-04-15, replaces the bundled C++ `fast_float` dependency with a pure C implementation. The change spans 19 files with +600 additions and -3995 deletions, yielding a net reduction of approximately 3,395 lines of code. The primary motivation is to eliminate the C++ (libstdc++) build dependency, which caused Redis builds to fail on systems without g++ installed — a common scenario in Linux distributions even after installing basic build tools. The PR description explicitly calls out embedded systems as a key use case where the g++ toolchain may be unavailable, stating: "There is no reason to depend on C++ in a project written in C."

## Architecture and Design Analysis

The new C implementation uses a two-tier parsing strategy. The fast path employs Clinger's algorithm, which handles numbers where the mantissa is <= 2^53 and the exponent is in the range [-22, 22]. The PR description states this fast path covers approximately 99% of real-world floating-point parsing cases, making it highly effective for production workloads.

For the remaining ~1% of cases — numbers with very large exponents, extreme precision requirements, or special values — the implementation falls back to the standard `strtod()` function. This ensures correctly-rounded results for all inputs, maintaining the same semantic guarantees as the original C++ implementation. The design is elegant in that it prioritizes performance for the common case while guaranteeing correctness through the C standard library fallback.

## File-by-File Review

**New Files: `src/fast_float_strtod.c` and `src/fast_float_strtod.h`**

The new implementation is approximately 360 lines of pure C, compared to the 3,800-line C++ template library it replaces. Moving this from the `deps/` directory into `src/` is appropriate since it is now a single file with no separate dependency management needs. The header exposes the `fast_float_strtod(const char*, size_t, ...)` API with a length-based interface, which is more appropriate for Redis's parsing patterns than null-terminated string approaches.

**Removed: `deps/fast_float` Directory**

The entire C++ fast_float dependency directory has been removed, including all template headers and build configurations. This eliminates the static library that was previously linked during the build process.

**Call-Site Updates: `src/util.c` and Others**

The PR updates all call sites to use the new `fast_float_strtod()` API. Key sites include RESP double parsing, zset score parsing, and the DEBUG SLEEP command handler. The `string2d` function in `src/util.c` has been tightened to reject partial parses, which is a correctness improvement — previously, `string2d` might accept a string like "3.14abc" as valid, but now it enforces that the entire input string constitutes a valid floating-point number.

**Build System Changes**

The Makefile has been updated to remove `fast_float` from dependency targets and to drop `-lstdc++` from linker flags. The `.gitignore` has been cleaned up to remove references to the old dependency directory.

**CI Workflow Changes**

Both `.github/workflows/ci.yml` and `daily.yml` have been updated to remove g++/gcc-c++ package installations. Specific changes include:
- `ci.yml`: Removed `g++-multilib` from the 32-bit build step
- `ci.yml`: Removed `gcc-c++` from the Fedora build step
- `ci.yml`: Removed `g++-4.8` and its `update-alternatives` entry from the old toolchain build
- `daily.yml`: Removed `g++` from multiple apt-get install lines across the standard, 32-bit, and valgrind test jobs

## API and Call-Site Migration

The original fast_float library used C++ template functions that took null-terminated strings or iterators. The replacement uses a C function with explicit length parameter: `fast_float_strtod(const char*, size_t len, double *result)`. This length-based API is more natural for Redis, where string lengths are often known from protocol parsing and avoiding unnecessary null-termination checks improves both clarity and safety.

Three primary call sites were migrated:
1. **RESP double parsing**: Where floating-point values are extracted from the Redis Serialization Protocol
2. **Zset score parsing**: Where sorted set scores are converted from string representations
3. **DEBUG SLEEP**: Where the sleep duration argument is parsed as a floating-point number

Additionally, the `string2d` function was modified to enforce complete-string validation. This tightens input validation across all Redis commands that accept floating-point parameters.

## Testing Assessment

The PR description reports comprehensive testing with over 10,000 test cases validated against both the standard `strtod()` function and the original C++ fast_float implementation. This dual-validation approach is sound: it confirms both correctness (matching `strtod` output) and behavioral parity (matching the previous implementation).

The test suite covers:
- Edge cases in floating-point representation
- Special values including infinity and NaN
- Random inputs for statistical coverage

A dedicated `fastfloat` unit test was added to the Redis test suite, and a SORT regression test was included to verify that sorted set operations with floating-point scores continue to work correctly. The Cursor Bugbot review classified this change as **Medium Risk**, noting that "parsing correctness and edge-case behavior could affect command semantics and tests across platforms."

## Risk Assessment

**Parsing Correctness**: The fallback to `strtod()` for edge cases introduces a dependency on platform-specific `strtod` implementations. While the C standard guarantees basic semantics, some embedded platforms may have non-conforming or imprecise `strtod` implementations. The fast path is deterministic and portable, but the fallback path's behavior could vary. This is the primary technical risk of this change.

**Build System Changes**: Downstream package maintainers who had g++ as a build dependency will need to update their packaging scripts. While this is ultimately a simplification, the transition requires communication. The removal of `-lstdc++` from linker flags means any downstream patches that accidentally depend on C++ standard library symbols will fail to link — which is actually desirable as it surfaces latent dependency issues.

**CI Pipeline Modifications**: The CI changes are straightforward removals of g++ package installations across multiple workflows (ci.yml and daily.yml). The risk here is low, as these are purely subtractive changes. However, if any CI job implicitly depended on g++ for reasons other than the fast_float library, those jobs would now fail, serving as a useful diagnostic.

The Cursor Bugbot automated review classified this PR as **Medium Risk**, specifically noting that parsing correctness and edge-case behavior could affect command semantics and tests across platforms.

## Conclusion and Recommendation

PR #14661 is a well-executed simplification that achieves its stated goals. The replacement of the 3,800-line C++ library with a ~360-line C implementation significantly reduces complexity and eliminates the C++ build dependency. The two-tier parsing approach (Clinger's fast path + strtod fallback) provides a good balance of performance and correctness.

The comprehensive testing with 10,000+ cases provides confidence in behavioral parity. The CI changes are clean and consistent across all workflows.

**Recommendation**: Approve. The change is technically sound and aligns with Redis's philosophy of minimal dependencies and simple build processes. Follow-up items: (1) Monitor for any platform-specific `strtod` issues on embedded systems, (2) Consider adding a CI job that explicitly tests on a minimal system without g++ to prevent regression of the C++ dependency.
