# Design Document: VS Code Autocomplete Support via dataclass_transform

## Abstract

This document describes the design and rationale for the change introduced in PR #2721, which adds autocomplete ("IntelliSense") support for Pydantic models in Visual Studio Code. The core mechanism is the application of a `__dataclass_transform__` marker to Pydantic's metaclass, which signals to type checkers like Pyright that the class behaves like a dataclass. This enables automatic generation of a typed `__init__` constructor, providing field name autocompletion during model instantiation in supported editors like VS Code via the Pylance extension.

## Motivation

Prior to this change, developers using Pydantic in Visual Studio Code did not receive autocompletion suggestions for field names when creating new instances of a model. While Pydantic's use of standard Python type annotations provides basic compatibility, the lack of an explicit signal to type checkers meant that the automatic `__init__` signature was not recognized, leaving a gap in the developer experience.

This gap was highlighted in community discussions. Eric Traut, the author of Pyright, initiated a draft standard for a `typing.dataclass_transform()` decorator to provide a uniform way for libraries to declare dataclass-like behavior. The draft standard and its rationale are documented in the pyright repository at `specs/dataclass_transforms.md`, with the community discussion occurring at `pyright/discussions/1782`. Within the Pydantic community, the potential for this standard was discussed in `pydantic/discussions/2698`, where the contributor koxudaxi pointed out the possibility.

## Technical Approach

The technical solution follows the draft standard's guidance for early adoption. The standard proposes a decorator `typing.dataclass_transform()` to be applied to a class or function that defines or returns a dataclass-like type. For Pydantic, this decorator would be applied to the metaclass that creates models.

Because the standard had not yet been accepted into Python's `typing` module, the PR implements a minimal shim. A custom `__dataclass_transform__` function is defined and used as a decorator on Pydantic's `ModelMetaclass`. This function serves the same purpose as the proposed `typing.dataclass_transform()` but works with current versions of Python. Type checkers that support the draft standard—specifically Pyright, and by extension Pylance in VS Code—already recognize this custom decorator and enable the enhanced autocompletion features.

## Implementation Details

The implementation consists of two main parts: a code change to apply the transform marker, and comprehensive documentation to guide users. The code change itself is minimal, as it only adds the decorator. The key files modified or added are:

- A changelog entry was created at `changes/2721-tiangolo.md` to describe the feature for the project's release notes.

- A new documentation page, `docs/visual_studio_code.md`, was added. This page provides a detailed guide on configuring VS Code to leverage the new autocomplete features, including installing the Pylance extension and configuring the Python language server.

- To support the documentation, eight new screenshot assets were added under `docs/img/`, named `vs_code_01.png` through `vs_code_08.png`. These screenshots visually demonstrate the autocomplete functionality in action.

## Impact and Trade-offs

The primary impact of this change is a significantly improved developer experience for users of Visual Studio Code. It provides autocompletion and error checking for Pydantic model instantiation that is comparable to the features offered by the dedicated PyCharm plugin maintained by koxudaxi. This brings VS Code support to a more feature-complete state without requiring users to install additional plugins beyond the standard Pylance extension.

A notable trade-off is the reliance on an unofficial, draft standard. The implementation uses a custom `__dataclass_transform__` function rather than the proposed `typing.dataclass_transform()`. While this works with current versions of Pyright/Pylance, it depends on continued support for this specific mechanism in those tools. If the draft standard is accepted and evolves, the implementation may need to be updated.

The PR description notes that if the `dataclass_transform` standard is accepted into Python, it could replace or simplify a large part of the Pydantic mypy plugin, which currently performs similar type-checking enhancements. This change is purely additive and has no impact on Pydantic's runtime behavior or its public API.

## References
