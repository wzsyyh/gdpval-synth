# PR #464 diff and description from the encode/httpx repository, titled 'First pass at autodoc support'


# Seed Material: encode/httpx#464: First pass at autodoc support
Source: github_issue_pr
Identifier: pr:encode/httpx#464

Repository: encode/httpx
PR Number: #464
PR Title: First pass at autodoc support
Merged At: 2019-10-30T15:21:40Z
Changed Files: 6
Additions: +290, Deletions: -33

## PR Description
I've started working on [an autodoc extension](https://github.com/tomchristie/mkautodoc) for use with mkdocs.

This pull request demonstrates using it with the `httpx.request` function, just for visibility of where I think we need to go here.

Bits to do:

- ~~Nested code blocks in the docstring are not rendering. (I tried installing the `pymdownx.superfences` extension, which didn't appear to resolve the issue, either. *Any help with resolving this would be much appreciated.**)~~ - *Resolved*
- ~~Need to look at rendering classes, not just functions. More complicated. There's some limited support for this, but will need work.~~ - *Resolved*
- Rendering docs for instance attributes on classes. This is more awkward to do than methods & properties, since we can only figure out instance attributes by grepping the code in the `__init__`.
- Ensure async methods get an "async" marker. We're not rendering any of these yet in this PR, so not currently an issue.
- ~~I'm using a `dd` element as a bit of a styling hack, as it gives me a nicely indented block for the docstring. Probably ought to be a div with an appropriate class, or some other appropriate block element, with styling applied ideally by mkdocs-material, rather than having to add custom styling for it.~~ - *Resolved*
- It'd be really nice to keep the typing information out of the main display, but have contextual information pop up against parameters. We can treat this as a nice-to-have-later.

![Screen Shot 2019-10-09 at 11 45 39](https://user-images.githubusercontent.com/647359/66475022-67d66100-ea8a-11e9-8402-ca9b9ee91685.png)




## Diff (first 3000 chars)
diff --git a/docs/api.md b/docs/api.md
index 6d2897c5fa..12b790af96 100644
--- a/docs/api.md
+++ b/docs/api.md
@@ -8,40 +8,35 @@
     enable HTTP/2 and connection pooling for more efficient and
     long-lived connections.
 
-* `get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `options(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `head(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `post(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `put(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `patch(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `delete(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `request(method, url, [data], [files], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `build_request(method, url, [data], [files], [json], [params], [headers], [cookies])`
+::: httpx.request
+    :docstring:
 
-## `Client`
+::: httpx.get
+    :docstring:
 
-*An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc.*
+::: httpx.options
+    :docstring:
 
-```python
->>> with httpx.Client() as client:
-...   response = client.get('https://example.org')
-```
+::: httpx.head
+    :docstring:
 
-* `def __init__([auth], [params], [headers], [cookies], [verify], [cert], [timeout], [pool_limits], [max_redirects], [app], [dispatch])`
-* `.params` - **QueryParams**
-* `.headers` - **Headers**
-* `.cookies` - **Cookies**
-* `def .get(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .options(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .head(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .post(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .put(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .patch(url, [data], [files], [json], [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .delete(url, [params], [headers], [cookies], [auth], [stream], [allow_redirects], [verify], [cert], [timeout], [proxies])`
-* `def .request(method, url, 