# Ideological Drift in Recommendation Networks
### A graph-based analysis of polarization in social media systems

This repository contains all necessary code, dependencies and documentation for the following assignment. The goal for this assignment is to determine whether algorithmic reccomendation systems on various media platforms (Instagram, Youtube, X (formerly Twitter), etc.) push users towards more extreme political content. Gathering and analyzing data with code, I aim to determine if the aforementioned assumption is correct, determine any possible alternatives, weighing tradeoffs, and develop different ways or solutions to combat the negative sides of algorithmic polarization in media.

## Purpose

- What problem are you solving?
    - This problem exists to determine whether algorithmic reccomendation systems structurally amplify political polarization by guiding users towards more extreme political content. Is polarization an emergent property of the network structure itself, and does simply following recommendations produce ideological drift?
- Why does this problem matter?
    - If recommendation systems do indeed push users towards more extreme political content, exposure to diverse viewpoints increase, users following these chains are more politically rigid and polarized, which directly affects voting beahvior, public discourse, and trust in United States institutions.

- What is the intended outcome?
    - The goal of this project is to determine whether **ideological drift** emerges from the structure of the recommendation network itself.

    - I aim to:
        - Measure whether users navigating recommendations tend to move toward more extreme political positions over time  
        - Identify whether the network exhibits **assortative structure** (i.e., content recommending ideologically similar content)  
        - Evaluate whether polarization can arise as a **structural property of the system**, rather than solely from user behavior  
    - This project is exploratory. Possible outcomes include:
        - **Evidence of drift toward extremes**, suggesting recommendation systems may amplify polarization  
        - **Evidence of clustering without drift**, indicating the presence of echo chambers  
        - **No significant structural effect**, suggesting user behavior may play a larger role  


## Current Status
Project status: planning.

Current completed setup:
- Git repository initialized
- Root .gitignore added
- Living [README.md](./README.md) added
- Initial project plan created

## Project Goal

The goal of this project is to help researchers analyze the effects of recommendation systems on political content exposure by providing a graph-based simulation of recommendation networks and user navigation.

The definition of success means being able to measure whether users following recommendations tend to drift toward more extreme political content, and to identify structural patterns such as *ideological clustering* (content with similar political viewpoints are more likely to be connected in the network.) or *echo chambers* (repeatedly exposed to the same type of viewpoint) within the network.

## Problem Statement

Recommendation systems may steer users toward ideologically similar or more extreme political content while reducing exposure to cross-cutting viewpoints. This creates uncertainty for researchers, policymakers, and platform users, because it is difficult to tell whether polarization is being driven mainly by user preference, by the structure of recommendation networks, or by both. If this remains poorly understood, platforms and policymakers will have limited evidence for addressing algorithmic amplification, filter bubbles, and the broader effects of online polarization on public discourse.


## Users
Primary User: 
A researcher or student who needs a reproducable way to model recommendation networks and measure whether recommendation paths show idealogical drift.

Secondary User:
A policy analyst or interested reader who needs interpretable evidence about whether recommendation network structure may reinforce ideological clustering or exposure to extreme content.

## MVP Scope
MVP means the smallest useful version of the project.

Write:
- What must version 1 do?
- What can wait until later?

Template:
Version 1 must:
- [required capability]
- [required capability]
- [required capability]

Version 1 will not include:
- [excluded feature]
- [excluded feature]

Example:
Version 1 must:
- ingest or construct a recommendation network dataset
- assign or estimate ideological scores for nodes in the network
- simulate user movement through recommendation paths
- measure whether recommendation paths trend toward ideological extremes
- produce basic visualizations or summary statistics of clustering and drift

Version 1 will not include:
- real-time data collection from every major platform
- a polished production web application
- causal claims about all user behavior on social platforms

## Core Features
Use this section to list the most important features at a high level.

Write:
- Main features only
- One short sentence per feature

Template:
- Feature: [name] - [what it does]
- Feature: [name] - [what it does]

Example:
- Feature: network builder - creates a graph from recommendation relationships between pieces of content
- Feature: ideology scoring - labels or estimates the political position of content nodes
- Feature: drift simulation - models how a user might move through recommendations over multiple steps
- Feature: polarization metrics - computes clustering, assortativity, and movement toward extremes
- Feature: result visualization - shows network structure and summarizes findings in plots or reports

## Success Criteria
Use this section to define how you will judge whether the project is working.

Write:
- What would prove the system is useful?
- What outcomes do you want technically or from the user perspective?

Template:
- Users can [action] without [problem]
- The system can [technical outcome]
- The project meets [assignment or product requirement]

Example:
- A researcher can run the analysis from input data to results using a clear and repeatable workflow
- The system can quantify ideological drift across recommendation paths and report whether drift appears significant
- The system can compute at least one structural polarization measure, such as assortativity or clustering by ideology
- The project produces interpretable outputs, such as tables, graphs, or network visualizations, that support the written analysis
- The project satisfies the assignment requirements with documented methods, assumptions, and limitations

## Repository Structure
How the repository is organized:

Current structure:

- `README.md`: top-level overview of the project
- `.gitignore`: files and generated artifacts not tracked by Git
- `docs/`: planning, architecture, and decision documents


## How We Will Work
This section explains the development process for this repository.

We will work in phases:

1. Set up the project foundation
2. Define requirements and scope
3. Design the architecture
4. Build in small testable steps
5. Debug and validate continuously
6. Document decisions as we go

## Setup Instructions

Write later:
- prerequisites
- install steps
- run steps
- test steps


## Next Steps

Template:
1. [next action]
2. [next action]
3. [next action]



## Notes
Keep this README concise and high level.
Detailed architecture, plans, debugging notes, and decision records should live in `docs`.