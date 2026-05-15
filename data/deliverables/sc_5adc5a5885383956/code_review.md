# Code Review: PR #5797 - Switch LGPL'd chardet for MIT licensed charset_normalizer

## Overview

This review covers PR #5797, titled "Switch LGPL'd chardet for MIT licensed charset_normalizer." The PR proposes to replace the mandatory `chardet` dependency for Python 3 with `charset_normalizer`, an MIT-licensed library, to resolve license ambiguity for downstream projects that bundle `requests` into a single binary. The change maintains backward compatibility by using `chardet` if it is already installed and introducing a new extra `[use_chardet_on_py3]` to explicitly install `chardet` on Python 3.

The PR affects 10 files, including core dependency checks (`requests/__init__.py`), compatibility modules (`requests/compat.py` and `requests/packages.py`), help/info functions (`requests/help.py`), documentation (`docs/user/advanced.rst` and `HISTORY.md`), and build/test configuration (`setup.py` and `tox.ini`). The overall approach is pragmatic, but several details require careful scrutiny.

## Architectural Impact

The PR introduces a dual-path dependency strategy: on Python 3, `charset_normalizer` is preferred, but `chardet` is used if installed. This is implemented via try/except import blocks in `requests/compat.py` and `requests/__init__.py`. The architecture remains largely unchanged, but the new conditional logic adds complexity to the initialization flow.

The most significant architectural change is in `requests/packages.py`. Previously, it iterated over `('urllib3', 'idna', 'chardet')` to re-export modules under the `requests.packages` namespace. Now, it only iterates over `('urllib3', 'idna')`, and then manually re-exports the chosen character detection library as `requests.packages.chardet`. This preserves backward compatibility for code that imports `requests.packages.chardet`, regardless of whether the underlying library is `charset_normalizer` or `chardet`.

The `requests.help.info()` function now includes two new keys: `'charset_normalizer'` and `'using_charset_normalizer'`. This expands the public API and is a welcome addition for debugging, but downstream tools parsing this output must be aware of the new fields.

## Backward Compatibility Analysis

The backward compatibility strategy is implemented in `requests/compat.py` with a simple try/except block: `try: import chardet; except ImportError: import charset_normalizer as chardet`. This ensures that any code importing from `requests.compat.chardet` will continue to work, as the alias is set regardless of which library is present. However, this approach silently masks the switch, which could lead to subtle differences in encoding detection behavior if the libraries' heuristics differ.

In `setup.py`, the dependency list is updated to `charset_normalizer~=2.0.0` for Python 3 and `chardet>=3.0.2,<5` for Python 2. The new extra `[use_chardet_on_py3]` allows users to explicitly install `chardet` on Python 3. This is a good escape hatch, but it requires users to be aware of the change and modify their installation commands. The PR description notes that Python 2 still depends on `chardet` directly, which is consistent with the library's support policy.

The version compatibility checks in `requests/__init__.py` have been expanded to handle both libraries. The function `check_compatibility` now accepts three arguments: `urllib3_version`, `chardet_version`, and `charset_normalizer_version`. It checks the version ranges `(3,0,2) <= (major, minor, patch) < (5,0,0)` for `chardet` and `(2,0,0) <= (major, minor, patch) < (3,0,0)` for `charset_normalizer`. If neither is installed, it raises an exception. This logic is correct but adds complexity to the initialization code. The warning message now includes both library versions, which is helpful for debugging.

The tox.ini configuration is updated to test both the default path (charset_normalizer) and the `use_chardet_on_py3` extra. This ensures that both dependency paths are tested in CI, which is critical for maintaining backward compatibility.

## Code Quality Issues

Several code quality issues were identified during the review:

1. **In `requests/__init__.py`**: The `check_compatibility` function now has three parameters, but the call site passes `chardet_version` and `charset_normalizer_version` which may be `None`. The function handles this correctly by checking for `None` before splitting the version string. However, if both are `None`, it raises a generic `Exception` with the message "You need either charset_normalizer or chardet installed." This is acceptable but could be replaced with a more specific exception type (e.g., `ImportError`).

