# pr646_metadata


# Seed Material: fastapi/fastapi#646: Make compatible with pydantic v1
Source: github_issue_pr
Identifier: pr:fastapi/fastapi#646

Repository: fastapi/fastapi
PR Number: #646
PR Title: Make compatible with pydantic v1
Merged At: 2019-11-27T19:32:02Z
Changed Files: 66
Additions: +802, Deletions: -425

## PR Description
Still needs docs updates, but tests pass and raise no deprecation warnings.

## Diff (first 3000 chars)
diff --git a/Pipfile b/Pipfile
index 9b8d31bea80d5..4f1ba44d8b2a4 100644
--- a/Pipfile
+++ b/Pipfile
@@ -26,7 +26,7 @@ uvicorn = "*"
 
 [packages]
 starlette = "==0.12.9"
-pydantic = "==0.32.2"
+pydantic = "==1.0.0"
 databases = {extras = ["sqlite"],version = "*"}
 hypercorn = "*"
 orjson = "*"
diff --git a/docs/src/body_schema/tutorial001.py b/docs/src/body_schema/tutorial001.py
index 6c8b101ba220a..7b2c9454d82f4 100644
--- a/docs/src/body_schema/tutorial001.py
+++ b/docs/src/body_schema/tutorial001.py
@@ -1,13 +1,13 @@
 from fastapi import Body, FastAPI
-from pydantic import BaseModel, Schema
+from pydantic import BaseModel, Field
 
 app = FastAPI()
 
 
 class Item(BaseModel):
     name: str
-    description: str = Schema(None, title="The description of the item", max_length=300)
-    price: float = Schema(..., gt=0, description="The price must be greater than zero")
+    description: str = Field(None, title="The description of the item", max_length=300)
+    price: float = Field(..., gt=0, description="The price must be greater than zero")
     tax: float = None
 
 
diff --git a/docs/src/body_updates/tutorial002.py b/docs/src/body_updates/tutorial002.py
index e10fbb9213cdd..56cb8c4dce663 100644
--- a/docs/src/body_updates/tutorial002.py
+++ b/docs/src/body_updates/tutorial002.py
@@ -31,7 +31,7 @@ async def read_item(item_id: str):
 async def update_item(item_id: str, item: Item):
     stored_item_data = items[item_id]
     stored_item_model = Item(**stored_item_data)
-    update_data = item.dict(skip_defaults=True)
+    update_data = item.dict(exclude_unset=True)
     updated_item = stored_item_model.copy(update=update_data)
     items[item_id] = jsonable_encoder(updated_item)
     return updated_item
diff --git a/docs/src/extra_models/tutorial001.py b/docs/src/extra_models/tutorial001.py
index aa8e7dad456b1..08d3659b0148d 100644
--- a/docs/src/extra_models/tutorial001.py
+++ b/docs/src/extra_models/tutorial001.py
@@ -1,6 +1,5 @@
 from fastapi import FastAPI
-from pydantic import BaseModel
-from pydantic.types import EmailStr
+from pydantic import BaseModel, EmailStr
 
 app = FastAPI()
 
diff --git a/docs/src/extra_models/tutorial002.py b/docs/src/extra_models/tutorial002.py
index 605baf91f05e9..ab680eca0adc3 100644
--- a/docs/src/extra_models/tutorial002.py
+++ b/docs/src/extra_models/tutorial002.py
@@ -1,6 +1,5 @@
 from fastapi import FastAPI
-from pydantic import BaseModel
-from pydantic.types import EmailStr
+from pydantic import BaseModel, EmailStr
 
 app = FastAPI()
 
diff --git a/docs/src/response_model/tutorial002.py b/docs/src/response_model/tutorial002.py
index 3fb475b9d9cc7..b36b2a347cdbd 100644
--- a/docs/src/response_model/tutorial002.py
+++ b/docs/src/response_model/tutorial002.py
@@ -1,6 +1,5 @@
 from fastapi import FastAPI
-from pydantic import BaseModel
-from pydantic.types import EmailStr
+from pydantic import BaseModel, EmailStr
 
 app = FastAPI()
 
diff --git a/docs/src/response_model/tutorial003.py b/docs/src/response_mode