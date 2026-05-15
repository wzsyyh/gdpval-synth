# Design Document: Discriminated Union Support in Pydantic

## Overview

This design document describes the discriminated union feature implemented in PR #2336, which closes two long-standing issues: #619 (Feature Request for tagged union support) and #3113. The feature enables users to specify a discriminator field on a Union of submodels, allowing pydantic to determine which submodel to validate against at runtime based on the value of that field.

A discriminated union (also called a tagged union) is a Union type where a designated field acts as a discriminator. Each variant in the union assigns a Literal value (or values) to this field. During validation, pydantic reads the discriminator value from the input and validates against only the matching submodel, rather than attempting validation against all submodels sequentially.

Setting a discriminated union has three key benefits: (1) validation is faster since it is only attempted against one model, (2) only one explicit error is raised in case of failure instead of multiple validation errors from each submodel, and (3) the generated JSON schema implements the OpenAPI discriminator specification (https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminatorObject).

## API Surface

The primary user-facing API adds a discriminator parameter to the Field function. Users declare a discriminated union by annotating a Union field with Field(discriminator='field_name'), where 'field_name' is the name of the common Literal field across all submodels. For example:

```python\nclass Cat(BaseModel):\n    pet_type: Literal['cat']\n    meows: int\n\nclass Dog(BaseModel):\n    pet_type: Literal['dog']\n    barks: float\n\nclass Lizard(BaseModel):\n    pet_type: Literal['reptile', 'lizard']\n    scales: bool\n\nclass Model(BaseModel):\n    pet: Union[Cat, Dog, Lizard] = Field(..., discriminator='pet_type')\n    n: int\n```

The Annotated syntax from typing_extensions can be used to compose discriminated unions declaratively. This is particularly useful for nesting multiple discriminator levels:

```python\nCat = Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]\nPet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]\n```

Two new standalone utility functions are added to pydantic.tools: schema() and schema_json(). These functions generate JSON schema for arbitrary pydantic-compatible types, not just BaseModel subclasses. They accept an optional title parameter (as a NameFactory) and return a dict or JSON string respectively. They are exported in pydantic.__init__ alongside parse_file_as, parse_obj_as, and parse_raw_as.

## Internal Architecture

The implementation spans six key files in the pydantic package. In pydantic/fields.py, the FieldInfo class gains a new discriminator attribute (stored in __slots__), and the Field() function accepts a discriminator: str = None parameter. The ModelField class adds three new attributes: discriminator_key (the field name string), discriminator_alias (the resolved alias for lookup), and sub_fields_mapping (a Dict[str, ModelField] mapping discriminator values to their corresponding sub-field).

The new error classes MissingDiscriminator and InvalidDiscriminator are defined in pydantic/errors.py. MissingDiscriminator uses code 'discriminated_union.missing_discriminator' and raises when the discriminator key is absent from the input. InvalidDiscriminator uses code 'discriminated_union.invalid_discriminator' and includes the discriminator_key, discriminator_value, and allowed_values in its context. Both extend PydanticValueError.

Utility functions in pydantic/utils.py handle alias resolution and value extraction. get_unique_discriminator_alias(all_aliases, discriminator_key) validates that all submodels use the same alias for the discriminator field and raises ConfigError if they differ. get_discriminator_alias_and_values(tp, discriminator_key) recursively extracts the alias and Literal values from a type, handling BaseModel classes, __root__ models, Annotated unions, and direct Union types via the helper _get_union_alias_and_all_values.

In pydantic/typing.py, the get_sub_types(tp) function recursively flattens Annotated and Union types into a flat list of concrete types. This is used by schema.py to enumerate all submodels for the discriminator mapping. The update_field_forward_refs function is modified to call prepare_discriminated_union_sub_fields again after ForwardRef resolution.

In pydantic/schema.py, the field_schema function detects field.discriminator_key is not None and generates the OpenAPI discriminator object. For each entry in sub_fields_mapping, it builds the mapping dict: if the sub_field is a Union (detected via is_union(get_origin(sub_field.type_))), it produces a dict of model name to $ref; otherwise it produces a single $ref string. The discriminator object includes propertyName (set to field.discriminator_alias) and mapping.

## Validation Flow

The validation flow begins in ModelField._validate_singleton. When sub_fields exist and discriminator_key is not None, it delegates to _validate_discriminated_union instead of the standard union validation loop. This is the key optimization: instead of trying each submodel sequentially, the method directly selects the correct one.

In _validate_discriminated_union, the method first attempts to read the discriminator value from the input. It tries v[self.discriminator_alias] for dict-like inputs. If that raises TypeError (indicating the input is not a dict, such as a BaseModel instance or dataclass), it falls back to getattr(v, self.discriminator_alias). If either access fails with KeyError or AttributeError, a MissingDiscriminator error is returned with the discriminator_key in context.

Once the discriminator value is obtained, the method looks it up in self.sub_fields_mapping. If sub_fields_mapping is None (which occurs when a ForwardRef was encountered during prepare_discriminated_union_sub_fields), a ConfigError is raised instructing the user to call update_forward_refs(). If the value is not found in the mapping, an InvalidDiscriminator error is returned listing the allowed values (the keys of sub_fields_mapping).

