# Design Document: Discriminated Unions in Pydantic

## Overview

Discriminated unions provide a mechanism for validating union types based on the value of a designated discriminator field. This feature was introduced in PR #2336 to address longstanding limitations in how Pydantic handles union types, particularly for compliance with JSON Schema and OpenAPI specifications. Standard `typing.Union` validation in Pydantic attempts each member type sequentially, which can be ambiguous and inefficient, and does not produce the semantic `oneOf` constructs with explicit discriminators required by OpenAPI.

The feature request originated in issue #619, which highlighted the gap between Pydantic's union support and the OpenAPI specification's concept of tagged unions. In OpenAPI, a discriminator object can be included in a schema to specify which field determines the variant, enabling more precise validation and clearer API documentation. PR #2336 closes both issue #619 and issue #3113 by implementing this capability directly within Pydantic's type system.

## Design Rationale

The design leverages Python's `typing_extensions.Annotated` type, combined with a specialized `Field` parameter, to specify discriminated unions. The chosen API is: `Union[TypeA, TypeB] = Field(..., discriminator='field_name')` or using `Annotated[Union[TypeA, TypeB], Field(discriminator='field_name')]`. This approach was selected over alternatives considered in issue #619 for several reasons.

A custom `TaggedUnion` constructor, as initially proposed in the issue, would have introduced a new top-level type that does not integrate naturally with Python's existing type system. By using `Annotated`, the solution remains composable with other type hints and is familiar to developers already using Pydantic's `Field` for metadata. Furthermore, extending the `Schema` class with OpenAPI-specific discriminator logic was rejected to avoid polluting the core validation schema with API-convention concerns; the `Annotated` approach cleanly separates the validation directive from the schema generation logic.

## Implementation Details

The implementation involves several key components, evidenced by the new files added in the PR. The file `docs/examples/types_union_discriminated.py` demonstrates the core pattern: models define a discriminator field (e.g., `pet_type: Literal['cat']`), and the union type is annotated with `Field(discriminator='pet_type')`. During validation, Pydantic inspects the discriminator field's value in the input data, matches it against the `Literal` annotations of the union members, and delegates validation to the corresponding model class. This bypasses the expensive trial-and-error validation of a standard union.

Nested discriminated unions are supported, as shown in `docs/examples/types_union_discriminated_nested.py`. Here, a union of `BlackCat` and `WhiteCat` is itself discriminated by a `color` field, and then that union is nested inside a `Pet` union discriminated by `pet_type`. The implementation must recursively resolve discriminator hierarchies. The schema generation example in `docs/examples/schema_ad_hoc.py` uses `Annotated` with `schema_json` to produce a compliant schema. A changelog entry, `changes/619-PrettyWood.md`, confirms the feature addition and links to documentation.

## OpenAPI/JSON Schema Alignment

A core requirement from issue #619 was that Pydantic's generated schema should include an OpenAPI discriminator object within a `oneOf` construct. The implementation fulfills this. When generating a JSON Schema for a discriminated union, Pydantic produces a `oneOf` array containing the schemas of the union members. It also includes a top-level `discriminator` object with two properties: `propertyName` (the field name used for discrimination) and `mapping` (an object mapping discriminator values to the corresponding schema references).

This structure directly aligns with the OpenAPI 3.0 specification for discriminators, enabling seamless integration with OpenAPI-based tooling for documentation, code generation, and validation. The approach is compatible with JSON Schema's `oneOf` keyword, though the `discriminator` object is an OpenAPI-specific extension. Pydantic's schema generation thus bridges the gap between its internal validation logic and the output required for OpenAPI-compliant APIs.

## Usage Examples

The primary usage pattern is illustrated in `types_union_discriminated.py`. Models `Cat`, `Dog`, and `Lizard` each define a `pet_type` field with a `Literal` type annotation specifying the discriminator value. The container `Model` has a field `pet` of type `Union[Cat, Dog, Lizard]` annotated with `Field(discriminator='pet_type')`. Validation then becomes efficient and deterministic: `Model(pet={'pet_type': 'dog', 'barks': 3.14}, n=1)` succeeds, while missing required fields for the selected variant (e.g., `Model(pet={'pet_type': 'dog'}, n=1)`) raise a `ValidationError` pinpointing the exact issue within the `Dog` model.

A more advanced example is in `types_union_discriminated_nested.py`. Here, `BlackCat` and `WhiteCat` are discriminated by a `color` field, forming a `Cat` type via `Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]`. This `Cat` union is then nested in a `Pet` union discriminated by `pet_type`. This demonstrates the composability of discriminated unions. The input `{'pet_type': 'cat', 'color': 'black', 'black_name': 'felix'}` is correctly routed to `BlackCat`, while an invalid color like `'red'` causes a validation error at the nested discrimination level.

## Testing and Validation

The PR checklist indicates that unit tests for the changes exist and that tests pass on CI with coverage remaining at 100%. This ensures that the discriminated union feature is thoroughly validated against a variety of cases, including valid discriminations, invalid discriminator values, missing discriminator fields, nested unions, and schema generation correctness. The rigorous test coverage guarantees reliability and backward compatibility for this new capability.

Documentation was updated to reflect the changes, as confirmed by the checklist item regarding documentation. The new examples in the `docs/examples/` directory serve as both usage guides and implicit tests, ensuring that the documented patterns work as described. This comprehensive testing and documentation approach supports the feature's adoption and maintainability.
