# PR description with change summary and related issue numbers


# Seed Material: pydantic/pydantic#2336: Support discriminated union
Source: github_issue_pr
Identifier: pr:pydantic/pydantic#2336

Repository: pydantic/pydantic
PR Number: #2336
PR Title: Support discriminated union
Merged At: 2021-12-18T16:31:36Z
Changed Files: 19
Additions: +1166, Deletions: -29

## PR Description
<!-- Thank you for your contribution! -->
<!-- Unless your change is trivial, please create an issue to discuss the change before creating a PR -->
<!-- See https://pydantic-docs.helpmanual.io/contributing/ for help on Contributing -->

## Change Summary
Add discriminated union support and support open api spec about it

## Related issue number
closes #619
closes #3113
<!-- Are there any issues opened that will be resolved by merging this change? -->

## Checklist

* [x] Unit tests for the changes exist
* [x] Tests pass on CI and coverage remains at 100%
* [x] Documentation reflects the changes where applicable
* [x] `changes/<pull request or issue id>-<github username>.md` file added describing change
  (see [changes/README.md](https://github.com/samuelcolvin/pydantic/blob/master/changes/README.md) for details)


## Linked Issue #619
# Feature Request

Pydantic currently has a decent support for union types through the `typing.Union` type from PEP484, but it does not currently cover all the cases covered by the JSONSchema and OpenAPI specifications, most likely because the two specifications diverge on those points.

OpenAPI supports something similar to tagged unions where a certain field is designated to serve as a "discriminator", which is then matched against literal values to determine which of multiple schemas to use for payload validation. In order to allow Pydantic to support those, I suppose there would have to be a specific type similar to `typing.Union` in order to specify what discriminator field to use and how to match it. Such a type would then be rendered into a schema object (`oneOf`) with an [OpenAPI discriminator object][2] built into it, as well as correctly validate incoming JSON into the correct type based on the value or the discriminator field. This change would only impact OpenAPI, as JSON schema (draft 7 onwards) uses [conditional types][3] instead, which would probably need to be the topic of a different feature request, as both methods appear mutually incompatible.

## Implementation ideas
I'd imagine the final result to be something like this.

```py
MyUnion = Union[Foo, Bar]
MyTaggedUnion = TaggedUnion(Union[Foo, Bar], discriminator='type', mapping={'foo': Foo, 'bar': Bar}))
```

Python doesn't have a feature like TypeScript to let you statically ensure that `discriminator` [exists as a field for all variants of that union][4], though that shouldn't be a problem since this is going to be raised during validation regardless.

`discriminator` and `mapping` could also simply be added to `Schema`, though I'm not sure about whether it's a good idea to add OpenAPI-specific extensions there.

[PEP 593][1] would also have been a nice alternative, since it would hypothetically allow tagged unions to be implemented as a regular union with annotations specific to Pydantic for that purpose, however it is only still a draft and most likely won't make it until Python 3.9 (if at all).

[1]: https://www.python.org/dev/peps/pep-0593/
[2]: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminatorObject
[3]: https://json-schema.org/understanding-json-schema/reference/conditionals.html
[4]: https://www.typescriptlang.org/docs/handbook/advanced-types.html#index-types

## Diff
diff --git a/changes/619-PrettyWood.md b/changes/619-PrettyWood.md
new file mode 100644
index 00000000000..929bfbf6d55
--- /dev/null
+++ b/changes/619-PrettyWood.md
@@ -0,0 +1 @@
+Add a discriminated union. See [the doc](https://pydantic-docs.helpmanual.io/usage/types/#discriminated-unions) for more information.
\ No newline at end of file
diff --git a/docs/examples/schema_ad_hoc.py b/docs/examples/schema_ad_hoc.py
new file mode 100644
index 00000000000..6e93f913def
--- /dev/null
+++ b/docs/examples/schema_ad_hoc.py
@@ -0,0 +1,20 @@
+from typing import Literal, Union
+
+from typing_extensions import Annotated
+
+from pydantic import BaseModel, Field, schema_json
+
+
+class Cat(BaseModel):
+    pet_type: Literal['cat']
+    cat_name: str
+
+
+class Dog(BaseModel):
+    pet_type: Literal['dog']
+    dog_name: str
+
+
+Pet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]
+
+print(schema_json(Pet, title='The Pet Schema', indent=2))
diff --git a/docs/examples/types_union_discriminated.py b/docs/examples/types_union_discriminated.py
new file mode 100644
index 00000000000..bae8476562c
--- /dev/null
+++ b/docs/examples/types_union_discriminated.py
@@ -0,0 +1,30 @@
+from typing import Literal, Union
+
+from pydantic import BaseModel, Field, ValidationError
+
+
+class Cat(BaseModel):
+    pet_type: Literal['cat']
+    meows: int
+
+
+class Dog(BaseModel):
+    pet_type: Literal['dog']
+    barks: float
+
+
+class Lizard(BaseModel):
+    pet_type: Literal['reptile', 'lizard']
+    scales: bool
+
+
+class Model(BaseModel):
+    pet: Union[Cat, Dog, Lizard] = Field(..., discriminator='pet_type')
+    n: int
+
+
+print(Model(pet={'pet_type': 'dog', 'barks': 3.14}, n=1))
+try:
+    Model(pet={'pet_type': 'dog'}, n=1)
+except ValidationError as e:
+    print(e)
diff --git a/docs/examples/types_union_discriminated_nested.py b/docs/examples/types_union_discriminated_nested.py
new file mode 100644
index 00000000000..df258b28b26
--- /dev/null
+++ b/docs/examples/types_union_discriminated_nested.py
@@ -0,0 +1,50 @@
+from typing import Literal, Union
+
+from typing_extensions import Annotated
+
+from pydantic import BaseModel, Field, ValidationError
+
+
+class BlackCat(BaseModel):
+    pet_type: Literal['cat']
+    color: Literal['black']
+    black_name: str
+
+
+class WhiteCat(BaseModel):
+    pet_type: Literal['cat']
+    color: Literal['white']
+    white_name: str
+
+
+# Can also be written with a custom root type
+#
+# class Cat(BaseModel):
+#   __root__: Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]
+
+Cat = Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]
+
+
+class Dog(BaseModel):
+    pet_type: Literal['dog']
+    name: str
+
+
+Pet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]
+
+
+class Model(BaseModel):
+    pet: Pet
+    n: int
+
+
+m = Model(pet={'pet_type': 'cat', 'color': 'black', 'black_name': 'felix'}, n=1)
+print(m)
+try:
+    Model(pet={'pet_type': 'cat', 'color': 'red'}, n='1')
+except ValidationError as e:
+    print(e)
+try:
+    Model(pet={'pet_type': 'cat', 'color': 'black'}, n='1')
+except ValidationError as e:
+    print(e)
diff --git a/docs/usage/schema.md b/docs/usage/schema.md
index 9c341961109..9c82cad785a 100644
--- a/docs/usage/schema.md
+++ b/docs/usage/schema.md
@@ -37,6 +37,19 @@ The format of `$ref`s (`"#/definitions/FooBar"` above) can be altered by calling
 with the `ref_template` keyword argument, e.g. `ApplePie.schema(ref_template='/schemas/{model}.json#/')`, here `{model}`
 will be replaced with the model naming using `str.format()`.
 
+## Getting schema of a specified type
+
+_Pydantic_ includes two standalone utility functions `schema` and `schema_json` that can be used to
+apply the schema generation logic used for _pydantic_ models in a more ad-hoc way.
+These functions behave similarly to `BaseModel.schema` and `BaseModel.schema_json`,
+but work with arbitrary pydantic-compatible types.
+
+```py
+{!.tmp_examples/schema_ad_hoc.py!}
+```
+_(This script is complete, it should run "as is")_
+
+
 ## Field customization
 
 Optionally, the `Field` function can be used to provide extra information about the field and validations.
