# issue_619


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

[PEP 593][1] would also have been a nice alternative, since it would hypothetically allow tagged unions to be implemented as a regular union with annotations specific

## Diff (first 3000 chars)
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
+