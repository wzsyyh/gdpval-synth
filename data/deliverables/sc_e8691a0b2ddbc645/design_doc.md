# Flask Async Support Design Document

# Flask Async Support Design Document

This document outlines the design and trade-offs of the async support feature added to Flask in PR #3412. It is intended for Flask maintainers and contributors to understand the implementation, its limitations, and recommended usage patterns.

## Overview

The async support feature was introduced in pull request #3412, titled "Add `async` support", and was merged on April 7, 2021. This change allows developers to write Flask views, error handlers, before request, after request, and teardown functions as asynchronous coroutine functions using `async def` and `await`.

A key aspect of this change is that it adds async support without supporting ASGI. As a result, Flask remains a WSGI application, and when using async, it is constrained to have worse performance than ASGI equivalents. This trade-off is necessary to maintain backward compatibility; Flask cannot be async throughout or support ASGI while being backward compatible. The feature enables users to add some async usage to existing codebases, with the option to switch to Quart if their usage becomes mostly async.

## Technical Design

Flask, as a WSGI application, uses one worker to handle one request/response cycle. When a request arrives for an async view, Flask starts an event loop in a thread, runs the view function there, then returns the result. This implementation means each request still ties up one worker, even for async views.

The async support extends to multiple components: routes (views), error handlers, before request functions, after request functions, and teardown functions can all be coroutine functions. This allows for async operations within these components, such as making concurrent database queries or HTTP requests to external APIs.

The feature requires Python 2 support to be dropped, as noted in the PR description. This dependency on modern Python enables the use of standard `async`/`await` syntax without additional patching libraries.

## Performance Characteristics

The documentation explicitly warns: "Async is not inherently faster than sync code." Async is beneficial when performing concurrent IO-bound tasks, such as multiple database queries or HTTP requests, but will probably not improve CPU-bound tasks. Traditional Flask views remain appropriate for most use cases.

Flask's async support is less performant than async-first frameworks due to its implementation. Because Flask is a WSGI application, the number of requests the application can handle at one time remains the same as with synchronous views. Each async request still occupies a worker, unlike ASGI frameworks that can handle many concurrent requests without individual worker processes or threads.

For comparison, Quart is a reimplementation of Flask based on the ASGI standard. It can handle many concurrent requests, long running requests, and websockets without requiring individual worker processes or threads. Flask's async support is a stepping stone for codebases that are transitioning or have mixed sync/async requirements.

## Migration & Usage Guidance

To enable async support, Flask must be installed with the `async` extra: `pip install flask[async]`. This is a one-time setup step that enables the async functionality.

Once installed, developers can define async view functions using the standard Flask route decorator. For example:

```python
@app.route("/get-data")
async def get_data():
    data = await async_db_query(...)
    return jsonify(data)
```

This allows views to use `await` for asynchronous operations within the request handling cycle.

Users with mainly async codebases are advised to consider Quart. Quart is a reimplementation of Flask based on the ASGI standard, which allows it to handle many concurrent requests, long running requests, and websockets more efficiently. The decision to use Flask, Quart, or another solution depends on the specific needs of the project.

It has also been possible to run Flask with Gevent or Eventlet to get async-like behavior. These libraries patch low-level Python functions, whereas `async`/`await` and ASGI use standard, modern Python capabilities.

## Future Considerations

The async support feature required dropping Python 2 support, as noted in the PR description. This aligns with the broader Python ecosystem's move toward Python 3 and enables the use of modern async syntax.

Looking forward, Flask cannot support ASGI while maintaining backward compatibility. This limitation is inherent to Flask's design as a WSGI framework. As noted in the PR description, users whose usage becomes mostly async should consider switching to Quart. The Flask team's focus remains on providing a stable, backward-compatible framework, with async support as an optional enhancement for specific use cases.

This design document captures the current state of async support in Flask. It will be updated as the feature evolves or if future changes alter the trade-offs described herein.