diff --git a/docs/usage/types.md b/docs/usage/types.md
index 37d779468a9..1595af3fa40 100644
--- a/docs/usage/types.md
+++ b/docs/usage/types.md
@@ -274,6 +274,39 @@ _(This script is complete, it should run "as is")_
 
     See more details in [Required Fields](models.md#required-fields).
 
+#### Discriminated Unions (a.k.a. Tagged Unions)
+
+When `Union` is used with multiple submodels, you sometimes know exactly which submodel needs to
+be checked and validated and want to enforce this.
+To do that you can set the same field - let's call it `my_discriminator` - in each of the submodels
+with a discriminated value, which is one (or many) `Literal` value(s).
+For your `Union`, you can set the discriminator in its value: `Field(discriminator='my_discriminator')`.
+
+Setting a discriminated union has many benefits:
+
+- validation is faster since it is only attempted against one model
+- only one explicit error is raised in case of failure
+- the generated JSON schema implements the [associated OpenAPI specification](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminatorObject)
+
+```py
+{!.tmp_examples/types_union_discriminated.py!}
+```
+_(This script is complete, it should run "as is")_
+
+!!! note
+    Using the [Annotated Fields syntax](../schema/#typingannotated-fields) can be handy to regroup
+    the `Union` and `discriminator` information. See below for an example!
+
+#### Nested Discriminated Unions
+
+Only one discriminator can be set for a field but sometimes you want to combine multiple discriminators.
+In this case you can always create "intermediate" models with `__root__` and add your discriminator.
+
+```py
+{!.tmp_examples/types_union_discriminated_nested.py!}
+```
+_(This script is complete, it should run "as is")_
+
 ### Enums and Choices
 
 *pydantic* uses python's standard `enum` classes to define choices.
diff --git a/pydantic/__init__.py b/pydantic/__init__.py
index ac7f558a53f..6b6c560951a 100644
--- a/pydantic/__init__.py
+++ b/pydantic/__init__.py
@@ -66,6 +66,8 @@
     'parse_file_as',
     'parse_obj_as',
     'parse_raw_as',
+    'schema',
+    'schema_json',
     # types
     'NoneStr',
     'NoneBytes',
diff --git a/pydantic/errors.py b/pydantic/errors.py
index 1b17cf12aaf..6b8d31c0aeb 100644
--- a/pydantic/errors.py
+++ b/pydantic/errors.py
@@ -1,6 +1,6 @@
 from decimal import Decimal
 from pathlib import Path
-from typing import TYPE_CHECKING, Any, Callable, Set, Tuple, Type, Union
+from typing import TYPE_CHECKING, Any, Callable, Sequence, Set, Tuple, Type, Union
 
 from .typing import display_as_type
 
@@ -99,6 +99,8 @@
     'InvalidLengthForBrand',
     'InvalidByteSize',
     'InvalidByteSizeUnit',
+    'MissingDiscriminator',
+    'InvalidDiscriminator',
 )
 
 
@@ -611,3 +613,23 @@ class InvalidByteSize(PydanticValueError):
 
 class InvalidByteSizeUnit(PydanticValueError):
     msg_template = 'could not interpret byte unit: {unit}'
+
+
+class MissingDiscriminator(PydanticValueError):
+    code = 'discriminated_union.missing_discriminator'
+    msg_template = 'Discriminator {discriminator_key!r} is missing in value'
+
+
+class InvalidDiscriminator(PydanticValueError):
+    code = 'discriminated_union.invalid_discriminator'
+    msg_template = (
+        'No match for discriminator {discriminator_key!r} and value {discriminator_value!r} '
+        '(allowed values: {allowed_values})'
+    )
+
+    def __init__(self, *, discriminator_key: str, discriminator_value: Any, allowed_values: Sequence[Any]) -> None:
+        super().__init__(
+            discriminator_key=discriminator_key,
+            discriminator_value=discriminator_value,
+            allowed_values=', '.join(map(repr, allowed_values)),
+        )
diff --git a/pydantic/fields.py b/pydantic/fields.py
index 8894158aacf..7ad442d8e5c 100644
--- a/pydantic/fields.py
+++ b/pydantic/fields.py
@@ -28,7 +28,7 @@
 from . import errors as errors_
 from .class_validators import Validator, make_generic_validator, prep_validators
 from .error_wrappers import ErrorWrapper
-from .errors import ConfigError, NoneIsNotAllowedError
+from .errors import ConfigError, InvalidDiscriminator, MissingDiscriminator, NoneIsNotAllowedError
 from .types import Json, JsonWrapper
 from .typing import (
     Callable,
@@ -45,7 +45,16 @@
     is_union,
     new_type_supertype,
 )
-from .utils import PyObjectStr, Representation, ValueItems, lenient_issubclass, sequence_like, smart_deepcopy
+from .utils import (
+    PyObjectStr,
+    Representation,
+    ValueItems,
+    get_discriminator_alias_and_values,
+    get_unique_discriminator_alias,
+    lenient_issubclass,
+    sequence_like,
+    smart_deepcopy,
+)
 from .validators import constant_validator, dict_validator, find_validators, validate_json
 
 Required: Any = Ellipsis
@@ -108,6 +117,7 @@ class FieldInfo(Representation):
         'allow_mutation',
         'repr',
         'regex',
+        'discriminator',
         'extra',
     )
 
@@ -147,6 +157,7 @@ def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
         self.max_length = kwargs.pop('max_length', None)
         self.allow_mutation = kwargs.pop('allow_mutation', True)
         self.regex = kwargs.pop('regex', None)
+        self.discriminator = kwargs.pop('discriminator', None)
         self.repr = kwargs.pop('repr', True)
         self.extra = kwargs
 
@@ -212,6 +223,7 @@ def Field(
     max_length: int = None,
     allow_mutation: bool = True,
     regex: str = None,
+    discriminator: str = None,
     repr: bool = True,
     **extra: Any,
 ) -> Any:
