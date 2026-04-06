# System Design — Ideological Drift in Recommendation Networks

> **Audience:** Someone who has never designed a software system before.
> Every decision in this document is explained from scratch, including
> *why* the decision matters, *what alternatives exist*, and *what the
> tradeoffs are*.

---

## Table of Contents

1. [What Is System Design and Why Does It Matter?](#1-what-is-system-design-and-why-does-it-matter)
2. [How to Think About Choosing a Stack](#2-how-to-think-about-choosing-a-stack)
3. [What This Project Needs to Do](#3-what-this-project-needs-to-do)
4. [Component Breakdown](#4-component-breakdown)
5. [Language Choice](#5-language-choice)
6. [Library and Tool Choices](#6-library-and-tool-choices)
7. [Data Format Decisions](#7-data-format-decisions)
8. [Project Layout](#8-project-layout)
9. [How the Pieces Fit Together (Data Flow)](#9-how-the-pieces-fit-together-data-flow)
10. [Testing Strategy](#10-testing-strategy)
11. [What We Are NOT Building (and Why)](#11-what-we-are-not-building-and-why)
12. [Summary of Decisions](#12-summary-of-decisions)
13. [Glossary](#13-glossary)

---

## 1. What Is System Design and Why Does It Matter?

System design is the process of deciding **what parts** a piece of software will have,
**how they connect**, and **what technology** they will be built with — *before* you start
writing code.

### Why bother?

Think of it like an architect drawing a blueprint before a construction crew pours
concrete. If the architect skips the blueprint the crew will start building rooms without
knowing how they connect, and eventually someone discovers the plumbing was supposed to go
where they already poured a wall. Fixing it now costs almost nothing (erasing a line on
paper). Fixing it after the concrete sets is expensive and painful.

In software the same dynamic applies:

| When you discover a problem | Cost to fix |
|-----------------------------|-------------|
| During design (now) | Change a sentence in a document |
| During early coding | Rewrite one module |
| After everything is built | Rewrite large parts and re-test everything |

Good system design reduces wasted effort, makes the project easier to debug, and means
that when you *do* start coding you know exactly what to build first.

### What does system design include?

For a project this size it includes four things:

1. **Component breakdown** — what distinct pieces of work exist
2. **Technology selection** — what language, libraries, and tools to use
3. **Data flow** — how information moves from input to output
4. **Interfaces** — how components talk to each other (what goes in, what comes out)

We do *not* need the kind of system design that large companies worry about (load
balancers, microservices, database replication). This is a single-user research project,
so the design stays simple.

---

## 2. How to Think About Choosing a Stack

A "stack" is the combination of **language + libraries + tools** used to build a project.

### The wrong way to choose

Many beginners choose based on popularity ("everyone uses X") or novelty ("Y just came
out"). This often leads to fighting the tools instead of doing the actual work.

### The right way to choose

Ask three questions in order:

1. **What does the project need to do?** — list the core operations (graph analysis,
   simulation, statistics, visualization).
2. **Which ecosystems have mature, well-documented tools for those operations?** — mature
   means the library has been around long enough to be stable and to have answers on Stack
   Overflow when you get stuck.
3. **Which of those ecosystems do I (or my team) already know, or can learn fastest?** —
   learning a new language *and* a new domain at the same time doubles the difficulty.

The goal is to pick the **simplest correct fit**, not the most impressive-sounding option.

---

## 3. What This Project Needs to Do

From the MVP scope defined in the README, the project must perform these operations:

| Operation | Description |
|-----------|-------------|
| **Graph construction** | Build a directed graph where nodes are content items and edges are recommendations |
| **Attribute assignment** | Attach an ideology score (a number) to each node |
| **Path simulation** | Walk through the graph following recommendation edges for N steps, recording the score at each step |
| **Drift measurement** | Determine whether those walks trend toward ideological extremes |
| **Structural metrics** | Compute graph-level statistics like assortativity and clustering |
| **Visualization** | Draw the network and plot drift trajectories |
| **Reporting** | Produce summary tables and figures for a written analysis |

***Nothing in that list requires a web server, a database, a front-end framework, or
real-time processing. Everything operates on a static dataset in memory.***

---

## 4. Component Breakdown

Each operation above becomes a **component** — a self-contained piece of code with a
clear input and output.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Data Loader │────▶│ Graph Builder│────▶│ Ideology Scorer  │
└──────────────┘     └──────────────┘     └──────────────────┘
                                                   │
                                                   ▼
                    ┌──────────────┐     ┌──────────────────┐
                    │ Drift        │◀────│ Path Simulator   │
                    │ Analyzer     │     └──────────────────┘
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌───────────┐  ┌──────────┐
      │ Metrics  │  │ Visualizer│  │ Reporter │
      └──────────┘  └───────────┘  └──────────┘
```

### Why must we separate our components?

**Modularity.** If you put everything in one giant script, a bug in the visualization
code can block you from testing whether your simulation logic is correct. Separating
components lets me build and verify each piece independently. They also make it
easier for someone else (or future-you) to understand the project, because each file has
one job.

### What if I just wrote one big script?

I could, and for very small experiments people sometimes do. The tradeoffs:

| Approach | Pros | Cons |
|----------|------|------|
| One script | Simpler to start; everything in one place | Hard to debug; hard to test parts independently; painful to modify later |
| Modular components | Each piece is testable alone; easier to debug; easier to extend | Slightly more setup up front; need to think about how components connect |

For a project with 6+ distinct operations, modular wins. The upfront cost is small (a few
extra files and import statements) and the payoff is large (you can test the graph builder
before the simulation even exists).

---

## 5. Language Choice

### Python

| Factor | Assessment |
|--------|------------|
| Graph libraries | **NetworkX** — the most widely used graph library in research. Mature, well-documented, handles directed graphs, node attributes, and all common graph metrics out of the box. |
| Statistics | **NumPy, SciPy, pandas** — the standard scientific Python stack. Every statistics tutorial you find will use these. |
| Visualization | **Matplotlib, Seaborn, Plotly** — from simple plots to interactive network diagrams. |
| Learning curve | Gentle. Python reads almost like English and has the largest collection of beginner tutorials of any language. |
| Community | Enormous. If you hit an error, someone has likely asked about it on Stack Overflow. |
| Drawback | Slower than compiled languages for very large datasets (millions of nodes). For this project's scale (~7,000 nodes, ~400,000 edges), irrelevant. |


### Recommendation: Python

Python has the **best combination of graph tooling, scientific libraries, visualization
options, community support, and learning-friendliness** for this kind of project. You get
NetworkX (purpose-built for this), the entire scientific Python ecosystem, and the fastest
path from "I have an idea" to "I have a result."

### What would change this recommendation?

- If the dataset were **billions of edges**, you'd need a compiled language or a
  specialized graph database (e.g., Neo4j). Our dataset is ~7,000 nodes and ~400,000
  edges — well within Python's comfortable range.
- If the deliverable were a **live interactive web dashboard**, JavaScript would make more
  sense for the front end (but you'd still likely use Python for the analysis backend).
- If the project were part of a **statistics-heavy thesis** with advanced modeling (mixed
  effects, Bayesian inference), R's statistical depth might edge out Python. For the
  graph-centric analysis we're doing, Python + NetworkX is the better fit.

---

## 6. Library and Tool Choices

Assuming Python, here are the specific libraries mapped to each component, with rationale
and alternatives.

### 6.1 Graph Construction and Analysis — NetworkX

**What it does:** Provides data structures for directed and undirected graphs, algorithms
for shortest paths, centrality, clustering, assortativity, community detection, and more.

**Why this one:**
- Purpose-built for the exact kind of analysis we are doing.
- Nodes can carry arbitrary attributes (like an ideology score) with no extra work.
- Every graph metric we need (assortativity, clustering coefficient, path analysis) is a
  single function call.
- The documentation includes academic references, so you can cite the algorithm you're
  using.

**Alternatives considered:**

| Library | Why not |
|---------|---------|
| **igraph (Python bindings)** | Faster on very large graphs, but the API is less Pythonic and the documentation assumes more background knowledge. For our scale, the speed difference is negligible. |
| **graph-tool** | Very fast (C++ backend), but harder to install (requires C++ compilation), less beginner-friendly, and narrower community. |
| **PyTorch Geometric / DGL** | Designed for graph neural networks and machine learning on graphs. Massive overkill — we need classical graph metrics, not deep learning. |

### 6.2 Numerical and Statistical Operations — NumPy + SciPy

**What they do:** NumPy provides fast array operations. SciPy adds statistical tests,
distributions, and scientific computing routines.

**Why these:**
- Industry and academic standard. Every tutorial, textbook, and Stack Overflow answer
  about scientific Python assumes you have NumPy.
- We will need basic stats (means, standard deviations, statistical significance tests)
  to determine whether observed drift is meaningful or just random noise.

**Alternatives considered:**

| Library | Why not |
|---------|---------|
| **Pure Python (no NumPy)** | Possible for very simple math, but dramatically slower on arrays and missing statistical test functions. Not worth it. |
| **Polars** | Newer, faster DataFrame library. Nice, but pandas is more widely documented and integrates more smoothly with the rest of the scientific stack. Premature optimization for this project. |

### 6.3 Data Handling — pandas

**What it does:** Provides DataFrames — essentially spreadsheets in code — for loading,
filtering, transforming, and exporting tabular data.

**Why this one:**
- Recommendation data and simulation results are naturally tabular (rows of edges, rows
  of path steps).
- pandas makes it trivial to load CSVs, filter rows, compute group statistics, and export
  results.

**Alternatives considered:**

| Library | Why not |
|---------|---------|
| **csv (standard library)** | Works, but you end up reimplementing filtering, grouping, and aggregation by hand. pandas does it in one line. |
| **Polars** | Faster for large datasets. For our scale, the speed gain doesn't offset the smaller documentation base for beginners. |

### 6.4 Visualization — Matplotlib + Seaborn (+ optional NetworkX drawing)

**What they do:** Matplotlib is the foundational Python plotting library. Seaborn adds
statistical plot types and better default aesthetics on top of Matplotlib.

**Why these:**
- Matplotlib can draw anything: line plots for drift trajectories, bar charts for
  metrics, and even basic network diagrams via NetworkX's drawing module.
- Seaborn makes common statistical plots (distributions, heatmaps) look good with minimal
  effort.
- Both produce publication-quality static images suitable for an academic paper or
  assignment.

**Alternatives considered:**

| Library | Why not |
|---------|---------|
| **Plotly** | Creates interactive, zoomable plots. Impressive, but adds complexity (HTML files, browser rendering) that we don't need for a static report. Good candidate for version 2 if you want an interactive dashboard later. |
| **Bokeh** | Similar to Plotly. Interactive, browser-based. Same tradeoff: more complex than what version 1 needs. |
| **D3.js** | JavaScript only. Would mean maintaining two languages. Not practical here. |

### 6.5 Testing — pytest

**What it does:** Discovers and runs test functions, reports pass/fail, shows helpful
error messages.

**Why this one:**
- The de facto standard for Python testing.
- Tests are just functions whose names start with `test_`. No boilerplate classes needed.
- Excellent error output: when a test fails, pytest shows you exactly what the expected
  vs. actual values were.

**Alternatives considered:**

| Library | Why not |
|---------|---------|
| **unittest (standard library)** | Built into Python, but requires class-based test structure that adds boilerplate. pytest can run unittest-style tests anyway, so there's no downside to starting with pytest. |
| **nose2** | Largely abandoned. pytest is the community standard now. |

### 6.6 Environment and Dependency Management — venv + pip + requirements.txt

**What it does:** `venv` creates an isolated Python environment so project dependencies
don't collide with the rest of your system. `pip` installs packages. `requirements.txt`
records exact versions so anyone can replicate your environment.

**Why this approach:**
- Built into Python — no extra installation.
- Simple to understand: `python -m venv .venv`, `pip install -r requirements.txt`, done.
- `requirements.txt` is the most universally understood dependency file in the Python
  ecosystem.

**Alternatives considered:**

| Tool | Why not (for now) |
|------|-------------------|
| **conda** | Common in data science. Handles non-Python dependencies (like C libraries) better. But it adds a large installation (Anaconda/Miniconda) and its own learning curve. If we hit a library that requires conda, we can switch. |
| **Poetry** | Modern dependency manager with a lock file and pyproject.toml. Excellent for published packages. Overkill for a single-user research project where `requirements.txt` does the job. |
| **Docker** | Containers guarantee the exact same environment everywhere. Great for deployment. Excessive for a research project that runs on one machine. |
| **pipenv** | Combines venv + pip with a Pipfile. Fallen out of favor; slower and buggier than alternatives. |

---

## 7. Data Format Decisions

### Input data: CSV files in `data/`

**What:** The project uses the **Recfluence** dataset (Ledwich & Zaitsev), a collection
of CSV files describing YouTube political channels, their ideology classifications, and
the recommendation relationships between them.

**Specific files:**

| File | Role | Key columns |
|------|------|-------------|
| `vis_channel_stats.csv` | **Node table** (7,079 rows) | `CHANNEL_ID`, `CHANNEL_TITLE`, `LR` (L/C/R), `RELEVANCE`, subscriber/view stats |
| `vis_channel_recs2.csv` | **Edge table** (401,384 rows) | `FROM_CHANNEL_ID`, `TO_CHANNEL_ID`, `RELEVANT_IMPRESSIONS_DAILY`, `PERCENT_OF_CHANNEL_RECS` |

**How nodes and edges connect:** Every `FROM_CHANNEL_ID` and `TO_CHANNEL_ID` in
the edge table has a matching row in the node table (100% coverage verified), so
the graph can be fully constructed with ideology labels on every node.

**Ideology encoding:** The `LR` column contains `L`, `C`, or `R`. For numerical
analysis these map to −1, 0, +1 respectively. This is the score used for drift
measurement and structural analysis.

**Why CSV:**
- Human-readable. You can open it in any text editor or spreadsheet program to inspect it.
- Universal. Every language and tool can read CSV.
- Simple. No schema definition, no server, no special reader. `pandas.read_csv()` and
  you're done.

**Alternatives considered:**

| Format | Tradeoffs |
|--------|-----------|
| **JSON** | Good for nested or hierarchical data. Recommendation edges are flat and tabular, so JSON adds verbosity without benefit. |
| **Parquet** | Binary columnar format. Fast for huge files. Unreadable in a text editor. Overkill for our data size. |
| **SQLite database** | Good if you need complex queries. We don't — we load the whole dataset into memory once. A database adds setup complexity for no gain. |
| **GraphML / GML / GEXF** | Graph-specific file formats. NetworkX can read them. Downside: harder to inspect manually and less familiar to most people. We can always *export* to GraphML for graph visualization tools while keeping the source data as CSV. |

### Output data: CSV tables + PNG/SVG images in `results/`

**Why:**
- CSV for table outputs (metrics, simulation logs) — easy to load into any tool for
  further analysis.
- PNG/SVG for figures — can be directly embedded in a report or paper. SVG is vector
  (scales without pixelation); PNG is raster (universally viewable).

---

## 8. Project Layout

Here is the intended directory structure once the stack is in place, with the rationale
for each folder:

```
project/
├── README.md               ← You are here. Top-level overview.
├── .gitignore              ← Keeps generated files out of version control.
├── requirements.txt        ← Pinned dependency list for reproducibility.
├── docs/                   ← All planning and decision documents.
│   ├── AI_ASSISTED_BUILD_PLAN.md
│   └── SYSTEM_DESIGN.md    ← This file.
├── data/                   ← Input datasets (CSVs) and any raw source files.
│   └── README.md           ← Documents where data came from and how to obtain it.
├── src/                    ← All analysis source code.
│   ├── __init__.py         ← Makes src/ a Python package (can be empty).
│   ├── graph_builder.py    ← Network construction from edge/node data.
│   ├── ideology.py         ← Ideology score assignment and estimation.
│   ├── simulator.py        ← Random-walk / user-path simulation.
│   ├── metrics.py          ← Assortativity, clustering, drift statistics.
│   └── visualize.py        ← Plotting and network drawing.
├── tests/                  ← Automated tests (pytest).
│   ├── test_graph_builder.py
│   ├── test_ideology.py
│   ├── test_simulator.py
│   └── test_metrics.py
└── results/                ← Generated output (not tracked in Git).
    ├── figures/
    └── tables/
```

### Why this layout?

- **`src/` separate from `tests/`:** Keeps production code and test code from tangling.
  pytest auto-discovers tests in `tests/`.
- **`data/` with its own README:** Data provenance (where it came from, how it was
  collected, any licensing) is critical for academic work. A README inside `data/`
  documents this in the most obvious place.
- **`results/` not tracked in Git:** Generated artifacts should be regenerable from code +
  data. Tracking them in Git bloats the repository and creates merge conflicts on binary
  files.
- **`docs/` for non-code documents:** Keeps the root directory clean. Architecture
  decisions, methodology notes, and build plans all go here.

---

## 9. How the Pieces Fit Together (Data Flow)

This describes the journey data takes from raw input to final output.

```
CSV files in data/
(vis_channel_stats.csv = nodes, vis_channel_recs2.csv = edges)
       │
       ▼
┌──────────────────┐
│  graph_builder.py │  Reads CSVs → creates a NetworkX DiGraph
└────────┬─────────┘
         │  DiGraph object (nodes + edges)
         ▼
┌──────────────────┐
│   ideology.py    │  Maps LR → numeric score (L=−1, C=0, R=+1) as node attribute
└────────┬─────────┘
         │  DiGraph with scored nodes
         ▼
┌──────────────────┐
│   simulator.py   │  Runs N random walks of K steps, records the trajectory
└────────┬─────────┘
         │  List of walk trajectories (node IDs + scores per step)
         ▼
┌──────────────────┐
│    metrics.py    │  Computes drift magnitude, assortativity, clustering, etc.
└────────┬─────────┘
         │  Metric results (numbers + tables)
         ▼
┌──────────────────┐
│   visualize.py   │  Draws network diagrams, drift trajectory plots, summaries
└──────────────────┘
         │
         ▼
   results/ folder (PNGs, SVGs, CSVs)
```

### Why this order?

Each step depends only on the output of the step before it. This is called a **pipeline**
and it is the simplest possible data flow architecture. You don't need message queues,
event systems, or callbacks. Data flows in one direction: **in → process → out**.

### What is the alternative?

For larger or more interactive systems you might use:

| Architecture | When to use | Why not here |
|--------------|-------------|--------------|
| **Pipeline (what we're using)** | Batch analysis on a static dataset. Input → process → output. | — |
| **Event-driven** | Systems reacting to real-time events (user clicks, incoming data streams). | We have no real-time events. |
| **Client-server** | When multiple users access the system simultaneously via a network. | Single user, local execution. |
| **Microservices** | When different parts of the system need to scale independently, be deployed on separate servers, or be written in different languages. | We have one user, one machine, one language. Microservices would add network overhead and operational complexity for zero benefit. |

The pipeline is the right choice because our workload is: load data once → process it →
save results. No interactivity, no concurrency, no scaling concerns.

---

## 10. Testing Strategy

### Why test at all?

Without tests, the only way to know if your code works is to run the entire pipeline
manually and eyeball the output. This fails in practice because:

- You won't notice subtle numerical bugs (e.g., off-by-one in path length).
- Changing one component might silently break another.
- You'll waste time re-checking things that used to work.

Automated tests catch these problems instantly.

### What kind of tests?

| Type | What it checks | Example |
|------|---------------|---------|
| **Unit test** | One function in isolation | Does `compute_assortativity()` return the correct value on a known graph? |
| **Integration test** | Two or more components working together | Does graph_builder → ideology → simulator produce a valid trajectory? |
| **Regression test** | That a previously-fixed bug stays fixed | After fixing an edge-case in the random walk, a test ensures it never re-breaks. |

For this project, **unit tests are the priority**. Each module gets its own test file.
Integration tests will be added once the pipeline is wired end-to-end.

### How to write a good test

A good test follows the **Arrange → Act → Assert** pattern:

1. **Arrange:** Set up the input (e.g., create a small graph with known properties).
2. **Act:** Call the function you're testing.
3. **Assert:** Check that the output matches what you expected.

If the test is hard to write, it often means the function is doing too many things and
should be split up. Tests are a design feedback mechanism, not just a safety net.

---

## 11. What We Are NOT Building (and Why)

Explicitly listing what we are *not* building is just as important as listing what we are.
This prevents scope creep and clarifies the project's boundaries.

| Not building | Why not |
|--------------|---------|
| **A web application** | Adds front-end code (HTML, CSS, JavaScript), a web server, and deployment concerns. None of this helps answer the research question. |
| **A database** | The entire dataset fits in memory. A database adds installation, schema management, and query complexity for zero analytical benefit at this scale. |
| **Real-time data collection** | API access to platforms is rate-limited, requires authentication keys, and changes frequently. Static datasets let us focus on analysis instead of data engineering. |
| **Machine learning models** | The project measures structural properties of a graph. ML would be appropriate if we were *predicting* ideology scores, but we are *assigning* them from a known source or a simple heuristic. |
| **Docker containers** | Reproducing the environment with `venv` + `requirements.txt` is sufficient. Docker adds a layer of abstraction that is unnecessary for a single-machine, single-user project. |
| **CI/CD pipeline** | Continuous integration is valuable for team projects with frequent merges. For a solo research project, running `pytest` locally before each commit achieves the same goal with no setup. |

---

## 12. Summary of Decisions

| Decision | Choice | Key reason |
|----------|--------|------------|
| Language | Python | Best graph + scientific ecosystem for this task |
| Graph library | NetworkX | Purpose-built for graph analysis; handles all needed metrics |
| Data manipulation | pandas | Tabular data handling in one line |
| Numerics / stats | NumPy + SciPy | Industry standard; statistical tests for significance |
| Visualization | Matplotlib + Seaborn | Publication-quality static plots |
| Testing | pytest | De facto Python testing standard; minimal boilerplate |
| Environment | venv + pip + requirements.txt | Built into Python; simplest reproducible setup |
| Data format | CSV in, CSV + PNG/SVG out | Human-readable, universal, no extra tooling |
| Architecture | Linear pipeline | Simplest correct fit for batch analysis on static data |

---

## 13. Glossary

Terms used in this document, explained without jargon.

| Term | Meaning |
|------|---------|
| **Directed graph (digraph)** | A graph where edges have a direction. A → B does not imply B → A. Recommendations are naturally directed: platform recommends content B after content A. |
| **Node** | A single item in a graph. In our case, a piece of content (a video, article, post). |
| **Edge** | A connection between two nodes. In our case, a recommendation link from one content item to another. |
| **Assortativity** | A measure of whether nodes with similar attributes tend to connect to each other. High assortativity by ideology means the network clusters by political position. |
| **Clustering coefficient** | A measure of how much nodes tend to form tightly connected groups. High clustering means recommendations keep you in a small neighborhood of content. |
| **Random walk** | A process of moving through a graph by randomly choosing an outgoing edge at each step. Used here to simulate a user following recommendations. |
| **Ideological drift** | A tendency for the ideology score to change (usually toward an extreme) as a user follows a sequence of recommendations. |
| **Echo chamber** | A situation where a user is repeatedly exposed to the same type of viewpoint because the network structure does not offer cross-cutting recommendations. |
| **Pipeline** | A software architecture where data flows in one direction through a sequence of processing steps. Step 2 depends on step 1's output, step 3 depends on step 2, and so on. |
| **MVP (Minimum Viable Product)** | The smallest version of the project that produces a useful result. Version 1 = MVP. |
| **venv** | Python's built-in virtual environment tool. Creates an isolated folder of packages so your project doesn't interfere with other Python projects on your machine. |
| **requirements.txt** | A text file listing every Python package the project needs, with version numbers. Anyone can recreate your environment by running `pip install -r requirements.txt`. |
| **pytest** | A Python testing framework. You write small functions that check whether your code behaves correctly. pytest discovers and runs them automatically. |
