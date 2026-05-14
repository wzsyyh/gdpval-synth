# Code Review: psf/requests#5797 – Switch to charset_normalizer

## PR Overview

PR #5797 in the `psf/requests` repository switches the default character encoding detection dependency for Python 3 from `chardet` to the MIT-licensed `charset_normalizer`. The primary motivation, as outlined in the PR description, is to resolve license ambiguity for downstream projects. While `requests` itself is Apache-licensed, its dependency on the LGPL-licensed `chardet` creates uncertainty for projects that bundle `requests` into a single binary, such as the example given of `docker-compose`'s approach. An LGPL dependency can force the entire bundle to be LGPL, which is prohibitive for many proprietary or differently-licensed projects. By changing to an MIT-licensed dependency, `requests` removes this ambiguity for its Python 3 users. For Python 2, `chardet` remains a mandatory dependency.

The PR also introduces an "escape hatch" mechanism to minimize disruption. If `chardet` is already installed in a user's environment, `requests` will continue to use it, preserving existing behavior. This backward compatibility is crucial for adoption. The PR author also added an optional extra, `[use_chardet_on_py3]`, allowing users to explicitly install `chardet` alongside `requests` if they prefer its behavior or encounter issues with `charset_normalizer`.

## Change Analysis

The diff modifies 10 files. The changes span documentation, dependency configuration, and core runtime logic. Below is a file-by-file analysis of the key changes:

- **`.gitignore`**: Adds common IDE files (`.idea`, `*.iml`) and a Python version file (`.python-version`) to the ignore list. This is a minor cleanup unrelated to the core change.
- **`HISTORY.md`**: Under a new `dev` section, a `Dependencies` subsection is added. It explicitly documents the change from `chardet` to `charset_normalizer` for Python 3, the backward-compatible behavior if `chardet` is installed, the new `[use_chardet_on_py3]` extra, and the continued use of `chardet` for Python 2. This provides clear user-facing release notes.
- **`docs/user/advanced.rst`**: The `Encodings` section is updated to explain the new dual-library support. It clarifies that `chardet` is used if installed, but is no longer mandatory for Python 3 due to its LGPL license. It also mentions `charset-normalizer` (MIT-licensed) as the new default and notes the `[use_chardet_on_py3]` extra. The documentation is now more detailed and accurate.

- **`requests/compat.py`**: This file contains the core fallback logic. A new function `get_encodings_from_content_type` is defined. Inside this function, the code first attempts to import `charset_normalizer`. If that import fails (i.e., the library is not installed), it falls back to importing `chardet`. The imported module is then assigned to a variable `chardet` for use downstream, regardless of which library was actually imported. This allows the rest of the codebase to reference `chardet` as a unified interface, abstracting away which library is actually performing the detection.
- **`setup.py`**: The `install_requires` list is changed to replace `chardet` with `charset_normalizer` for Python 3. A new `extras_require` entry is added: `use_chardet_on_py3: ['chardet>=3.0.2,<5']`. This extra allows users to explicitly add the old dependency. The `chardet` dependency for Python 2 is left in place.
- **`requests/__init__.py`**: The direct `import chardet` at the top of the module is removed. Instead, the import is now conditional and happens within the `requests/compat.py` logic. This ensures that the correct library is loaded based on availability.

## Backward Compatibility & Migration

The PR is designed as a soft migration with strong backward compatibility. The primary strategy is to check for the presence of `chardet` first. As stated in the PR description and implemented in `requests/compat.py`, the code "will use chardet first if it is installed." This means existing environments where `chardet` is already a transitive dependency (from an older version of `requests` or another package) will see no behavioral change. Only new installations of `requests` in clean environments (where `charset_normalizer` is the new default) will experience the switch.

For users who want to explicitly retain `chardet` on Python 3, the PR introduces the `[use_chardet_on_py3]` extra. The PR description references an extra named `[lgpl]`, but the actual diff in `HISTORY.md` and `setup.py` uses the name `[use_chardet_on_py3]`. This is a minor discrepancy between the description and the implementation; the code uses `[use_chardet_on_py3]`.