@@ -249,6 +261,8 @@ def Field(
       assigned on an instance.  The BaseModel Config must set validate_assignment to True
     :param regex: only applies to strings, requires the field match against a regular expression
       pattern string. The schema will have a ``pattern`` validation keyword
+    :param discriminator: only useful with a (discriminated a.k.a. tagged) `Union` of sub models with a common field.
+      The `discriminator` is the name of this common field to shorten validation and improve generated schema
     :param repr: show this field in the representation
     :param **extra: any additional keyword arguments will be added as is to the schema
     """
@@ -272,6 +286,7 @@ def Field(
         max_length=max_length,
         allow_mutation=allow_mutation,
         regex=regex,
+        discriminator=discriminator,
         repr=repr,
         **extra,
     )
@@ -315,6 +330,7 @@ class ModelField(Representation):
         'type_',
         'outer_type_',
         'sub_fields',
+        'sub_fields_mapping',
         'key_field',
         'validators',
         'pre_validators',
@@ -327,6 +343,8 @@ class ModelField(Representation):
         'alias',
         'has_alias',
         'field_info',
+        'discriminator_key',
+        'discriminator_alias',
         'validate_always',
         'allow_none',
         'shape',
@@ -359,10 +377,13 @@ def __init__(
         self.required: 'BoolUndefined' = required
         self.model_config = model_config
         self.field_info: FieldInfo = field_info or FieldInfo(default)
+        self.discriminator_key: Optional[str] = self.field_info.discriminator
+        self.discriminator_alias: Optional[str] = self.discriminator_key
 
         self.allow_none: bool = False
         self.validate_always: bool = False
         self.sub_fields: Optional[List[ModelField]] = None
+        self.sub_fields_mapping: Optional[Dict[str, 'ModelField']] = None  # used for discriminated union
         self.key_field: Optional[ModelField] = None
         self.validators: 'ValidatorsList' = []
         self.pre_validators: Optional['ValidatorsList'] = None
@@ -547,6 +568,15 @@ def _type_analysis(self) -> None:  # noqa: C901 (ignore complexity)
             return
 
         origin = get_origin(self.type_)
+
+        if origin is Annotated:
+            self.type_ = get_args(self.type_)[0]
+            self._type_analysis()
+            return
+
+        if self.discriminator_key is not None and not is_union(origin):
+            raise TypeError('`discriminator` can only be used with `Union` type')
+
         # add extra check for `collections.abc.Hashable` for python 3.10+ where origin is not `None`
         if origin is None or origin is CollectionsHashable:
             # field is not "typing" object eg. Union, Dict, List etc.
@@ -554,10 +584,6 @@ def _type_analysis(self) -> None:  # noqa: C901 (ignore complexity)
             if isinstance(self.type_, type) and isinstance(None, self.type_):
                 self.allow_none = True
             return
-        elif origin is Annotated:
-            self.type_ = get_args(self.type_)[0]
-            self._type_analysis()
-            return
         elif origin is Callable:
             return
         elif is_union(origin):
@@ -579,6 +605,9 @@ def _type_analysis(self) -> None:  # noqa: C901 (ignore complexity)
                 self._type_analysis()
             else:
                 self.sub_fields = [self._create_sub_type(t, f'{self.name}_{display_as_type(t)}') for t in types_]
+
+                if self.discriminator_key is not None:
+                    self.prepare_discriminated_union_sub_fields()
             return
         elif issubclass(origin, Tuple):  # type: ignore
             # origin == Tuple without item type
@@ -672,6 +701,30 @@ def _type_analysis(self) -> None:  # noqa: C901 (ignore complexity)
         # type_ has been refined eg. as the type of a List and sub_fields needs to be populated
         self.sub_fields = [self._create_sub_type(self.type_, '_' + self.name)]
 
+    def prepare_discriminated_union_sub_fields(self) -> None:
+        """
+        Prepare the mapping <discriminator key> -> <ModelField> and update `sub_fields`
+        Note that this process can be aborted if a `ForwardRef` is encountered
+        """
+        assert self.discriminator_key is not None
+        assert self.sub_fields is not None
+        sub_fields_mapping: Dict[str, 'ModelField'] = {}
+        all_aliases: Set[str] = set()
+
+        for sub_field in self.sub_fields:
+            t = sub_field.type_
+            if t.__class__ is ForwardRef:
+                # Stopping everything...will need to call `update_forward_refs`
+                return
+
+            alias, discriminator_values = get_discriminator_alias_and_values(t, self.discriminator_key)
+            all_aliases.add(alias)
+            for discriminator_value in discriminator_values:
+                sub_fields_mapping[discriminator_value] = sub_field
+
+        self.sub_fields_mapping = sub_fields_mapping
+        self.discriminator_alias = get_unique_discriminator_alias(all_aliases, self.discriminator_key)
+
     def _create_sub_type(self, type_: Type[Any], name: str, *, for_keys: bool = False) -> 'ModelField':
         if for_keys:
             class_validators = None
@@ -689,11 +742,15 @@ def _create_sub_type(self, type_: Type[Any], name: str, *, for_keys: bool = Fals
                 for k, v in self.class_validators.items()
                 if v.each_item
             }
+
+        field_info, _ = self._get_field_info(name, type_, None, self.model_config)
+
         return self.__class__(
             type_=type_,
             name=name,
             class_validators=class_validators,
             model_config=self.model_config,
+            field_info=field_info,
         )
 
     def populate_validators(self) -> None:
@@ -940,6 +997,9 @@ def _validate_singleton(
         self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
     ) -> 'ValidateReturn':
         if self.sub_fields:
+            if self.discriminator_key is not None:
+                return self._validate_discriminated_union(v, values, loc, cls)
+
             errors = []
 
             if self.model_config.smart_union and is_union(get_origin(self.type_)):
@@ -980,6 +1040,46 @@ def _validate_singleton(
         else:
             return self._apply_validators(v, values, loc, cls, self.validators)
 
+    def _validate_discriminated_union(
+        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
+    ) -> 'ValidateReturn':
+        assert self.discriminator_key is not None
+        assert self.discriminator_alias is not None
+
+        try:
+            discriminator_value = v[self.discriminator_alias]
+        except KeyError:
+            return v, ErrorWrapper(MissingDiscriminator(discriminator_key=self.discriminator_key), loc)
+        except TypeError:
+            try:
+                # BaseModel or dataclass
+                discriminator_value = getattr(v, self.discriminator_alias)
+            except (AttributeError, TypeError):
+                return v, ErrorWrapper(MissingDiscriminator(discriminator_key=self.discriminator_key), loc)
+
+        try:
+            sub_field = self.sub_fields_mapping[discriminator_value]  # type: ignore[index]
+        except TypeError:
+            assert cls is not None
+            raise ConfigError(
+                f'field "{self.name}" not yet prepared so type is still a ForwardRef, '
+                f'you might need to call {cls.__name__}.update_forward_refs().'
+            )
+        except KeyError:
+            assert self.sub_fields_mapping is not None
+            return v, ErrorWrapper(
+                InvalidDiscriminator(
+                    discriminator_key=self.discriminator_key,
+                    discriminator_value=discriminator_value,
+                    allowed_values=list(self.sub_fields_mapping),
+                ),
+                loc,
+            )
+        else:
+            if not isinstance(loc, tuple):
+                loc = (loc,)
+            return sub_field.validate(v, values, loc=(*loc, display_as_type(sub_field.type_)), cls=cls)
+
     def _apply_validators(
         self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc'], validators: 'ValidatorsList'
     ) -> 'ValidateReturn':
diff --git a/pydantic/schema.py b/pydantic/schema.py
index 727fc7274b8..d5a6d085347 100644
--- a/pydantic/schema.py
+++ b/pydantic/schema.py
@@ -70,6 +70,7 @@
     all_literal_values,
     get_args,
     get_origin,
+    get_sub_types,
     is_callable_type,
     is_literal_type,
     is_namedtuple,
@@ -250,6 +251,37 @@ def field_schema(
         ref_template=ref_template,
         known_models=known_models or set(),
     )
+
+    # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminator-object
+    if field.discriminator_key is not None:
+        assert field.sub_fields_mapping is not None
+
+        discriminator_models_refs: Dict[str, Union[str, Dict[str, Any]]] = {}
+
+        for discriminator_value, sub_field in field.sub_fields_mapping.items():
+            # sub_field is either a `BaseModel` or directly an `Annotated` `Union` of many
+            if is_union(get_origin(sub_field.type_)):
+                sub_models = get_sub_types(sub_field.type_)
+                discriminator_models_refs[discriminator_value] = {
+                    model_name_map[sub_model]: get_schema_ref(
+                        model_name_map[sub_model], ref_prefix, ref_template, False
+                    )
+                    for sub_model in sub_models
+                }
+            else:
+                sub_field_type = sub_field.type_
+                if hasattr(sub_field_type, '__pydantic_model__'):
+                    sub_field_type = sub_field_type.__pydantic_model__
+
+                discriminator_model_name = model_name_map[sub_field_type]
+                discriminator_model_ref = get_schema_ref(discriminator_model_name, ref_prefix, ref_template, False)
+                discriminator_models_refs[discriminator_value] = discriminator_model_ref['$ref']
+
+        s['discriminator'] = {
+            'propertyName': field.discriminator_alias,
+            'mapping': discriminator_models_refs,
+        }
+
     # $ref will only be returned when there are no schema_overrides
     if '$ref' in f_schema:
         return f_schema, f_definitions, f_nested_models
diff --git a/pydantic/tools.py b/pydantic/tools.py
index 19d992b4692..f1d651cd4e6 100644
--- a/pydantic/tools.py
+++ b/pydantic/tools.py
@@ -1,16 +1,19 @@
 import json
 from functools import lru_cache
 from pathlib import Path
-from typing import Any, Callable, Optional, Type, TypeVar, Union
+from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, Union
 
 from .parse import Protocol, load_file, load_str_bytes
 from .types import StrBytes
 from .typing import display_as_type
 
-__all__ = ('parse_file_as', 'parse_obj_as', 'parse_raw_as')
+__all__ = ('parse_file_as', 'parse_obj_as', 'parse_raw_as', 'schema', 'schema_json')
 
 NameFactory = Union[str, Callable[[Type[Any]], str]]
 
+if TYPE_CHECKING:
+    from .typing import DictStrAny
+
 
 def _generate_parsing_type_name(type_: Any) -> str:
     return f'ParsingModel[{display_as_type(type_)}]'
@@ -77,3 +80,13 @@ def parse_raw_as(
         json_loads=json_loads,
     )
     return parse_obj_as(type_, obj, type_name=type_name)
+
+
+def schema(type_: Any, *, title: Optional[NameFactory] = None, **schema_kwargs: Any) -> 'DictStrAny':
+    """Generate a JSON schema (as dict) for the passed model or dynamically generated one"""
+    return _get_parsing_type(type_, type_name=title).schema(**schema_kwargs)
+
+
+def schema_json(type_: Any, *, title: Optional[NameFactory] = None, **schema_json_kwargs: Any) -> str:
+    """Generate a JSON schema (as JSON) for the passed model or dynamically generated one"""
+    return _get_parsing_type(type_, type_name=title).schema_json(**schema_json_kwargs)
diff --git a/pydantic/typing.py b/pydantic/typing.py
index 409b35a0ced..b2742bf097c 100644
--- a/pydantic/typing.py
+++ b/pydantic/typing.py
@@ -262,6 +262,7 @@ def is_union(tp: Type[Any]) -> bool:
     'WithArgsTypes',
     'get_args',
     'get_origin',
+    'get_sub_types',
     'typing_base',
     'get_all_type_hints',
     'is_union',
@@ -310,6 +311,9 @@ def display_as_type(v: Type[Any]) -> str:
     if not isinstance(v, typing_base) and not isinstance(v, WithArgsTypes) and not isinstance(v, type):
         v = v.__class__
 
+    if is_union(get_origin(v)):
+        return f'Union[{", ".join(map(display_as_type, get_args(v)))}]'
+
     if isinstance(v, WithArgsTypes):
         # Generic alias are constructs like `list[int]`
         return str(v).replace('typing.', '')
@@ -443,10 +447,14 @@ def update_field_forward_refs(field: 'ModelField', globalns: Any, localns: Any)
     if field.type_.__class__ == ForwardRef:
         field.type_ = evaluate_forwardref(field.type_, globalns, localns or None)
         field.prepare()
+
     if field.sub_fields:
         for sub_f in field.sub_fields:
             update_field_forward_refs(sub_f, globalns=globalns, localns=localns)
 
+    if field.discriminator_key is not None:
+        field.prepare_discriminated_union_sub_fields()
+
 
 def update_model_forward_refs(
     model: Type[Any],
@@ -487,3 +495,17 @@ def get_class(type_: Type[Any]) -> Union[None, bool, Type[Any]]:
     except (AttributeError, TypeError):
         pass
     return None
+
+
+def get_sub_types(tp: Any) -> List[Any]:
+    """
+    Return all the types that are allowed by type `tp`
+    `tp` can be a `Union` of allowed types or an `Annotated` type
+    """
+    origin = get_origin(tp)
+    if origin is Annotated:
+        return get_sub_types(get_args(tp)[0])
+    elif is_union(origin):
+        return [x for t in get_args(tp) for x in get_sub_types(t)]
+    else:
+        return [tp]
diff --git a/pydantic/utils.py b/pydantic/utils.py
index 9305a30ee16..ec94f76c7fd 100644
--- a/pydantic/utils.py
+++ b/pydantic/utils.py
@@ -9,6 +9,7 @@
     AbstractSet,
     Any,
     Callable,
+    Collection,
     Dict,
     Generator,
     Iterable,
@@ -23,7 +24,19 @@
     Union,
 )
 
-from .typing import NoneType, WithArgsTypes, display_as_type
+from typing_extensions import Annotated
+
+from .errors import ConfigError
+from .typing import (
+    NoneType,
+    WithArgsTypes,
+    all_literal_values,
+    display_as_type,
+    get_args,
+    get_origin,
+    is_literal_type,
+    is_union,
+)
 from .version import version_info
 
 if TYPE_CHECKING:
@@ -57,6 +70,8 @@
     'ClassAttribute',
     'path_type',
     'ROOT_KEY',
+    'get_unique_discriminator_alias',
+    'get_discriminator_alias_and_values',
 )
 
 ROOT_KEY = '__root__'
@@ -665,3 +680,63 @@ def all_identical(left: Iterable[Any], right: Iterable[Any]) -> bool:
         if left_item is not right_item:
             return False
     return True
+
+
+def get_unique_discriminator_alias(all_aliases: Collection[str], discriminator_key: str) -> str:
+    """Validate that all aliases are the same and if that's the case return the alias"""
+    unique_aliases = set(all_aliases)
+    if len(unique_aliases) > 1:
+        raise ConfigError(
+            f'Aliases for discriminator {discriminator_key!r} must be the same (got {", ".join(sorted(all_aliases))})'
+        )
+    return unique_aliases.pop()
+
+
+def get_discriminator_alias_and_values(tp: Any, discriminator_key: str) -> Tuple[str, Tuple[str, ...]]:
+    """
+    Get alias and all valid values in the `Literal` type of the discriminator field
+    `tp` can be a `BaseModel` class or directly an `Annotated` `Union` of many.
+    """
+    is_root_model = getattr(tp, '__custom_root_type__', False)
+
+    if get_origin(tp) is Annotated:
+        tp = get_args(tp)[0]
+
+    if hasattr(tp, '__pydantic_model__'):
+        tp = tp.__pydantic_model__
+
+    if is_union(get_origin(tp)):
+        alias, all_values = _get_union_alias_and_all_values(tp, discriminator_key)
+        return alias, tuple(v for values in all_values for v in values)
+    elif is_root_model:
+        union_type = tp.__fields__[ROOT_KEY].type_
+        alias, all_values = _get_union_alias_and_all_values(union_type, discriminator_key)
+
+        if len(set(all_values)) > 1:
+            raise ConfigError(
+                f'Field {discriminator_key!r} is not the same for all submodels of {display_as_type(tp)!r}'
+            )
+
+        return alias, all_values[0]
+
+    else:
+        try:
+            t_discriminator_type = tp.__fields__[discriminator_key].type_
+        except AttributeError as e:
+            raise TypeError(f'Type {tp.__name__!r} is not a valid `BaseModel` or `dataclass`') from e
+        except KeyError as e:
+            raise ConfigError(f'Model {tp.__name__!r} needs a discriminator field for key {discriminator_key!r}') from e
+
+        if not is_literal_type(t_discriminator_type):
+            raise ConfigError(f'Field {discriminator_key!r} of model {tp.__name__!r} needs to be a `Literal`')
+
+        return tp.__fields__[discriminator_key].alias, all_literal_values(t_discriminator_type)
+
+
+def _get_union_alias_and_all_values(
+    union_type: Type[Any], discriminator_key: str
+) -> Tuple[str, Tuple[Tuple[str, ...], ...]]:
+    zipped_aliases_values = [get_discriminator_alias_and_values(t, discriminator_key) for t in get_args(union_type)]
+    # unzip: [('alias_a',('v1', 'v2)), ('alias_b', ('v3',))] => [('alias_a', 'alias_b'), (('v1', 'v2'), ('v3',))]
+    all_aliases, all_values = zip(*zipped_aliases_values)
+    return get_unique_discriminator_alias(all_aliases, discriminator_key), all_values
diff --git a/tests/test_dataclasses.py b/tests/test_dataclasses.py
index 46340b72496..e99a9c72343 100644
--- a/tests/test_dataclasses.py
+++ b/tests/test_dataclasses.py
@@ -3,9 +3,10 @@
 from collections.abc import Hashable
 from datetime import datetime
 from pathlib import Path
-from typing import Callable, ClassVar, Dict, FrozenSet, List, Optional
+from typing import Callable, ClassVar, Dict, FrozenSet, List, Optional, Union
 
 import pytest
+from typing_extensions import Literal
 
 import pydantic
 from pydantic import BaseModel, ValidationError, validator
@@ -922,6 +923,49 @@ class A2:
     }
 
 
