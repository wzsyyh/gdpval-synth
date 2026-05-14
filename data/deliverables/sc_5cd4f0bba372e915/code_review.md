# Code Review - PR #15280 @app.vibe()

## Summary

This review covers PR #15280, titled '✨ Add support for @app.vibe()'. The PR introduces documentation and a code example for a new `@app.vibe()` decorator in FastAPI. The changes consist of three files: a new Markdown documentation page (`docs/en/docs/advanced/vibe.md`), a new Python example file (`docs_src/vibe/tutorial001_py310.py`), and a one-line addition to the site navigation configuration (`docs/en/mkdocs.yml`). The PR's scope is limited to adding documentation and an example for the proposed feature.

## Technical Assessment

The code example is located in `docs_src/vibe/tutorial001_py310.py`. It imports `Any` from `typing` and `FastAPI` from `fastapi`. It creates an app instance with `app = FastAPI()` and uses the `@app.vibe('/vibe/')` decorator on a function. The function itself appears to have no body in the provided diff snippet, as the diff cuts off after showing the decorator line. The documentation claims the decorator handles any HTTP method and any payload, and that the body should be annotated with `Any`. The example aligns with this description but is minimal. A complete example would typically show a function body or at least a `pass` statement. The line reference `hl[8:12]` in the documentation suggests the example is meant to be highlighted, but the diff does not show the full file content.

## Documentation Quality

The new documentation page `docs/en/docs/advanced/vibe.md` uses a playful, informal tone with emojis (🤖, 🤷, ✨, 🧘, 😎) and phrases like 'Are you tired of all that data validation...' and 'just vibe'. This is a significant departure from FastAPI's usual professional, instructive tone. The page uses standard FastAPI documentation conventions like section anchors (`{ #how-it-works }`, `{ #vibe-coding }`) and a `/// tip` block. However, the content makes several exaggerated claims for comedic effect, such as listing 'No documentation', 'No serialization', and 'No code reviews' as benefits. While clearly satirical, this could be confusing for new users or those unfamiliar with the context. The page references the code example via include directives.

## Integration & Build

The change to `docs/en/mkdocs.yml` adds a single line: `- advanced/vibe.md`. This line is inserted after `advanced/strict-content-type.md` in the 'Advanced' section of the navigation. The indentation is consistent with the surrounding lines, and the path correctly corresponds to the location of the new documentation file. This ensures the new page will appear in the correct location in the built documentation site.

## Potential Issues & Recommendations

Several issues arise from this PR. First, the code example file `docs_src/vibe/tutorial001_py310.py` appears to be truncated in the diff; the function definition is incomplete. Second, the documentation's tone is highly informal and satirical, which contrasts sharply with FastAPI's established documentation style. While humorous, it could be misleading if interpreted as a serious feature recommendation. There is no disclaimer clarifying that this is a joke or April Fools' content (the merge date is 2026-04-01). Third, the PR contains only documentation and an example stub; it does not include the actual implementation of the `@app.vibe()` decorator in the FastAPI codebase. If this is intended as a real feature, it would require corresponding code changes, tests, and type stubs. If it's a joke, it should be clearly marked as such to avoid confusion.

## Overall Verdict

**Request Changes**. The PR in its current form raises several concerns that prevent approval. The code example is incomplete, the documentation tone is inconsistent with the rest of the FastAPI project and could be confusing, and most critically, the PR lacks any actual implementation of the advertised `@app.vibe()` decorator. For a project like FastAPI that prides itself on explicit, well-typed, and validated APIs, merging documentation for a feature that contradicts these core principles without clear contextual framing is problematic. The changes should not be merged until these issues are addressed: the example must be complete, the tone must be reconciled with project standards or clearly marked as satirical, and if it's a real feature, the implementation must be included with tests.