The change does not affect Python 2 at all. The `HISTORY.md` entry and the `setup.py` changes confirm that Python 2 continues to depend on `chardet` as a mandatory dependency, as `charset_normalizer` does not support Python 2.

Overall, this is a careful migration path. Most users will not need to take any action. Users with strict dependency pinning will continue to use their pinned version of `requests`, which would still use `chardet`. The change only affects users who upgrade to the new version of `requests` and either don't have `chardet` installed or choose to remove it.

## Impact on Internal Services

For our internal services, the impact depends on their current dependency management. Services using a `requirements.txt` file with a pinned version of `requests` (e.g., `requests==2.25.1`) will be unaffected until they explicitly upgrade. Services using looser version specifiers (e.g., `requests>=2.25`) will pick up this change upon their next dependency resolution.

The main risk is subtle differences in encoding detection behavior between `chardet` and `charset_normalizer`. While the PR author states their non-exhaustive tests showed identical results, there is no guarantee of 100% parity. Services that handle non-standard or tricky encodings could potentially see different text decoding, leading to data processing errors or garbled text in logs or user interfaces.

**Recommended Actions:**
1.  **Inventory:** Identify which services are on a version of `requests` >=2.26.0 (when this change was merged) or use loose version specifiers.
2.  **Test:** For high-risk services (those processing user-uploaded content, legacy APIs with specific charsets), run a test suite with the new `charset_normalizer` default and verify the decoded output matches expectations.
3.  **Control:** If a service is found to behave incorrectly with `charset_normalizer`, use the `[use_chardet_on_py3]` extra in its dependency file (e.g., `pip install requests[use_chardet_on_py3]`) to force the use of `chardet`.
4.  **Pin:** For stability, consider pinning `requests` to a specific version in production `requirements.txt` files and manage upgrades deliberately.

## Quality & Risks

The implementation quality is high. The fallback logic in `requests/compat.py` is clean and abstracts the choice of library effectively, allowing the rest of the codebase to use a single interface (`chardet`). The documentation updates in `HISTORY.md` and `docs/user/advanced.rst` are thorough and clear, explaining the change, the rationale, and the migration path for users. This transparency is excellent for an open-source project.

One minor risk is the discrepancy in extra naming between the PR description and the actual code. The description mentions a `[lgpl]` extra, but the code implements `[use_chardet_on_py3]`. This could cause confusion if a user reads the PR description and tries to install `requests[lgpl]`, which would fail. The code, however, is the source of truth.

The primary technical risk, as mentioned, is the potential for `charset_normalizer` to detect encodings differently than `chardet` for a subset of inputs. The PR author's testing was non-exhaustive. For most common encodings (UTF-8, ISO-8859-1, ASCII), both libraries will perform identically. The risk is higher for less common encodings or malformed content.

The change correctly isolates the risk to Python 3 only, leaving the well-tested Python 2 path untouched. This is a sensible and conservative approach.

## Conclusion & Recommendation

In conclusion, PR #5797 is a well-executed, backward-compatible change that solves a legitimate licensing concern for a wide class of downstream projects. The implementation prioritizes stability through its fallback mechanism and provides clear escape hatches for users.

For our internal services, the risk is low but not zero. I recommend the following plan:
1.  **Communication:** Notify the team about this change and its implications.
2.  **Dependency Review:** Audit our service `requirements.txt` files to understand which will be affected.
3.  **Staged Rollout:** For services using loose version specifiers, upgrade `requests` in staging environments first and run integration tests, paying close attention to any text-heavy or encoding-sensitive operations.
4.  **Mitigation:** For any service that exhibits issues, apply the `[use_chardet_on_py3]` extra as a quick fix.

The change itself is safe to adopt. The licensing benefit is significant, and the backward compatibility measures are sound. A proactive but measured approach to upgrading our services will ensure a smooth transition.
