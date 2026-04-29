# Project Overview: Ideological Drift in Recommendation Networks

This document is intentionally long.

It is meant to do several jobs at once:

- explain the project
- help both of you understand what is happening 
- serve as a master teaching script 
- account for the meaningful content of the repository so you both can see how the project fits together from top to bottom

## Before The Code

Most people have used a platform that keeps recommending the next thing to watch, click, or read. You open one video, then the platform suggests another. Then another. Then another. At some point, it stops feeling like a single choice and starts feeling like a path.

This repository studies a simple but important question:

When a person keeps following recommendations, does the recommendation system tend to move that person in a predictable ideological direction, and does it tend to move that person toward more extreme political content?

That question matters because public debate about recommendation systems often sounds like this:

- Do algorithms quietly push people left or right?
- Do algorithms make people more extreme over time?
- Are recommendation systems creating *echo chambers*?

This project does not claim to read real viewers directly. Instead, it builds a careful model of the recommendation environment itself. In plain language, it asks:

>> If we treat the recommendation network like a map, and we treat a viewer like a traveler who keeps following the signs the map shows them, where does that traveler tend to end up most of the time?

That simple idea is the whole project.

## The Project

This repository takes a dataset of YouTube political recommendation relationships, turns that dataset into a network, gives each channel a simple ideology score (-1, 0 or +1), simulates many recommendation-following paths through that network, measures how those paths change ideological position and ideological extremity, and then saves figures and tables that help us explain the findings.

That same sentence can be said more simply:

- The project starts with political YouTube channel data.
- It turns the data into a map.
- It lets simulated viewers walk through that map.
- It measures where those viewers drift.
- It turns the results into figures and graph statistical models.

## The Two Main Questions The Project Tries To Answer

1. Do recommendation paths tend to change ideology direction overall?
2. Do recommendation paths tend to increase ideological extremity?

Those two questions are the center of the project.

We should always be coming back to these two questions.

## Figure 1: The Big Picture

**Figure 1: The Flow of the Project**

```text
Real YouTube recommendation data
            |
            v
  Node table + Edge table CSV files
            |
            v
   Directed recommendation graph
            |
            v
   Ideology scores on each channel
            |
            v
 Simulated recommendation-following walks
            |
            v
   Drift and structure calculations and measurements
            |
            v
 Figures, summary tables, and presentation outputs
```

This picture is important because it keeps the project from feeling mysterious.

The repository is doing a sequence of understandable steps through a specfic pipeline:

- raw data becomes a graph
- the graph becomes a scored graph with numerical values associated to each channel (node)
- the scored graph becomes simulated paths
- the simulated paths are then measured
- the measurements become visuals and tables for us to present

That flow is both the conceptual story and the software design.

## Why This Problem Matters

This project matters for at least four reasons.

### 1. Recommendation systems shape information exposure

A person does not need to search for extreme content directly if the platform keeps placing new suggestions in front of them. Recommendations can shape what comes next, and what the viewer ends up seeing.

### 2. Political content matters beyond entertainment

If the content were only about cooking or music, the stakes would still be interesting. But political content affects how people understand public life, social conflict, and democratic debate.

### 3. People often argue about algorithmic influence without a clear model

Public conversations about algorithms are often emotional and vague. This project tries to replace some of that vagueness with a concrete experiment.

### 4. The project is understandable

A good project does not only ask an interesting question. It asks a question in a way that can be defended, explained, and reproduced. This repository is designed to be teachable.

## Where The Data Comes From

The project is built around the Recfluence dataset by Mark Ledwich and Anna Zaitsev.

According to [../data/README.md](../data/README.md), the important provenance details are:

- source project: Recfluence
- license: MIT
- data generated: 2023-02-18
- source repository: https://github.com/markledwich2/Recfluence
- shared data download link documented in the data README

The repository uses recommendation data collected from **logged-off** YouTube browsing, which matters because the project is modeling the platform's default recommendation environment rather than a personally tailored account history, which is much more technically complex.

That is worth repeating in plain language:

It is saying, "this is what the default recommendation environment looked like in this dataset when no personalized login history are steering the results."

## The Data Directory, Explained Slowly

The `data/` folder contains both the files the current pipeline directly uses and additional files that help explain the larger Recfluence dataset. This should not be looked at by you guys.

### The Main Data Files The Pipeline Uses Directly

