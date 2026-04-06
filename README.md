# Ideological Drift in Recommendation Networks
### A graph-based analysis of polarization in social media systems

This repository contains all necessary code, dependencies and documentation for the following assignment. The goal for this assignment is to determine whether algorithmic recommendation systems on various media platforms (Instagram, Youtube, X (formerly Twitter), etc.) push users towards more extreme political content. Gathering and analyzing data with code, I aim to determine if the aforementioned assumption is correct, determine any possible alternatives, weighing tradeoffs, and develop different ways or solutions to combat the negative sides of algorithmic polarization in media.

## Purpose

- What problem are you solving?
    - This problem exists to determine whether algorithmic recommendation systems structurally amplify political polarization by guiding users towards more extreme political content. Is polarization an emergent property of the network structure itself, and does simply following recommendations produce ideological drift?
- Why does this problem matter?
    - If recommendation systems do indeed push users towards more extreme political content, exposure to diverse viewpoints increase, users following these chains are more politically rigid and polarized, which directly affects voting behavior, public discourse, and trust in United States institutions.

- What is the intended outcome?
    - The goal of this project is to determine whether **ideological drift** emerges from the structure of the recommendation network itself.

    - We aim to:
        - Measure whether users navigating recommendations tend to move toward more extreme political positions over time  
        - Identify whether the network exhibits **assortative structure** (i.e., content recommending ideologically similar content)  
        - Evaluate whether polarization can arise as a **structural property of the system**, rather than solely from user behavior  
    - This project is exploratory. Possible outcomes include:
        - **Evidence of drift toward extremes**, suggesting recommendation systems may amplify polarization  
        - **Evidence of clustering without drift**, indicating the presence of echo chambers  
        - **No significant structural effect**, suggesting user behavior may play a larger role  


## Current Status
Project status: data acquired, preparing for implementation.

Current completed setup:
- Git repository initialized
- Root .gitignore added (includes data file exclusions)
- Living [README.md](./README.md) added
- Initial project plan created
- System design and stack selection documented
- **Dataset acquired:** Recfluence (Ledwich & Zaitsev) — YouTube political recommendation network data

## Project Goal

The goal of this project is to help researchers analyze the effects of recommendation systems on political content exposure by providing a graph-based simulation of recommendation networks and user navigation.

The definition of success means being able to measure whether users following recommendations tend to drift toward more extreme political content, and to identify structural patterns such as *ideological clustering* (content with similar political viewpoints are more likely to be connected in the network.) or *echo chambers* (repeatedly exposed to the same type of viewpoint) within the network.

## Problem Statement

Recommendation systems may steer users toward ideologically similar or more extreme political content while reducing exposure to cross-cutting viewpoints. This creates uncertainty for researchers, policymakers, and platform users, because it is difficult to tell whether polarization is being driven mainly by user preference, by the structure of recommendation networks, or by both. If this remains poorly understood, platforms and policymakers will have limited evidence for addressing algorithmic amplification, filter bubbles, and the broader effects of online polarization on public discourse.


## Users
Primary User: 
A researcher or student who needs a reproducible way to model recommendation networks and measure whether recommendation paths show ideological drift.

Secondary User:
A policy analyst or interested reader who needs interpretable evidence about whether recommendation network structure may reinforce ideological clustering or exposure to extreme content.

## MVP Scope
MVP = minimal viable product
- locks in what version 1 **must** do

Version 1 must:
- intake the Recfluence recommendation network dataset (CSV files: channel metadata, recommendation edges, ideology classifications)
    - *without a graph to analyze, no analysis can happen*
- represent the platform as a directed graph of content nodes and recommendation edges      
    - *graphs would be the obvious choice of data structure for recommendation chains as each recommendation is a directional link from video to the next*
- someway assign an idealogical label or score to content nodes
    - *the Recfluence dataset provides Left/Center/Right classifications (coded as −1, 0, +1) — these map directly to this requirement*
- simulate user movement through recommendation paths over multiple steps
    -  *this is the core experiment: what happens when someone follows the algorithm?*
- measure whether those paths show ideological drift toward more extreme positions 
    - *this is the primary research question*
- compute at least one structural polarization metric such as assortativity or clustering
- produce interpretable outputs: summary tables, plots, or simple network visualizations

This project will not include:
- real-time scraping from every social media platform as *API access is unreliable and rate-limited; static datasets are sufficient to answer the research question*
- a polished public-facing web application 
- strong causal claims about all user behavior online 
- personalized behavioral modeling for many user types  
    - *version 1 treats the "user" as a generic walker on the graph; individual differences might be a later concern for future research*
- production-scale deployment or live dashboards

## Core Features
Each feature maps to one distinct responsibility in the project. Keeping feature's
separation of concern means each piece can be built, tested, and debugged on its own before being
combined into the full workflow.


- **Network Constructing** — build a directed graph from recommendation relationships between pieces of content. 
- **Ideology Scoring** — assigns or imports ideological position values for each content node. 
- **Navigation Simulation** — models how a user follows recommendations across multiple steps, recording the ideology score at each hop. 
- **Drift Analysis** — measures whether recommendation paths move users toward ideological extremes over time.      
    - *This directly answers the primary research question.*
