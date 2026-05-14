# Technical Summary & Review: PR #40007 - Support host.docker.internal in dockerd on Linux

# Technical Summary & Review: PR #40007 - Support host.docker.internal in dockerd on Linux

## Summary

PR #40007, titled "Support host.docker.internal in dockerd on Linux," was merged on 2020-01-27. It introduces the ability for containers running on Linux to resolve the `host.docker.internal` DNS name, connecting to the host machine's IP address. This brings Linux in line with the behavior already present in Docker for Mac and Docker for Windows.

The core mechanism is the new special string `"host-gateway"` used with the `--add-host` container run flag (e.g., `--add-host=host.docker.internal:host-gateway`). When used, the Docker daemon replaces this string with the IP address configured via the new `--host-gateway-ip` daemon flag. By default, this IP is the address of the default bridge network.

This change resolves a long-standing feature request from the Linux Docker community, making host access from containers more consistent and user-friendly across all platforms.

## Problem Statement

Prior to this PR, a significant inconsistency existed in the Docker ecosystem. The convenient DNS name `host.docker.internal` automatically resolved to the host's IP address within containers on Docker for Mac and Docker for Windows. However, on Linux, users had to manually determine and hardcode the host's IP, often the Docker bridge gateway IP (e.g., `172.17.0.1`), in their container configurations. This was a frequent source of confusion and friction.

This issue was explicitly tracked in the primary feature request `docker/for-linux#264`. The problem was compounded by users and tooling expecting cross-platform parity. For instance, users migrating from Mac or Windows to Linux found that setups relying on `host.docker.internal` for Xdebug remote debugging (as noted in issues like `jtreminio/dashtainer#2` and `drud/ddev#843`) or for services like nginx proxy manager (`jc21/nginx-proxy-manager#259`) would break without manual intervention.

The PR description links to numerous other duplicate or related issues (e.g., `docker/for-mac#2705`, `moby/moby#36625`, `cypress-io/cypress-docker-images#183`), all highlighting the desire for a unified, simple way to connect containers to the host across operating systems. This PR directly addresses that core pain point.

## Solution Design

The solution is elegantly split into two cooperating parts: a user-facing container flag and a daemon-level configuration. At the container level, users specify the new magic string `host-gateway` as the IP value in an `--add-host` entry (e.g., `--add-host=host.docker.internal:host-gateway`).

When the daemon processes a container's configuration, it checks if the IP part of an extra host entry matches the constant `network.HostGatewayName` (presumably `"host-gateway"`). If it does, the daemon replaces this string with the actual IP address stored in its configuration variable `daemon.configStore.HostGatewayIP`. This replacement happens in the `buildSandboxOptions` function within `daemon/container_operations.go`.

The second part is the new daemon flag `--host-gateway-ip`. This flag sets the `HostGatewayIP` field within the `CommonConfig.DNSConfig` struct, as seen in the `daemon/config/config.go` diff. The `HostGatewayIP` field is of type `net.IP`. The default value is an empty string, which instructs the daemon to derive the IP from the default bridge network. If the user sets the flag (e.g., `--host-gateway-ip=1.2.3.4`), that explicit IP is used.

## Implementation Details

The provided diff shows modifications across three critical files. In `cmd/dockerd/config.go`, a new command-line flag is registered using `flags.Var`. The flag is named `"host-gateway-ip"` and is bound to the `conf.HostGatewayIP` configuration field, which is of type `opts.NewIPOpt`. The help string explicitly states its default behavior.

In `daemon/config/config.go`, the `DNSConfig` struct is extended with a new field: `HostGatewayIP net.IP`. This struct is part of the daemon's `CommonConfig`, meaning the host gateway IP is a daemon-wide setting. The `"net"` package import is added to support the `net.IP` type.

The core logic resides in `daemon/container_operations.go` within the `buildSandboxOptions` function. After splitting an `extraHost` string into host and IP parts (`parts`), the code checks if `parts[1]` equals the constant `network.HostGatewayName`. If true, it retrieves the IP string from `daemon.configStore.HostGatewayIP.String()`. If this derived IP is empty, an error is returned. Otherwise, `parts[1]` is overwritten with the gateway IP before appending the option. This ensures the container's `/etc/hosts` file gets the correct, resolved IP address.

## Verification & Impact

The PR description provides clear verification steps. After starting `dockerd`, running a container with `--add-host=host.docker.internal:host-gateway` and inspecting its `/etc/hosts` file should show `host.docker.internal` mapped to the host's gateway IP (e.g., `172.18.0.1`). When `dockerd` is started with an explicit `--host-gateway-ip=1.2.3.4`, that same container should show `host.docker.internal` mapped to `1.2.3.4`.

The impact is twofold. For Docker Desktop on Mac and Windows, the `--host-gateway-ip` flag can be set by the application to point to the VPNkit proxy IP, seamlessly integrating with their existing networking layers. For native Linux installations, the default behavior (using the bridge IP) provides a sensible, automatic configuration that "just works" for the majority of use cases, eliminating a common manual setup step.

This change effectively resolves the suite of linked issues, from the core Linux feature request (`docker/for-linux#264`) to various downstream problems in tools and applications that depended on this hostname being available. It promotes consistency and reduces the platform-specific knowledge required to write portable Docker run commands and configurations.

## Potential Concerns & Questions

While the PR is well-targeted, a thorough review raises several points for consideration:
1. **Error Handling:** The code returns a generic error `"unable to derive the IP value for host-gateway"` if `HostGatewayIP.String()` is empty. Should this error message be more specific, guiding the user to set the `--host-gateway-ip` flag explicitly? Is the empty default handled reliably on all Linux configurations?

2. **Configuration Scope:** The `HostGatewayIP` is a single daemon-wide setting. Does this present any limitation in complex multi-network setups where different bridge networks might have different host gateways? The current design assumes one host IP for all containers.

3. **Default Behavior Clarity:** The PR states the default is "the IP address of the default bridge." This is derived programmatically. Is the documentation clear enough on what happens if the default bridge is not present or if the daemon is configured with a custom bridge as default?

4. **Security Implications:** By making `host.docker.internal` trivially available, does this lower the barrier for containers to access host services, potentially expanding the attack surface? This is a broader design consideration beyond this PR, but worth noting.

5. **Constant Definition:** The logic depends on the constant `network.HostGatewayName`. The exact value of this constant (e.g., `"host-gateway"`) and its location in the codebase are not visible in the provided diff. A reviewer would need to verify this constant is correctly defined and exported.