+def test_discrimated_union_basemodel_instance_value():
+    @pydantic.dataclasses.dataclass
+    class A:
+        l: Literal['a']
+
+    @pydantic.dataclasses.dataclass
+    class B:
+        l: Literal['b']
+
+    @pydantic.dataclasses.dataclass
+    class Top:
+        sub: Union[A, B] = dataclasses.field(metadata=dict(discriminator='l'))
+
+    t = Top(sub=A(l='a'))
+    assert isinstance(t, Top)
+    assert Top.__pydantic_model__.schema() == {
+        'title': 'Top',
+        'type': 'object',
+        'properties': {
+            'sub': {
+                'title': 'Sub',
+                'discriminator': {'propertyName': 'l', 'mapping': {'a': '#/definitions/A', 'b': '#/definitions/B'}},
+                'anyOf': [{'$ref': '#/definitions/A'}, {'$ref': '#/definitions/B'}],
+            }
+        },
+        'required': ['sub'],
+        'definitions': {
+            'A': {
+                'title': 'A',
+                'type': 'object',
+                'properties': {'l': {'title': 'L', 'enum': ['a'], 'type': 'string'}},
+                'required': ['l'],
+            },
+            'B': {
+                'title': 'B',
+                'type': 'object',
+                'properties': {'l': {'title': 'L', 'enum': ['b'], 'type': 'string'}},
+                'required': ['l'],
+            },
+        },
+    }
+
+
 def test_keeps_custom_properties():
     class StandardClass:
         """Class which modifies instance creation."""
