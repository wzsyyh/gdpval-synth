# Design Doc - psf/requests#5797 Dependency Change

## Overview: Motivation for Dependency Change

The primary motivation for switching the default character encoding detection library in the requests package is to resolve license ambiguity for downstream projects. The previous dependency, `chardet`, is licensed under the GNU Lesser General Public License (LGPL). While this license is compatible with requests' own Apache 2.0 license for direct use, it creates significant uncertainty for projects that bundle requests—and by extension, its dependencies—into a single binary or distribution artifact.

A key example highlighted is the case of projects similar to docker-compose, which bundle their dependencies. Including an LGPL-licensed module like `chardet` makes it unclear whether the resulting artifact must also be released under the LGPL, potentially imposing copyleft obligations that conflict with the project's licensing strategy. This ambiguity is not merely theoretical; the PR description notes that the Apache Software Foundation (ASF) currently does not allow its projects to depend on LGPL-licensed code, a policy that directly impacts any ASF project using requests as a dependency.

To eliminate this license ambiguity, this change replaces `chardet` with `charset_normalizer` as the default encoding detection library for Python 3. `charset_normalizer` is released under the permissive MIT license, which imposes no such copyleft requirements. This switch ensures that projects bundling requests can do so with complete clarity regarding their licensing obligations, removing a significant barrier to adoption in corporate and foundation environments with strict licensing policies.

## Implementation Details

The implementation maintains backward compatibility while shifting the default dependency for Python 3 users. The core change is in the dependency resolution logic within `requests/__init__.py`. For Python 3, `charset_normalizer` becomes the mandatory dependency, replacing `chardet`. However, `chardet` is not removed as an option; the code retains an 'escape hatch' where if `chardet` is already installed in the user's environment, it will be used instead of `charset_normalizer`.

For Python 2, which `charset_normalizer` does not support, `chardet` remains the sole and mandatory dependency. This ensures no disruption for users still on the legacy Python version. The logic can be summarized as: for Python 3, prefer `charset_normalizer` but use `chardet` if it is present; for Python 2, require `chardet`.

To provide users with a straightforward way to explicitly choose the LGPL-licensed library, a new pip install extra has been added: `[use_chardet_on_py3]`. Installing requests with `pip install "requests[use_chardet_on_py3]"` will install `chardet` as a dependency, overriding the default behavior for Python 3. This extra is documented in the updated HISTORY.md file.

## User Impact and Migration Path

For most users, this change will be transparent. New Python 3 installations of requests will automatically receive `charset_normalizer` as the encoding detection backend, requiring no action. Existing Python 3 environments where `chardet` is already installed will continue to use `chardet`, as the implementation checks for its presence first. This 'escape hatch' ensures zero disruption for users who have a working setup or who rely on specific `chardet` behaviors.

Users who explicitly want to use `chardet` on Python 3, for example to resolve a hypothetical compatibility issue with `charset_normalizer`, can do so by installing the `[use_chardet_on_py3]` extra. This is a supported migration path and provides a clear, documented alternative to the default behavior.

The user-facing documentation for encoding detection has been significantly updated in `docs/user/advanced.rst` to reflect this change. The new text explains the dual-library support, the fallback logic, the licensing distinction, and the use of the optional extra. This ensures that the change in underlying dependency is clearly communicated to advanced users who consult the documentation.

## Documentation and Configuration Updates

The pull request includes updates to several project files to support, document, and facilitate the dependency switch. These changes are part of the complete deliverable for this feature.

First, the `.gitignore` file was expanded to include common IDE and environment file patterns, specifically adding entries for IntelliJ/PyCharm (`.idea`, `*.iml`) and `.python-version`. This is a housekeeping improvement to keep repository noise low for developers using those tools.

Second, the `HISTORY.md` changelog file received a new entry under the 'dev' section. It documents the dependency switch, explains the rationale (license ambiguity), describes the fallback behavior for existing `chardet` installations, and specifies the name of the new pip extra: `[use_chardet_on_py3]`. This entry serves as the formal record for the release notes.

Third, the core documentation in `docs/user/advanced.rst` under the 'Encodings' section was revised. The previous text only mentioned `chardet`. The new text explains that `charset_normalizer` (MIT-licensed) or `chardet` (LGPL-licensed) will be used, details the default preference for `charset_normalizer` on Python 3, notes that `chardet` is still mandatory for Python 2, and describes the `[use_chardet_on_py3]` extra for explicit control.

## Testing and Compatibility

The change was designed with test coverage and compatibility in mind. According to the PR description, the existing code path for environments where `chardet` is installed—the "have chardet" path—is still exercised in the test suite. This is crucial for ensuring that the fallback mechanism on Python 3 and the mandatory path on Python 2 continue to function correctly after the dependency change.

The author of the PR conducted non-exhaustive tests comparing the output of `charset_normalizer` and `chardet`. In every case tested, `charset_normalizer` detected the same encoding as `chardet`. While not a formal guarantee of 100% behavioral parity, this testing provides confidence that for the vast majority of real-world use cases, the switch should be seamless and not introduce regressions in response encoding detection.

The compatibility strategy is therefore multi-layered: it defaults to the new, license-clean library for new setups, gracefully falls back to the old library for existing setups to avoid breaking changes, and provides an explicit opt-in mechanism for users who need it. This approach minimizes risk while achieving the primary licensing objective.