The pipeline directly depends on two CSV files.

1. `data/vis_channel_stats.csv`
2. `data/vis_channel_recs2.csv`

These two files are enough to build the graph used by the experiment.


## Figure 2: From CSV Files To A Usable Experiment

**Figure 2: Data-To-Experiment Flow**

```text
vis_channel_stats.csv          vis_channel_recs2.csv
     |                               |
     |                               |
     +-----------> graph_builder.py <+
                         |
                         v
              Directed recommendation graph
                         |
                         v
                  ideology.py adds scores
                         |
                         v
                simulator.py runs walks
                         |
                         v
                 metrics.py measures drift
                         |
                         v
                visualize.py writes outputs to figures in /results
```

This figure shows the pipeline as the software actually uses it.

It is helpful in a presentation because it connects the abstract idea of "an experiment" to concrete files and stages.

## The Core Ideas, Explained Only When We Need Them

This section introduces the most important technical ideas, but in plain language and in the order they become useful.

### What Is A Graph?

In computer science, a graph is a network.

For this project, a graph is a set of places and links.

- a channel is a place
- a recommendation is a link from one place to another

### What Is A Directed Graph?

The recommendations have direction.

If channel A recommends channel B, that does not automatically mean channel B recommends channel A.

That is why the project uses a directed graph.

### What Is A Weight?

Some recommendation links appear more often than others.

The project does not treat every edge as equally strong. It uses `RELEVANT_IMPRESSIONS_DAILY` from the dataset as the main edge weight.

In plain language, a weight tells us how strong or common a recommendation link is.


### What Is An Ideology Score?

The raw data uses labels such as `L`, `C`, and `R`.

Those labels are good for humans to read, but the experiment also needs simple numeric values so it can measure movement.

The scoring used here is deliberately simple:

- Left becomes `-1.0`
- Center becomes `0.0`
- Right becomes `1.0`

### What Is A Random Walk?

A random walk is one of the most important ideas in the project.

It sounds technical, but the intuition is simple. Imagine you are standing at a crossroads and several signs point to several next destinations. You choose one and move there. Then you repeat the process. That sequence of moves is a walk.

It becomes a random walk because the next move is chosen probabilistically rather than fixed in advance.

In this project, the simulated viewer is a traveler who keeps following recommended links.

### Why Are We Using Weighted Random Walks Instead Of Uniform Random Walks?

Because not all recommendations are equally likely to be seen.

If one recommendation appears far more often than another, the experiment should reflect that. Otherwise it would treat the loudest and quietest signals as if they were identical. So this project uses a weighted random walk.

In plain language, the simulated viewer is more likely to follow a recommendation that the platform shows more often.

### What Is Drift?

Drift answers the question: did the simulated viewer end up more left or more right than where they started?

The formula is:

`final ideology score - initial ideology score`

Examples:

- `0.0 -> 1.0` gives positive drift
- `1.0 -> 0.0` gives negative drift
- `-1.0 -> 1.0` gives a larger positive drift

### What Is Extremity Change?

Extremity change asks something slightly different.

It asks: did the simulated viewer end farther from the center?

The formula is:

`abs(final score) - abs(initial score)`

This matters because moving from left to right is not automatically the same thing as becoming more extreme. A person can cross the center line and still not move farther from the center overall.

The difference? Signed drift measures direction. Extremity change measures distance from the center.

## Figure 3: How One Simulated Walk Works

**Figure 3:**

```text
Start at Channel A
    |
    | platform offers several next channels
    v
Choose one outgoing recommendation
    |
    v
Move to Channel B
    |
    | platform offers several next channels again
    v
Choose again
    |
    v
Repeat for a fixed number of steps
```

We are not trying to predict one real person's exact behavior. We are using the network itself to simulate what would happen if a viewer kept clicking the next recommended option, with stronger recommendation links being more likely to be followed.

## How The Experiment Works From Start To Finish

Now that the core ideas are in place, the full experiment becomes much easier to explain.

### Step 1: Load the raw channel and recommendation tables

The project reads the main node and edge CSV files.

### Step 2: Build the recommendation graph

The software turns channel rows into nodes and recommendation rows into directed edges.

This is where the experiment stops being "just tables" and becomes a network that we can manipulate.

### Step 3: Remove self-loops

A self-loop is a recommendation from a channel to itself.

The project removes self-loops because a recommendation that keeps a simulated viewer on the same channel is not very informative for measuring navigation.

