# Design Doc - Flask Nested Blueprints (PR #3923)

## Overview

This design document describes the implementation of nested blueprint support in Flask, merged as PR #3923. This feature addresses two long-standing community requests: issue #593, which proposed a `Blueprint.register_blueprint` method for nesting blueprints, and issue #1548. The solution allows a blueprint to be registered within another blueprint, with the parent blueprint's configuration cascading to the child. When the parent blueprint is subsequently registered with the Flask application, all child blueprints are automatically registered as well, preserving their relative URL prefixes and endpoint hierarchies.

## Implementation Details

The core implementation constructs endpoint names by joining the full chain of blueprint names from parent to child with a dot delimiter. For a child blueprint nested two levels deep, the endpoint would be formatted as `parent.child.endpoint`.

The application iterates over blueprint names in reverse order, from the most specific (deepest child) to the most general (the application itself). This ensures that template context processors and other blueprint-specific behaviors are correctly resolved in the proper hierarchy.

In `src/flask/app.py`, the `update_template_context` method was modified to iterate over all blueprints in the request chain rather than just the direct blueprint. The previous implementation checked if the request's blueprint was in `self.template_context_processors` and used its context processors. The new implementation iterates over all blueprints in the request chain using `self._request_blueprints()`, chaining context processors from each blueprint that has them registered.

The `register_blueprint` method was also simplified by removing the previous blueprint name collision assertion and replacing it with a more robust registration mechanism that supports nested registration. The key change is the removal of the strict name collision check and the addition of logic to handle the parent-child blueprint relationship.

## Usage Example

The following example from the documentation shows how to create and register nested blueprints:

```python
parent = Blueprint("parent", __name__, url_prefix="/parent")
child = Blueprint("child", __name__, url_prefix="/child")
parent.register_blueprint(child)
app.register_blueprint(parent)
```

After this registration, the child blueprint's endpoints are accessible with the parent's URL prefix. For example, using `url_for('parent.child.create')` would generate the URL `/parent/child/create`.

## Behavioral Guarantees

The implementation ensures two important inheritance behaviors. First, blueprint-specific before_request functions registered with the parent blueprint will trigger for requests routed to child blueprints. This allows shared authentication, logging, or other middleware to be defined once at the parent level and automatically applied to all nested routes.

Second, if a child blueprint does not have an error handler that can handle a given exception, the application will attempt to use the parent blueprint's error handler. This provides a natural fallback mechanism for error handling across a blueprint hierarchy.

## Changelog Entry

The following entry was added to `CHANGES.rst` under the Unreleased section:

```
-   Support nesting blueprints. :issue:`593, 1548`, :pr:`3923`
```

## Constraints and Considerations

The implementation maintains backward compatibility; existing code that registers blueprints directly with the application will continue to work without modification. However, when using nested blueprints, developers must ensure that blueprint names are unique across all registrations to avoid conflicts. The PR included a comprehensive test suite to demonstrate correct behavior, updates to documentation in the `docs` folder and in code, and passes all pre-commit hooks, pytest, and tox test suites as verified by the contributor.