diff --git a/tests/test_discrimated_union.py b/tests/test_discrimated_union.py
new file mode 100644
index 00000000000..520301174f8
--- /dev/null
+++ b/tests/test_discrimated_union.py
@@ -0,0 +1,363 @@
+import re
+from enum import Enum
+from typing import Union
+
+import pytest
+from typing_extensions import Annotated, Literal
+
+from pydantic import BaseModel, Field, ValidationError
+from pydantic.errors import ConfigError
+
+
+def test_discriminated_union_only_union():
+    with pytest.raises(TypeError, match='`discriminator` can only be used with `Union` type'):
+
+        class Model(BaseModel):
+            x: str = Field(..., discriminator='qwe')
+
+
+def test_discriminated_union_invalid_type():
+    with pytest.raises(TypeError, match="Type 'str' is not a valid `BaseModel` or `dataclass`"):
+
+        class Model(BaseModel):
+            x: Union[str, int] = Field(..., discriminator='qwe')
+
+
+def test_discriminated_union_defined_discriminator():
+    class Cat(BaseModel):
+        c: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        d: str
+
+    with pytest.raises(ConfigError, match="Model 'Cat' needs a discriminator field for key 'pet_type'"):
+
+        class Model(BaseModel):
+            pet: Union[Cat, Dog] = Field(..., discriminator='pet_type')
+            number: int
+
+
+def test_discriminated_union_literal_discriminator():
+    class Cat(BaseModel):
+        pet_type: int
+        c: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        d: str
+
+    with pytest.raises(ConfigError, match="Field 'pet_type' of model 'Cat' needs to be a `Literal`"):
+
+        class Model(BaseModel):
+            pet: Union[Cat, Dog] = Field(..., discriminator='pet_type')
+            number: int
+
+
+def test_discriminated_union_root_same_discriminator():
+    class BlackCat(BaseModel):
+        pet_type: Literal['blackcat']
+
+    class WhiteCat(BaseModel):
+        pet_type: Literal['whitecat']
+
+    class Cat(BaseModel):
+        __root__: Union[BlackCat, WhiteCat]
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+
+    with pytest.raises(ConfigError, match="Field 'pet_type' is not the same for all submodels of 'Cat'"):
+
+        class Pet(BaseModel):
+            __root__: Union[Cat, Dog] = Field(..., discriminator='pet_type')
+
+
+def test_discriminated_union_validation():
+    class BlackCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['black']
+        black_infos: str
+
+    class WhiteCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['white']
+        white_infos: str
+
+    class Cat(BaseModel):
+        __root__: Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        d: str
+
+    class Lizard(BaseModel):
+        pet_type: Literal['reptile', 'lizard']
+        l: str
+
+    class Model(BaseModel):
+        pet: Annotated[Union[Cat, Dog, Lizard], Field(discriminator='pet_type')]
+        number: int
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_typ': 'cat'}, 'number': 'x'})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet',),
+            'msg': "Discriminator 'pet_type' is missing in value",
+            'type': 'value_error.discriminated_union.missing_discriminator',
+            'ctx': {'discriminator_key': 'pet_type'},
+        },
+        {'loc': ('number',), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'},
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': 'fish', 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet',),
+            'msg': "Discriminator 'pet_type' is missing in value",
+            'type': 'value_error.discriminated_union.missing_discriminator',
+            'ctx': {'discriminator_key': 'pet_type'},
+        },
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'fish'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet',),
+            'msg': (
+                "No match for discriminator 'pet_type' and value 'fish' "
+                "(allowed values: 'cat', 'dog', 'reptile', 'lizard')"
+            ),
+            'type': 'value_error.discriminated_union.invalid_discriminator',
+            'ctx': {
+                'discriminator_key': 'pet_type',
+                'discriminator_value': 'fish',
+                'allowed_values': "'cat', 'dog', 'reptile', 'lizard'",
+            },
+        },
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'lizard'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {'loc': ('pet', 'Lizard', 'l'), 'msg': 'field required', 'type': 'value_error.missing'},
+    ]
+
+    m = Model.parse_obj({'pet': {'pet_type': 'lizard', 'l': 'pika'}, 'number': 2})
+    assert isinstance(m.pet, Lizard)
+    assert m.dict() == {'pet': {'pet_type': 'lizard', 'l': 'pika'}, 'number': 2}
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'cat', 'color': 'white'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet', 'Cat', '__root__', 'WhiteCat', 'white_infos'),
+            'msg': 'field required',
+            'type': 'value_error.missing',
+        }
+    ]
+    m = Model.parse_obj({'pet': {'pet_type': 'cat', 'color': 'white', 'white_infos': 'pika'}, 'number': 2})
+    assert isinstance(m.pet.__root__, WhiteCat)
+
+
+def test_discriminated_annotated_union():
+    class BlackCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['black']
+        black_infos: str
+
+    class WhiteCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['white']
+        white_infos: str
+
+    Cat = Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        dog_name: str
+
+    Pet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]
+
+    class Model(BaseModel):
+        pet: Pet
+        number: int
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_typ': 'cat'}, 'number': 'x'})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet',),
+            'msg': "Discriminator 'pet_type' is missing in value",
+            'type': 'value_error.discriminated_union.missing_discriminator',
+            'ctx': {'discriminator_key': 'pet_type'},
+        },
+        {'loc': ('number',), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'},
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'fish'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet',),
+            'msg': "No match for discriminator 'pet_type' and value 'fish' " "(allowed values: 'cat', 'dog')",
+            'type': 'value_error.discriminated_union.invalid_discriminator',
+            'ctx': {'discriminator_key': 'pet_type', 'discriminator_value': 'fish', 'allowed_values': "'cat', 'dog'"},
+        },
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'dog'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {'loc': ('pet', 'Dog', 'dog_name'), 'msg': 'field required', 'type': 'value_error.missing'},
+    ]
+    m = Model.parse_obj({'pet': {'pet_type': 'dog', 'dog_name': 'milou'}, 'number': 2})
+    assert isinstance(m.pet, Dog)
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'cat', 'color': 'red'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet', 'Union[BlackCat, WhiteCat]'),
+            'msg': "No match for discriminator 'color' and value 'red' " "(allowed values: 'black', 'white')",
+            'type': 'value_error.discriminated_union.invalid_discriminator',
+            'ctx': {'discriminator_key': 'color', 'discriminator_value': 'red', 'allowed_values': "'black', 'white'"},
+        }
+    ]
+
+    with pytest.raises(ValidationError) as exc_info:
+        Model.parse_obj({'pet': {'pet_type': 'cat', 'color': 'white'}, 'number': 2})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('pet', 'Union[BlackCat, WhiteCat]', 'WhiteCat', 'white_infos'),
+            'msg': 'field required',
+            'type': 'value_error.missing',
+        }
+    ]
+    m = Model.parse_obj({'pet': {'pet_type': 'cat', 'color': 'white', 'white_infos': 'pika'}, 'number': 2})
+    assert isinstance(m.pet, WhiteCat)
+
+
+def test_discriminated_union_basemodel_instance_value():
+    class A(BaseModel):
+        l: Literal['a']
+
+    class B(BaseModel):
+        l: Literal['b']
+
+    class Top(BaseModel):
+        sub: Union[A, B] = Field(..., discriminator='l')
+
+    t = Top(sub=A(l='a'))
+    assert isinstance(t, Top)
+
+
+def test_discriminated_union_int():
+    class A(BaseModel):
+        l: Literal[1]
+
+    class B(BaseModel):
+        l: Literal[2]
+
+    class Top(BaseModel):
+        sub: Union[A, B] = Field(..., discriminator='l')
+
+    assert isinstance(Top.parse_obj({'sub': {'l': 2}}).sub, B)
+    with pytest.raises(ValidationError) as exc_info:
+        Top.parse_obj({'sub': {'l': 3}})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('sub',),
+            'msg': "No match for discriminator 'l' and value 3 (allowed values: 1, 2)",
+            'type': 'value_error.discriminated_union.invalid_discriminator',
+            'ctx': {'discriminator_key': 'l', 'discriminator_value': 3, 'allowed_values': '1, 2'},
+        }
+    ]
+
+
+def test_discriminated_union_enum():
+    class EnumValue(Enum):
+        a = 1
+        b = 2
+
+    class A(BaseModel):
+        l: Literal[EnumValue.a]
+
+    class B(BaseModel):
+        l: Literal[EnumValue.b]
+
+    class Top(BaseModel):
+        sub: Union[A, B] = Field(..., discriminator='l')
+
+    assert isinstance(Top.parse_obj({'sub': {'l': EnumValue.b}}).sub, B)
+    with pytest.raises(ValidationError) as exc_info:
+        Top.parse_obj({'sub': {'l': 3}})
+    assert exc_info.value.errors() == [
+        {
+            'loc': ('sub',),
+            'msg': "No match for discriminator 'l' and value 3 (allowed values: <EnumValue.a: 1>, <EnumValue.b: 2>)",
+            'type': 'value_error.discriminated_union.invalid_discriminator',
+            'ctx': {
+                'discriminator_key': 'l',
+                'discriminator_value': 3,
+                'allowed_values': '<EnumValue.a: 1>, <EnumValue.b: 2>',
+            },
+        }
+    ]
+
+
+def test_alias_different():
+    class Cat(BaseModel):
+        pet_type: Literal['cat'] = Field(alias='U')
+        c: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog'] = Field(alias='T')
+        d: str
+
+    with pytest.raises(
+        ConfigError, match=re.escape("Aliases for discriminator 'pet_type' must be the same (got T, U)")
+    ):
+
+        class Model(BaseModel):
+            pet: Union[Cat, Dog] = Field(discriminator='pet_type')
+
+
+def test_alias_same():
+    class Cat(BaseModel):
+        pet_type: Literal['cat'] = Field(alias='typeOfPet')
+        c: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog'] = Field(alias='typeOfPet')
+        d: str
+
+    class Model(BaseModel):
+        pet: Union[Cat, Dog] = Field(discriminator='pet_type')
+
+    assert Model(**{'pet': {'typeOfPet': 'dog', 'd': 'milou'}}).pet.pet_type == 'dog'
+
+
+def test_nested():
+    class Cat(BaseModel):
+        pet_type: Literal['cat']
+        name: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        name: str
+
+    CommonPet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]
+
+    class Lizard(BaseModel):
+        pet_type: Literal['reptile', 'lizard']
+        name: str
+
+    class Model(BaseModel):
+        pet: Union[CommonPet, Lizard] = Field(..., discriminator='pet_type')
+        n: int
+
+    assert isinstance(Model(**{'pet': {'pet_type': 'dog', 'name': 'Milou'}, 'n': 5}).pet, Dog)
diff --git a/tests/test_forward_ref.py b/tests/test_forward_ref.py
index 12a337f824d..aac1dae10a4 100644
--- a/tests/test_forward_ref.py
+++ b/tests/test_forward_ref.py
@@ -564,6 +564,53 @@ class NestedTuple(BaseModel):
     assert obj.dict() == {'x': (1, {'x': (2, {'x': (3, None)})})}
 
 
