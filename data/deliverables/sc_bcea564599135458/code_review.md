# Post-Merge Code Review: PR #2335 – Starlette Upgrade and UJSONResponse Migration

## Summary of Changes

PR #2335 upgrades the Starlette dependency from version 0.13.6 to 0.14.2. This change addresses a breaking change in Starlette where the `UJSONResponse` class was removed from its core responses module. To maintain backward compatibility for FastAPI users, this PR migrates the `UJSONResponse` into FastAPI itself, implementing it as a custom response class similar to the existing `ORJSONResponse`.

The changes span three files: `fastapi/responses.py` where the new `UJSONResponse` class is defined, `pyproject.toml` where dependency versions are updated, and a new test file `tests/test_tutorial/test_custom_response/test_tutorial001.py` that verifies OpenAPI schema generation for a custom response tutorial.

## Motivation and Breaking Changes

The primary motivation for this upgrade is to incorporate a fix in Starlette PR #942 for users who want to use the `@requires` decorator from `AuthenticationMiddleware` on FastAPI routes. The Starlette version 0.14.1 includes this fix.

The breaking change driving the migration is that Starlette removed `UJSONResponse` from its core module, as documented in Starlette issue #901. Since `UJSONResponse` was explicitly exported in FastAPI's `responses.py` (via the line `from starlette.responses import UJSONResponse as UJSONResponse`), the upgrade required a decision: either remove the export to align with Starlette's direction, or implement a custom version within FastAPI. The PR author chose the latter approach, consistent with how `ORJSONResponse` is already handled in FastAPI.

## Technical Analysis

The new `UJSONResponse` class in `fastapi/responses.py` extends `JSONResponse` and overrides the `render` method to use `ujson` for serialization. It includes an assertion that `ujson` is not None before attempting to serialize, raising an `AssertionError` with the message "ujson must be installed to use UJSONResponse" if the library is missing. The import for `ujson` is wrapped in a try/except block, setting `ujson` to `None` on `ImportError`, which mirrors the pattern used for the `orjson` import just below it.

Compared to the `ORJSONResponse` class, the `UJSONResponse` implementation is simpler. `ORJSONResponse` explicitly sets the `media_type` class attribute to `"application/json"`, while `UJSONResponse` inherits it from `JSONResponse`. Both use a similar try/except import pattern for their respective libraries. The `ORJSONResponse.render` method uses `orjson.dumps` directly, while `UJSONResponse.render` calls `ujson.dumps` and then encodes the result to UTF-8 bytes. The assert-based error handling in `UJSONResponse` is a development-time check; in production, if `ujson` is not installed, the class would fail at runtime when `render` is called. This is acceptable because `ujson` is an optional dependency, but it differs from the silent failure that would occur if the import were to fail without setting the variable to `None`.

## Dependency Management Review

The `pyproject.toml` changes update the `starlette` dependency in the `requires` section from `==0.13.6` to `==0.14.2`. This is an exact version pin, which ensures reproducible builds but may require manual updates for security patches. For the optional `ujson` dependency, the version is updated in two places: in the `test` extras section from `>=3.0.0,<4.0.0` to `>=4.0.1,<5.0.0`, and in the `all` extras section from `>=3.0.0,<4.0.0` to `>=4.0.1,<5.0.0`. This adds `ujson` as a test dependency and broadens its version range in the `all` extras.

The pinning strategy for `starlette` is strict (`==0.14.2`), which is appropriate for a core framework dependency where compatibility is critical. The version ranges for `ujson` are more permissive (`>=4.0.1,<5.0.0`), allowing minor updates within the 4.x series. This is typical for optional, less critical dependencies. The addition of `ujson` to the `test` dependencies ensures that the new `UJSONResponse` tests can run in the CI environment.

## Test Coverage Assessment

The new test file `tests/test_tutorial/test_custom_response/test_tutorial001.py` contains a test that verifies the OpenAPI schema generation for a custom response tutorial. It defines an expected `openapi_schema` dictionary and uses a `TestClient` to fetch `/openapi.json`, asserting the response status code and JSON content match the expected schema. This test ensures that the tutorial example, which likely uses `UJSONResponse`, does not break the OpenAPI endpoint.

However, there are no direct unit tests for the `UJSONResponse` class itself. The existing test does not validate the behavior of the `render` method, the encoding, or the error handling when `ujson` is missing. This is a gap in test coverage for a newly implemented response class.

## Action Items and Recommendations

1. **Add Dedicated Unit Tests for `UJSONResponse`**: Create a test file (e.g., `tests/test_ujson_response.py`) that verifies the `UJSONResponse` class functions correctly. This should include testing serialization with valid data, ensuring the `ujson` assert fails appropriately when the library is not installed, and confirming the `media_type` is inherited correctly from `JSONResponse`.

2. **Update Documentation**: The FastAPI documentation should be updated to reflect that `UJSONResponse` is now a built-in FastAPI class, not a Starlette export. The migration path for users who were directly importing from `starlette.responses` should be documented.

3. **Monitor for Starlette Upgrade Issues**: The team should monitor the issue tracker for any regressions or compatibility issues introduced by the upgrade to Starlette 0.14.2, particularly related to the `@requires` decorator fix mentioned in the PR description.

4. **Review Import Patterns**: Consider standardizing the optional import pattern across all custom response classes (`UJSONResponse`, `ORJSONResponse`) for consistency and clarity.