On a successful match, the selected sub_field is validated with the full location path appended with display_as_type(sub_field.type_). The loc parameter is converted to a tuple if it is not already, ensuring nested location tracking works correctly. The sub_field.validate call receives the original values dict and cls parameter.

## Schema Generation

The schema generation for discriminated unions is implemented in pydantic/schema.py within the field_schema function. After the standard schema generation, the function checks if field.discriminator_key is not None and constructs the OpenAPI discriminator object as specified in https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminatorObject.

For each (discriminator_value, sub_field) pair in field.sub_fields_mapping, the function determines the schema reference. If the sub_field's type is a Union (checked via is_union(get_origin(sub_field.type_))), it uses get_sub_types to flatten the union into individual models and builds a mapping dict where each key is the model name from model_name_map and each value is the $ref from get_schema_ref. This handles nested discriminated unions where a single discriminator value maps to multiple submodels.

For simple BaseModel subfields (non-Union), the function extracts the __pydantic_model__ if present (for dataclass types) and produces a single $ref string in the mapping. The final discriminator object is set on the schema with propertyName (set to field.discriminator_alias) and the constructed mapping dict.

The resulting schema includes an anyOf array with $ref entries for each submodel, plus the discriminator object. For example, a Model with a pet field discriminated by pet_type produces a discriminator with propertyName 'pet_type' and mapping entries like 'cat': '#/definitions/Cat', 'dog': '#/definitions/Dog', etc. Nested discriminated unions produce richer mapping entries with nested dicts of model refs.

## Edge Cases and Error Handling

Several edge cases are explicitly handled in the implementation. Alias validation is enforced by get_unique_discriminator_alias in pydantic/utils.py: if different submodels define different aliases for the same discriminator field (e.g., one uses alias='T' and another uses alias='U'), a ConfigError is raised with the message listing the conflicting aliases. This ensures the discriminator value can be consistently resolved regardless of which alias convention each submodel uses.

The discriminator field on each submodel must be a Literal type. get_discriminator_alias_and_values checks is_literal_type(t_discriminator_type) and raises ConfigError if the field is not Literal. This restriction ensures the set of valid discriminator values is statically known at class definition time, enabling the sub_fields_mapping to be built eagerly.

ForwardRef handling is implemented in prepare_discriminated_union_sub_fields: if any sub_field's type_ is a ForwardRef, the method returns early without populating sub_fields_mapping. The update_field_forward_refs function in pydantic/typing.py calls prepare_discriminated_union_sub_fields again after all ForwardRefs are resolved. If validation is attempted before update_forward_refs is called, _validate_discriminated_union detects sub_fields_mapping is None and raises a ConfigError with the model name and instruction to call update_forward_refs().

The discriminator parameter is restricted to Union types: _type_analysis raises TypeError with message '`discriminator` can only be used with `Union` type` if discriminator_key is set on a non-Union field. Integer and Enum discriminator values are supported, as demonstrated by test_discriminated_union_int and test_discriminated_union_enum in the test suite.

## Testing Strategy

The test suite for discriminated unions is comprehensive, covering validation, schema generation, error handling, and edge cases. The primary test file is tests/test_discrimated_union.py (note the typo in the filename, preserved from the original PR). It contains 15 test functions covering: discriminator-only-with-union restriction (test_discriminated_union_only_union), invalid type errors (test_discriminated_union_invalid_type), missing discriminator field on submodel (test_discriminated_union_defined_discriminator), non-Literal discriminator field (test_discriminated_union_literal_discriminator), root model same discriminator validation (test_discriminated_union_root_same_discriminator), full validation flow with nested unions (test_discriminated_union_validation), Annotated syntax (test_discriminated_annotated_union), BaseModel instance values (test_discriminated_union_basemodel_instance_value), integer discriminators (test_discriminated_union_int), enum discriminators (test_discriminated_union_enum), alias conflict detection (test_alias_different), alias consistency (test_alias_same), and nested Annotated unions (test_nested).

Schema generation is tested in tests/test_schema.py with test_discriminated_union (covering nested Cat/Dog/Lizard with nested Cat having its own discriminator on color) and test_discriminated_annotated_union (covering deeply nested Annotated unions with three discriminator levels and mapping dicts of model refs). The test_alias_same function in test_schema.py verifies that alias-based discriminator fields produce correct propertyName in the schema.

Dataclass support is tested in tests/test_dataclasses.py with test_discrimated_union_basemodel_instance_value, which defines discriminator via dataclasses.field(metadata=dict(discriminator='l')) and verifies the generated schema includes the discriminator object with correct mapping. ForwardRef handling is tested in tests/test_forward_ref.py with test_discriminated_union_forward_ref, which creates a module with forward-referenced Cat and Dog types, verifies the ConfigError before update_forward_refs, calls update_forward_refs, and then validates the schema output. The new standalone utility functions schema and schema_json are tested in tests/test_tools.py with test_schema, verifying both dict and JSON output for Union[int, str].