2. **In `requests/packages.py`**: The code uses a list comprehension to iterate over `sys.modules` and re-export the chosen library as `chardet`. The variable `target` is set to `chardet.__name__`, which is `'chardet'` if `chardet` is imported, or `'charset_normalizer'` if `charset_normalizer` is imported (since it's aliased as `chardet` in the except block). The line `sys.modules['requests.packages.' + target.replace(target, 'chardet')]` is redundant because `target.replace(target, 'chardet')` always evaluates to `'chardet'`. This should be simplified to `sys.modules['requests.packages.chardet']`.

3. **In `docs/user/advanced.rst`**: There is a typo: `When you install ``request`` without specifying ``[use_chardet_on_py3]]`` extra` has an extra closing bracket. It should be `` `[use_chardet_on_py3]` ``.

4. **In `HISTORY.md`**: The documentation for the extra is shown with a shell code block, but it uses double quotes which may not be portable on all shells. It could be improved with a note about quoting differences.

5. **In `requests/help.py`**: The key `'using_charset_normalizer'` is set to `chardet is None`. This is a boolean that indicates whether `charset_normalizer` is in use, but the logic is inverted: if `chardet` is `None`, then `charset_normalizer` must be in use. This is correct but could be confusing; a more explicit name like `'uses_charset_normalizer'` might be clearer.

## Testing Implications

The `tox.ini` changes introduce two test environments: `default` and `use_chardet_on_py3`. The `default` environment will use `charset_normalizer` on Python 3, while `use_chardet_on_py3` will explicitly install `chardet`. This ensures that both dependency paths are tested. However, there is no explicit test environment that verifies the behavior when neither library is installed (the `else` branch in `requests/__init__.py` that raises an exception). This edge case should be tested to ensure the error message is clear and helpful.

Additionally, there are no tests that verify the encoding detection behavior of `charset_normalizer` versus `chardet` on a representative set of test cases. The PR description mentions that the author's non-exhaustive tests showed no differences, but for a library as widely used as `requests`, a more comprehensive regression test suite would be beneficial. At a minimum, the existing test suite should be run with both libraries to ensure no regressions.

The changes to `requests/packages.py` affect the `requests.packages` namespace. Existing tests that import `requests.packages.chardet` should continue to pass, but there should be explicit tests that verify the module is correctly re-exported when using `charset_normalizer` as the backend.

## Documentation Accuracy

The documentation updates in `docs/user/advanced.rst` are generally accurate. The text correctly explains that `charset_normalizer` is used by default on Python 3, but `chardet` is used if installed. It also notes that Python 2 still depends on `chardet`. However, there is a minor error: the section says "When you install ``request`` without specifying ``[use_chardet_on_py3]]`` extra" – note the double closing bracket. This should be corrected to `` `[use_chardet_on_py3]` ``.

The `HISTORY.md` changes are clear and concise. They explain the dependency change, the backward compatibility strategy, and the new extra. The inclusion of a shell command example is helpful. However, the documentation could be improved by noting that the `[use_chardet_on_py3]` extra is only relevant for Python 3, as the dependency is already mandatory on Python 2.

Overall, the documentation accurately reflects the code changes, but the typo in `docs/user/advanced.rst` should be fixed before merging.

## Recommendation

**Recommendation: Request Changes**

While the PR achieves its goal of switching from an LGPL to an MIT dependency for Python 3 and maintains backward compatibility, there are several issues that should be addressed before merging:

1. **Fix the typo** in `docs/user/advanced.rst` (extra closing bracket).
2. **Simplify the redundant code** in `requests/packages.py` (the `target.replace(target, 'chardet')` line).
3. **Add a test** for the case when neither `charset_normalizer` nor `chardet` is installed.
4. **Consider adding a note** in `HISTORY.md` that the `[use_chardet_on_py3]` extra is in `docs/user/advanced.rst`.

These are all minor issues, but they should be corrected to ensure code quality and clarity. The overall approach is sound, and the backward compatibility strategy is well-designed. The PR also includes good updates to the help/info output and tox.ini testing configuration.

After these changes are made, the PR can be approved.
