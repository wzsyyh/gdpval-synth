# Design Document: kubectl port-forward --address flag

# Design Document: kubectl port-forward --address flag

Design Document: kubectl port-forward --address flag

## Overview

This design document outlines the implementation of a new `--address` flag for the `kubectl port-forward` command. The feature allows users to specify the local address(es) on which the port-forwarding listener binds, enabling the command to be used in non-localhost environments such as Docker containers or remote machines.

The current implementation of `kubectl port-forward` hardcodes binding to `127.0.0.1` and `::1` (localhost). This limitation prevents its use in scenarios where the user needs to expose forwarded ports to other interfaces, which is a common requirement in containerized development environments and when accessing pods from different network segments.

This change resolves issues #36152 and #29678, which requested the ability to bind to addresses other than localhost. It implements the proposal described in issue #43962.

## Design Goals & Constraints

The primary design goals are: (1) Allow binding to one or more specific IPv4/IPv6 addresses or the symbolic name `localhost`; (2) Preserve full backward compatibility by defaulting to `localhost`; (3) Maintain the existing behavior when no `--address` flag is provided.

The implementation must be backward compatible. The default value of the new flag must be `localhost` to ensure that existing workflows and scripts that depend on port-forward binding only to localhost continue to function without change.

The flag will be named `--address` (with `-a` as an optional shorthand, though not explicitly shown in the diff). It will accept a comma-separated list of addresses, enabling multiple listeners if needed.

## API Changes

The `PortForwardOptions` struct in `pkg/kubectl/cmd/portforward/portforward.go` will be extended with a new `Address` field of type `[]string`. This field will store the list of addresses provided via the `--address` flag.

The new flag is defined in the `NewCmdPortForward` function with the following call: `cmd.Flags().StringSliceVar(&opts.Address, "address", []string{"localhost"}, "Addresses to listen on (comma separated)")`. The default value is `[]string{"localhost"}`, ensuring backward compatibility.

The usage examples will be updated to include two new entries: listening on all addresses with `--address 0.0.0.0` and listening on multiple addresses (localhost and a specific IP) with `--address localhost,10.19.21.23`.

## Implementation Plan

The `Use` string in the `NewCmdPortForward` function will be updated from `"port-forward TYPE/NAME [LOCAL_PORT:]REMOTE_PORT [...[LOCAL_PORT_N:]REMOTE_PORT_N]"` to `"port-forward TYPE/NAME [options] [LOCAL_PORT:]REMOTE_PORT [...[LOCAL_PORT_N:]REMOTE_PORT_N]"` to indicate that options are now available.

The `ForwardPorts` method in the `defaultPortForwarder` will be modified to call the new `NewOnAddresses` function instead of `New`. The call will pass the `opts.Address` slice as an additional argument: `fw, err := portforward.NewOnAddresses(dialer, opts.Address, opts.Ports, opts.StopChannel, opts.ReadyChannel, f.Out, f.ErrOut)`.

A new function `NewOnAddresses` will be introduced in the client-go portforward package (`staging/src/k8s.io/client-go/tools/portforward/portforward.go`). This function will accept a slice of addresses and handle the logic of creating listeners on each specified address. The existing `New` function will be refactored to become a wrapper that calls `NewOnAddresses` with a default address of `"localhost"`, preserving the old API for any external consumers.

## Backward Compatibility

Backward compatibility is maintained because the `--address` flag defaults to `[]string{"localhost"}`. When a user runs `kubectl port-forward` without specifying the `--address` flag, the behavior is identical to the previous implementation: listening on both `127.0.0.1` and `::1`.

The existing `New` function in the portforward package is preserved as a public API. It is refactored to call `NewOnAddresses` with the default address, so any existing code that directly uses the `New` function will continue to work without modification.

Scripts and automation that rely on the command's interface will not break because no existing flags are removed or altered. The new flag is purely additive.

## Testing Strategy

Unit tests should be added for the `NewOnAddresses` function to verify it correctly handles various address formats: a single IPv4 address, a single IPv6 address, the string `localhost`, multiple addresses, and empty or nil slices. Tests should also verify that invalid addresses (e.g., non-existent interfaces) are handled gracefully.

Unit tests in the `kubectl/cmd/portforward` package should verify that the `--address` flag is parsed correctly into the `Address` field of `PortForwardOptions`, including default value, single address, and multiple comma-separated addresses.

Integration tests should be created to validate the end-to-end functionality. These tests should verify that port-forwarding works correctly when binding to `0.0.0.0`, a specific loopback address, and multiple addresses simultaneously. Negative test cases should include attempting to bind to an address that is not available on the system.

Existing tests for the `New` function should be updated to confirm they still pass after the refactoring, ensuring no regression in backward compatibility.

## References

This design implements the proposal from GitHub issue #43962: https://github.com/kubernetes/kubernetes/issues/43962

It resolves the long-standing feature requests in issues #36152 and #29678.

The corresponding implementation pull request is PR #46517: https://github.com/kubernetes/kubernetes/pull/46517