### Step 4: Translate ideology labels into ideology scores

The project converts `L`, `C`, and `R` into `-1.0`, `0.0`, and `1.0`.

This does not claim that ideology is truly one-dimensional in real life, but is a deliberate simplification that makes the experiment measurable and teachable.

### Step 5: Choose valid starting nodes

Not every channel is a useful starting point.

The default starting node rule says a start node must:

- have a known ideology score
- have at least one outgoing recommendation

This avoids starting the experiment at a place where the viewer cannot move or where the starting ideology is unknown.

### Step 6: Simulate recommendation-following behavior

The simulator runs many weighted random walks.

Each walk stores step-by-step records that include:

- the step number
- the node id
- the ideology score at that step

This matters because the project does not only want the final answer. We also want the path the walk took.

### Step 7: Measure the paths

The metrics layer just computes:

- signed drift
- absolute drift
- extremity change
- ideology assortativity
- average clustering

These measurements let the project summarize both movement through ideology space and structure in the network itself, and gives us numbers that actually mean something

### Step 8: Save visual outputs and tables

The visualization layer writes the figures and CSV tables used for interpretation and presentation.

At that point, the experiment becomes something a presenter can show and explain and not just the code I wrote.

## Running the Project

The repository supports two run modes.

This distinction is very important because it shows the project has both a simple default workflow and a stronger repeated-experiment workflow.

### Baseline Mode

Baseline mode is the default mode.

It runs one deterministic full-start simulation using the current default settings.

The default baseline settings in the code are:

- `num_steps = 10`
- `walks_per_start = 1`
- `seed = 42`

This mode is useful because it gives one clean end-to-end run of the project.

### Experiment Mode

Experiment mode first refreshes the baseline outputs, then runs a larger repeated experiment.

The repeated experiment varies:

- start policy
- steps per walk
- random seed

The implemented experiment settings are:

- start policies: `all_valid`, `center_only`, `ideology_balanced`
- step counts: `1`, `5`, `10`, `20`
- walks per start: `5`
- number of seeds: `5`
- maximum selected start nodes per policy: `900`

This produces `60` repeated experiment configurations in the current implementation.

The logic here is easy to explain in plain language:

Baseline mode asks, "what happens in one clean representative run?"

Experiment mode asks, "does the answer still hold up when we repeat the experiment across different starting conditions and multiple random seeds?"

That is a stronger scientific posture.

## Figure 4: How To Read The Main Results

**Figure 4: Signed Drift Versus Extremity Change**

```text
Signed drift:
left <---- negative ---- 0 ---- positive ----> right

Extremity change:
closer to center <---- negative ---- 0 ---- positive ----> farther from center
```


Negative drift does not mean "bad." It means leftward movement.

Positive extremity change does not mean "rightward." It means farther from the center.

Those are different ideas!!!!

### Presentation-Ready Headline Table

The file `results/tables/presentation_headline_metrics.csv` is especially important because it is already shaped for presentation. Its full current local contents are summarized below.

| Start group | Steps per walk | Signed ideological drift | Extremity change |
|---|---:|---:|---:|
| Current valid starts | 1 | -0.31793990415493306 | -0.0670725359419001 |
| Current valid starts | 5 | -0.7796888888888889 | 0.03951111111111111 |
| Current valid starts | 10 | -0.9637333333333334 | 0.10897777777777777 |
| Current valid starts | 20 | -1.0712444444444444 | 0.158 |
| Center-only starts | 1 | -0.07368888888888889 | 0.5108444444444444 |
| Center-only starts | 5 | -0.37546666666666667 | 0.6984 |
| Center-only starts | 10 | -0.5391555555555556 | 0.7881333333333334 |
| Center-only starts | 20 | -0.6330222222222222 | 0.8539111111111112 |
| Ideology-balanced starts | 1 | -0.029199999999999997 | -0.035333333333333335 |
| Ideology-balanced starts | 5 | -0.38079999999999997 | 0.07635555555555555 |
| Ideology-balanced starts | 10 | -0.5444 | 0.1444888888888889 |
| Ideology-balanced starts | 20 | -0.6326666666666666 | 0.19319999999999998 |

This table is useful because it shows several patterns clearly:

