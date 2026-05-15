# PR #32691 diff: full changes to README


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


## Diff
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
+All Moby components are containers, so creating new components is as easy as building a new OCI-compatible container.
 
-A common method for distributing applications and sandboxing their
-execution is to use virtual machines, or VMs. Typical VM formats are
-VMware's vmdk, Oracle VirtualBox's vdi, and Amazon EC2's ami. In theory
-these formats should allow every developer to automatically package
-their application into a "machine" for easy distribution and deployment.
-In practice, that almost never happens, for a few reasons:
+## Principles
 
-  * *Size*: VMs are very large which makes them impractical to store
-     and transfer.
-  * *Performance*: running VMs consumes significant CPU and memory,
-    which makes them impractical in many scenarios, for example local
-    development of multi-tier applications, and large-scale deployment
-    of cpu and memory-intensive applications on large numbers of
-    machines.
-  * *Portability*: competing VM environments don't play well with each
-     other. Although conversion tools do exist, they are limited and
-     add even more overhead.
-  * *Hardware-centric*: VMs were designed with machine operators in
-    mind, not software developers. As a result, they offer very
-    limited tooling for what developers need most: building, testing
-    and running their software. For example, VMs offer no facilities
-    for application versioning, monitoring, configuration, logging or
-    service discovery.
+Moby is an open project guided by strong principles, but modular, flexible and without too strong an opinion on user experience, so it is open to the community to help set its direction.
+The guiding principles are:
 
