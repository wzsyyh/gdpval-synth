# Design Document: mkautodoc Integration for API Documentation

## Executive Summary

This design document assesses the integration of mkautodoc into our MkDocs-based documentation site, as demonstrated in PR #464 from the encode/httpx repository. The pull request represents a first-pass proof-of-concept that replaces manual API documentation with automatically generated docstrings using mkautodoc directives. Based on this analysis, we recommend proceeding with Phase 1 of the adoption plan to complete the proof-of-concept for the core HTTP functions.

## Background and Motivation

mkautodoc is an MkDocs plugin that automatically generates API documentation from Python docstrings. It provides a custom directive syntax that renders docstrings directly into the built documentation site, reducing the manual effort required to keep documentation synchronized with code changes.

Automatic documentation generation is valuable because it ensures documentation accuracy by deriving content directly from source code. This eliminates the common problem of stale or outdated documentation that plagues manually maintained references. For a project like httpx, where the API surface includes numerous functions and classes with detailed docstrings, automation significantly reduces maintenance overhead.

PR #464 demonstrates the use of mkautodoc with the httpx library by replacing the existing manual bullet-point API reference in docs/api.md with mkautodoc directives. The pull request author created an autodoc extension for mkdocs and uses this PR to showcase the approach with the httpx.request function as a starting point.

## Current State Analysis

The changes in PR #464 modify the docs/api.md file. The previous content consisted of manually written bullet-point lists describing the API for each function and the Client class. For example, the top-level functions were listed as: `get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])` and similar entries for options, head, post, put, patch, delete, request, and build_request.

The new content replaces these manual lists with mkautodoc directives using the syntax `::: httpx.<function_name>` followed by `:docstring:`. This syntax tells the mkautodoc plugin to automatically render the docstring of the specified function in the documentation.

Currently, the following functions are covered by autodoc directives: httpx.request, httpx.get, httpx.options, httpx.head, httpx.post, httpx.put, httpx.patch, httpx.delete, and httpx.build_request. Each is represented by a directive block like `::: httpx.request` with `:docstring:`.

The PR description includes a checklist of items. Nested code blocks in docstrings not rendering was resolved by installing the pymdownx.superfences extension. Rendering classes beyond just functions was resolved with limited support. The use of a dd element as a styling hack was also resolved, likely by using a div with an appropriate class. Two items remain open: rendering docs for instance attributes on classes, and ensuring async methods get an 'async' marker. A nice-to-have item is keeping typing information out of the main display with contextual pop-ups.

## Remaining Work Items

Based on the checklist in the PR description, three work items remain open. First, rendering docs for instance attributes on classes is classified as 'Required for MVP' because it is essential for complete API documentation of classes like Client, which have instance attributes such as params, headers, and cookies.

Second, ensuring async methods get an 'async' marker is classified as 'Nice-to-have' for the current phase, as no async methods are being rendered in this PR, but it will become necessary as the codebase evolves to include async client methods.

Third, keeping typing information out of the main display but having contextual pop-ups against parameters is classified as 'Future enhancement'. This is a user experience improvement that can be deferred until after the core documentation is stable and functional.

## Proposed Adoption Plan

Phase 1: Complete the proof-of-concept for the core HTTP functions. The goal is to ensure all listed functions in the PR (httpx.request, httpx.get, httpx.options, httpx.head, httpx.post, httpx.put, httpx.patch, httpx.delete, httpx.build_request) render correctly with their docstrings. This includes resolving any remaining rendering issues with nested code blocks and confirming the directive syntax works as expected. Estimated effort is 1-2 days. Dependencies: mkautodoc plugin installed, pymdownx.superfences extension configured.

Phase 2: Extend to the Client class. The goal is to render documentation for the Client class, including its methods and properties. This phase must address the challenge of rendering instance attributes by implementing code analysis in the __init__ method. Estimated effort is 3-5 days. Dependencies: Phase 1 complete, potential enhancements to mkautodoc to parse __init__ for instance attribute assignments.

Phase 3: Address async method markers and typing information display. The goal is to add an 'async' marker to async methods and implement a user experience for typing information that keeps the main display clean while providing contextual pop-ups. Estimated effort is 2-3 days. Dependencies: Phase 2 complete, UI/UX design decisions for typing information.

## Risks and Mitigations

Risk 1: Rendering limitations in mkautodoc may not support all docstring formats or complex code examples. The PR description noted issues with nested code blocks initially, which were resolved by adding the pymdownx.superfences extension. Mitigation: Maintain a test suite of docstring examples and continuously validate rendering against updates to mkautodoc and MkDocs extensions.

Risk 2: Dependency on mkdocs-material for styling and layout. The PR author initially used a dd element as a styling hack, which was later resolved. Reliance on external theme support may introduce fragility. Mitigation: Define a set of custom CSS classes that can be used as fallbacks if theme support is insufficient, and document these as part of the integration guide.

## Conclusion and Recommendation

PR #464 provides a solid foundation for integrating mkautodoc into our documentation site. The proof-of-concept demonstrates that automatic generation of API documentation from docstrings is feasible and can significantly reduce maintenance effort. The remaining work items are well-defined and can be addressed in a phased approach.

We recommend proceeding immediately with Phase 1 to complete the proof-of-concept for the core HTTP functions. This will provide immediate value by validating the integration and establishing the pattern for future work. Subsequent phases can then be planned based on the outcomes of Phase 1.