- signed drift stays negative in all shown conditions
- longer walks generally produce stronger leftward drift in the current local run
- center-only starts show especially strong positive extremity change
- ideology-balanced starts still show negative drift, but usually less dramatically than the all-valid baseline-style starts

## The Generated Figures And What Each One Means

The project writes figure files into `results/figures/`.

The current output set is:

- `ideology_distribution.png`
- `drift_distribution.png`
- `trajectory_sample.png`
- `extremity_distribution.png`
- `experiment_signed_drift_summary.png`
- `experiment_extremity_change_summary.png`
- `experiment_stepwise_signed_drift.png`
- `experiment_stepwise_extremity_change.png`

Each one exists for a reason.

### `ideology_distribution.png`

This figure shows how many channels fall into Left, Center, and Right.

Before interpreting drift, the audience should understand the starting landscape. If the network already contains more channels on one side than the other, that background matters.

### `drift_distribution.png`

This figure shows the distribution of per-walk signed drift values.

It helps the audience see whether the movement is centered near zero or shifted in one direction.

### `trajectory_sample.png`

This figure shows example walks step by step.

In the current presentation-friendly version, it shows three clearly colored walks,
labels them as Walk 1, Walk 2, and Walk 3, and keeps the ideology reference lines
in a separate key so the figure is easier to read.

### `extremity_distribution.png`

This figure shows per-walk extremity change. 

*Must later convert into percentages for viewers to clearly understand how much percent change the simulated walk changed extremity by*

### `experiment_signed_drift_summary.png`

This figure summarizes average signed drift across repeated experiment settings.

### `experiment_extremity_change_summary.png`

This figure summarizes average extremity change across repeated experiment settings.

It helps the audience see whether some kinds of starts, especially center-only starts, produce stronger movement away from the center.

### `experiment_stepwise_signed_drift.png`

This figure shows average signed drift at each intermediate step of the longest repeated walks.

It is useful because it answers the challenge, "Did you only compare the start and the end?" by showing how the average walk changes across the whole path.

### `experiment_stepwise_extremity_change.png`

This figure shows average extremity change at each intermediate step of the longest repeated walks.

It helps the audience see whether extremity grows gradually as the walk gets longer instead of relying only on the final endpoint summary.


## The Software Architecture Behind The Project

The project is not one giant script. It is a pipeline made of smaller, focused modules.

Each part of the process has a clear job.

The implemented order is:

`graph_builder.py -> ideology.py -> simulator.py -> metrics.py -> visualize.py`

On top of that pipeline sits `src/run_pipeline.py`, and the beginner-facing front door is `run.py`.

## Figure 5: System Architecture

**Figure 5: Implemented Module Chain**

```text
run.py
  |
  v
src/run_pipeline.py
  |
  +--> src/graph_builder.py
  +--> src/ideology.py
  +--> src/simulator.py
  +--> src/metrics.py
  +--> src/visualize.py
```

## The Root-Level Files, Explained

The root of the repository contains several important items.

### `README.md`

This is the main project overview file.

It tells the reader:

- what the project does
- how to set it up
- how to run the baseline and experiment modes
- what outputs it writes
- where to look for more detailed documentation


### `docs/`

This folder holds long-form documentation.

At minimum it includes:

- `docs/SYSTEM_DESIGN.md`
- `docs/project_overview.md`

The system design file is architecture-focused.

This new overview file is the broad, presenter-friendly teaching document.

### `data/`

This folder holds the main dataset materials and documentation.

### `src/`

This folder holds the actual analysis code.

### `tests/`

This folder holds the validation suite.

### `results/`

This folder holds generated outputs.


## The Source Modules, One By One

### `src/__init__.py`

This file marks `src` as a Python package. It does not carry the analytical story by itself, but it helps Python treat the folder as importable project code.

### `src/graph_builder.py`

This is the first real analytical stage.

Its public functions are:

- `load_nodes(filepath)`
- `load_edges(filepath)`
- `build_graph(nodes_df, edges_df)`

Its job is to:

- read the node CSV
- read the edge CSV
- create a directed NetworkX graph
- attach node metadata
- attach edge metadata
- remove self-loops

Why it exists separately:

If graph construction is wrong, everything else becomes wrong. So the project isolates that responsibility.

This is like building the map before trying to navigate it.

### `src/ideology.py`

This is the second stage.

Its key public function is:

- `assign_ideology_scores(G)`

Its job is to translate `LR` labels into numeric ideology scores.

Why it exists separately:

The raw data and the numerical scoring step are conceptually different jobs.

This is like taking labels from a survey and turning them into a simple ruler that the rest of the experiment can use.

### `src/simulator.py`

This is the third stage.

Its key public functions are:

- `choose_next_node(...)`
- `simulate_walk(...)`
- `simulate_walks(...)`

Its job is to create weighted random walks through the graph.

Important design features include:

- default weight attribute: `RELEVANT_IMPRESSIONS_DAILY`
- clean dead-end handling
- fallback to uniform choice when weights are unusable
- support for seeded randomness for reproducibility

Why it exists separately:

The simulator should generate paths. It should not also be responsible for interpreting them.

### `src/metrics.py`

This is the fourth stage.

Its key public functions include:

- `compute_walk_drift(...)`
- `compute_walk_extremity_change(...)`
- `compute_mean_drift(...)`
- `compute_mean_absolute_drift(...)`
- `compute_mean_extremity_change(...)`
- `compute_ideology_assortativity(...)`
- `compute_average_clustering(...)`
- `compute_graph_metrics(...)`
- `compute_all_metrics(...)`

Its job is to turn paths and graph structure into interpretable numbers.

Why it exists separately:

The project wants the math in one explicit place so that the measurement logic can be tested directly.

### `src/visualize.py`

This is the fifth stage.

Its key public functions include:

- `plot_ideology_distribution(...)`
- `plot_drift_distribution(...)`
- `plot_trajectory_sample(...)`
- `plot_extremity_distribution(...)`
- `save_metrics_table(...)`
- `save_rows_table(...)`
- `generate_all_figures(...)`
- `generate_experiment_outputs(...)`

Its job is to turn metrics and trajectories into figures and CSV tables.

Why it exists separately:

The final reporting layer should be separate from both the simulation logic and the metric formulas.

### `src/run_pipeline.py`

This file is the orchestrator.

Its important public functions include:

- `prepare_graph(...)`
- `choose_start_nodes(...)`
- `run_pipeline(...)`
- `build_argument_parser()`
- `main(argv=None)`

It is the conductor that calls the other modules in the right order.

It also implements:

- baseline mode
- experiment mode
- output directory selection
- progress bar behavior
- start-node policies for the repeated experiment

In plain language, this file is the full checklist behind the front door.

## The Tests, One By One

The project has strong value as a teaching repository partly because the test suite mirrors the pipeline.

That makes it easy to explain what is validated.

### `tests/__init__.py`

This helps mark the tests folder as a package context in Python. It is support structure rather than analytical content.

### `tests/test_graph_builder.py`

This file validates the graph-construction layer.

It checks things such as:

- node and edge row counts in fixture loading
- required columns
- graph type is directed
- node count
- edge count after self-loop removal
- no self-loops remain
- expected nodes and edges exist
- node and edge attributes are attached
- isolated-node behavior
- LR label coverage in the fixture graph

Why this matters:

It proves that the map is built correctly before later modules use it.

### `tests/test_ideology.py`

This file validates ideology scoring.

It checks things such as:

- Left maps to `-1.0`
- Center maps to `0.0`
- Right maps to `1.0`
- every node gets a score attribute
- isolated nodes still get scored
- missing or unknown labels become `None`
- the function returns the same graph object it modifies

Why this matters:

It proves that the experiment is not silently inventing bad ideology numbers.

### `tests/test_simulator.py`

This file validates weighted-walk behavior.

It checks things such as:

- dead ends return `None`
- forced one-choice paths behave deterministically
- invalid nodes raise errors
- zero-weight fallbacks still choose among neighbors
- the start node appears as step zero
- walks stop early at dead ends
- step records include ideology scores
- custom weight attributes can be used
- multi-walk outputs have the right structure

Why this matters:

It proves the simulated traveler is moving through the network in the way the project claims.

### `tests/test_metrics.py`

This file validates the formulas.

It checks things such as:

- drift formula correctness
- extremity change correctness
- mean summaries across multiple trajectories
- handling of invalid trajectories
- clustering on a triangle graph
- assortativity behavior
- `compute_all_metrics()` field packaging

Why this matters:

The research claim lives in the metrics. If the formulas are wrong, the conclusions are wrong.

### `tests/test_visualize.py`

This file smoke-tests the output layer.

It checks things such as:

- PNG files get created
- empty trajectory cases do not crash
- sample-line limits do not crash
- metrics CSV gets created
- CSV content matches expected headers and values
- the wrapper output function creates the full baseline bundle

Why this matters:

It proves the reporting layer actually writes what the rest of the project promises.

### `tests/test_run_pipeline.py`

This file validates the orchestration layer.

It checks things such as:

- `prepare_graph()` returns a scored graph
- `choose_start_nodes()` filters bad starts correctly
- baseline mode writes expected files
- experiment mode writes expected extra outputs
- progress reporting can print
- start-node caps work
- stale images are cleaned up while CSV tables are preserved
- the pipeline raises a clear error when there are no valid starts

Why this matters:

It proves that the whole workflow behaves like one complete system rather than just a pile of separate modules.

## The Synthetic Fixtures, Explained

The `tests/fixtures/` folder contains:

- `README.txt`
- `test_nodes.csv`
- `test_edges.csv`

These files are extremely important for teaching.

They are like a dress rehearsal version of the full experiment.

### `tests/fixtures/README.txt`

This file explains the design of the synthetic fixture data.

It highlights why the small fixture world contains specific cases such as:

- exactly 10 nodes
- 16 edges with one self-loop
- all three ideology labels
- one isolated node
- intentional drift chains
- within-ideology clusters
- cross-ideology bridges
- varying edge weights

In plain language, this file explains why the miniature test world was built the way it was.

### `tests/fixtures/test_nodes.csv`

This is the small practice version of the real node table.

It uses readable ids such as `ch_L1`, `ch_C1`, and `ch_R1` so tests are easy to follow.

### `tests/fixtures/test_edges.csv`

This is the small practice version of the real edge table.

It includes deliberately designed scenarios such as:

- a self-loop to remove
- strong within-group links
- weaker cross-group links
- predictable routes for deterministic tests

If you need an analogy, the fixtures are like a training circuit before running a full marathon. They let the team practice each idea in a controlled environment.

## The Results Folder, Explained

The `results/` directory is where the pipeline writes output artifacts.

Its structure includes:

- `results/figures/`
- `results/tables/`

The `.gitkeep` files inside those subdirectories help preserve the folder structure, and the committed PNG figures make the current presentation bundle visible in the repository while CSV tables remain regenerable local outputs.

This is a small detail, but it is part of the repository design.

## How The Project Is Run In Practice

There are two main ways to run the full pipeline.

### The Beginner-Friendly Way

Open `run.py` and press the VS Code Play button.

### The Terminal Way

Use commands such as:

```bash
python3 run.py
python3 run.py --mode experiment
python3 run.py --num-steps 15 --walks-per-start 2 --seed 123
```

The baseline mode writes the baseline outputs.

The experiment mode writes both the baseline outputs and the repeated-experiment outputs.

## Scientific Rigor. More than just a demo

This project is not the final word on recommendation systems, but it is no demo

Several design choices make it scientifically stronger.

### 1. The problem is operationalized clearly

The project asks focused questions and defines measurements for them.

### 2. The data source is documented

The provenance is clear and traceable.

### 3. The pipeline is modular

Each stage has a clear job and can be validated independently.

### 4. The experiment uses deterministic controls where possible

Fixed seeds make stochastic behavior reproducible.

### 5. The repeated experiment adds credibility

Instead of trusting one setup, the project checks whether patterns persist across different starts, lengths, and seeds.

### 6. The test suite is broad

When I verified the current repository, the full suite reported `73 passed`.

## The Assumptions And Limitations

### 1. Logged-off recommendations are not the same as personalized recommendations

The project models the default environment, not the full personalized experience of a logged-in user with a watch history.

### 2. Ideology is simplified heavily

Reducing channels to `Left`, `Center`, and `Right`, then to `-1`, `0`, and `1`, is useful but coarse.

Real political ideology is more complicated than a one-dimensional line, and is encompassed on a wide-range spectrum of internal rationales that are not measurable by a simple computer model.

### 3. A random walk is a MODEL

The simulated viewer is not a real person with emotions, habits, resistance, or selective attention.

It is a controlled modeling device that simply picks the "most popular" recommendation that is attached to it


### 4. Recommendation exposure is not the same as persuasion

The experiment measures movement through the recommendation network. It does not directly measure whether a person changed their beliefs mid-way through clicking


## How To Present This Project To A Non-Technical Audience