-By contrast, Docker relies on a different sandboxing method known as
-*containerization*. Unlike traditional virtualization, containerization
-takes place at the kernel level. Most modern operating system kernels
-now support the primitives necessary for containerization, including
-Linux with [openvz](https://openvz.org),
-[vserver](http://linux-vserver.org) and more recently
-[lxc](https://linuxcontainers.org/), Solaris with
-[zones](https://docs.oracle.com/cd/E26502_01/html/E29024/preface-1.html#scrolltoc),
-and FreeBSD with
-[Jails](https://www.freebsd.org/doc/handbook/jails.html).
+- Batteries included but swappable: Moby includes enough components to build fully featured container system, but its modular architecture ensures that most of the components can be swapped by different implementations.
+- Usable security: Moby will provide secure defaults without compromising usability.
+- Container centric: Moby is built with containers, for running containers.
 
-Docker builds on top of these low-level primitives to offer developers a
-portable format and runtime environment that solves all four problems.
-Docker containers are small (and their transfer can be optimized with
-layers), they have basically zero memory and cpu overhead, they are
-completely portable, and are designed from the ground up with an
-application-centric design.
+With Moby, you should be able to describe all the components of your distributed application, from the high-level configuration files down to the kernel you would like to use and build and deploy it easily.
 
-Perhaps best of all, because Docker operates at the OS level, it can still be
-run inside a VM!
+Moby uses [containerd](https://github.com/containerd/containerd) as the default container runtime.
 
-## Plays well with others
+## Audience
 
-Docker does not require you to buy into a particular programming
-language, framework, packaging system, or configuration language.
+Moby is recommended for anyone who wants to assemble a container-based system. This includes:
 
-Is your application a Unix process? Does it use files, tcp connections,
-environment variables, standard Unix streams and command-line arguments
-as inputs and outputs? Then Docker can run it.
+- Hackers who want to customize or patch their Docker build
+- System engineers or integrators building a container system
+- Infrastructure providers looking to adapt existing container systems to their environment
+- Container enthusiasts who want to experiment with the latest container tech
+- Open-source developers looking to test their project in a variety of different systems
+- Anyone curious about Docker internals and how it’s built
 
-Can your application's build be expressed as a sequence of such
-commands? Then Docker can build it.
+Moby is NOT recommended for:
 
-## Escape dependency hell
+- Application developers looking for an easy way to run their applications in containers. We recommend Docker CE instead.
+- Enterprise IT and development teams looking for a ready-to-use, commercially supported container platform. We recommend Docker EE instead.
+- Anyone curious about containers and looking for an easy way to learn. We recommend the docker.com website instead.
 
-A common problem for developers is the difficulty of managing all
-their application's dependencies in a simple and automated way.
+# Transitioning to Moby
 
-This is usually difficult for several reasons:
+Docker is transitioning all of its open source collaborations to the Moby project going forward.
+During the transition, all open source activity should continue as usual.
 
-  * *Cross-platform dependencies*. Modern applications often depend on
-    a combination of system libraries and binaries, language-specific
-    packages, framework-specific modules, internal components
-    developed for another project, etc. These dependencies live in
-    different "worlds" and require different tools - these tools
-    typically don't work well with each other, requiring awkward
-    custom integrations.
+We are proposing the following list of changes:
 
-  * *Conflicting dependencies*. Different applications may depend on
-    different versions of the same dependency. Packaging tools handle
-    these situations with various degrees of ease - but they all
-    handle them in different and incompatible ways, which again forces
-    the developer to do extra work.
+- splitting up the engine into more open components
+- removing the docker UI, SDK etc to keep them in the Docker org
+- clarifying that the project is not limited to the engine, but to the assembly of all the individual components of the Docker platform
+- open-source new tools & components which we currently use to assemble the Docker product, but could benefit the community
+- defining an open, community-centric governance inspired by the Fedora project (a very successful example of balancing the needs of the community with the constraints of the primary corporate sponsor)
 
-  * *Custom dependencies*. A developer may need to prepare a custom
-    version of their application's dependency. Some packaging systems
-    can handle custom versions of a dependency, others can't - and all
-    of them handle it differently.
+-----
 
-
-Docker solves the problem of dependency hell by giving developers a simple
-way to express *all* their application's dependencies in one place, while
-streamlining the process of assembling them. If this makes you think of
-[XKCD 927](https://xkcd.com/927/), don't worry. Docker doesn't
-*replace* your favorite packaging systems. It simply orchestrates
-their use in a simple and repeatable way. How does it do that? With
-layers.
-
-Docker defines a build as running a sequence of Unix commands, one
-after the other, in the same container. Build commands modify the
-contents of the container (usually by installing new files on the
-filesystem), the next command modifies it some more, etc. Since each
-build command inherits the result of the previous commands, the
-*order* in which the commands are executed expresses *dependencies*.
-
-Here's a typical Docker build process:
-
-```bash
-FROM ubuntu:12.04
-RUN apt-get update && apt-get install -y python python-pip curl
-RUN curl -sSL https://github.com/shykes/helloflask/archive/master.tar.gz | tar -xzv
-RUN cd helloflask-master && pip install -r requirements.txt
-```
-
-Note that Docker doesn't care *how* dependencies are built - as long
-as they can be built by running a Unix command in a container.
-
-
-Getting started
-===============
-
-Docker can be installed either on your computer for building applications or
-on servers for running them. To get started, [check out the installation
-instructions in the
-documentation](https://docs.docker.com/engine/installation/).
-
-Usage examples
-==============
-
-Docker can be used to run short-lived commands, long-running daemons
-(app servers, databases, etc.), interactive shell sessions, etc.
-
-You can find a [list of real-world
-examples](https://docs.docker.com/engine/examples/) in the
-documentation.
-
-Under the hood
---------------
-
-Under the hood, Docker is built on the following components:
-
-* The
-  [cgroups](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt)
-  and
-  [namespaces](http://man7.org/linux/man-pages/man7/namespaces.7.html)
-  capabilities of the Linux kernel
-* The [Go](https://golang.org) programming language
-* The [Docker Image Specification](https://github.com/docker/docker/blob/master/image/spec/v1.md)
-* The [Libcontainer Specification](https://github.com/opencontainers/runc/blob/master/libcontainer/SPEC.md)
-
-Contributing to Docker [![GoDoc](https://godoc.org/github.com/docker/docker?status.svg)](https://godoc.org/github.com/docker/docker)
-======================
-
-| **Master** (Linux) | **Experimental** (Linux) | **Windows** | **FreeBSD** |
-|------------------|----------------------|---------|---------|
-| [![Jenkins Build Status](https://jenkins.dockerproject.org/view/Docker/job/Docker%20Master/badge/icon)](https://jenkins.dockerproject.org/view/Docker/job/Docker%20Master/) | [![Jenkins Build Status](https://jenkins.dockerproject.org/view/Docker/job/Docker%20Master%20%28experimental%29/badge/icon)](https://jenkins.dockerproject.org/view/Docker/job/Docker%20Master%20%28experimental%29/) | [![Build Status](http://jenkins.dockerproject.org/job/Docker%20Master%20(windows)/badge/icon)](http://jenkins.dockerproject.org/job/Docker%20Master%20(windows)/) | [![Build Status](http://jenkins.dockerproject.org/job/Docker%20Master%20(freebsd)/badge/icon)](http://jenkins.dockerproject.org/job/Docker%20Master%20(freebsd)/) |
-
-Want to hack on Docker? Awesome! We have [instructions to help you get
-started contributing code or documentation](https://docs.docker.com/opensource/project/who-written-for/).
-
-These instructions are probably not perfect, please let us know if anything
-feels wrong or incomplete. Better yet, submit a PR and improve them yourself.
-
-Getting the development builds
-==============================
-
-Want to run Docker from a master build? You can download
-master builds at [master.dockerproject.org](https://master.dockerproject.org).
-They are updated with each commit merged into the master branch.
-
-Don't know how to use that super cool new feature in the master build? Check
-out the master docs at
-[docs.master.dockerproject.org](http://docs.master.dockerproject.org).
-
-How the project is run
-======================
-
-Docker is a very, very active project. If you want to learn more about how it is run,
-or want to get more involved, the best place to start is [the project directory](https://github.com/docker/docker/tree/master/project).
-
-We are always open to suggestions on process improvements, and are always looking for more maintainers.
-
-### Talking to other Docker users and contributors
-
-<table class="tg">
-  <col width="45%">
-  <col width="65%">
-  <tr>
-    <td>Internet&nbsp;Relay&nbsp;Chat&nbsp;(IRC)</td>
-    <td>
-      <p>
-        IRC is a direct line to our most knowledgeable Docker users; we have
-        both the  <code>#docker</code> and <code>#docker-dev</code> group on
-        <strong>irc.freenode.net</strong>.
-        IRC is a rich chat protocol but it can overwhelm new users. You can search
-        <a href="https://botbot.me/freenode/docker/#" target="_blank">our chat archives</a>.
-      </p>
-      Read our <a href="https://docs.docker.com/opensource/get-help/#/irc-quickstart" target="_blank">IRC quickstart guide</a> for an easy way to get started.
-    </td>
-  </tr>
-  <tr>
-    <td>Docker Community Forums</td>
-    <td>
-      The <a href="https://forums.docker.com/c/open-source-projects/de" target="_blank">Docker Engine</a>
-      group is for users of the Docker Engine project.
-    </td>
-  </tr>
-  <tr>
-    <td>Google Groups</td>
-    <td>
-      The <a href="https://groups.google.com/forum/#!forum/docker-dev"
-      target="_blank">docker-dev</a> group is for contributors and other people
-      contributing to the Docker project.  You can join this group without a
-      Google account by sending an email to <a
-      href="mailto:docker-dev+subscribe@googlegroups.com">docker-dev+subscribe@googlegroups.com</a>.
-      You'll receive a join-request message; simply reply to the message to
-      confirm your subscription.
-    </td>
-  </tr>
-  <tr>
-    <td>Twitter</td>
-    <td>
-      You can follow <a href="https://twitter.com/docker/" target="_blank">Docker's Twitter feed</a>
-      to get updates on our products. You can also tweet us questions or just
-      share blogs or stories.
-    </td>
-  </tr>
-  <tr>
-    <td>Stack Overflow</td>
-    <td>
-      Stack Overflow has thousands of Docker questions listed. We regularly
-      monitor <a href="https://stackoverflow.com/search?tab=newest&q=docker" target="_blank">Docker questions</a>
-      and so do many other knowledgeable Docker users.
-    </td>
-  </tr>
-</table>
-
-### Legal
+Legal
+=====
 
 *Brought to you courtesy of our legal counsel. For more context,
-please see the [NOTICE](https://github.com/docker/docker/blob/master/NOTICE) document in this repo.*
+please see the [NOTICE](https://github.com/moby/moby/blob/master/NOTICE) document in this repo.*
 
-Use and transfer of Docker may be subject to certain restrictions by the
+Use and transfer of Moby may be subject to certain restrictions by the
 United States and other governments.
 
 It is your responsibility to ensure that your use and/or transfer does not
@@ -278,30 +83,6 @@ For more information, please see https://www.bis.doc.gov
 
 Licensing
 =========
-Docker is licensed under the Apache License, Version 2.0. See
-[LICENSE](https://github.com/docker/docker/blob/master/LICENSE) for the full
+Moby is licensed under the Apache License, Version 2.0. See
+[LICENSE](https://github.com/moby/moby/blob/master/LICENSE) for the full
 license text.
-
-Other Docker Related Projects
-=============================
-There are a number of projects under development that are based on Docker's
-core technology. These projects expand the tooling built around the
-Docker platform to broaden its application and utility.
-
-* [Docker Registry](https://github.com/docker/distribution): Registry
-server for Docker (hosting/delivery of repositories and images)
-* [Docker Machine](https://github.com/docker/machine): Machine management
-for a container-centric world
-* [Docker Swarm](https://github.com/docker/swarm): A Docker-native clustering
-system
-* [Docker Compose](https://github.com/docker/compose) (formerly Fig):
-Define and run multi-container apps
-* [Kitematic](https://github.com/docker/kitematic): The easiest way to use
-Docker on Mac and Windows
-
-If you know of another project underway that should be listed here, please help
-us keep this list up-to-date by submitting a PR.
-
-Awesome-Docker
-==============
-You can find more projects, tools and articles related to Docker on the [awesome-docker list](https://github.com/veggiemonk/awesome-docker). Add your project there.
diff --git a/docs/static_files/moby-project-logo.png b/docs/static_files/moby-project-logo.png
new file mode 100644
index 0000000000000..2914186efdd0d
Binary files /dev/null and b/docs/static_files/moby-project-logo.png differ