- **Polarization Metrics** — computes any structural indicators such as assortativity, clustering coefficients, and echo-chamber strength. 
- **Results Output** — generates summary statistics, plots, and analysis-ready findings. 

## Success Criteria
Success criteria turn vague ambitions into checkable statements. Each criterion below
is written so that at the end of the project you can answer **yes or no** — that is the
whole point. If you cannot tell whether a criterion has been met, the criterion is too
vague and should be rewritten.

- Researchers can move from input data to analysis results through a clear, repeatable workflow — *reproducibility is a core requirement of any research project*
- The system can report whether recommendation paths show measurable ideological drift 
- The system can compute at least one structural polarization measure on the network
- The project produces interpretable outputs (tables, plots, network visualizations) that support a written analysis — *outputs must be understandable to someone who did not run the code*
- The methodology, assumptions, and limitations are documented clearly enough for an academic audience
- The repository is understandable to someone encountering the project for the first time

## Repository Structure

**Why plan the structure before writing code?** A clear folder layout means every file
has an obvious home. This prevents the common failure mode where scripts, data, and
documentation all pile up in the root directory until the project becomes unnavigable.

The structure below is *intended* — folders will be created as each phase begins.

| Path | Purpose | Status |
|------|---------|--------|
| `README.md` | top-level overview of the project | exists |
| `.gitignore` | files and generated artifacts not tracked by Git | exists |
| `docs/` | planning, architecture decisions, methodology notes | exists |
| `data/` | source datasets and data provenance documentation | exists |
| `src/` | core analysis code (modules, scripts) | planned — created after stack is chosen |
| `tests/` | automated validation for analysis logic and metrics | planned — created after stack is chosen |
| `results/` | generated charts, tables, and summary artifacts | planned |


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

Setup instructions will be finalized after the analysis stack is chosen.

## Next Steps

1. **Scaffold the repository structure** — create `src/`, `tests/`, and `results/`
   directories with placeholder files matching the layout in [docs/SYSTEM_DESIGN.md](./docs/SYSTEM_DESIGN.md).
2. **Set up the Python environment** — create virtualenv, install dependencies, write
   `requirements.txt`.
3. **Create a small synthetic test dataset** — a hand-crafted CSV with ~20 nodes and
   known properties so modules can be tested independently of the real data.
4. **Build the first vertical slice** — `graph_builder.py` loads the Recfluence CSVs,
   constructs a NetworkX DiGraph, and computes one metric end-to-end.


## Dataset

### Source
**Recfluence** by Mark Ledwich & Anna Zaitsev
- Repository: [github.com/markledwich2/Recfluence](https://github.com/markledwich2/Recfluence)
- License: MIT
- Data generated: 2023-02-18

### What the dataset contains
The Recfluence project collected YouTube recommendation data and politically classified ~7,000 channels using multiple independent reviewers. The data was collected by scraping YouTube's recommendations from a logged-out US IP address for channels with 10k+ subscribers focused on US political or cultural commentary.

### Files used in this project

| File | Role | Rows | Description |
|------|------|------|-------------|
| `vis_channel_stats.csv` | **Node data** | 7,079 | Channel metadata: `CHANNEL_ID`, `CHANNEL_TITLE`, `LR` (Left/Center/Right), `RELEVANCE`, subscriber counts, view stats |
| `vis_channel_recs2.csv` | **Edge data** | 401,384 | Directed recommendation edges: `FROM_CHANNEL_ID` → `TO_CHANNEL_ID`, weighted by `RELEVANT_IMPRESSIONS_DAILY` and `PERCENT_OF_CHANNEL_RECS` |

### Key statistics

| Metric | Value |
|--------|-------|
| Total channels (nodes) | 7,079 |
| Total recommendation edges | 401,384 |
| Channels with ideology labels | 7,079 (100% coverage) |
| Self-loops (channel recommends itself) | 6,942 |
| Left channels | 925 |
| Center channels | 2,120 |
| Right channels | 4,034 |

### How this project maps

| Project concept | Dataset field |
|-----------------|---------------|
| Graph nodes | `CHANNEL_ID` from `vis_channel_stats.csv` |
| Graph edges | `FROM_CHANNEL_ID` → `TO_CHANNEL_ID` from `vis_channel_recs2.csv` |
| Ideology score (numeric) | `LR` column: L=−1, C=0, R=+1 |
| Edge weight | `RELEVANT_IMPRESSIONS_DAILY` — allows weighted random walks |


### Limitations of this data
- **Logged-off recommendations only** — reflects YouTube's baseline algorithm, not personalized results. This is acceptable for studying structural properties of the network.
- **Time period** — data reflects YouTube's recommendation behavior through early 2023. The algorithm has changed since then.
- **US-centric** — channels and scraping were focused on US political content. Findings may not generalize to other countries or topics.
- **Right-skew in channel count** — 4,034 Right vs. 925 Left channels. This could reflect the actual landscape of US political YouTube or a collection bias. A more advanced analysis should account for this asymmetry.
