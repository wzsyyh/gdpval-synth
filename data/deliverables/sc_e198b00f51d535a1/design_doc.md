# Impact Assessment - Docker to Moby Transition

## Executive Summary

The Docker project has undergone a significant architectural restructuring, transitioning the monolithic docker/docker repository (now moby/moby) into a modular, component-based architecture under the newly announced Moby Project. As stated in PR #32691, "Docker is, and will remain, a open source product that lets you build, ship and run containers. It is staying exactly the same from a user's perspective." This means that while the upstream project structure is fundamentally changing, the end-user experience of Docker as a container engine remains stable.

The Moby Project represents a new paradigm for container platform development. As described in the PR, "Moby is a project which provides a 'Lego set' of dozens of components, the framework for assembling them into custom container-based systems, and a place for all container enthusiasts to experiment and exchange ideas." The project introduces a command-line tool called moby that currently assembles bootable OS images and will soon be used to assemble Docker itself from independent components.

This design document evaluates the impact of this transition on our container platform infrastructure. Our analysis must account for both the near-term stability (Docker users see no change) and the long-term implications of the componentization strategy, where "the monolithic docker repo eventually ceases to exist, instead being assembled from a set of components." Docker the product "will be assembled from components that are packaged by the Moby project."

## Technical Background

The transition to the Moby Project did not occur in isolation. As the PR description notes, "Work has been ongoing to break Docker into modular components for some time, with runc and containerd as examples. Containerd for example has been donated to the CNCF." This prior work established the pattern and technical feasibility of extracting core functionality from the Docker monolith into standalone, independently maintainable projects.

The Moby project extends this modular philosophy to the entire container platform stack. According to the PR, the Moby framework provides a library of containerized components for all vital aspects of a container system: OS, container runtime, orchestration, infrastructure management, networking, storage, security, build, image distribution, and more. All Moby components are containers themselves, so creating new components is as easy as building a new OCI-compatible container.

The moby command-line tool serves as the assembly mechanism for these components. The PR states it currently assembles bootable OS images, but soon it will also be used by Docker for assembling Docker out of components, many of which will be independent projects. This tool-based assembly approach means that Docker will ultimately become one particular assembly of Moby components, rather than a monolithic codebase.

## Impact Analysis

### Container Runtime Dependencies

Our current platform relies on the Docker Engine as a single dependency. With the Moby transition, this engine will eventually be decomposed into multiple independent components. The PR states that "as the Docker Engine continues to be split up into more components the Moby project will also be the home for those components until a more appropriate location is found." In the near term, the docker/docker to moby/moby repository rename affects our dependency declarations, but "during the transition, all open source activity should continue as usual." Our container runtime layer—which already uses containerd and runc as separate dependencies—will see minimal disruption.

### Build and CI/CD Pipelines

Our CI/CD pipelines currently reference the docker/docker repository for source builds and contributions. The rename to moby/moby means all repository URLs, git remotes, and CI configuration referencing the old path must be updated. However, since "Docker is transitioning all of its open source collaborations to the Moby project going forward," our open-source contributions and issue tracking will need to follow the Moby project conventions. The moby CLI tool will eventually become relevant for assembling custom Docker configurations, which may require us to integrate this tool into our build processes.

### Container Orchestration

Our orchestration layer interacts with Docker through its API. Since "Docker is staying exactly the same from a user's perspective," the Docker API surface should remain stable during the transition. However, the underlying implementation will be composed of Moby components, which introduces potential version skew between independently released components. The Moby project provides tools to assemble the components into runnable artifacts for a variety of platforms and architectures: bare metal (both x86 and Arm); executables for Linux, Mac and Windows; VM images for popular cloud and virtualization providers.

## Migration Strategy

### Phase 1: Assessment (Weeks 1-4)

Conduct a comprehensive audit of all Docker-related dependencies, repository references, and integration points. Update all references from docker/docker to moby/moby. Evaluate which Moby components (runc, containerd, and others as they emerge) are already in use independently versus consumed as part of the monolithic Docker engine. The PR notes that "during the transition, all open source activity should continue as usual," so this phase has low risk of service disruption.

### Phase 2: Adaptation (Weeks 5-12)

Begin consuming Moby components directly where advantageous. Evaluate the moby command-line tool for assembling custom container system configurations. As the PR describes, "the Moby project provides a command-line tool called moby which assembles components"—we should prototype using this tool for our specific deployment targets. Update CI/CD pipelines to handle the new repository structure and contribute any necessary patches upstream through Moby's open source collaboration channels.

### Phase 3: Optimization (Weeks 13-24)

Fully leverage the modular architecture by independently upgrading Moby components. Since "as the Docker Engine continues to be split up into more components the Moby project will also be the home for those components," we can adopt individual component releases on their own cadence. Build custom assemblies using the Moby framework's tools to assemble the components into runnable artifacts for a variety of platforms and architectures: bare metal (both x86 and Arm); executables for Linux, Mac and Windows. This phase positions our platform to benefit from the full flexibility of the Moby component model.

## Risk Register

| Risk ID | Risk Description | Severity | PR Reference | Mitigation Strategy |

|---------|-----------------|----------|--------------|---------------------|

| R1 | Repository rename from docker/docker to moby/moby breaks build scripts and dependency references | High | PR changes the README and kicks off the process of breaking up the engine under Moby | Automated find-and-replace across all CI configs; dual-registry caching during transition |

| R2 | Component fragmentation leads to version incompatibility between independently released Moby components | High | As the Docker Engine continues to be split up into more components | Pin component versions in assemblies; maintain compatibility matrix; use the moby CLI tool assembly specifications |

| R3 | Loss of upstream community focus as contributions migrate from Docker to Moby | Medium | Docker is transitioning all of its open source collaborations to the Moby project going forward | Assign dedicated engineers to Moby project participation; monitor both old and new issue trackers |

| R4 | Increased operational complexity from managing multiple component lifecycles instead of one Docker release | Medium | Docker product will be assembled from components that are packaged by the Moby project | Invest in automation for component updates; maintain internal component registry with tested combinations |

| R5 | Confusion among engineering teams about the distinction between Docker the product and Moby the project | Low | PR explicitly states relationship: Docker is staying exactly the same from a user's perspective while Moby is the framework | Internal documentation and training sessions; clear naming conventions in internal tooling |

## Recommendations

1. **Immediate Repository Reference Update**: All internal tooling, CI/CD configurations, and documentation referencing docker/docker should be updated to moby/moby within the next sprint. The PR confirms this rename is the first step in the transition and kicks off the process of breaking up the engine under Moby.

2. **Establish Moby Component Tracking**: Create an internal registry of Moby components and their version compatibility. Since Docker will eventually be assembled from components that are packaged by the Moby project, understanding the component dependency graph is essential for long-term platform stability.

3. **Prototype the Moby CLI Tool**: Allocate engineering time to evaluate the moby command-line tool for assembling container systems. The PR states it currently assembles bootable OS images, but soon it will also be used by Docker for assembling Docker out of components. Early adoption will give us a competitive advantage in customizing our container platform.

4. **Participate in Moby Open Source**: As Docker is transitioning all of its open source collaborations to the Moby project going forward, we should redirect our upstream contributions to the Moby project. This ensures our patches and features are incorporated into the evolving component ecosystem.

5. **Dual-Track Testing Strategy**: Maintain testing against both the current Docker releases and emerging Moby component assemblies. Since the monolithic docker repo eventually ceases to exist, instead being assembled from a set of components, we must validate our platform against both the legacy and future architectures during the transition period.
