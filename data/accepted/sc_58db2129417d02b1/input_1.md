# integration/container/daemon_linux_test


# Seed Material: moby/moby#40007: Support host.docker.internal in dockerd on Linux
Source: github_issue_pr
Identifier: pr:moby/moby#40007

Repository: moby/moby
PR Number: #40007
PR Title: Support host.docker.internal in dockerd on Linux
Merged At: 2020-01-27T12:42:27Z
Changed Files: 8
Additions: +95, Deletions: -5

## PR Description
- addresses https://github.com/docker/for-linux/issues/264 Support host.docker.internal DNS name to host
- replaces, closes https://github.com/docker/libnetwork/pull/2348 special DNS record for host.docker.internal + gateway.docker.internal

Other issues (linking for discoverability)

- addresses https://github.com/docker/for-win/issues/5167 Unable to connect to WSL2 host IP after update to 2.1.6.0
- addresses https://github.com/docker/for-mac/issues/2705 They're close, but "docker.for.mac.host.*" and "docker.for.win.*" should be bette
- addresses https://github.com/moby/moby/issues/36625 They're close, but "docker.for.mac.host.*" and "docker.for.win.*" should be better
- addresses https://github.com/docker/for-win/issues/1855 They're close, but "docker.for.mac.host.*" and "docker.for.win.*" should be better docker/for-win#1855
- addresses https://github.com/jtreminio/dashtainer/issues/2 Xdebug on Linux needs a programmatic value for remote_host
- addresses https://github.com/bscheshirwork/docker-yii2-app-advanced/issues/1 Docker image bscheshir/php:7.2.5-fpm-alpine-4yii2-xdebug cannot connect to the host machine for XDebug
- addresses https://github.com/drud/ddev/issues/843 v0.18.0 xdebug instructions don't work on linux due to no "host.docker.internal" hostname
- addresses https://github.com/jc21/nginx-proxy-manager/issues/259 host.docker.internal is not resolved by nginx
- addresses https://github.com/cypress-io/cypress-docker-images/issues/183 http://host.docker.internal Does not work
- addresses https://github.com/Decathlon/ara/issues/222 local installation does not work on Ubuntu (with Docker and docker compose)
- addresses https://github.com/davidfowl/Micronetes/issues/22 Support for container networks / multicontainer workloads

**- What I did**
This PR allows containers to connect to Linux hosts
    by appending a special string "host-gateway" to --add-host
    e.g. "--add-host=host.docker.internal:host-gateway" which adds
    host.docker.internal DNS entry in /etc/hosts and maps it to host-gateway-ip
    This PR also add a daemon flag call host-gateway-ip which defaults to
    the default bridge IP
    Docker Desktop will need to set this field to the Host Proxy IP
    so DNS requests for host.docker.internal can be routed to VPNkit

**- How to verify it**
```
dockerd &
docker run -it --add-host=host.docker.internal:host-gateway alpine cat /etc/hosts
127.0.0.1	localhost
::1	localhost ip6-localhost ip6-loopback
fe00::0	ip6-localnet
ff00::0	ip6-mcastprefix
ff02::1	ip6-allnodes
ff02::2	ip6-allrouters
172.18.0.1	host.docker.internal
172.18.0.2	9f74a81028b7
```

```
dockerd --host-gateway-ip=1.2.3.4 &
docker run -it --add-host=host.docker.internal:host-gateway alpine cat /etc/hosts
127.0.0.1	localhost
::1	localhost ip6-localhost ip6-loopback
fe00::0	ip6-localnet
ff00::0	ip6-mcastprefix
ff02::1	ip6-allnodes
ff02::2	ip6-allrouters
1.2.3.4	host.docker.internal
172.18.0.2	a5f53cc81d24
```