This section is written directly for you guys who need to speak about the work a little bit.

### Emphasize The Two Core Questions Early

Keep repeating the same two questions:

1. Does the path move viewers left or right overall?
2. Does the path move viewers farther from the center?

### Use The Map Analogy Often

These analogies are safe and helpful:

- nodes (channels) are places on a map
- edges (recommendations) are roads
- stronger recommendations are wider roads or busier highways
- a simulated walk is a traveler following the signs

### Explain Drift And Extremity Separately

Drift tells us which direction the viewer moved. Extremity tells us whether the viewer ended farther from the middle. Those are not the same question.

That one line can prevent a lot of confusion later on.

### Use Baseline Mode And Experiment Mode As A Story Of Increasing Confidence

Explain them like this:

- baseline mode shows one complete run from start to finish
- experiment mode repeats the test in many settings to see whether the pattern still holds and takes a more meaningful average and collection of metrics to analyze

This helps the audience see that the project is trying to be careful rather than cherry-pick one convenient run.


### What To Emphasize In The Current Local Results

The safest way to summarize the currently observed outputs is:

- the simulated recommendation paths tend to move left overall in the current local run
- longer paths generally show stronger movement
- center-only starts show especially strong movement away from the center
- the repeated experiment keeps the basic pattern from depending on a single run

### What Not To Claim

- "the algorithm proves people become radicalized"
- "the platform definitely changes real beliefs this exact amount"
- "this model captures all political complexity"

This is better:

- the model shows how recommendation paths are structured
- the model shows where simulated viewers tend to move in that structure
- the model gives evidence about directional and extremity tendencies in the recommendation network


## Repository Map

Below is a simplified map of the repository's meaningful structure.

**Figure 6: Repository Map**

```text
project/
|- .gitignore
|- README.md
|- requirements.txt
|- run.py
|- .github/
|  |- copilot-instructions.md
|  |- skills/
|- docs/
|  |- SYSTEM_DESIGN.md
|  |- project_overview.md
|- data/
|  |- README.md
|  |- readme.txt
|  |- channel_review.csv
|  |- vis_category_recs.csv
|  |- vis_channel_recs2.csv
|  |- vis_channel_stats.csv
|  |- vis_tag_recs.csv
|- src/
|  |- __init__.py
|  |- graph_builder.py
|  |- ideology.py
|  |- simulator.py
|  |- metrics.py
|  |- visualize.py
|  |- run_pipeline.py
|- tests/
|  |- __init__.py
|  |- test_graph_builder.py
|  |- test_ideology.py
|  |- test_simulator.py
|  |- test_metrics.py
|  |- test_visualize.py
|  |- test_run_pipeline.py
|  |- fixtures/
|     |- README.txt
|     |- test_nodes.csv
|     |- test_edges.csv
|- results/
   |- figures/
   |- tables/
```

This map is useful because it shows that the repository is organized around one main story:

- explain the project
- hold the data
- run the analysis
- validate the analysis
- save the outputs

## Last Words

This repository asks a clear, socially important question: if a viewer keeps following recommendations in a political content network, where does that path tend to lead?

It answers that question by turning recommendation data into a graph, turning ideology labels into simple scores, simulating weighted recommendation-following paths, measuring movement, and saving outputs that people can actually interpret.

The current local results suggest that, in this snapshot and model, recommendation-following paths tend to move left overall and often end farther from the ideological center, especially under some starting conditions such as center-only starts.

Just as important, the project explains itself well.

If your group needs one sentence to close on, use this:

This project studies not just what political content exists on a platform, but what journeys the recommendation system makes easiest to take.

## Appendix A: File-By-File Inventory

This appendix exists to reduce omission risk. It briefly states the role of each meaningful repository file or file family.

### Root files and folders

| Path | Role |
|---|---|
| `.gitignore` | Keeps local machine files, raw data CSVs, generated results, and support artifacts out of version control |
| `README.md` | Main project overview, setup guide, run guide, output summary |
| `requirements.txt` | Declares core analysis, visualization, and testing dependencies |
| `run.py` | Beginner-friendly front door that launches the full pipeline |
| `.github/` | Development-support folder, not part of the scientific pipeline itself |
| `docs/` | Long-form documentation |
| `data/` | Dataset materials and data documentation |
| `src/` | Analysis source code |
| `tests/` | Validation suite |
| `results/` | Generated figures and tables |

