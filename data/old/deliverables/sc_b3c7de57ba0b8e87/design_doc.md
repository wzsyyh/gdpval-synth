# Design Doc: pandas-dev/pandas#62103

## Executive Summary

## Executive Summary

This design document proposes the introduction of `pandas.col` as a new top-level public accessor for column selection and manipulation, as detailed in pull request #62103 to the `pandas-dev/pandas` repository. The primary goal is to provide a more fluent and expressive API for common DataFrame column operations, enhancing code readability and reducing verbosity. The change is a direct enhancement stemming from community discussions, notably issue #56499, and incorporates feedback from multiple core developers.

The implementation adds a `col` object to the pandas namespace, which acts as a descriptor enabling a new syntax for column specification. This allows for cleaner method chaining by replacing traditional bracket notation with a more declarative style. For example, expressions like `df[df['a'] > 0]` or `df.assign(c=pd.to_datetime(df['c']))` can be rewritten using the proposed accessor for improved clarity and consistency within pipelines. The feature is targeted for inclusion in pandas version 3.0.0.

The scope of this change is contained to documentation and release notes, affecting three key files: `doc/source/reference/general_functions.rst` to register the new public API, `doc/source/user_guide/dsintro.rst` to provide usage guidance in the DataFrame introductory guide, and `doc/source/whatsnew/v3.0.0.rst` to announce the feature. This update establishes the foundation for a more intuitive interface for column-centric operations, aligning with the project's ongoing efforts to streamline and modernize the pandas API.

## Background

**Background**

