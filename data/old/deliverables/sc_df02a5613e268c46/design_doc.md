# Design Doc: nodejs/node#56350

## Executive Summary

**Executive Summary**

This document details the design and implementation for enabling TypeScript file execution by default in Node.js without requiring explicit flags. The core change, implemented in PR #56350, unflags the existing `--experimental-strip-types` functionality, making it a default, non-experimental capability. This evolution simplifies the developer experience by allowing direct execution of `.ts` files via the `node` command, provided the TypeScript syntax used aligns with the documented limitations (e.g., no enums, namespaces, or decorators). The change is proposed as a semver minor update to the Node.js runtime.

The primary objective of this proposal is to promote the type-stripping feature from an opt-in experiment to a stable, supported mode of operation. This will catch a broader range of potential bugs through wider adoption and real-world usage ahead of a potential future semver major release. The change modifies Node.js's default behavior, so it includes updates to core documentation and benchmarking suites to reflect the new status. The PR addresses an outstanding issue from the nodejs/typescript repository (issue #17), signaling a maturity milestone for this TypeScript support pathway.

The scope of this change is intentionally focused. Implementation touches two key files within the `nodejs/node` repository: `benchmark/ts/strip-typescript.js` and `doc/api/cli.md`. The benchmark script is updated to ensure performance metrics are collected under the new default condition, validating that no regressions are introduced. The CLI documentation is revised to remove the "experimental" designation, accurately describing the flag's now-default behavior and its supported syntax limitations. This design doc will elaborate on the rationale, backward compatibility considerations, and specific code changes required to execute this transition safely.

## Background

**Background**

The primary change under consideration stems from nodejs/node PR #56350, which proposes to unflag the `--experimental-strip-types` feature, enabling it by default. Currently, this capability is behind an explicit command-line flag. This design doc outlines the rationale and implications of transitioning this experimental feature into a default, stable behavior within the Node.js runtime.

The motivation for this change is to improve the out-of-the-box developer experience for TypeScript users and to leverage broader adoption to surface potential bugs. The TypeScript stripping feature, while functional, has been in an experimental state. The PR asserts that with no open issues against the feature, the time is appropriate to enable it by default to gather more real-world usage data and catch edge cases before a potential future semver-major release. This move acknowledges the growing prevalence of TypeScript in the ecosystem and aims to reduce configuration friction for developers.

The implementation of this change is localized. The `benchmark/ts/strip-typescript.js` file has been updated to reflect the new default behavior in performance testing. Concurrently, `doc/api/cli.md` requires documentation updates to indicate that `--experimental-strip-types` is now enabled by default, ensuring users are aware of the runtime's capabilities without needing to set the flag manually.

## Goals

**Goals**

The primary goal of PR #56350 in the `nodejs/node` repository is to enhance the developer experience by promoting TypeScript type-stripping from an experimental opt-in feature to a default behavior. This change is foundational for improving Node.js's out-of-the-box support for TypeScript, reducing configuration overhead for developers. The specific, measurable objectives for this initiative are as follows:

First, to modify the default runtime behavior so that the `--experimental-strip-types` flag is enabled unconditionally. This is a concrete change to the Node.js startup logic, directly measured by the removal of the flag's requirement for TypeScript file execution. Success is binary: the flag is enabled by default, and TypeScript files execute without additional configuration.

Second, to validate and establish a performance baseline for this new default behavior. The addition of the benchmark file `benchmark/ts/strip-typescript.js` provides the instrument to measure execution overhead. The goal is to confirm that enabling the feature does not introduce performance regressions against this benchmark, ensuring the new default is efficient.

Third, to update all official documentation to reflect the new status and detail the supported syntax limitations. This involves comprehensively reviewing and modifying `doc/api/cli.md` to remove the "experimental" labeling and to ensure all known constraints are clearly communicated. The measurable outcome is a complete and accurate documentation set that aligns with the new default behavior.

