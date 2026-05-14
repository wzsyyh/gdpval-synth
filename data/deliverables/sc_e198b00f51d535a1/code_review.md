# Code Review: moby/moby#32691 – A new upstream project to break up Docker into independent components

## PR Summary

PR #32691 in the moby/moby repository, titled "A new upstream project to break up Docker into independent components," was merged on April 20, 2017. This pull request rewrites the project README.md from Docker-specific branding and content to the new Moby Project identity. The change removes 269 lines of Docker-focused documentation and replaces them with 50 lines of Moby Project content, reflecting the beginning of the monolithic Docker engine's decomposition into modular components.

## Motivation and Rationale

The PR description states that work has been ongoing to break Docker into modular components for some time, with runc and containerd cited as examples of components already extracted. Containerd in particular has been donated to the CNCF, demonstrating the project's commitment to open governance. The goal is that the monolithic Docker repository will eventually cease to exist, instead being assembled from a set of independent components.

The Moby Project is positioned as providing a "Lego set" of dozens of components, the framework for assembling them into custom container-based systems, and a place for all container enthusiasts to experiment and exchange ideas. The new README describes Moby as an open-source project created by Docker to advance the software containerization movement, with a core framework to assemble specialized container systems.

## User Impact Assessment

The PR description explicitly states that "Docker is, and will remain, a open source product that lets you build, ship and run containers. It is staying exactly the same from a user's perspective. Users can download Docker from the docker.com website." This reassurance is critical for the community: while the internal architecture is changing dramatically, the end-user product and experience remain identical.

Docker the product will be assembled from components that are packaged by the Moby project. This separation of concerns means the user-facing Docker product is a curated distribution built on top of the Moby component library, while Moby serves as the upstream project and experimentation platform.

## README Changes Analysis

The README.md diff shows significant restructuring. The removed content includes the Docker Engine header with release badge, the tagline about Docker as a container engine, the description of Docker containers as hardware-agnostic and platform-agnostic, historical context about Docker's origins from dotCloud (a Platform-as-a-Service), the Security Disclosure section directing security issues to security@docker.com, a "Better than VMs" section, and the Docker logo image reference.

The new README begins with a redirect notice for Docker maintainers and contributors pointing to a "Transitioning to Moby" section. It introduces The Moby Project with its own logo image (docs/static_files/moby-project-logo.png). The Overview section describes Moby's core framework, listing three key provisions: a library of containerized components covering OS, container runtime, orchestration, infrastructure management, networking, storage, security, build, and image distribution; tools to assemble components into runnable artifacts for various platforms and architectures including bare metal (x86 and Arm), executables for Linux/Mac/Windows, and VM images for cloud providers; and a set of reference assemblies that can be used as-is or modified.

## Project Structure Implications

The PR description explains that as the Docker Engine continues to be split into more components, the Moby project will serve as the home for those components until a more appropriate location is found. The Moby project provides a command-line tool called moby that assembles components. Currently it assembles bootable OS images, but the description notes it will soon also be used by Docker for assembling Docker out of components, many of which will be independent projects.

The README diff shows the beginning of a section stating that all Moby components are containers, so creating new components is as easy as building a new OCI-compatible image. This container-native approach to component architecture is fundamental to the Moby design philosophy.

## Contributor Guidance

The PR description states that Docker is transitioning all of its open source collaborations to the Moby project going forward. However, it explicitly notes that during the transition, all open source activity should continue as usual. This pull request itself is described as changing the README and kicking off the process of breaking up the engine under Moby.

The description concludes by reiterating that if you are a Docker user, nothing changes. Contributors working on the project should understand that this is the beginning of a gradual modularization process, not an abrupt restructuring. The repository will continue to function as the primary development location during the transition period.
