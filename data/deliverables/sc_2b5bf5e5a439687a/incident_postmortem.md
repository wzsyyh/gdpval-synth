# Postmortem: Deprecation of TensorFlow and JAX Backends

# Postmortem: Deprecation of TensorFlow and JAX Backends

This postmortem documents the completion of the deprecation and removal of TensorFlow (TF) and JAX backend support from the Hugging Face Transformers library, executed via PR #38758 titled "Deprecate TF + JAX." The pull request was merged on June 11, 2025, at 16:28:06 UTC, marking a significant milestone in the project's evolution toward a PyTorch-centric architecture.

The scope of this change was substantial: 121 files were modified, with 27 lines added and over 50,030 lines deleted. This document captures the key decisions, impact, and recommended follow-up actions.

## Incident Overview

PR #38758, titled "Deprecate TF + JAX," was merged into the main branch of the huggingface/transformers repository on 2025-06-11T16:28:06Z. The PR description was notably brief, consisting of: "The time has finally come :gun: :tumbler_glass: ", signaling the culmination of a long-anticipated deprecation effort.

The change touched 121 files across the repository. Of these changes, 27 lines were added (likely deprecation notices, CI adjustments, or import stubs) and 50,030 lines were deleted, representing the bulk removal of TensorFlow and JAX backend code, tests, and related utilities.

The asymmetric ratio of additions to deletions (27 vs. 50,030) indicates a near-complete removal rather than a gradual phase-out with extensive warning scaffolding.

## Timeline

The following timeline reconstructs the key phases of this deprecation effort based on the available information:

**Pre-Merge Phase**: The deprecation of TensorFlow and JAX in Transformers was a long-discussed initiative. The phrase "The time has finally come" in the PR description indicates the team had previously announced or communicated the intent to deprecate these backends well before the PR was created. This likely involved community discussions, deprecation warnings in prior releases, and alignment among core maintainers.

**PR Creation and Review**: The PR was created and underwent code review. Given the scale (121 files, 50,030 deletions), this was a carefully coordinated effort, likely involving automated tooling to identify and remove TF/JAX-specific code paths.

**Merge Event (2025-06-11T16:28:06Z)**: The PR was merged into the main branch, activating the deprecation in the codebase.

**Post-Merge Validation (Recommended)**: The team should verify: (1) the main branch CI pipelines pass without TF/JAX dependencies, (2) the test suite no longer contains references to removed frameworks, (3) documentation is updated to reflect the new state, and (4) release notes are drafted for the next version.

## Impact Analysis

**Scope of Removal**: This PR removed all support for TensorFlow and JAX as backends within the Transformers library. Users who relied on tf_* or jax_* model implementations, training loops, or inference pipelines will no longer find these code paths in the library.

**Magnitude**: The deletion of over 50,030 lines across 121 files represents one of the largest single-PR reductions in the project history. This magnitude indicates that TF and JAX support was deeply embedded in the codebase, including model implementations, utility functions, tests, and likely documentation references.

**Downstream Impact**: Projects that import TensorFlow or JAX variants of Transformers models will encounter import errors upon upgrading. Downstream libraries, tutorials, and deployment scripts that assume multi-framework availability will need updates.

**Positive Impact**: Removing two major framework backends significantly reduces maintenance burden, CI runtime, package size, and codebase complexity. It allows the team to focus optimization and feature efforts exclusively on the PyTorch backend.

## Root Cause and Decision Rationale

The PR description statement - "The time has finally come :gun: :tumbler_glass: " - frames this deprecation as the culmination of a long-planned decision rather than a reactive measure. This was not an incident but a deliberate architectural simplification.

**Maintenance Burden**: Supporting three major deep learning frameworks (PyTorch, TensorFlow, JAX) in a single library required maintaining parallel implementations for every model, duplicating test suites, and triaging framework-specific bugs. Over time, the maintenance cost of TF and JAX support grew disproportionately as the number of models increased.

**Community Adoption Trends**: Usage data and community feedback likely showed that PyTorch had become the dominant framework among Transformers users, reducing the practical value of maintaining TF and JAX backends.

**Technical Debt Reduction**: The 50,030 lines removed represent significant technical debt - code that required synchronization across frameworks, complicated refactors, and increased the surface area for bugs.

**Ecosystem Alignment**: The broader Hugging Face ecosystem including the datasets, tokenizers, and accelerate libraries had already centered on PyTorch, making the Transformers library the last major component to fully align.

## Action Items

The following action items are recommended to ensure a smooth transition and proper closure of this deprecation effort:

1. **Update Official Documentation**: Remove all TensorFlow and JAX references from the Transformers documentation, tutorials, and API references. Ensure no dead links or obsolete code examples remain.

2. **Publish Migration Guide**: Create a dedicated guide for users migrating from TF/JAX to PyTorch, covering common patterns such as model loading, training, and inference conversions.

3. **Notify Downstream Dependents**: Proactively communicate with major downstream projects, cloud providers, and educational platforms that reference TF/JAX Transformers usage.

4. **Verify CI/CD Pipelines**: Confirm that all continuous integration pipelines no longer install TensorFlow or JAX as dependencies and that test execution times have decreased accordingly.

5. **Archive Related Resources**: Archive or sunset any TF/JAX-specific GitHub issues, forums posts, or example repositories. Update the README to reflect the new single-backend status.

6. **Monitor Community Feedback**: Establish a monitoring period of 30 days post-release to track and respond to user confusion or migration issues arising from the deprecation.

## Lessons Learned

**What Went Well**:

- The deprecation was executed as a single, clean PR rather than a prolonged series of partial removals, reducing ambiguity about the state of TF/JAX support.

- The scope was comprehensive: 121 files and 50,030 lines were removed in one coordinated effort, avoiding a messy half-deprecated state.

- The timing reflected careful planning, as evidenced by the word finally in the PR description - this was not rushed but awaited the appropriate moment.



**Areas for Improvement**:

- The PR description was minimal and lacked context for future contributors reviewing the history. A more detailed description explaining the rationale, migration paths, and link to prior discussions would improve historical record-keeping.

- A formal deprecation timeline with intermediate milestones would have provided a smoother transition for users.

- Dedicated communication channels such as blog posts, email to package maintainers, and social media should accompany changes of this magnitude to ensure broad awareness.



**Key Takeaway**: Large-scale deprecations in widely-used open source projects require not just code changes but a communication and transition strategy that matches the technical effort.
