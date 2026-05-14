# Design Document: Review of PR #34263 - Add --chown flag to ADD/COPY commands

## Overview

This design document reviews PR #34263 from the moby/moby repository, titled "Add --chown flag to ADD/COPY commands." The PR carries work from earlier efforts, specifically #28499 and #27303, to implement a long-requested feature for Dockerfile syntax.

The core purpose of this change is to add a `--chown` flag to the `ADD` and `COPY` instructions in Dockerfiles. This allows users to specify the ownership (user and group) of files and directories as they are copied into the container filesystem. Previously, users had to follow a `COPY` instruction with a separate `RUN chown` command, which created an extra layer in the image and increased complexity. The `--chown` flag streamlines this process, enabling more efficient and secure image building.

## Proposed Design

The implementation introduces a `--chown` flag that accepts a colon-separated string defining the target user and group. The supported formats include combinations of names and numeric IDs, such as `--chown=someuser:555`, `--chown=anyuser:anygroup`, `--chown=1001:1002`, and `--chown=333:agroupname`. This flexibility allows users to specify ownership by name, ID, or a mix.

In the code, the `copyInstruction` struct gains a new field `chownStr` to hold the raw flag value. The `copyFileOptions` struct adds a `chownPair` field of type `idtools.IDPair`, which represents the resolved numeric user and group IDs. The core copy functions, `copyDirectory` and `copyFile`, are modified to accept this `chownPair` as a parameter, replacing the previous use of `archiver.IDMappings.RootPair()` for setting directory and file ownership.

The `fixPermissions` function is also updated. Its call signature now includes the `chownPair` and an additional boolean parameter. In `copyDirectory`, this boolean is set to `!destExists`, indicating whether the destination directory was newly created. In `copyFile`, it is set to `false`. This change suggests that permission fixing logic may differ based on whether the destination already existed.

## Technical Analysis

The PR description states that name-to-ID lookups will use the `/etc/passwd` and `/etc/group` files found in the container's filesystem. This is a critical detail: it means the resolution happens at build time using the filesystem context of the image being built, not the host system. If only numeric IDs are provided, no lookups are performed, which simplifies the process and avoids potential failures.

User namespace support is explicitly mentioned. After names are translated to integer IDs, those IDs are shifted based on the user namespace mappings configured in the Docker daemon. This ensures that ownership is correctly set within namespaced containers, maintaining security and consistency.

The diff shows concrete changes. In `copy.go`, the `copyDirectory` function now first checks if the destination directory exists (`destExists, err := isExistingDirectory(dest)`). It then passes `options.chownPair` to `archiver.CopyWithTar` and `fixPermissions`. The `fixPermissions` call now includes a new boolean parameter, which in the directory case is `!destExists`. This indicates that the function's behavior may be conditional on whether the directory was newly created, though the exact logic is not fully visible in the provided diff snippet.

Similarly, `copyFile` replaces the previous `rootIDs` (obtained from `archiver.IDMappings.RootPair()`) with the provided `chownPair`. It uses this pair when creating the parent directory via `idtools.MkdirAllAndChownNew` and when calling `fixPermissions`. This ensures consistent ownership application across both files and directories.

## Issues and Risks

The PR description highlights a significant risk: Windows containers will not have the `/etc/passwd` and `/etc/group` files. Currently, the build will fail if these files are missing during a name lookup. The author suggests the need for a way to fail gracefully or ignore failures on Windows. This is a critical compatibility issue that must be addressed before merging.

Another risk is noted by the author: "a few more tests are necessary to fully test the behavior." This indicates that the current test suite is incomplete. Given the complexity of the feature—handling mixed name/ID formats, user namespaces, and different operating systems—comprehensive testing is essential to ensure reliability and prevent regressions.

Additional risks include potential gaps in error handling. For example, what happens if the `--chown` string is malformed? The diff does not show parsing logic, so we must assume it is handled elsewhere, but it should be verified. Backward compatibility is also a concern: existing Dockerfiles without the `--chown` flag must continue to work unchanged, and the default behavior (using root ownership) should be preserved when the flag is omitted.

## Recommendations

Based on this analysis, we recommend the following actions:
1. **Address Windows Compatibility**: Implement a graceful failure mechanism for Windows containers where `/etc/passwd` and `/etc/group` do not exist. This could involve skipping lookups when numeric IDs are used, or providing a clear error message for name-based lookups on unsupported platforms.
2. **Expand Test Coverage**: Add integration and unit tests to cover all supported `--chown` formats (`--chown=user:group`, `--chown=user:ID`, `--chown=ID:group`, `--chown=ID:ID`), user namespace scenarios, and error conditions (malformed strings, missing files). The author's note confirms this is needed.
3. **Approve with Conditions**: The core design is sound and addresses a long-standing need. We recommend approving the PR contingent on the resolution of the Windows compatibility issue and the addition of sufficient tests.
4. **Update Documentation**: Ensure that the official Docker documentation is updated to describe the new `--chown` flag, its supported formats, and its behavior with user namespaces.