## Diff
diff --git a/cmd/dockerd/config.go b/cmd/dockerd/config.go
index f4b48a4097390..f75ea3c38ebe5 100644
--- a/cmd/dockerd/config.go
+++ b/cmd/dockerd/config.go
@@ -64,6 +64,7 @@ func installCommonConfigFlags(conf *config.Config, flags *pflag.FlagSet) error {
 	flags.Var(opts.NewListOptsRef(&conf.DNS, opts.ValidateIPAddress), "dns", "DNS server to use")
 	flags.Var(opts.NewNamedListOptsRef("dns-opts", &conf.DNSOptions, nil), "dns-opt", "DNS options to use")
 	flags.Var(opts.NewListOptsRef(&conf.DNSSearch, opts.ValidateDNSSearch), "dns-search", "DNS search domains to use")
+	flags.Var(opts.NewIPOpt(&conf.HostGatewayIP, ""), "host-gateway-ip", "IP address that the special 'host-gateway' string in --add-host resolves to. Defaults to the IP address of the default bridge")
 	flags.Var(opts.NewNamedListOptsRef("labels", &conf.Labels, opts.ValidateLabel), "label", "Set key=value labels to the daemon")
 	flags.StringVar(&conf.LogConfig.Type, "log-driver", "json-file", "Default driver for container logs")
 	flags.Var(opts.NewNamedMapOpts("log-opts", conf.LogConfig.Config, nil), "log-opt", "Default log driver options for containers")
diff --git a/daemon/config/config.go b/daemon/config/config.go
index 0fbd81f02120f..247ac41cb92ce 100644
--- a/daemon/config/config.go
+++ b/daemon/config/config.go
@@ -6,6 +6,7 @@ import (
 	"fmt"
 	"io"
 	"io/ioutil"
+	"net"
 	"os"
 	"reflect"
 	"strings"
@@ -115,9 +116,10 @@ type CommonTLSOptions struct {
 
 // DNSConfig defines the DNS configurations.
 type DNSConfig struct {
-	DNS        []string `json:"dns,omitempty"`
-	DNSOptions []string `json:"dns-opts,omitempty"`
-	DNSSearch  []string `json:"dns-search,omitempty"`
+	DNS           []string `json:"dns,omitempty"`
+	DNSOptions    []string `json:"dns-opts,omitempty"`
+	DNSSearch     []string `json:"dns-search,omitempty"`
+	HostGatewayIP net.IP   `json:"host-gateway-ip,omitempty"`
 }
 
 // CommonConfig defines the configuration of a docker daemon which is
diff --git a/daemon/container_operations.go b/daemon/container_operations.go
index 205c0905017a1..d488d09f842c8 100644
--- a/daemon/container_operations.go
+++ b/daemon/container_operations.go
@@ -115,6 +115,16 @@ func (daemon *Daemon) buildSandboxOptions(container *container.Container) ([]lib
 			return nil, err
 		}
 		parts := strings.SplitN(extraHost, ":", 2)
+		// If the IP Address is a string called "host-gateway", replace this
+		// value with the IP address stored in the daemon level HostGatewayIP
+		// config variable
+		if parts[1] == network.HostGatewayName {
+			gateway := daemon.configStore.HostGatewayIP.String()
+			if gateway == "" {
+				return nil, fmt.Errorf("unable to derive the IP value for host-gateway")
+			}
+			parts[1] = gateway
+		}
 		sboxOptions = append(sboxOptions, libnetwork.OptionExtraHost(parts[0], parts[1]))
 	}
 
diff --git a/daemon/daemon_unix.go b/daemon/daemon_unix.go
index f2d1fc932fbc8..9f1422295d8e7 100644
--- a/daemon/daemon_unix.go
+++ b/daemon/daemon_unix.go
@@ -925,6 +925,19 @@ func (daemon *Daemon) initNetworkController(config *config.Config, activeSandbox
 		removeDefaultBridgeInterface()
 	}
 
+	// Set HostGatewayIP to the default bridge's IP  if it is empty
+	if daemon.configStore.HostGatewayIP == nil && controller != nil {
+		if n, err := controller.NetworkByName("bridge"); err == nil {
+			v4Info, v6Info := n.Info().IpamInfo()
+			var gateway net.IP
+			if len(v4Info) > 0 {
+				gateway = v4Info[0].Gateway.IP
+			} else if len(v6Info) > 0 {
+				gateway = v6Info[0].Gateway.IP
+			}
+			daemon.configStore.HostGatewayIP = gateway
+		}
+	}
 	return controller, nil
 }
 
diff --git a/daemon/network/constants.go b/daemon/network/constants.go
new file mode 100644
index 0000000000000..e7d97018fd595
--- /dev/null
+++ b/daemon/network/constants.go
@@ -0,0 +1,8 @@
+package network
+
+const (
+	// HostGatewayName is the string value that can be passed
+	// to the IPAddr section in --add-host that is replaced by
+	// the value of HostGatewayIP daemon config value
+	HostGatewayName = "host-gateway"
+)
diff --git a/integration/container/daemon_linux_test.go b/integration/container/daemon_linux_test.go
index 39f056fabe545..5e260a495d6ff 100644
--- a/integration/container/daemon_linux_test.go
+++ b/integration/container/daemon_linux_test.go
@@ -120,3 +120,47 @@ func TestDaemonRestartIpcMode(t *testing.T) {
 	assert.NilError(t, err)
 	assert.Check(t, is.Equal(string(inspect.HostConfig.IpcMode), "shareable"))
 }
+
+// TestDaemonHostGatewayIP verifies that when a magic string "host-gateway" is passed
+// to ExtraHosts (--add-host) instead of an IP address, its value is set to
+// 1. Daemon config flag value specified by host-gateway-ip or
+// 2. IP of the default bridge network
+// and is added to the /etc/hosts file
+func TestDaemonHostGatewayIP(t *testing.T) {
+	skip.If(t, testEnv.IsRemoteDaemon)
+	skip.If(t, testEnv.DaemonInfo.OSType == "windows")
+	t.Parallel()
+
+	// Verify the IP in /etc/hosts is same as host-gateway-ip
+	d := daemon.New(t)
+	// Verify the IP in /etc/hosts is same as the default bridge's IP
+	d.StartWithBusybox(t)
+	c := d.NewClientT(t)
+	ctx := context.Background()
+	cID := container.Run(ctx, t, c,
+		container.WithExtraHost("host.docker.internal:host-gateway"),
+	)
+	res, err := container.Exec(ctx, c, cID, []string{"cat", "/etc/hosts"})
+	assert.NilError(t, err)
+	assert.Assert(t, is.Len(res.Stderr(), 0))
+	assert.Equal(t, 0, res.ExitCode)
+	inspect, err := c.NetworkInspect(ctx, "bridge", types.NetworkInspectOptions{})
+	assert.NilError(t, err)
+	assert.Check(t, is.Contains(res.Stdout(), inspect.IPAM.Config[0].Gateway))
+	c.ContainerRemove(ctx, cID, types.ContainerRemoveOptions{Force: true})
+	d.Stop(t)
+
+	// Verify the IP in /etc/hosts is same as host-gateway-ip
+	d.StartWithBusybox(t, "--host-gateway-ip=6.7.8.9")
+	cID = container.Run(ctx, t, c,
+		container.WithExtraHost("host.docker.internal:host-gateway"),
+	)
+	res, err = container.Exec(ctx, c, cID, []string{"cat", "/etc/hosts"})
+	assert.NilError(t, err)
+	assert.Assert(t, is.Len(res.Stderr(), 0))
+	assert.Equal(t, 0, res.ExitCode)
+	assert.Check(t, is.Contains(res.Stdout(), "6.7.8.9"))
+	c.ContainerRemove(ctx, cID, types.ContainerRemoveOptions{Force: true})
+	d.Stop(t)
+
+}
diff --git a/integration/internal/container/ops.go b/integration/internal/container/ops.go
index b9ba8c4e85db8..c829ad1717a34 100644
--- a/integration/internal/container/ops.go
+++ b/integration/internal/container/ops.go
@@ -180,3 +180,11 @@ func WithCgroupnsMode(mode string) func(*TestContainerConfig) {
 		c.HostConfig.CgroupnsMode = containertypes.CgroupnsMode(mode)
 	}
 }