Finally, to address the underlying community issue (nodejs/typescript#17) and align with TSC expectations. The PR explicitly aims to "catch some more bugs" by increasing usage and scrutiny. A key goal is to demonstrate stability sufficient for the TSC to approve this as a semver-minor change, thereby advancing the TypeScript integration roadmap.

## Non-Goals

**Non-Goals**

This design explicitly excludes several related areas to maintain a focused scope and manage expectations. First, unflagging `--experimental-strip-types` does not remove its experimental status. The feature remains subject to change, and runtime errors arising from TypeScript syntax limitations documented in `doc/api/cli.md` will not be considered release-blocking regressions. The goal is to gather broader usage data, not to declare the feature stable. A future proposal for stability will require a separate, rigorous review.

Second, this change does not aim to introduce a full TypeScript compiler, type checker, or transpiler into Node.js core. The project's scope is strictly limited to *stripping* type annotations, as implemented and benchmarked in `benchmark/ts/strip-typescript.js`. Support for advanced TypeScript-specific syntax features that require code transformation (e.g., `enum`, decorators, `namespace`) is out of scope. Users requiring such features must continue to use external build tools to generate valid JavaScript before execution.

Finally, this initiative will not guarantee compatibility or optimized behavior with third-party tooling, bundlers, or alternative runtimes. While enabling the feature by default may improve discovery, it does not commit the project to resolving ecosystem tooling conflicts. Adjustments in tools like TypeScript-aware linters or editors are the responsibility of their respective maintainers. The Node.js core team will focus on the execution semantics as defined by the module system and the strip-types loader.

## Proposed Design

**Proposed Design**

The core of this change is a single, high-impact modification: removing the experimental status of the TypeScript type-stripping feature. In the PR #56350 for the `nodejs/node` repository, this is achieved by altering the default state of the `--experimental-strip-types` flag. Instead of requiring users to explicitly opt-in with a flag, Node.js will now enable TypeScript execution by default. This aligns with the project's goal to provide seamless TypeScript support out of the box, reducing initial configuration overhead for users. The technical justification is straightforward: as noted in the PR, there are currently no open blocking issues, indicating the feature has reached a stable state suitable for broader adoption and real-world stress testing by the community.

The change must be precisely reflected in two key areas of the codebase. First, the documentation in `doc/api/cli.md` must be updated to reflect that `--experimental-strip-types` is now enabled by default. The description of the flag should be revised to clarify that its use is now the default behavior, while noting any remaining limitations. Second, the benchmark file `benchmark/ts/strip-typescript.js` must be verified or adjusted to ensure it accurately measures the performance of this newly default behavior. This file is critical for establishing performance baselines and detecting regressions in the core TypeScript stripping logic that all users will now rely upon.

The justification for this design is rooted in maturation and confidence. Enabling the feature by default is a semver-minor change, signaling it is a non-breaking addition to Node.js's capabilities. This approach maximizes the potential for catching latent issues through widespread usage while maintaining backward compatibility for existing JavaScript projects. The documentation and benchmark changes ensure the feature's integration is transparent, well-documented, and performance-monitored, fulfilling the project's standards for core functionality.

## Alternatives Considered

**Alternatives Considered**

The primary alternative to enabling `--experimental-strip-types` by default (as implemented in PR #56350) was to maintain the flag's opt-in status indefinitely. This approach would have preserved complete backward compatibility, as no existing startup behavior or scripting expectations would be altered. However, it fundamentally undermines the goal of providing seamless TypeScript execution out-of-the-box, requiring every new project or script author to discover and configure the flag. This creates friction for adoption and positions TypeScript support as a secondary, "experimental" concern rather than a core, integrated feature, which conflicts with the project's direction.

A second alternative involved a more invasive, lazy-loading architecture where the TypeScript stripping logic (and its dependencies) would only be loaded and initialized upon the first encounter of a `.ts` file during module resolution. The primary tradeoff here concerns startup performance and predictability. While this could theoretically optimize for pure JavaScript workloads by avoiding any upfront cost, it introduces inconsistent startup latency. The first `.ts` import or execution would incur a significant, unpredictable delay as the transpiler is loaded and initialized, which is detrimental to developer experience and complicates performance profiling. The decision to unflag by default, as validated in the benchmark file `benchmark/ts/strip-typescript.js`, prioritizes consistent and measurable startup overhead over the marginal benefit of a zero-cost baseline for non-TypeScript users.

Finally, a third alternative was to ship a dedicated, standalone executable (e.g., `node-ts`) or a CLI wrapper that bundles the necessary TypeScript processing configuration. This would have completely isolated the experimental feature, avoiding any impact on the core `node` binary. The tradeoff is a fragmented tooling experience and added maintenance burden. It would force ecosystem tooling to handle two different entry points, complicate documentation, and create a separate distribution channel. The chosen approach—integrating the functionality into the main runtime and documenting it as a default behavior in `doc/api/cli.md`—provides a unified, discoverable experience that aligns with how developers expect Node.js capabilities to work.

## Risks & Mitigations

The primary risk in enabling `--experimental-strip-types` by default (PR #56350) is a potential breaking change for users whose scripts unintentionally rely on the flag’s previous disabled state. While the feature is considered stable, flipping this default alters the fundamental input handling of the Node.js executable. Any user or toolchain that invokes `node` with `.ts` files in an environment where the flag was not previously used will now experience different behavior. The mitigation is clear communication via the updated documentation in **doc/api/cli.md**, which must explicitly state this change in default behavior and link to the documented syntax limitations. This ensures users can anticipate and adapt to the new default.

A secondary risk involves performance regression for all users, even those not using TypeScript, if the detection and stripping logic introduces overhead for `.js` files. The existing benchmark suite, specifically **benchmark/ts/strip-typescript.js**, must be utilized to measure and track performance before and after this change. If any regression is detected in the baseline `.js` module load path, it must be resolved before this change can land. The mitigation is the existing performance benchmark infrastructure, which provides a clear means to gate the change on performance neutrality.

A final consideration is user confusion stemming from the documented limitations of the type-stripping feature. Users may expect full TypeScript compilation support when they first use a `.ts` file. The mitigation is to ensure the release notes and the updated **doc/api/cli.md** prominently feature a link to the limitations section. This sets correct expectations and directs users to the appropriate documentation for supported syntax, reducing frustration and misfiled issues.

## Rollout Plan

The rollout plan for PR #56350, which enables `--experimental-strip-types` by default, will follow a phased deployment strategy to ensure stability and backward compatibility across the Node.js ecosystem. The primary goal is to validate the feature's readiness under real-world conditions before removing the experimental flag designation. All changes will be confined to the `nodejs/node` repository.

**Phase 1: Benchmark and Documentation Validation.** The initial merge will focus on updating the two affected files: `benchmark/ts/strip-typescript.js` and `doc/api/cli.md`. The benchmark file will be executed within our CI performance tracking suite to establish stable baseline metrics for TypeScript stripping overhead, confirming no regressions in performance-critical areas. Concurrently, the documentation update in `doc/api/cli.md` will be merged to ensure all official guidance accurately reflects the new default behavior and its documented limitations before any users encounter the change in a release.

**Phase 2: Canary Runtime and Ecosystem Monitoring.** After the merge, the change will enter the main branch and be included in subsequent "Current" releases. This phase focuses on runtime validation. We will actively monitor issue trackers, including the referenced `nodejs/typescript` repository issue #17, for reports of unexpected behavior, edge cases, or breaking changes in dependent toolchains. This period acts as a controlled canary test, leveraging the broader open-source user base to surface any issues that were not caught in the pre-merge test suite.

**Phase 3: Stable Release and Potential Unflagging.** Assuming Phase 2 monitoring shows no critical issues, the feature will propagate into the next LTS (Long-Term Support) release line. Success metrics will be defined as a sustained period with no open, high-severity bugs directly attributable to the default-enabled stripping behavior. Upon meeting these criteria, a subsequent PR can be considered to formally remove the `experimental-` prefix from the flag, completing its graduation to a stable feature. This phased approach minimizes risk while systematically advancing the feature's lifecycle.
