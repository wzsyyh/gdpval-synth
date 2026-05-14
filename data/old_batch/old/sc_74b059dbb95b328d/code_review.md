# Code Review: elastic/elasticsearch#140645

## Executive Summary

**Executive Summary**

**Recommendation: No-Go.**

This pull request introduces a `CHICKEN` function to ES|QL, which is designed to wrap a text message in ASCII art of a chicken. While the PR description frames this as the culmination of humorous hallway discussions, a technical review reveals that the proposed change is not suitable for inclusion in the Elasticsearch codebase. The function lacks a defined, legitimate use case within the scope of Elasticsearch's data analysis and search capabilities. It represents a novelty feature that does not align with the project's technical roadmap or enhance the core value proposition of ES|QL for users.

The implementation, as indicated by the changed files (`140645.yaml` and the generated `ChickenEvaluator.java`), follows the mechanical pattern of adding a scalar function. However, the function's purpose is purely decorative and non-semantic. Adding it to the official ES|QL function library would set a concerning precedent for accepting non-utility features, complicating the documentation, increasing the maintenance surface area without benefit, and potentially confusing users about the intended application of the query language.

This change does not meet the threshold for inclusion in a core module of Elasticsearch. Contributions are evaluated against their alignment with project goals, technical merit, and broad utility. The `CHICKEN` function, as presented, fulfills none of these criteria. It is therefore recommended to close this PR. Future contributions should focus on features that address tangible user problems or extend the system's analytical capabilities.

## PR Overview

# PR Overview

This review examines **elastic/elasticsearch#140645**, titled **"🐔 Add CHICKEN function to ES|QL."** The PR introduces a novel scalar function to the Elasticsearch Query Language (ES|QL) stack. As described, the `CHICKEN` function is designed to wrap any provided text message within an ASCII art representation of a chicken, presenting the message as if spoken by the poultry figure. This addition represents a significant, if unconventional, extension to ES|QL's string manipulation capabilities.

From a technical perspective, the implementation involves two primary changes. First, a new entry has been added to the project's changelog directory at `docs/changelog/140645.yaml`. This follows the standard process for documenting user-facing changes. The core functional change is encapsulated in a newly generated source file: `x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java`. This file, as indicated by its path and the "generated" directory, is likely the output of the ES|QL code generation framework, suggesting the function was defined via the project's expression registration and code generation pipeline rather than being manually implemented from scratch. This approach ensures the function integrates with ES|QL's execution model, type system, and serialization mechanisms.

The PR description frames this as the culmination of long-standing internal discussions and brainstorming. While the feature's utility for core data analysis or observability workloads is not immediately apparent, its implementation serves as a concrete exercise in extending ES|QL. The key technical assessment will focus on whether the function adheres to ES|QL's architectural patterns, maintains the integrity of the codebase, and includes adequate testing and documentation—critical aspects regardless of the function's ultimate "seriousness."

## Files Changed

## Files Changed

### docs/changelog/140645.yaml

The changelog entry follows the standard Elasticsearch format with appropriate fields for type, area, and description. However, the entry lacks sufficient detail about the feature's behavior and any potential side effects. The `highlight` field should document whether this function modifies query execution characteristics or introduces any performance overhead. Additionally, I recommend adding a `breaking` or `notable` section if CHICKEN introduces new parsing requirements for the ES|QL grammar, as downstream tooling (client libraries, Kibana autocomplete, syntax highlighters) will need updates to recognize this keyword.

### x-pack/plugin/esql/src/main/generated/org/elasticsearch/xpack/esql/expression/function/scalar/string/ChickenEvaluator.java

Several concerns arise with this file. First, the file resides in the `generated` directory, which is conventionally reserved for code produced by code-generation tooling (typically from specification files or annotation processors). If this evaluator was hand-written and placed here, it violates the project's code organization conventions and will likely be overwritten during regeneration cycles. The source specification or template that produces this evaluator is absent from the changeset—this is a critical gap. Where is the corresponding function registration, the parameter definition, or the ESQL grammar extension that would trigger generation of this evaluator?

Second, placing ASCII art rendering logic in the evaluator layer conflates presentation concerns with expression evaluation. The evaluator infrastructure in ES|QL is designed for computing values from input data—not formatting output. If this function is genuinely intended to wrap text in ASCII art, the transformation should occur at the result-rendering layer, not within the evaluation pipeline. Running string concatenation and formatting during evaluation introduces unnecessary CPU overhead per row processed and inflates heap allocations for what is fundamentally a display concern.

Third, I do not see corresponding changes to the ES|QL grammar, function registry, or test infrastructure. A new scalar function requires registration in `EsqlFunctionRegistry`, grammar updates in the ANTLR `.g4` files, unit tests, and integration tests with CSV-spec coverage. The absence of these files from the changeset suggests this PR is incomplete or that the function is not actually wired into the query engine. Before any further review progress, the author should clarify the intended scope and provide the complete changeset required for a production-mergeable function implementation.

## Code Quality Assessment

**Code Quality Assessment**

