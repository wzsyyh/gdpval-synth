# Code Review: PR #38758 — Deprecate TF + JAX

## Change Summary

This review covers PR #38758, titled 'Deprecate TF + JAX', which was merged into the huggingface/transformers repository on June 11, 2025. The PR represents a landmark architectural change: the complete removal of TensorFlow and JAX deep learning framework backends from the transformers library.

The scope of this change is substantial. A total of 121 files were modified, with only 27 lines added against 50,030 lines deleted. This near-total deletion ratio indicates that the PR primarily removes existing TF and JAX implementation code, tests, and associated utilities rather than introducing new functionality. The PR description was characteristically brief ('The time has finally come :gun: :tumbler_glass:'), reflecting that this was a long-anticipated decision within the team.

The change effectively transitions the transformers library from a multi-framework architecture supporting PyTorch, TensorFlow, and JAX to a more focused codebase. This consolidation aligns with the observed community usage patterns where PyTorch has become the dominant framework for transformer-based model development.

## Architectural Impact Assessment

The removal of TensorFlow and JAX support fundamentally changes the library's architectural posture. The transformers library has historically maintained a multi-framework abstraction layer, allowing models to be implemented once and run on multiple backends. With this PR, the library narrows its focus to PyTorch as the primary (and now sole) deep learning framework backend.

For downstream consumers, this change creates a clear bifurcation. Teams and projects that relied on TF or JAX backends within transformers will need to either migrate their codebases to PyTorch, maintain their own forked versions of the removed code, or seek alternative libraries that provide equivalent TF/JAX transformer implementations. The 50,030 deleted lines represent a significant volume of tested, production-quality code that consumers may have depended upon.

From a maintenance perspective, the benefits are substantial. Eliminating two framework backends reduces the combinatorial complexity of testing, the surface area for bugs, and the cognitive load on contributors. The team will no longer need to maintain parallel implementations of each model architecture across three frameworks, which historically has been a significant source of maintenance burden and delayed releases.

The 121 affected files likely span model implementations, framework-specific utility functions, test suites, documentation references, and CI/CD configuration. This breadth of change indicates a thorough removal rather than a partial or incomplete deprecation.

## Risk Analysis

The primary risk is the breaking nature of this change for any user importing TensorFlow or JAX functionality from the transformers library. Any code that references `transformers.TF*` or `transformers.Flax*` classes will immediately break after updating to the post-merge version. Given the library's widespread adoption (it is one of the most downloaded Python packages), the blast radius of this breaking change is potentially very large.

Migration path concerns are significant. While PyTorch equivalents exist for most model architectures, the migration is not always a trivial code change. Differences in training loops, data loading patterns, and framework-specific optimizations mean that affected teams may face substantial refactoring efforts. The lack of a formal migration guide in the PR (based on the minimal description) represents a gap that should be addressed.

The dependency chain impact extends beyond direct users. Libraries and tools that build on top of transformers' TF or JAX interfaces will also break. This includes fine-tuning frameworks, serving solutions, and educational materials that demonstrate TF/JAX usage with transformers. The downstream effect will ripple through the ecosystem over weeks and months following the merge.

There is also a community perception risk. Some users may view this as an abandonment of framework diversity in the ML ecosystem. The team should be prepared for community feedback and have clear communication about the rationale, emphasizing the practical maintenance trade-offs rather than any judgment on the frameworks themselves.

## Code Quality Observations

The approach taken—bulk deletion rather than gradual deprecation—is appropriate for a change of this magnitude. A gradual approach (deprecating over multiple releases) would have extended the maintenance burden and created a confusing intermediate state where some TF/JAX features worked and others did not. The clean break, while disruptive, is ultimately clearer for the community.

The +27/-50,030 ratio is striking and warrants analysis. The 27 added lines likely serve specific purposes: deprecation warnings in remaining import paths, updates to top-level __init__.py files to remove TF/JAX exports, updates to setup.py or pyproject.toml to remove TF/JAX dependencies, and possibly brief migration notes in documentation. Each added line in a deletion PR of this scale carries disproportionate importance and should be carefully reviewed.

The deletion of 50,030 lines across 121 files suggests thorough removal. If TF/JAX code had been left behind in scattered locations, it would represent incomplete cleanup. The volume indicates that model implementations, framework-specific utilities, test files, and documentation were all systematically targeted. However, without access to the full diff, it is not possible to verify that no TF/JAX references remain in edge-case locations such as example scripts, benchmarks, or contributing guidelines.

From a code quality standpoint, the deletion of well-tested code is always a concern for regression risks. While the TF/JAX code is being removed rather than modified, any shared utility functions or common code paths that were used by both PyTorch and TF/JAX implementations need to remain intact and functional for the PyTorch case.

## Testing and Rollout Considerations

For a change of this scale, comprehensive testing is essential. The test suite should verify that: (1) all PyTorch model implementations continue to function correctly after TF/JAX code removal, (2) no import errors occur for standard usage patterns, (3) CI pipelines pass without TF/JAX-specific test configurations, and (4) documentation builds successfully with updated references. Given that 121 files were changed, there is a risk that shared code was inadvertently affected.

Communication to the user community should be multi-channel and proactive. Recommended channels include: a prominent notice in the release notes, a dedicated blog post explaining the rationale and migration paths, updates to the README and getting-started guides, and a pinned discussion thread in the repository. The brief PR description ('The time has finally come :gun: :tumbler_glass:'), while memorable for insiders, is insufficient for public communication.

Versioning implications are significant. Removing two major framework backends constitutes a breaking change that warrants a major version bump under semantic versioning. If the library is currently at version 4.x, this change should be released as version 5.0.0 to clearly signal the breaking nature to automated dependency resolution systems and human readers alike.

A rollback plan should be documented. While it is unlikely the team would reverse this decision, having a clear plan for how to respond if critical issues are discovered post-merge is prudent. This could include maintaining a TF/JAX-supported release branch for emergency patches or having a clear communication about the last version that supports these frameworks.

## Recommendations

First, publish a comprehensive migration guide that covers common patterns for moving from TF and JAX implementations to PyTorch equivalents. This guide should include code examples for typical use cases such as fine-tuning, inference, and custom model implementation. Given the 50,030 lines of removed code, there are likely many nuanced usage patterns that need to be addressed.

Second, consider an extended support period for the last version that includes TF/JAX support. This could take the form of critical security patches for 6-12 months following the deprecation release, giving downstream consumers time to migrate without being left on an unsupported version. The 121-file scope of this change suggests many consumers will be affected.

Third, implement a monitoring plan to track community feedback and breaking change reports in the weeks following release. Key metrics to watch include: issue volume related to TF/JAX removal, download statistics for the pre-deprecation version, and community sentiment in forums and social media. The dramatic nature of this change (50,030 lines deleted) will likely generate significant discussion.

Fourth, ensure all documentation is updated to reflect the single-framework architecture. This includes API references, tutorial content, model cards, and the library's contributing guide. Any remaining references to TF or JAX usage will create confusion and should be systematically removed or updated to note the deprecation. The 27 added lines in the PR may have started this process, but a full documentation audit is recommended.