+def test_discriminated_union_forward_ref(create_module):
+    @create_module
+    def module():
+        from typing import Union
+
+        from typing_extensions import Literal
+
+        from pydantic import BaseModel, Field
+
+        class Pet(BaseModel):
+            __root__: Union['Cat', 'Dog'] = Field(..., discriminator='type')  # noqa: F821
+
+        class Cat(BaseModel):
+            type: Literal['cat']
+
+        class Dog(BaseModel):
+            type: Literal['dog']
+
+    with pytest.raises(ConfigError, match='you might need to call Pet.update_forward_refs()'):
+        module.Pet.parse_obj({'type': 'pika'})
+
+    module.Pet.update_forward_refs()
+
+    with pytest.raises(ValidationError, match="No match for discriminator 'type' and value 'pika'"):
+        module.Pet.parse_obj({'type': 'pika'})
+
+    assert module.Pet.schema() == {
+        'title': 'Pet',
+        'discriminator': {'propertyName': 'type', 'mapping': {'cat': '#/definitions/Cat', 'dog': '#/definitions/Dog'}},
+        'anyOf': [{'$ref': '#/definitions/Cat'}, {'$ref': '#/definitions/Dog'}],
+        'definitions': {
+            'Cat': {
+                'title': 'Cat',
+                'type': 'object',
+                'properties': {'type': {'title': 'Type', 'enum': ['cat'], 'type': 'string'}},
+                'required': ['type'],
+            },
+            'Dog': {
+                'title': 'Dog',
+                'type': 'object',
+                'properties': {'type': {'title': 'Type', 'enum': ['dog'], 'type': 'string'}},
+                'required': ['type'],
+            },
+        },
+    }
+
+
 @skip_pre_37
 def test_class_var_as_string(create_module):
     module = create_module(
diff --git a/tests/test_main.py b/tests/test_main.py
index ceb925db41e..f44776c53d3 100644
--- a/tests/test_main.py
+++ b/tests/test_main.py
@@ -19,7 +19,6 @@
 from uuid import UUID, uuid4
 
 import pytest
-from pytest import param
 
 from pydantic import (
     BaseConfig,
@@ -1373,61 +1372,61 @@ class Bar(BaseModel):
 @pytest.mark.parametrize(
     'exclude,expected,raises_match',
     [
-        param(
+        pytest.param(
             {'foos': {0: {'a'}, 1: {'a'}}},
             {'c': 3, 'foos': [{'b': 2}, {'b': 4}]},
             None,
             id='excluding fields of indexed list items',
         ),
-        param(
+        pytest.param(
             {'foos': {'a'}},
             TypeError,
             'expected integer keys',
             id='should fail trying to exclude string keys on list field (1).',
         ),
-        param(
+        pytest.param(
             {'foos': {0: ..., 'a': ...}},
             TypeError,
             'expected integer keys',
             id='should fail trying to exclude string keys on list field (2).',
         ),
-        param(
+        pytest.param(
             {'foos': {0: 1}},
             TypeError,
             'Unexpected type',
             id='should fail using integer key to specify list item field name (1)',
         ),
-        param(
+        pytest.param(
             {'foos': {'__all__': 1}},
             TypeError,
             'Unexpected type',
             id='should fail using integer key to specify list item field name (2)',
         ),
-        param(
+        pytest.param(
             {'foos': {'__all__': {'a'}}},
             {'c': 3, 'foos': [{'b': 2}, {'b': 4}]},
             None,
             id='using "__all__" to exclude specific nested field',
         ),
-        param(
+        pytest.param(
             {'foos': {0: {'b'}, '__all__': {'a'}}},
             {'c': 3, 'foos': [{}, {'b': 4}]},
             None,
             id='using "__all__" to exclude specific nested field in combination with more specific exclude',
         ),
-        param(
+        pytest.param(
             {'foos': {'__all__'}},
             {'c': 3, 'foos': []},
             None,
             id='using "__all__" to exclude all list items',
         ),
-        param(
+        pytest.param(
             {'foos': {1, '__all__'}},
             {'c': 3, 'foos': []},
             None,
             id='using "__all__" and other items should get merged together, still excluding all list items',
         ),
-        param(
+        pytest.param(
             {'foos': {1: {'a'}, -1: {'b'}}},
             {'c': 3, 'foos': [{'a': 1, 'b': 2}, {}]},
             None,
@@ -1458,13 +1457,13 @@ class Bar(BaseModel):
 @pytest.mark.parametrize(
     'excludes,expected',
     [
-        param(
+        pytest.param(
             {'bars': {0}},
             {'a': 1, 'bars': [{'y': 2}, {'w': -1, 'z': 3}]},
             id='excluding first item from list field using index',
         ),
-        param({'bars': {'__all__'}}, {'a': 1, 'bars': []}, id='using "__all__" to exclude all list items'),
-        param(
+        pytest.param({'bars': {'__all__'}}, {'a': 1, 'bars': []}, id='using "__all__" to exclude all list items'),
+        pytest.param(
             {'bars': {'__all__': {'w'}}},
             {'a': 1, 'bars': [{'x': 1}, {'y': 2}, {'z': 3}]},
             id='exclude single dict key from all list items',
@@ -2094,7 +2093,7 @@ class Model(Base, some_config='new_value'):
 
 @pytest.mark.skipif(sys.version_info < (3, 10), reason='need 3.10 version')
 def test_new_union_origin():
-    """On 3.10+, origin of `int | str` is `types.Union`, not `typing.Union`"""
+    """On 3.10+, origin of `int | str` is `types.UnionType`, not `typing.Union`"""
 
     class Model(BaseModel):
         x: int | str
diff --git a/tests/test_schema.py b/tests/test_schema.py
index 709b468b2f5..c1e1f01b028 100644
--- a/tests/test_schema.py
+++ b/tests/test_schema.py
@@ -27,7 +27,7 @@
 from uuid import UUID
 
 import pytest
-from typing_extensions import Literal
+from typing_extensions import Annotated, Literal
 
 from pydantic import BaseModel, Extra, Field, ValidationError, confrozenset, conlist, conset, validator
 from pydantic.color import Color
@@ -2626,3 +2626,254 @@ def resolve(self) -> 'Model':  # noqa
         },
         '$ref': '#/definitions/Model',
     }
+
+
+def test_discriminated_union():
+    class BlackCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['black']
+
+    class WhiteCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['white']
+
+    class Cat(BaseModel):
+        __root__: Union[BlackCat, WhiteCat] = Field(..., discriminator='color')
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+
+    class Lizard(BaseModel):
+        pet_type: Literal['reptile', 'lizard']
+
+    class Model(BaseModel):
+        pet: Union[Cat, Dog, Lizard] = Field(..., discriminator='pet_type')
+
+    assert Model.schema() == {
+        'title': 'Model',
+        'type': 'object',
+        'properties': {
+            'pet': {
+                'title': 'Pet',
+                'discriminator': {
+                    'propertyName': 'pet_type',
+                    'mapping': {
+                        'cat': '#/definitions/Cat',
+                        'dog': '#/definitions/Dog',
+                        'reptile': '#/definitions/Lizard',
+                        'lizard': '#/definitions/Lizard',
+                    },
+                },
+                'anyOf': [
+                    {'$ref': '#/definitions/Cat'},
+                    {'$ref': '#/definitions/Dog'},
+                    {'$ref': '#/definitions/Lizard'},
+                ],
+            }
+        },
+        'required': ['pet'],
+        'definitions': {
+            'BlackCat': {
+                'title': 'BlackCat',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['cat'], 'type': 'string'},
+                    'color': {'title': 'Color', 'enum': ['black'], 'type': 'string'},
+                },
+                'required': ['pet_type', 'color'],
+            },
+            'WhiteCat': {
+                'title': 'WhiteCat',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['cat'], 'type': 'string'},
+                    'color': {'title': 'Color', 'enum': ['white'], 'type': 'string'},
+                },
+                'required': ['pet_type', 'color'],
+            },
+            'Cat': {
+                'title': 'Cat',
+                'discriminator': {
+                    'propertyName': 'color',
+                    'mapping': {'black': '#/definitions/BlackCat', 'white': '#/definitions/WhiteCat'},
+                },
+                'anyOf': [{'$ref': '#/definitions/BlackCat'}, {'$ref': '#/definitions/WhiteCat'}],
+            },
+            'Dog': {
+                'title': 'Dog',
+                'type': 'object',
+                'properties': {'pet_type': {'title': 'Pet Type', 'enum': ['dog'], 'type': 'string'}},
+                'required': ['pet_type'],
+            },
+            'Lizard': {
+                'title': 'Lizard',
+                'type': 'object',
+                'properties': {'pet_type': {'title': 'Pet Type', 'enum': ['reptile', 'lizard'], 'type': 'string'}},
+                'required': ['pet_type'],
+            },
+        },
+    }
+
+
+def test_discriminated_annotated_union():
+    class BlackCatWithHeight(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['black']
+        info: Literal['height']
+        black_infos: str
+
+    class BlackCatWithWeight(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['black']
+        info: Literal['weight']
+        black_infos: str
+
+    BlackCat = Annotated[Union[BlackCatWithHeight, BlackCatWithWeight], Field(discriminator='info')]
+
+    class WhiteCat(BaseModel):
+        pet_type: Literal['cat']
+        color: Literal['white']
+        white_infos: str
+
+    Cat = Annotated[Union[BlackCat, WhiteCat], Field(discriminator='color')]
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog']
+        dog_name: str
+
+    Pet = Annotated[Union[Cat, Dog], Field(discriminator='pet_type')]
+
+    class Model(BaseModel):
+        pet: Pet
+        number: int
+
+    assert Model.schema() == {
+        'title': 'Model',
+        'type': 'object',
+        'properties': {
+            'pet': {
+                'title': 'Pet',
+                'discriminator': {
+                    'propertyName': 'pet_type',
+                    'mapping': {
+                        'cat': {
+                            'BlackCatWithHeight': {'$ref': '#/definitions/BlackCatWithHeight'},
+                            'BlackCatWithWeight': {'$ref': '#/definitions/BlackCatWithWeight'},
+                            'WhiteCat': {'$ref': '#/definitions/WhiteCat'},
+                        },
+                        'dog': '#/definitions/Dog',
+                    },
+                },
+                'anyOf': [
+                    {
+                        'anyOf': [
+                            {
+                                'anyOf': [
+                                    {'$ref': '#/definitions/BlackCatWithHeight'},
+                                    {'$ref': '#/definitions/BlackCatWithWeight'},
+                                ]
+                            },
+                            {'$ref': '#/definitions/WhiteCat'},
+                        ]
+                    },
+                    {'$ref': '#/definitions/Dog'},
+                ],
+            },
+            'number': {'title': 'Number', 'type': 'integer'},
+        },
+        'required': ['pet', 'number'],
+        'definitions': {
+            'BlackCatWithHeight': {
+                'title': 'BlackCatWithHeight',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['cat'], 'type': 'string'},
+                    'color': {'title': 'Color', 'enum': ['black'], 'type': 'string'},
+                    'info': {'title': 'Info', 'enum': ['height'], 'type': 'string'},
+                    'black_infos': {'title': 'Black Infos', 'type': 'string'},
+                },
+                'required': ['pet_type', 'color', 'info', 'black_infos'],
+            },
+            'BlackCatWithWeight': {
+                'title': 'BlackCatWithWeight',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['cat'], 'type': 'string'},
+                    'color': {'title': 'Color', 'enum': ['black'], 'type': 'string'},
+                    'info': {'title': 'Info', 'enum': ['weight'], 'type': 'string'},
+                    'black_infos': {'title': 'Black Infos', 'type': 'string'},
+                },
+                'required': ['pet_type', 'color', 'info', 'black_infos'],
+            },
+            'WhiteCat': {
+                'title': 'WhiteCat',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['cat'], 'type': 'string'},
+                    'color': {'title': 'Color', 'enum': ['white'], 'type': 'string'},
+                    'white_infos': {'title': 'White Infos', 'type': 'string'},
+                },
+                'required': ['pet_type', 'color', 'white_infos'],
+            },
+            'Dog': {
+                'title': 'Dog',
+                'type': 'object',
+                'properties': {
+                    'pet_type': {'title': 'Pet Type', 'enum': ['dog'], 'type': 'string'},
+                    'dog_name': {'title': 'Dog Name', 'type': 'string'},
+                },
+                'required': ['pet_type', 'dog_name'],
+            },
+        },
+    }
+
+
+def test_alias_same():
+    class Cat(BaseModel):
+        pet_type: Literal['cat'] = Field(alias='typeOfPet')
+        c: str
+
+    class Dog(BaseModel):
+        pet_type: Literal['dog'] = Field(alias='typeOfPet')
+        d: str
+
+    class Model(BaseModel):
+        pet: Union[Cat, Dog] = Field(discriminator='pet_type')
+        number: int
+
+    assert Model.schema() == {
+        'type': 'object',
+        'title': 'Model',
+        'properties': {
+            'number': {'title': 'Number', 'type': 'integer'},
+            'pet': {
+                'anyOf': [{'$ref': '#/definitions/Cat'}, {'$ref': '#/definitions/Dog'}],
+                'discriminator': {
+                    'mapping': {'cat': '#/definitions/Cat', 'dog': '#/definitions/Dog'},
+                    'propertyName': 'typeOfPet',
+                },
+                'title': 'Pet',
+            },
+        },
+        'required': ['pet', 'number'],
+        'definitions': {
+            'Cat': {
+                'properties': {
+                    'c': {'title': 'C', 'type': 'string'},
+                    'typeOfPet': {'enum': ['cat'], 'title': 'Typeofpet', 'type': 'string'},
+                },
+                'required': ['typeOfPet', 'c'],
+                'title': 'Cat',
+                'type': 'object',
+            },
+            'Dog': {
+                'properties': {
+                    'd': {'title': 'D', 'type': 'string'},
+                    'typeOfPet': {'enum': ['dog'], 'title': 'Typeofpet', 'type': 'string'},
+                },
+                'required': ['typeOfPet', 'd'],
+                'title': 'Dog',
+                'type': 'object',
+            },
+        },
+    }
diff --git a/tests/test_tools.py b/tests/test_tools.py
index c1a13e68ca4..97784d55277 100644
--- a/tests/test_tools.py
+++ b/tests/test_tools.py
@@ -1,11 +1,11 @@
 import json
-from typing import Dict, List, Mapping
+from typing import Dict, List, Mapping, Union
 
 import pytest
 
 from pydantic import BaseModel, ValidationError
 from pydantic.dataclasses import dataclass
-from pydantic.tools import parse_file_as, parse_obj_as, parse_raw_as
+from pydantic.tools import parse_file_as, parse_obj_as, parse_raw_as, schema, schema_json
 
 
 @pytest.mark.parametrize('obj,type_,parsed', [('1', int, 1), (['1'], List[int], [1])])
@@ -98,3 +98,23 @@ class Item(BaseModel):
     item_data = '[{"id": 1, "name": "My Item"}]'
     items = parse_raw_as(List[Item], item_data)
     assert items == [Item(id=1, name='My Item')]
+
+
+def test_schema():
+    assert schema(Union[int, str], title='IntOrStr') == {
+        'title': 'IntOrStr',
+        'anyOf': [{'type': 'integer'}, {'type': 'string'}],
+    }
+    assert schema_json(Union[int, str], title='IntOrStr', indent=2) == (
+        '{\n'
+        '  "title": "IntOrStr",\n'
+        '  "anyOf": [\n'
+        '    {\n'
+        '      "type": "integer"\n'
+        '    },\n'
+        '    {\n'
+        '      "type": "string"\n'
+        '    }\n'
+        '  ]\n'
+        '}'
+    )