+
+// WithExtraHost sets the user defined IP:Host mappings in the container's
+// /etc/hosts file
+func WithExtraHost(extraHost string) func(*TestContainerConfig) {
+	return func(c *TestContainerConfig) {
+		c.HostConfig.ExtraHosts = append(c.HostConfig.ExtraHosts, extraHost)
+	}
+}
diff --git a/opts/hosts.go b/opts/hosts.go
index a6f2662df0888..41caae307271b 100644
--- a/opts/hosts.go
+++ b/opts/hosts.go
@@ -8,6 +8,7 @@ import (
 	"strconv"
 	"strings"
 
+	"github.com/docker/docker/daemon/network"
 	"github.com/docker/docker/pkg/homedir"
 )
 
@@ -169,8 +170,11 @@ func ValidateExtraHost(val string) (string, error) {
 	if len(arr) != 2 || len(arr[0]) == 0 {
 		return "", fmt.Errorf("bad format for add-host: %q", val)
 	}
-	if _, err := ValidateIPAddress(arr[1]); err != nil {
-		return "", fmt.Errorf("invalid IP address in add-host: %q", arr[1])
+	// Skip IPaddr validation for special "host-gateway" string
+	if arr[1] != network.HostGatewayName {
+		if _, err := ValidateIPAddress(arr[1]); err != nil {
+			return "", fmt.Errorf("invalid IP address in add-host: %q", arr[1])
+		}
 	}
 	return val, nil
 }