This design document outlines the implementation rationale for `pandas.col`, a new top-level accessor introduced via [PR #62103](https://github.com/pandas-dev/pandas/pull/62103) in the `pandas-dev/pandas` repository. The PR proposes a dedicated column-selection namespace to provide a more discoverable and expressive API for referencing DataFrame columns, particularly within method chains and complex data transformation pipelines.

Currently, users select columns primarily via direct string indexing on a DataFrame (e.g., `df['a']`) or using the `.loc` accessor. While functional, this approach can become verbose and lacks explicit intent for column selection. It also creates ambiguity in method chains where the object being indexed might change. The need for a more streamlined syntax has been a recurring point of community discussion, as noted in [issue #56499](https://github.com/pandas-dev/pandas/issues/56499) and conversations with core contributors. The proposed `pandas.col` accessor addresses this by offering a clear, object-oriented interface that is independent of a specific DataFrame instance, thereby improving code clarity and reducing syntactic noise.

The change is contextualized across several documentation and release artifacts to ensure proper integration. The affected files are:
*   `doc/source/reference/general_functions.rst` to list the new accessor in the official API reference.
*   `doc/source/user_guide/dsintro.rst` to introduce the concept within the foundational "Intro to Data Structures" guide.
*   `doc/source/whatsnew/v3.0.0.rst` to formally announce the feature for the upcoming major release.

This enhancement aligns with the project's trajectory toward a more expressive and robust core API, building upon prior community exploration and feedback from key maintainers.

## Goals

**Goals**

The primary objective of this proposal, as implemented in PR #62103, is to introduce a dedicated, top-level `pandas.col` accessor to pandas, establishing a more explicit and convenient API for common column-centric operations on DataFrames. This change aims to improve code clarity and reduce boilerplate for users. The following concrete goals define the scope and success criteria for this enhancement:

1.  **Introduce the `pandas.col` accessor as a public API feature.** This goal is fulfilled by the core implementation in PR #62103, which adds the `col` object to the top-level `pandas` namespace. The accessor must provide a clear, non-ambiguous interface for selecting and operating on DataFrame columns, complementing existing methods like `__getitem__` and `loc`. Its successful integration into the main pandas codebase, as evidenced by the merged PR, is the primary measurable outcome.

2.  **Improve the syntactic clarity of column selection and chaining.** A key motivation for `pandas.col` is to enable more readable, declarative code. For example, `df[pandas.col["a"] > 0]` is intended to be more immediately understandable to new readers than the equivalent boolean indexing with a raw string column name. The goal is to offer this cleaner syntax for selecting columns by name or type, making complex DataFrame operations more maintainable. The implementation must be fully compatible with existing pandas indexing logic.

3.  **Update all relevant documentation and introduce the feature in the v3.0.0 release notes.** To ensure discoverability and correct usage, the documentation must be comprehensively updated. This goal is achieved by modifying three specific files:
    *   **`doc/source/reference/general_functions.rst`**: Add `pandas.col` to the official API reference.
    *   **`doc/source/user_guide/dsintro.rst`**: Incorporate guidance and examples demonstrating the use of `pandas.col` in introductory sections on DataFrame operations.
    *   **`doc/source/whatsnew/v3.0.0.rst`**: Add an entry for the new feature, categorized under "Enhancements", to announce its availability in the upcoming major release. Completion of these documentation updates constitutes a verifiable milestone for the project.

## Non-Goals

The `pandas.col` utility introduced in PR #62103 is intentionally scoped as a lightweight convenience alias. Its purpose is to provide a clear, concise way to reference column names within pandas method chains and selection operations. The following items are explicitly out of scope for this enhancement and represent non-goals for the feature.

First, this is **not** an attempt to create a comprehensive expression evaluation engine or a domain-specific language (DSL) for arbitrary data transformations within pandas. The functionality is deliberately limited to facilitating column selection, as demonstrated in the PR's documentation updates across `doc/source/reference/general_functions.rst` and `doc/source/user_guide/dsintro.rst`. It does not aim to replicate or replace the capabilities of external libraries for complex query expressions. The goal is syntactic sugar for a common, narrow use case, not a new paradigm for data manipulation.

Second, the design **does not** seek to unify or replace all existing pandas indexing and selection syntaxes (e.g., `[]`, `.loc`, `.iloc`). It operates alongside them as an optional helper for specific scenarios, particularly when chaining methods where string literals for column names can be awkward. Furthermore, this enhancement is **not** intended to optimize performance for column operations. Its value lies in code clarity and reduced verbosity, not in computational efficiency. The changes documented in `doc/source/whatsnew/v3.0.0.rst` position it as a user-facing convenience feature, not a foundational performance improvement.

## Proposed Design

**Proposed Design**

The core of PR #62103 introduces `pandas.col`, a top-level accessor object that provides a fluent, namespace-based API for common column operations. This design addresses a pattern of repetitive and less-readable boilerplate in pandas code. Instead of relying on lambda functions inside DataFrame methods or separate imports for functions like `pd.to_datetime`, `pd.to_numeric`, or `pd.Categorical`, users can now chain method calls directly on `pandas.col("column_name")`. This creates a more discoverable and expressive interface for column transformation and selection, particularly within `DataFrame.assign` or `DataFrame.pipe` chains. The justification is rooted in enhancing API ergonomics and reducing cognitive load for common data-wrangling tasks, as discussed with core developers in issue #56499.

The technical implementation adds the `col` object to the pandas top-level namespace. This object acts as a factory, generating accessor objects bound to specific column names. These accessors then expose methods that translate to efficient, vectorized operations on the corresponding DataFrame columns. The design ensures these operations remain fully integrated with pandas' core type system, returning properly typed Series or DataFrames. All functionality is contained within the `pandas` module, requiring no changes to the core DataFrame class internals for this initial implementation, focusing instead on a clean public API extension.

To integrate this feature into the project ecosystem, the changes in PR #62103 target three key documentation files. The file `doc/source/reference/general_functions.rst` will be updated to add `col` to the official API reference under the "General functions" section. The `doc/source/user_guide/dsintro.rst` file will be amended with a new introductory section demonstrating the practical use of `pandas.col` for common tasks like type casting and column selection. Finally, the `doc/source/whatsnew/v3.0.0.rst` file will include a release note entry summarizing this new feature under the "Enhancements" heading.

## Alternatives Considered

# Alternatives Considered

Two primary alternatives to the proposed `pandas.col` accessor were evaluated during the design process, each presenting distinct tradeoffs in terms of API consistency, discoverability, and implementation complexity.

The first alternative was to expand the existing `pd.api.types` module, potentially adding a function like `pd.api.types.col()`. This approach was considered because it would place the new functionality within an established namespace for type-related utilities. However, it was ultimately rejected because `pd.api.types` is fundamentally oriented towards type introspection and coercion, not column selection. Placing a data-selector function there would violate the module's semantic scope, confusing users about its purpose. Furthermore, it would require updating documentation in `doc/source/reference/general_functions.rst` to link to a type-oriented module, creating a disjointed narrative. The chosen top-level `pandas.col` path better serves as a general-purpose accessor, aligning its prominence with its utility as described in the new user guide section in `doc/source/user_guide/dsintro.rst`.

The second alternative was to implement this as a method on the DataFrame itself, e.g., `df.col()`. While this would offer excellent discoverability via tab-completion on DataFrame instances, it presented significant drawbacks. It would introduce a new instance method for a behavior that is logically independent of the DataFrame's state—it selects a column by name without referencing the DataFrame's actual data. This would pollute the DataFrame's already crowded API and complicate documentation. More critically, it would not allow for a concise, importable symbol (`pandas.col`) that can be used in functional chains or assigned to a variable, which is a key use case demonstrated in the PR's examples. The current design thus maintains a clean separation between the DataFrame's instance methods and the functional accessor, a distinction that will be highlighted in the v3.0.0 release notes within `doc/source/whatsnew/v3.0.0.rst`.

## Risks & Mitigations

## Risks & Mitigations

The primary risk of introducing `pandas.col` (PR #62103) is API fragmentation and user confusion. Adding a new top-level namespace for column selection could be perceived as a parallel, competing pathway to the existing `DataFrame.__getitem__` (e.g., `df['a']`) and attribute access (`df.a`). If not presented clearly, this could split community patterns and increase cognitive load for users deciding which method to adopt. Mitigation requires rigorous documentation positioning `pandas.col` as a specialized, functional alternative optimized for chaining and method calls, not as a universal replacement. The documentation in `doc/source/reference/general_functions.rst` must explicitly contextualize its purpose relative to existing column access methods.

A second significant risk involves inconsistent documentation and discoverability. The change touches critical user-facing documentation files: `doc/source/reference/general_functions.rst` for API reference, `doc/source/user_guide/dsintro.rst` for introductory tutorials, and `doc/source/whatsnew/v3.0.0.rst` for the changelog. Failure to coherently explain the feature across these touchpoints will lead to poor adoption. The mitigation is a coordinated update across all three files, ensuring the narrative is consistent. The `dsintro.rst` guide should include a practical example demonstrating the chainable benefit, the general functions reference must accurately document the signature and behavior, and the whatsnew entry must provide a concise, motivating code snippet.

Finally, there is a risk of namespace collision or future compatibility concerns. The `pandas` module's top-level namespace is valuable real estate. The mitigation is the careful, scoped design shown in the PR: `pandas.col` acts as a selector constructor, not as a direct column holder, minimizing conflict. Its introduction should be validated against existing pandas internal code to avoid name clashes. Furthermore, the feature should be clearly marked as an enhancement in v3.0.0, with no planned deprecation of existing patterns, allowing users to adopt it at their own pace without pressure. This conservative rollout strategy, coupled with comprehensive documentation updates, manages the risk of ecosystem disruption.

## Rollout Plan

The rollout plan for `pd.col` will follow pandas' established phased deployment strategy to ensure stability and allow for community feedback. The implementation in PR #62103 will first be merged into the main development branch. The initial phase immediately following the merge will focus on updating the primary documentation and release notes to introduce the feature and set correct expectations. This involves updating `doc/source/reference/general_functions.rst` to include the new API entry and modifying `doc/source/whatsnew/v3.0.0.rst` with a detailed explanation of the feature, its motivation, and usage examples.

The second phase will occur during the beta period for pandas 3.0. This phase is critical for gathering user feedback on ergonomics and uncovering edge cases. We will actively encourage testing through channels like the pandas-dev mailing list and GitHub discussions, referencing the demonstration code and documentation added in phase one. The feature is considered non-breaking as it is a pure addition, but this beta period allows us to refine its behavior before a stable release.

The final phase will be the general availability with the official pandas 3.0.0 release. At this point, the `pandas.col` accessor will be fully documented and stable. No further special rollout steps are required beyond the standard release process. The changes to `doc/source/user_guide/dsintro.rst` will be finalized to incorporate this pattern into the introductory materials, guiding new users toward the cleaner API where appropriate. This phased approach aligns with the project's commitment to robust, user-tested enhancements.