### `.github/`

| Path | Role |
|---|---|
| `.github/copilot-instructions.md` | Local AI-assistant guidance for repo-aware development behavior |
| `.github/skills/` | AI workflow skill support directory |
| `.github/skills/project-status-check/` | Skill folder for plain-English project status reporting |
| `.github/skills/project-status-check/SKILL.md` | Defines the `project-status-check` skill and its expected status-report format |

### `docs/`

| Path | Role |
|---|---|
| `docs/SYSTEM_DESIGN.md` | Architecture, module boundaries, data flow, validation strategy |
| `docs/project_overview.md` | This exhaustive teaching and presentation guide |

### `data/`

| Path | Role |
|---|---|
| `data/README.md` | Main source-of-truth file for dataset provenance and schema |
| `data/readme.txt` | Short catalog of the broader Recfluence dataset contents |
| `data/vis_channel_stats.csv` | Main node table used by the pipeline |
| `data/vis_channel_recs2.csv` | Main edge table used by the pipeline |
| `data/channel_review.csv` | Reviewer-level classification and notes data |
| `data/vis_category_recs.csv` | Aggregate recommendation summaries by categories or ideology groups |
| `data/vis_tag_recs.csv` | Aggregate recommendation summaries by tags |

### `src/`

| Path | Role |
|---|---|
| `src/__init__.py` | Package marker for project code |
| `src/graph_builder.py` | Loads CSV data, builds directed graph, removes self-loops |
| `src/ideology.py` | Maps `L/C/R` labels to numeric ideology scores |
| `src/simulator.py` | Runs weighted random walks through the graph |
| `src/metrics.py` | Computes drift, extremity change, assortativity, clustering, and summary metrics |
| `src/visualize.py` | Generates figures and CSV tables |
| `src/run_pipeline.py` | Orchestrates the end-to-end baseline and experiment workflows |

### `tests/`

| Path | Role |
|---|---|
| `tests/__init__.py` | Package marker for tests |
| `tests/test_graph_builder.py` | Validates loading, graph construction, schema, self-loop removal |
| `tests/test_ideology.py` | Validates ideology score mapping and edge cases |
| `tests/test_simulator.py` | Validates walk generation behavior and random-choice logic |
| `tests/test_metrics.py` | Validates formulas and summary packaging |
| `tests/test_visualize.py` | Validates figure and CSV generation |
| `tests/test_run_pipeline.py` | Validates the full orchestration behavior |
| `tests/fixtures/README.txt` | Explains the design of the synthetic fixture world |
| `tests/fixtures/test_nodes.csv` | Small fixture node table |
| `tests/fixtures/test_edges.csv` | Small fixture edge table |

### `results/figures/`

| Path | Role |
|---|---|
| `results/figures/.gitkeep` | Preserves the output directory structure |
| `results/figures/ideology_distribution.png` | Baseline ideology-count chart |
| `results/figures/drift_distribution.png` | Baseline drift histogram |
| `results/figures/trajectory_sample.png` | Baseline sample trajectory plot showing three labeled walks with a separate ideology key |
| `results/figures/extremity_distribution.png` | Baseline extremity-change histogram |
| `results/figures/experiment_signed_drift_summary.png` | Repeated-experiment signed drift summary figure |
| `results/figures/experiment_extremity_change_summary.png` | Repeated-experiment extremity summary figure |
| `results/figures/experiment_stepwise_signed_drift.png` | Repeated-experiment step-by-step signed drift figure |
| `results/figures/experiment_stepwise_extremity_change.png` | Repeated-experiment step-by-step extremity figure |

### `results/tables/`

| Path | Role |
|---|---|
| `results/tables/.gitkeep` | Preserves the output directory structure |
| `results/tables/summary_metrics.csv` | Baseline one-row summary |
| `results/tables/experiment_per_run.csv` | One row per repeated experiment configuration |
| `results/tables/experiment_grouped_summary.csv` | Grouped repeated-experiment summary |
| `results/tables/experiment_step_trend_summary.csv` | Step-by-step repeated-experiment summary table |
| `results/tables/presentation_headline_metrics.csv` | Presentation-oriented headline metric table |

### Local development artifacts present in the workspace but not part of the scientific deliverable

These are present in the workspace but should not be confused with the project's research content:

- `.git/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`

They support development, version control, or Python execution, but they are not part of the experiment's conceptual story.