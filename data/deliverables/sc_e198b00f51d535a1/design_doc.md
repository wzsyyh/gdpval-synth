# Design Doc - Moby Component Extraction Plan

# Design Doc - Moby Component Extraction Plan

## Executive Summary

This document outlines the technical plan for decomposing the Docker engine into modular, independently-buildable components under the Moby project, as initiated by PR #32691 on the moby/moby repository. The Moby project (http://mobyproject.org) provides a 'Lego set' of dozens of components, a framework for assembling them into custom container-based systems, and a community hub for container enthusiasts. The end-state vision is that the monolithic docker repo ceases to exist, replaced by a collection of independent projects assembled via the Moby toolchain. Docker the product will remain a user-facing open-source tool to build, ship, and run containers, but its internal architecture will be fully modularized.

PR #32691 represents the first concrete step: rewriting the README from Docker-centric language to Moby branding, adding the Moby project logo (docs/static_files/moby-project-logo.png), and documenting the transition plan. This design document extends that foundation into a full extraction architecture.

## Motivation and Background

The Docker project has been progressively decomposing its monolithic architecture. Two major components have already been extracted: runc (the OCI-compliant container runtime) and containerd, which was donated to the Cloud Native Computing Foundation (CNCF). PR #32691 continues this trajectory by formally renaming the repository from docker/docker to moby/moby and rewriting the README to reflect the new identity.

The README diff in PR #32691 removes 269 lines of Docker-specific content (including sections on 'Better than VMs', 'Plays well with others', 'Escape dependency hell', build examples, community links, and the 'Other Docker Related Projects' list) and replaces them with 50 lines of Moby-focused documentation. A new logo file, docs/static_files/moby-project-logo.png, is added to visually anchor the new identity.

The 'Transitioning to Moby' section of the new README specifies five proposed changes: (1) splitting up the engine into more open components, (2) removing the Docker UI, SDK etc. to keep them in the Docker org, (3) clarifying that the project is not limited to the engine but to the assembly of all individual components of the Docker platform, (4) open-sourcing new tools and components currently used to assemble the Docker product but which could benefit the community, and (5) defining an open, community-centric governance inspired by the Fedora project.

## Target Audience Analysis

The Moby README explicitly defines its target audience. The project IS recommended for: (1) hackers who want to customize or patch their Docker build, and (2) system engineers or integrators building a container system. For hackers, the extraction must preserve deep customizability — every component should be replaceable without forking the entire system. For system engineers, the extraction must provide stable, well-documented interfaces between components so that integrators can assemble systems reliably.

The README also lists three groups for whom Moby is NOT recommended: (1) application developers looking for an easy way to run applications in containers (recommended Docker CE instead), (2) enterprise IT and development teams seeking a commercially supported platform (recommended Docker EE instead), and (3) anyone curious about containers looking for an easy learning path (recommended the docker.com website instead). These exclusions imply that the Moby extraction does not need to prioritize backward-compatible user-facing APIs or simplified onboarding flows; instead, it can optimize for composability and internal flexibility.

## Component Extraction Architecture

The extraction will proceed in three phases, organized by dependency order and risk. Each phase extracts component categories identified in the README's Overview section: OS, container runtime, orchestration, infrastructure management, networking, storage, security, build, and image distribution.

**Phase 1 — Core Runtime Extraction** (container runtime, OS, security): Extract containerd integration, the daemon's OS abstraction layer, and security subsystems into standalone components. This phase has the fewest external dependencies and the most mature interfaces, thanks to the prior runc and containerd extractions. All components remain OCI-compatible as stated in the README: 'All Moby components are containers, so creating new components is as easy as building a new OCI-compatible container.'

**Phase 2 — Platform Services Extraction** (networking, storage, build, image distribution): Extract the libnetwork driver interface, volume/storage plugins, the build subsystem, and the image distribution/push-pull logic. These components have more complex interdependencies and require careful API boundary definition. The moby CLI tool — described in the README as assembling bootable OS images and soon to be used by Docker for assembling Docker out of components — will serve as the integration test harness, verifying that extracted components compose correctly.

**Phase 3 — Orchestration and Infrastructure** (orchestration, infrastructure management): Extract Swarm mode and infrastructure management integrations. These are the highest-level components and depend on everything extracted in Phases 1 and 2. This phase completes the dissolution of the monolith.

Each phase must respect the three guiding principles from the README: (1) 'Batteries included but swappable' — every extracted component must expose a well-defined interface so alternative implementations can be swapped in; (2) 'Usable security' — secure defaults must be preserved through the extraction, with no security regressions; (3) 'Container centric' — all Moby components are themselves containers, ensuring consistent build and deployment.

## Governance and Transition Risks

The README specifies that the Moby project will adopt 'an open, community-centric governance inspired by the Fedora project,' balancing community needs with the constraints of Docker, Inc. as the primary corporate sponsor. This model requires clear maintainer roles, transparent decision-making processes, and formal contribution guidelines.

**Risk 1 — Contributor Confusion**: The rename from docker/docker to moby/moby may confuse existing contributors. Mitigation: maintain prominent transition documentation in the README (as PR #32691 already does with the 'Transitioning to Moby' section), provide redirect links from old URLs, and run community outreach sessions during the transition period.

**Risk 2 — Fragmented Documentation**: As components are extracted into separate repositories, documentation may become scattered and inconsistent. Mitigation: establish a central Moby documentation hub at mobyproject.org, enforce documentation standards for all extracted components, and require that the moby CLI tool's help system remains a unified entry point.

Legal considerations must also be addressed. The LICENSE file path changes from github.com/docker/docker/blob/master/LICENSE to github.com/moby/moby/blob/master/LICENSE. The NOTICE document at github.com/moby/moby/blob/master/NOTICE must be updated to reflect the new project structure. Both documents are referenced in the README's Legal and Licensing sections and must remain accurate throughout the extraction.

## Success Criteria

The extraction is complete when the following criteria are met, aligned with the PR description's assurance that 'Docker is, and will remain, a open source product that lets you build, ship and run containers' from a user perspective:

1. **Monolith Elimination**: The moby/moby repository contains only the moby CLI assembler and metadata; all engine functionality lives in independently-buildable component repositories.

2. **User Experience Preservation**: Docker CE and Docker EE can be assembled from Moby components via the moby tool with zero user-visible behavioral changes — users can 'download Docker from the docker.com website' as before.

3. **Component Independence**: Each extracted component (container runtime, orchestration, networking, storage, security, build, image distribution, OS abstraction, infrastructure management) has its own CI pipeline, test suite, and release cycle.

4. **Assembly Verification**: The moby CLI tool successfully assembles a fully functional Docker binary from extracted components on at least three target platforms (Linux x86, Linux Arm, macOS/Windows executables), consistent with the README's description of building 'runnable artifacts for a variety of platforms and architectures.'

5. **Community Governance**: The Fedora-inspired governance model is operational, with documented maintainer roles, contribution guidelines, and a transparent decision-making process.