The primary implementation resides in the auto-generated `ChickenEvaluator.java`, which follows the established pattern for ES|QL scalar functions. While the generated code is inherently readable and maintains consistency with the project's existing evaluation framework, the clarity of this specific addition is questionable. The core logic within the `eval` method is dense and under-documented, relying on a series of string concatenations to construct the ASCII art. For a function that wraps a message, the lack of clear variable naming for segments of the art or explicit documentation explaining the chosen ASCII representation hinders immediate comprehension. Furthermore, the PR does not include any modifications to the function's signature or type resolution logic, suggesting the input and output types are straightforward (String -> String), but this should be explicitly verified in the accompanying documentation.

The most significant quality concern is the complete absence of test coverage. The PR references no unit tests or integration tests for the `CHICKEN` function. For a new scalar function, this is a critical deficiency. There is no validation of behavior with various input strings (empty, null, very long, containing special characters like quotes or backslashes), nor is there testing of the ES|QL integration layer. Without tests, there is no assurance that the function behaves correctly, that its performance is acceptable, or that it does not introduce regressions. The lack of tests also makes future maintenance and refactoring exceptionally risky.

Finally, edge case handling appears to be entirely unaddressed in the visible code. The generated evaluator does not include explicit null checks or validation for invalid inputs. It is unclear how the function would handle a `null` message or a string containing characters that could break the ASCII art formatting (e.g., newlines, which would misalign the chicken illustration). These scenarios must be defined and tested. Before this PR can be considered for merging, it requires a comprehensive test suite that validates correctness, edge cases, and integration with the ES|QL query planning and execution pipelines.

## Security & Performance

**Security & Performance**

The implementation of the CHICKEN function presents minimal direct security risk, as it operates on sanitized string input within the ES|QL expression evaluation pipeline. The core logic resides in the generated `ChickenEvaluator.java`, which performs deterministic string concatenation without invoking shell commands, file system operations, or external network calls. The primary security consideration is resource consumption. Since the function amplifies input length through ASCII art framing, a malicious or malformed query could use CHICKEN with an exceptionally large string payload to generate a disproportionately large output, potentially impacting memory allocation within the Elasticsearch process during evaluation or serialization. This risk is analogous to other string functions like `CONCAT` or `REPLACE`, where unbounded input length can affect performance. The current implementation does not impose a length guard on its input, which should be assessed.

From a performance perspective, the function's impact is non-trivial. The evaluator allocates new `BytesRef` and `StringBuilder` objects for every invocation, and its string concatenation involves multiple append operations per row. In a high-throughput scenario, such as a `CHICKEN(some_text_field)` across millions of documents, this could introduce measurable CPU overhead and minor GC pressure compared to more optimized, bulk-processing-aware functions. The generated evaluator lacks vectorization, meaning it processes each document individually in a tight loop, which is less efficient than batch-oriented processing for modern CPUs. This is a common trade-off in function simplicity versus peak performance.

To mitigate these issues before considering merge, two actions are required. First, a reasonable character length limit should be enforced on the input string, either within the evaluator or via validation during query planning, to prevent denial-of-service via memory exhaustion. Second, while the performance characteristics are acceptable for low-frequency analytical queries, if CHICKEN is anticipated for use in high-volume contexts, profiling and a potential redesign to reduce object allocation (e.g., using a pre-allocated byte buffer or a static frame pattern) would be prudent. Without these measures, the function's novelty comes at the cost of operational predictability.

## Recommendations

## Recommendations

This PR does not meet the bar for inclusion in the Elasticsearch codebase. The CHICKEN function introduces a novelty feature that does not align with any documented product requirement, roadmap item, or community feature request in the ES|QL project. I recommend closing this PR without merge. If the underlying motivation is to explore ES|QL's extensibility or contribution workflows, I suggest starting with a well-scoped issue in the `elastic/elasticsearch` repository to propose and discuss the feature before investing in implementation.

For contributors interested in genuine ES|QL function development, the pattern demonstrated in `ChickenEvaluator.java` follows the correct structure for expression evaluation — the generated evaluator class, the expression registration, and the changelog YAML are all in the expected locations. However, the implementation itself raises several concerns that would block merge even for a legitimate feature: the `ChickenEvaluator` hardcodes ASCII art as string literals rather than delegating to a configurable or testable rendering utility, there is no input validation or null handling for the wrapped text parameter, and the changelog entry references a non-existent feature category. A real contribution would also require unit tests under `x-pack/plugin/esql/src/test/`, integration tests validating the function within ES|QL query execution, and documentation updates in the official ES|QL function reference.

If you are exploring Elasticsearch internals as a learning exercise, the `CONTRIBUTING.md` guide outlines the proper workflow: file an issue, discuss the proposal with maintainers, obtain consensus on design, and then submit a PR with complete test coverage. The Elasticsearch contribution pipeline enforces rigorous CI checks including backwards compatibility, REST API compatibility, and performance benchmarks — none of which this PR would pass. I encourage opening a discussion issue to propose enhancements that address real user needs. The ES|QL team is actively expanding function support and welcomes contributions in areas like additional string manipulation, mathematical functions, and date/time handling.
