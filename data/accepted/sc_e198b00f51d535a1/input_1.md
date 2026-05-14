# README


# Seed Material: moby/moby#32691: A new upstream project to break up Docker into independent components
Source: github_issue_pr
Identifier: pr:moby/moby#32691

Repository: moby/moby
PR Number: #32691
PR Title: A new upstream project to break up Docker into independent components
Merged At: 2017-04-20T22:32:33Z
Changed Files: 2
Additions: +50, Deletions: -269

## PR Description
Work has been ongoing to break Docker into modular components for some time, with runc and containerd as examples. Containerd for example has been donated to the CNCF. We are now completing this work with the goal being that the monolithic docker repo eventually ceases to exist, instead being assembled from a set of components.

Docker is, and will remain, a open source product that lets you build, ship and run containers. It is staying exactly the same from a user’s perspective. Users can download Docker from the docker.com website.

Moby is a project which provides a “Lego set” of dozens of components, the framework for assembling them into custom container-based systems, and a place for all container enthusiasts to experiment and exchange ideas. You can learn more at http://mobyproject.org

Docker the product will be assembled from components that are packaged by the Moby project.

The Moby project provides a command-line tool called moby which assembles components. Currently it assembles bootable OS images, but soon it will also be used by Docker for assembling Docker out of components, many of which will be independent projects.

As the Docker Engine continues to be split up into more components the Moby project will also be the home for those components until a more appropriate location is found.

Docker is transitioning all of its open source collaborations to the Moby project going forward.
During the transition, all open source activity should continue as usual.

This pull request changes the README and kicks off the process of breaking up the engine under Moby. Again: if you are a Docker user, nothing changes.


## Diff (first 3000 chars)
diff --git a/README.md b/README.md
index c4b9e74014422..5317b88090a8c 100644
--- a/README.md
+++ b/README.md
@@ -1,273 +1,78 @@
-**Docker is transitioning to the Moby Project. [Click here for more information](https://github.com/moby/moby/pull/32691)**
----------------
+### Docker maintainers and contributors, see [Transitioning to Moby](#transitioning-to-moby) for more details
 
-Docker: the container engine [![Release](https://img.shields.io/github/release/docker/docker.svg)](https://github.com/docker/docker/releases/latest)
-============================
+The Moby Project
+================
 
-Docker is an open source project to pack, ship and run any application
-as a lightweight container.
+![Moby Project logo](docs/static_files/moby-project-logo.png "The Moby Project")
 
-Docker containers are both *hardware-agnostic* and *platform-agnostic*.
-This means they can run anywhere, from your laptop to the largest
-cloud compute instance and everything in between - and they don't require
-you to use a particular language, framework or packaging system. That
-makes them great building blocks for deploying and scaling web apps,
-databases, and backend services without depending on a particular stack
-or provider.
+Moby is an open-source project created by Docker to advance the software containerization movement.
+It provides a “Lego set” of dozens of components, the framework for assembling them into custom container-based systems, and a place for all container enthusiasts to experiment and exchange ideas.
 
-Docker began as an open-source implementation of the deployment engine which
-powered [dotCloud](http://web.archive.org/web/20130530031104/https://www.dotcloud.com/),
-a popular Platform-as-a-Service. It benefits directly from the experience
-accumulated over several years of large-scale operation and support of hundreds
-of thousands of applications and databases.
+# Moby
 
-![Docker logo](docs/static_files/docker-logo-compressed.png "Docker")
+## Overview
 
-## Security Disclosure
+At the core of Moby is a framework to assemble specialized container systems.
+It provides:
 
-Security is very important to us. If you have any issue regarding security,
-please disclose the information responsibly by sending an email to
-security@docker.com and not by creating a GitHub issue.
+- A library of containerized components for all vital aspects of a container system: OS, container runtime, orchestration, infrastructure management, networking, storage, security, build, image distribution, etc.
+- Tools to assemble the components into runnable artifacts for a variety of platforms and architectures: bare metal (both x86 and Arm); executables for Linux, Mac and Windows; VM images for popular cloud and virtualization providers.
+- A set of reference assemblies which can be used as-is, modified, or used as inspiration to create your own.
 
-## Better than VMs
+All Moby components are containers, so creating new components is as easy as building a new OCI-compa