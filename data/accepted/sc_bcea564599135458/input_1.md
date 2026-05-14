# PR description text from fastapi/fastapi#2335


# Seed Material: fastapi/fastapi#2335: ⬆️  Upgrade Starlette to 0.14.2, including internal `UJSONResponse` migrated from Starlette
Source: github_issue_pr
Identifier: pr:fastapi/fastapi#2335

Repository: fastapi/fastapi
PR Number: #2335
PR Title: ⬆️  Upgrade Starlette to 0.14.2, including internal `UJSONResponse` migrated from Starlette
Merged At: 2021-05-10T14:09:05Z
Changed Files: 3
Additions: +51, Deletions: -3

## PR Description
starlette 0.14.1 includes a [fix](https://github.com/encode/starlette/pull/942) for users that want to use the `@requires` decorator from the `AuthenticationMiddleware` on FastAPI routes.

Breaking in starlette changes as far as I can see are:
 -  `UJSONResponse` was removed from the core [as per this issue](https://github.com/encode/starlette/issues/901), they added [documentation](https://www.starlette.io/responses/#custom-json-serialization) on how to implement custom JSON serialization. `UJSONResponse` is explicitly exported in FastAPI and should either be removed to follow starlette or added back in as done with `ORJSONResponse`. For this PR I chose to add a custom `UJSONResponse` and add test cases.

Is there any reason it was hard locked to 13.6 I am not aware of or is it as straightforward as updating the requirement?

## Diff (first 3000 chars)
diff --git a/fastapi/responses.py b/fastapi/responses.py
index 8d9d62dfb0068..6cd7931571fc9 100644
--- a/fastapi/responses.py
+++ b/fastapi/responses.py
@@ -7,7 +7,12 @@
 from starlette.responses import RedirectResponse as RedirectResponse  # noqa
 from starlette.responses import Response as Response  # noqa
 from starlette.responses import StreamingResponse as StreamingResponse  # noqa
-from starlette.responses import UJSONResponse as UJSONResponse  # noqa
+
+try:
+    import ujson
+except ImportError:  # pragma: nocover
+    ujson = None  # type: ignore
+
 
 try:
     import orjson
@@ -15,6 +20,12 @@
     orjson = None  # type: ignore
 
 
+class UJSONResponse(JSONResponse):
+    def render(self, content: Any) -> bytes:
+        assert ujson is not None, "ujson must be installed to use UJSONResponse"
+        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")
+
+
 class ORJSONResponse(JSONResponse):
     media_type = "application/json"
 
diff --git a/pyproject.toml b/pyproject.toml
index 2f057f5aa844e..009c6a755525e 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -32,7 +32,7 @@ classifiers = [
     "Topic :: Internet :: WWW/HTTP",
 ]
 requires = [
-    "starlette ==0.13.6",
+    "starlette ==0.14.2",
     "pydantic >=1.0.0,<2.0.0"
 ]
 description-file = "README.md"
@@ -57,6 +57,7 @@ test = [
     "peewee >=3.13.3,<4.0.0",
     "databases[sqlite] >=0.3.2,<0.4.0",
     "orjson >=3.2.1,<4.0.0",
+    "ujson >=4.0.1,<5.0.0",
     "async_exit_stack >=1.0.1,<2.0.0",
     "async_generator >=1.10,<2.0.0",
     "python-multipart >=0.0.5,<0.0.6",
@@ -87,7 +88,7 @@ all = [
     "itsdangerous >=1.1.0,<2.0.0",
     "pyyaml >=5.3.1,<6.0.0",
     "graphene >=2.1.8,<3.0.0",
-    "ujson >=3.0.0,<4.0.0",
+    "ujson >=4.0.1,<5.0.0",
     "orjson >=3.2.1,<4.0.0",
     "email_validator >=1.1.1,<2.0.0",
     "uvicorn[standard] >=0.12.0,<0.14.0",
diff --git a/tests/test_tutorial/test_custom_response/test_tutorial001.py b/tests/test_tutorial/test_custom_response/test_tutorial001.py
new file mode 100644
index 0000000000000..430076f88f0fd
--- /dev/null
+++ b/tests/test_tutorial/test_custom_response/test_tutorial001.py
@@ -0,0 +1,36 @@
+from fastapi.testclient import TestClient
+
+from docs_src.custom_response.tutorial001 import app
+
+client = TestClient(app)
+
+openapi_schema = {
+    "openapi": "3.0.2",
+    "info": {"title": "FastAPI", "version": "0.1.0"},
+    "paths": {
+        "/items/": {
+            "get": {
+                "responses": {
+                    "200": {
+                        "description": "Successful Response",
+                        "content": {"application/json": {"schema": {}}},
+                    }
+                },
+                "summary": "Read Items",
+                "operationId": "read_items_items__get",
+            }
+        }
+    },
+}
+
+
+def test_openapi_schema():
+    response = client.get("/openapi.json")
+    assert response.status_code == 200, response.text
+    assert response.json() == openap