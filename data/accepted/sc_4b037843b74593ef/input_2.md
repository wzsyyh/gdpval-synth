# First 3000 characters of the code diff from PR #46517


# Seed Material: kubernetes/kubernetes#46517: port-forward listen on address
Source: github_issue_pr
Identifier: pr:kubernetes/kubernetes#46517

Repository: kubernetes/kubernetes
PR Number: #46517
PR Title: port-forward listen on address
Merged At: 2018-10-09T19:38:56Z
Changed Files: 4
Additions: +170, Deletions: -43

## PR Description
**What this PR does / why we need it**:

Implements #43962 proposal. Adds `--address` flag to port-forward command that allows listening on addresses other then localhost, so that port-forward can ie. be opened to consumers other then residing in local host like running in docker or different machine/vm

**Which issue this PR fixes**: 

fixes #43962, fixes #36152, fixes #29678

**Release note**:
```
allows selecting non-localhost addresses to listen on with port-forward
```

## Linked Issue #43962
Implementing this proposal that will solve issues raised in https://github.com/kubernetes/kubernetes/issues/36152 and https://github.com/kubernetes/kubernetes/issues/29678. In short: allow binding on addresses other then currently supported `127.0.0.1` and `::1`

The idea is to implement a new method `NewOnAddress` in pkg/client/unversioned/portforward/portforward.go that will add an address parameter, and refactor `New` as a wrapper on the `NewOnAddress` pointing to "localhost" address.

The `NewOnAddress` would work as `New` did previously (that is calling `listenOnPortAndAddress`) with a difference of setting the new PortForwarder private variable `address` that can take string representations of IPv4, IPv6, "localhost" or nil. Then `listenOnPort` will be changed in a way that if IPv4 or IPv6 is provided in `PortForwarder.address`, the address given wil be the only one used (if it is a valid one). If value "localhost" or nil is passed, it will behave exactly as it does now - listening on `127.0.0.1` and `[::1]`.

pkg/kubectl/cmd/portforward.go will be modified to call `NewOnAddress` method instead of `New` with new option address provided by `-a` or `--address` flag on `kubectl port-forward` command and passed via a new string variable `Address` in updated PortForwardOptions type.

## Diff (first 3000 chars)
diff --git a/pkg/kubectl/cmd/portforward/portforward.go b/pkg/kubectl/cmd/portforward/portforward.go
index 3cc08ed1e3a55..236293e1b5a1c 100644
--- a/pkg/kubectl/cmd/portforward/portforward.go
+++ b/pkg/kubectl/cmd/portforward/portforward.go
@@ -50,6 +50,7 @@ type PortForwardOptions struct {
 	RESTClient    *restclient.RESTClient
 	Config        *restclient.Config
 	PodClient     corev1client.PodsGetter
+	Address       []string
 	Ports         []string
 	PortForwarder portForwarder
 	StopChannel   chan struct{}
@@ -79,6 +80,12 @@ var (
 		# Listen on port 8888 locally, forwarding to 5000 in the pod
 		kubectl port-forward pod/mypod 8888:5000
 
+		# Listen on port 8888 on all addresses, forwarding to 5000 in the pod
+		kubectl port-forward --address 0.0.0.0 pod/mypod 8888:5000
+
+		# Listen on port 8888 on localhost and selected IP, forwarding to 5000 in the pod
+		kubectl port-forward --address localhost,10.19.21.23 pod/mypod 8888:5000
+
 		# Listen on a random port locally, forwarding to 5000 in the pod
 		kubectl port-forward pod/mypod :5000`))
 )
@@ -95,7 +102,7 @@ func NewCmdPortForward(f cmdutil.Factory, streams genericclioptions.IOStreams) *
 		},
 	}
 	cmd := &cobra.Command{
-		Use:                   "port-forward TYPE/NAME [LOCAL_PORT:]REMOTE_PORT [...[LOCAL_PORT_N:]REMOTE_PORT_N]",
+		Use:                   "port-forward TYPE/NAME [options] [LOCAL_PORT:]REMOTE_PORT [...[LOCAL_PORT_N:]REMOTE_PORT_N]",
 		DisableFlagsInUseLine: true,
 		Short:                 i18n.T("Forward one or more local ports to a pod"),
 		Long:                  portforwardLong,
@@ -113,6 +120,7 @@ func NewCmdPortForward(f cmdutil.Factory, streams genericclioptions.IOStreams) *
 		},
 	}
 	cmdutil.AddPodRunningTimeoutFlag(cmd, defaultPodPortForwardWaitTimeout)
+	cmd.Flags().StringSliceVar(&opts.Address, "address", []string{"localhost"}, "Addresses to listen on (comma separated)")
 	// TODO support UID
 	return cmd
 }
@@ -131,7 +139,7 @@ func (f *defaultPortForwarder) ForwardPorts(method string, url *url.URL, opts Po
 		return err
 	}
 	dialer := spdy.NewDialer(upgrader, &http.Client{Transport: transport}, method, url)
-	fw, err := portforward.New(dialer, opts.Ports, opts.StopChannel, opts.ReadyChannel, f.Out, f.ErrOut)
+	fw, err := portforward.NewOnAddresses(dialer, opts.Address, opts.Ports, opts.StopChannel, opts.ReadyChannel, f.Out, f.ErrOut)
 	if err != nil {
 		return err
 	}
diff --git a/staging/src/k8s.io/client-go/tools/portforward/portforward.go b/staging/src/k8s.io/client-go/tools/portforward/portforward.go
index bc6f43d7d15f2..0e9b369a98317 100644
--- a/staging/src/k8s.io/client-go/tools/portforward/portforward.go
+++ b/staging/src/k8s.io/client-go/tools/portforward/portforward.go
@@ -39,8 +39,9 @@ const PortForwardProtocolV1Name = "portforward.k8s.io"
 // PortForwarder knows how to listen for local connections and forward them to
 // a remote pod via an upgraded HTTP request.
 type PortForwarder struct {
-	ports    []ForwardedPort
-	stopChan <-chan struct{