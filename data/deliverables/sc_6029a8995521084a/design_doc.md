# Design Document: Replacing fast_float C++ Library with Pure C Implementation

# Design Document: Replacing fast_float C++ Library with Pure C Implementation

## Overview

This design document captures the rationale and technical approach for PR #14661, merged on 2026-04-15, which replaces the bundled `deps/fast_float` C++ library with a minimal pure C implementation for floating-point parsing in Redis. The change introduces 600 lines of new code while removing 3995 lines of the previous C++ template library, resulting in a net reduction of complexity and the complete elimination of the C++ (libstdc++) build dependency from the Redis project.

The primary motivation was to simplify the Redis build process. The C++ fast_float library required the g++ toolchain and libstdc++ to be present during compilation and linking, which is not guaranteed in minimal Linux distributions or embedded systems environments. By replacing it with a single-file C implementation (`src/fast_float_strtod.c`), Redis can now be built with just a C compiler (gcc), making the build process more accessible and robust.

The new implementation preserves full correctness and performance for the vast majority of cases through a two-tier parsing strategy: a fast path based on Clinger's algorithm handles numbers with mantissa <= 2^53 and exponent in the range [-22, 22] (covering ~99% of real-world inputs), while a fallback to the standard `strtod()` function ensures correctly-rounded results for all edge cases. This approach was validated with over 10,000 test cases, including special values (infinity, NaN) and random inputs.

## Motivation

Redis is a project written in C. The prior dependency on the fast_float C++ library introduced an unnecessary and problematic requirement for a C++ compiler (`g++`) and its standard library (`libstdc++`). As stated in the PR description, "there is no reason to depend on C++ in a project written in C."

This dependency caused practical issues. The Redis build process would fail in environments where `g++` was not installed, which is a common situation even on Linux distributions that have the basic C build tools (`gcc`) installed. Furthermore, Redis is sometimes compiled for embedded systems that lack the `g++` toolchain entirely, making the build impossible without complex workarounds.

The core goal was to make the build process of Redis "the simplest possible". Removing the C++ dependency achieves this by ensuring that only a standard C compiler is required. This reduces the barrier to entry for developers and system administrators, simplifies CI environments, and aligns the build toolchain with the language of the project itself.

## Technical Design

The new implementation in `src/fast_float_strtod.c` and `src/fast_float_strtod.h` replaces the 3800-line C++ template library with approximately 360 lines of pure C code. The design follows a two-tier strategy to balance performance with correctness.

**Fast Path (Clinger's Algorithm)**: For the common case of decimal floating-point numbers where the mantissa (significand) can be represented exactly in 53 bits (i.e., <= 2^53) and the exponent is within the range of -22 to 22, the algorithm computes the value directly using integer arithmetic. This fast path is highly optimized and is estimated to cover approximately 99% of real-world floating-point parsing cases encountered by Redis (e.g., scores, weights, configuration values).

**Fallback to `strtod()`**: For any input that does not meet the criteria for the fast path—such as numbers with very large exponents, very long mantissas, or special values—the implementation falls back to the standard C library function `strtod()`. This ensures that all inputs are parsed correctly with properly rounded results, maintaining full compatibility with the behavior expected by Redis commands and data structures.

## API Changes

The replacement involved introducing a new API and updating all internal call sites that previously used the fast_float C++ interface. The primary new function is `fast_float_strtod(const char*, size_t, ...)`. This function takes a character pointer and a length, providing a safer, length-based interface compared to null-terminated string alternatives.

All relevant floating-point parsing within the Redis source code was updated to use this new function. The key call sites that were modified include:

- **RESP Double Parsing**: The protocol parser that handles double values in the Redis Serialization Protocol (RESP) was updated.

- **Zset Score Parsing**: The code that parses scores for sorted set (zset) commands now uses the new implementation.

- **DEBUG SLEEP Command**: The parsing of the sleep duration argument in the `DEBUG SLEEP` command was also migrated.

Additionally, the `string2d` helper function was tightened to ensure it rejects partial parses. This means it will only accept strings where the entire input represents a valid floating-point number, improving data integrity.

## Build & CI Impact

The change significantly simplifies the Redis build system and continuous integration (CI) pipelines. The entire `deps/fast_float` directory, which contained the C++ library and its build rules, was removed from the dependency tree.

Consequently, the linker flag `-lstdc++` was dropped from the build process, as the pure C implementation has no dependency on the C++ standard library. The new implementation file `fast_float_strtod.c` was moved into the `src/` directory as it no longer requires a separate dependency folder.

The CI workflows were updated to reflect the reduced build requirements. Specific changes were made to:

- **`.github/workflows/ci.yml`**: Installation commands for `g++-multilib` and `gcc-c++` were removed from jobs like `build-32bit` and `build-fedora`.

- **`.github/workflows/daily.yml`**: Similar removal of `g++` installation from multiple jobs, including the `test-fedora` and `test-valgrind` configurations.

These changes ensure that CI environments only install the necessary C compiler, reducing setup time and potential points of failure.

## Testing & Validation

Rigorous testing was performed to ensure the new implementation is correct and robust. The PR description states the implementation was tested against both the standard `strtod` function and the original C++ fast_float library.

The test suite comprised over 10,000 test cases, covering:

- **Edge Cases**: Numbers with extreme precision requirements, boundary values for mantissa and exponent limits.

- **Special Values**: Inputs representing positive/negative infinity (`inf`) and Not-a-Number (`NaN`).

- **Random Inputs**: A large set of randomly generated floating-point strings to ensure statistical coverage.

To integrate this testing into the Redis development workflow, two new test assets were added:

- A dedicated `fastfloat` unit test to validate the core parsing logic in isolation.

- A `SORT` regression test to ensure the correct behavior of sorted set operations that rely on score parsing.

## Risk Assessment

The change was assessed as **Medium Risk** by the automated Cursor Bugbot review system. This rating is appropriate given the nature of the modification.

The primary risk stems from altering a core component—the floating-point parser—that is fundamental to how Redis interprets numeric data. Incorrect parsing could affect the semantics of numerous commands, including those for sorted sets (scores), Lua scripting (numbers), and configuration settings.

The risk is further compounded by the need to handle edge cases and special values (like `inf` and `NaN`) correctly across different platforms. While the two-tier design and extensive testing mitigate this risk, any subtle behavioral difference between the new implementation and the old one (or `strtod`) could potentially lead to data inconsistencies or command failures.

Therefore, the change required careful review and validation, which was achieved through the comprehensive test suite described above.
