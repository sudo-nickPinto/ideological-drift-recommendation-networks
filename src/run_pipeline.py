# ==============================================================================
# MODULE: run_pipeline.py
# PURPOSE: Hold the real step-by-step logic for running the entire project.
# ==============================================================================
#
# HIGH-LEVEL EXPLANATION:
#   Think of this file as the "engine room" of the project.
#   The other files each do one smaller job:
#
#       graph_builder.py  ->  ideology.py  ->  simulator.py  ->  metrics.py  ->  visualize.py
#
#   This file ties those smaller jobs together in the correct order.
#
#   MOST USERS SHOULD NOT START HERE.
#   The beginner-friendly file to run is the root-level file named:
#
#       run.py
#
#   You can open run.py and press the VS Code Play button on THAT file.
#   That file is just a very small front door. This file is the room behind
#   the door where the real work happens.
#
#   When the full project runs, these steps happen in order:
#     1. Read the real CSV files from data/
#     2. Build the recommendation graph
#     3. Add ideology scores to the graph nodes
#     4. Choose reasonable starting channels for the simulated user walks
#     5. Run the weighted random walks
#     6. Compute the summary metrics
#     7. Save the figures and CSV table into results/
#
# WHY THIS FILE IS IMPORTANT:
#   Without this file, the project is just a set of separate parts.
#   This file is the checklist that says what order those parts must run in.
#
# WHY THE IMPORT SETUP LOOKS A LITTLE STRANGE:
#   Python treats code differently depending on HOW you run it.
#
#   - If you run a file directly, Python starts from that file.
#   - If you run a package/module, Python starts from the package.
#
#   The earlier version of this file only worked in the second case.
#   That was confusing for a beginner because the Play button usually runs a
#   FILE directly, not a package. So this file now supports the direct-file
#   workflow on purpose.
#
# DESIGN DECISIONS:
#   - The logic is split into small functions so each step is easier to read
#     and test.
#   - The default run uses a fixed random seed so results are reproducible.
#   - Default starting nodes must have both a known ideology score and at
#     least one outgoing recommendation.
#
# ==============================================================================


from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path


# When you run this file directly with "python3 src/run_pipeline.py",
# Python starts inside the src/ folder. That means "from src..." imports would
# normally fail, because Python is looking from the wrong starting location.
#
# To fix that, we manually add the PROJECT ROOT folder to Python's import path
# when this file is run directly.
#
# In plain English: we tell Python where the rest of the project lives.
if __package__ in {None, ""}:
    import sys

    PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.metrics import (
    ASSORTATIVITY_FIELD,
    CLUSTERING_FIELD,
    MEAN_ABSOLUTE_DRIFT_FIELD,
    MEAN_DRIFT_FIELD,
    MEAN_EXTREMITY_CHANGE_FIELD,
    TRAJECTORY_COUNT_FIELD,
    VALID_DRIFT_COUNT_FIELD,
    compute_graph_metrics,
    compute_all_metrics,
)
from src.simulator import simulate_walks
from src.visualize import generate_all_figures, generate_experiment_outputs


# --- DEFAULT PATHS ------------------------------------------------------------
#
# Path = the location of a file or folder on your computer.
#
# We define the important paths once here so the rest of the file can reuse
# them without hardcoding long folder names over and over.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NODES_PATH = PROJECT_ROOT / "data" / "vis_channel_stats.csv"
DEFAULT_EDGES_PATH = PROJECT_ROOT / "data" / "vis_channel_recs2.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"


# --- DEFAULT RUN PARAMETERS ---------------------------------------------------

# A "constant" is a value we define once and reuse.
# These are the default settings used if the user does not pass custom values.

# Ten steps is long enough to observe movement while still keeping the default
# run fast and easy to interpret.
DEFAULT_NUM_STEPS = 10

# One walk per starting node keeps the default run lightweight while still
# sampling the whole network structure.
DEFAULT_WALKS_PER_START = 1

# Fixed seed = reproducible outputs.
DEFAULT_RANDOM_SEED = 42


# --- RUN MODES ----------------------------------------------------------------

DEFAULT_MODE = "baseline"
EXPERIMENT_MODE = "experiment"
VALID_MODES = {DEFAULT_MODE, EXPERIMENT_MODE}


# --- EXPERIMENT SETTINGS ------------------------------------------------------

# These constants define the repeated experiment matrix. They live at module
# scope on purpose so tests can temporarily monkeypatch them to smaller values.
EXPERIMENT_START_POLICIES = [
    "all_valid",
    "center_only",
    "ideology_balanced",
]
EXPERIMENT_START_POLICY_LABELS = {
    "all_valid": "Current valid starts",
    "center_only": "Center-only starts",
    "ideology_balanced": "Ideology-balanced starts",
}
EXPERIMENT_STEP_COUNTS = [1, 5, 10, 20]
EXPERIMENT_WALKS_PER_START = 5
EXPERIMENT_SEED_COUNT = 5
EXPERIMENT_MAX_START_NODES_PER_POLICY = 900


# --- OUTPUT COLUMN ORDERS -----------------------------------------------------

EXPERIMENT_PER_RUN_FIELDNAMES = [
    "start_policy",
    "start_policy_label",
    "step_count",
    "seed",
    "walks_per_start",
    "available_start_nodes",
    "selected_start_nodes",
    TRAJECTORY_COUNT_FIELD,
    VALID_DRIFT_COUNT_FIELD,
    MEAN_DRIFT_FIELD,
    MEAN_ABSOLUTE_DRIFT_FIELD,
    MEAN_EXTREMITY_CHANGE_FIELD,
    ASSORTATIVITY_FIELD,
    CLUSTERING_FIELD,
]

EXPERIMENT_GROUPED_SUMMARY_FIELDNAMES = [
    "start_policy",
    "start_policy_label",
    "step_count",
    "runs_aggregated",
    "available_start_nodes",
    "selected_start_nodes",
    "walks_per_start",
    "signed_drift_mean",
    "signed_drift_std",
    "signed_drift_min",
    "signed_drift_max",
    "extremity_change_mean",
    "extremity_change_std",
    "extremity_change_min",
    "extremity_change_max",
]

PRESENTATION_HEADLINE_FIELDNAMES = [
    "start group",
    "steps per walk",
    "signed ideological drift",
    "extremity change",
    "how to read signed ideological drift",
    "how to read extremity change",
]


# --- FUNCTIONS ----------------------------------------------------------------

def _should_show_progress(show_progress, stream):
    """
    Decide whether the CLI progress bar should render.

    RULES:
        - If the caller explicitly passes True or False, respect that.
        - Otherwise, only auto-enable the live bar when the stream looks like
          an interactive terminal (TTY). This avoids messy control characters
          when output is redirected to a file.
    """
    if show_progress is not None:
        return bool(show_progress)

    stream_is_tty = getattr(stream, "isatty", None)
    return bool(stream_is_tty and stream_is_tty())


class _CliProgressBar:
    """
    Small built-in terminal progress bar for long-running simulations.

    WHY THIS EXISTS:
        The experiment mode can run for a long time on the full dataset.
        Without a live progress display, the terminal can look frozen even
        though the simulation is still working. This helper gives the user a
        simple "it is still moving" signal without adding any new dependency.
    """

    def __init__(
        self,
        total,
        label,
        stream=None,
        enabled=True,
        width=30,
        min_render_interval_seconds=0.25,
    ):
        self.total = max(int(total), 1)
        self.label = label
        self.stream = stream if stream is not None else sys.stdout
        self.enabled = enabled
        self.width = width
        self.min_render_interval_seconds = min_render_interval_seconds
        self.current = 0
        self.detail = ""
        self._finished = False
        self._started_at = time.monotonic()
        self._last_render_at = 0.0
        self._rendered_line_count = 0
        self._interactive_dashboard = (
            self.enabled
            and bool(getattr(self.stream, "isatty", None))
            and self.stream.isatty()
        )
        self.current_configuration_index = None
        self.total_configurations = None
        self.start_policy_label = None
        self.step_count = None
        self.seed = None
        self.selected_start_nodes = None
        self.available_start_nodes = None
        self.walks_per_start = None

        if self.enabled:
            self._render(force=True)

    def set_detail(self, detail):
        """Update the short status note shown to the right of the bar."""
        self.set_context(detail=detail)

    def set_context(
        self,
        *,
        detail=None,
        current_configuration_index=None,
        total_configurations=None,
        start_policy_label=None,
        step_count=None,
        seed=None,
        selected_start_nodes=None,
        available_start_nodes=None,
        walks_per_start=None,
    ):
        """Update the dashboard context shown around the progress bar."""
        if not self.enabled or self._finished:
            return

        if detail is not None:
            self.detail = detail
        if current_configuration_index is not None:
            self.current_configuration_index = current_configuration_index
        if total_configurations is not None:
            self.total_configurations = total_configurations
        if start_policy_label is not None:
            self.start_policy_label = start_policy_label
        if step_count is not None:
            self.step_count = step_count
        if seed is not None:
            self.seed = seed
        if selected_start_nodes is not None:
            self.selected_start_nodes = selected_start_nodes
        if available_start_nodes is not None:
            self.available_start_nodes = available_start_nodes
        if walks_per_start is not None:
            self.walks_per_start = walks_per_start

        self._render(force=True)

    def update(self, increment=1, detail=None):
        """Advance the bar by a fixed amount and redraw it."""
        if not self.enabled or self._finished:
            return

        if detail is not None:
            self.detail = detail

        self.current = min(self.total, self.current + increment)
        self._render()

    def finish(self, detail=None):
        """Mark the progress bar complete and move to the next terminal line."""
        if not self.enabled or self._finished:
            return

        self.current = self.total
        if detail is not None:
            self.detail = detail

        self._render(force=True)
        print(file=self.stream, flush=True)
        self._finished = True

    def _render(self, force=False):
        now = time.monotonic()
        should_render = force or self.current >= self.total
        if not should_render and (now - self._last_render_at) < self.min_render_interval_seconds:
            return

        fraction_complete = self.current / self.total
        filled_width = int(self.width * fraction_complete)
        empty_width = self.width - filled_width
        bar = "#" * filled_width + "-" * empty_width
        elapsed_seconds = max(now - self._started_at, 0.000001)
        walks_per_second = self.current / elapsed_seconds if self.current else 0.0

        if self.current and walks_per_second > 0.0 and self.current < self.total:
            remaining_walks = self.total - self.current
            eta_seconds = remaining_walks / walks_per_second
            eta_text = f"ETA {eta_seconds / 60:.1f}m"
        else:
            eta_text = "ETA --"

        main_line = (
            f"\r{self.label}: [{bar}] "
            f"{fraction_complete * 100:6.2f}% "
            f"({self.current}/{self.total} walks) "
            f"| {walks_per_second:,.0f} walks/s "
            f"| {eta_text}"
        )
        lines = [main_line]

        if self._interactive_dashboard:
            context_parts = []
            if (
                self.current_configuration_index is not None
                and self.total_configurations is not None
            ):
                context_parts.append(
                    f"Config {self.current_configuration_index}/{self.total_configurations}"
                )
            if self.start_policy_label:
                context_parts.append(f"Start group: {self.start_policy_label}")
            if self.step_count is not None:
                context_parts.append(f"Steps/walk: {self.step_count}")
            if self.seed is not None:
                context_parts.append(f"Seed: {self.seed}")
            if context_parts:
                lines.append(" | ".join(context_parts))

            volume_parts = []
            if (
                self.selected_start_nodes is not None
                and self.available_start_nodes is not None
            ):
                volume_parts.append(
                    "Selected starts: "
                    f"{self.selected_start_nodes:,}/{self.available_start_nodes:,}"
                )
            elif self.selected_start_nodes is not None:
                volume_parts.append(f"Start nodes: {self.selected_start_nodes:,}")
            if self.walks_per_start is not None:
                volume_parts.append(f"Walks/start: {self.walks_per_start}")
            if self.detail:
                volume_parts.append(f"Status: {self.detail}")
            if volume_parts:
                lines.append(" | ".join(volume_parts))
        else:
            inline_context_parts = []
            if (
                self.current_configuration_index is not None
                and self.total_configurations is not None
            ):
                inline_context_parts.append(
                    f"Config {self.current_configuration_index}/{self.total_configurations}"
                )
            if self.start_policy_label:
                inline_context_parts.append(self.start_policy_label)
            if self.step_count is not None:
                inline_context_parts.append(f"{self.step_count} steps/walk")
            if self.seed is not None:
                inline_context_parts.append(f"seed {self.seed}")
            if (
                self.selected_start_nodes is not None
                and self.available_start_nodes is not None
            ):
                inline_context_parts.append(
                    f"starts {self.selected_start_nodes:,}/{self.available_start_nodes:,}"
                )
            elif self.selected_start_nodes is not None:
                inline_context_parts.append(f"starts {self.selected_start_nodes:,}")
            if self.walks_per_start is not None:
                inline_context_parts.append(f"walks/start {self.walks_per_start}")
            if self.detail:
                inline_context_parts.append(self.detail)
            if inline_context_parts:
                lines[0] += " | " + " | ".join(inline_context_parts)

        self._print_lines(lines)
        self._last_render_at = now

    def _print_lines(self, lines):
        if not self._interactive_dashboard:
            print(lines[0], end="", file=self.stream, flush=True)
            return

        if self._rendered_line_count:
            cursor_reset = "\r" + ("\033[F" * (self._rendered_line_count - 1))
            print(cursor_reset, end="", file=self.stream)

        for line_index, line in enumerate(lines):
            line_end = "\n" if line_index < (len(lines) - 1) else ""
            print(f"\r\033[2K{line}", end=line_end, file=self.stream)

        self.stream.flush()
        self._rendered_line_count = len(lines)


def _sample_start_nodes(node_ids, rng, max_total_start_nodes=None):
    """
    Downsample experiment start nodes to keep the repeated run practical.

    WHY THIS EXISTS:
        The real dataset has thousands of valid start nodes. Repeating the
        experiment over every possible start for every seed and step count
        pushes the walk count into the millions, which is too slow for an
        interactive presentation workflow.
    """
    sorted_node_ids = sorted(node_ids)

    if max_total_start_nodes is None:
        max_total_start_nodes = EXPERIMENT_MAX_START_NODES_PER_POLICY

    if max_total_start_nodes is None or len(sorted_node_ids) <= max_total_start_nodes:
        return sorted_node_ids

    if max_total_start_nodes < 1:
        raise ValueError("Experiment start-node cap must be at least 1.")

    return sorted(rng.sample(sorted_node_ids, k=max_total_start_nodes))


def _balanced_group_cap(max_total_start_nodes=None):
    """
    Convert the total balanced-policy cap into a per-ideology-group cap.
    """
    if max_total_start_nodes is None:
        max_total_start_nodes = EXPERIMENT_MAX_START_NODES_PER_POLICY

    if max_total_start_nodes is None:
        return None

    if max_total_start_nodes < 3:
        raise ValueError(
            "Balanced experiment start-node cap must be at least 3 so Left, "
            "Center, and Right can each contribute one start node."
        )

    return max_total_start_nodes // 3


def prepare_graph(nodes_path, edges_path):
    """
    Build the scored recommendation graph from the two real dataset CSV files.

    PARAMETERS:
        nodes_path (str or Path): Path to vis_channel_stats.csv
        edges_path (str or Path): Path to vis_channel_recs2.csv

    RETURNS:
        networkx.DiGraph: A graph with IDEOLOGY_SCORE attached to each node.
    """
    # STEP 1: Read the channel table.
    # This gives us one row per YouTube channel.
    nodes_df = load_nodes(nodes_path)

    # STEP 2: Read the recommendation-edge table.
    # This gives us one row per recommendation link.
    edges_df = load_edges(edges_path)

    # STEP 3: Turn those tables into a directed graph.
    graph = build_graph(nodes_df, edges_df)

    # STEP 4: Add numeric ideology scores to every node.
    # Example: L -> -1.0, C -> 0.0, R -> +1.0
    assign_ideology_scores(graph)

    # Return the finished graph so later steps can use it.
    return graph


def choose_start_nodes(G, score_attr=SCORE_ATTRIBUTE):
    """
    Select the default starting nodes for simulation.

    RULES:
        A node is a valid default start node only if:
        1. It has a numeric ideology score (not None)
        2. It has at least one outgoing edge

    WHY THESE RULES:
        - Drift cannot be interpreted if the starting ideology is unknown.
        - A node with zero outgoing edges immediately dead-ends, which makes it
          unhelpful as the default starting point for a recommendation walk.

    RETURNS:
        list: Node IDs that satisfy both rules.
    """
    # We build a list step by step.
    # A list is just an ordered collection of values.
    start_nodes = []

    # G.nodes(data=True) gives us:
    #   - node_id: the unique name/ID of a node
    #   - attrs: a dictionary of extra information attached to that node
    for node_id, attrs in G.nodes(data=True):
        # attrs.get(score_attr) reads the ideology score from the node.
        # "is not None" means: the score exists and is not missing.
        has_score = attrs.get(score_attr) is not None

        # out_degree tells us how many outgoing edges leave this node.
        # If that number is 0, a walk starting here cannot go anywhere.
        has_outgoing_edge = G.out_degree(node_id) > 0

        # Only keep nodes that satisfy BOTH rules.
        if has_score and has_outgoing_edge:
            start_nodes.append(node_id)

    return start_nodes


def _select_experiment_start_nodes(
    G,
    valid_start_nodes,
    policy_name,
    rng,
    score_attr=SCORE_ATTRIBUTE,
):
    """
    Select the start nodes for ONE experiment policy.

    BIG PICTURE:
        The baseline pipeline uses one broad rule for start nodes:
        "known ideology score + at least one outgoing edge."
        The experiment mode keeps that same foundation but asks whether the
        answer changes when we begin from different kinds of users.

        By the time this helper runs, graph_builder.py has already created the
        recommendation network and ideology.py has already attached the numeric
        ideology scores that let us define policies like "center only."

    WHY THIS HELPER EXISTS:
        We want one small place where a beginner can read:
            - what each start policy means
            - why the policy exists
            - how the selected nodes feed into simulator.py

        This helper does ONLY the selection step. It does not run the walks
        and it does not compute metrics. That separation keeps the experiment
        workflow easier to follow.

    POLICIES IMPLEMENTED:
        1. all_valid
           Use the same valid-start rule as the baseline pipeline.

        2. center_only
           Restrict the starts to channels whose ideology score is exactly 0.0.
           This is the cleanest way to ask whether center-starting users get
           nudged left, right, or toward the extremes.

        3. ideology_balanced
           Build three buckets (Left, Center, Right), find the smallest bucket,
           and sample that many nodes from each ideology. This keeps the start
           mix balanced instead of letting the largest ideology group dominate.

    RETURNS:
        tuple(list[str], int):
            - the concrete start-node list for this one experiment run
            - the number of nodes that were eligible before any balancing step
    """
    if policy_name == "all_valid":
        available_start_nodes = len(valid_start_nodes)
        selected_start_nodes = _sample_start_nodes(valid_start_nodes, rng)
    elif policy_name == "center_only":
        center_only_start_nodes = [
            node_id
            for node_id in valid_start_nodes
            if G.nodes[node_id].get(score_attr) == 0.0
        ]
        available_start_nodes = len(center_only_start_nodes)
        selected_start_nodes = _sample_start_nodes(center_only_start_nodes, rng)
    elif policy_name == "ideology_balanced":
        ideology_groups = {
            -1.0: [],
            0.0: [],
            1.0: [],
        }

        for node_id in valid_start_nodes:
            ideology_score = G.nodes[node_id].get(score_attr)
            if ideology_score in ideology_groups:
                ideology_groups[ideology_score].append(node_id)

        missing_scores = [
            ideology_score
            for ideology_score, group_nodes in ideology_groups.items()
            if not group_nodes
        ]
        if missing_scores:
            raise ValueError(
                "Start policy 'ideology_balanced' needs at least one valid "
                "Left, Center, and Right start node."
            )

        available_start_nodes = sum(len(group_nodes) for group_nodes in ideology_groups.values())
        balanced_group_size = min(len(group_nodes) for group_nodes in ideology_groups.values())
        per_ideology_group_cap = _balanced_group_cap()
        if per_ideology_group_cap is not None:
            balanced_group_size = min(balanced_group_size, per_ideology_group_cap)

        selected_start_nodes = []
        for ideology_score in (-1.0, 0.0, 1.0):
            population = sorted(ideology_groups[ideology_score])
            sampled_nodes = rng.sample(population, k=balanced_group_size)
            selected_start_nodes.extend(sorted(sampled_nodes))
    else:
        raise ValueError(f"Unknown experiment start policy: {policy_name}")

    if not selected_start_nodes:
        raise ValueError(
            f"Start policy '{policy_name}' produced no eligible start nodes."
        )

    return selected_start_nodes, available_start_nodes


def _run_repeated_experiments(
    G,
    valid_start_nodes,
    seed,
    score_attr=SCORE_ATTRIBUTE,
    graph_metrics=None,
    progress_bar=None,
):
    """
    Run the full repeated experiment matrix and collect ONE compact row per run.

    BIG PICTURE:
        This helper is where the baseline simulation becomes a slightly more
        rigorous experiment. Instead of trusting one narrow setup, we repeat
        the walks across:
            - several start-node policies
            - several walk lengths
            - several random seeds

        Each configuration still uses the same lower-level building blocks:
            - simulator.py generates trajectories
            - metrics.py turns trajectories into the two headline outcomes
            - visualize.py later writes the compact rows into presentation-
              friendly CSV tables
            - this helper stores only the summary row and then moves on

    WHY THIS HELPER EXISTS:
        The experiment loop is conceptually different from the baseline run.
        Keeping it in one helper lets a beginner understand the repeated-run
        logic without mixing it into the simpler default path above.

    MEMORY DESIGN:
        We intentionally compute one configuration at a time:
            select starts -> simulate walks -> compute metrics -> save one row
        Then the large trajectory list falls out of scope before the next run.
        That keeps the experiment upgrade strong enough for presentation while
        still staying lightweight in architecture.
    """
    per_run_rows = []
    total_configurations = _count_total_experiment_configurations()
    configuration_index = 0

    for start_policy in EXPERIMENT_START_POLICIES:
        start_policy_label = EXPERIMENT_START_POLICY_LABELS[start_policy]

        for step_count in EXPERIMENT_STEP_COUNTS:
            for seed_offset in range(EXPERIMENT_SEED_COUNT):
                configuration_index += 1
                experiment_seed = seed + seed_offset
                rng = random.Random(experiment_seed)

                selected_start_nodes, available_start_nodes = _select_experiment_start_nodes(
                    G,
                    valid_start_nodes,
                    start_policy,
                    rng,
                    score_attr=score_attr,
                )

                if progress_bar is not None:
                    progress_bar.set_context(
                        current_configuration_index=configuration_index,
                        total_configurations=total_configurations,
                        start_policy_label=start_policy_label,
                        step_count=step_count,
                        seed=experiment_seed,
                        selected_start_nodes=len(selected_start_nodes),
                        available_start_nodes=available_start_nodes,
                        walks_per_start=EXPERIMENT_WALKS_PER_START,
                    )

                trajectories = simulate_walks(
                    G,
                    start_nodes=selected_start_nodes,
                    num_steps=step_count,
                    walks_per_start=EXPERIMENT_WALKS_PER_START,
                    rng=rng,
                    progress_callback=progress_bar.update if progress_bar is not None else None,
                )
                metrics_dict = compute_all_metrics(
                    G,
                    trajectories,
                    graph_metrics=graph_metrics,
                )

                per_run_rows.append(
                    {
                        "start_policy": start_policy,
                        "start_policy_label": start_policy_label,
                        "step_count": step_count,
                        "seed": experiment_seed,
                        "walks_per_start": EXPERIMENT_WALKS_PER_START,
                        "available_start_nodes": available_start_nodes,
                        "selected_start_nodes": len(selected_start_nodes),
                        TRAJECTORY_COUNT_FIELD: metrics_dict[TRAJECTORY_COUNT_FIELD],
                        VALID_DRIFT_COUNT_FIELD: metrics_dict[VALID_DRIFT_COUNT_FIELD],
                        MEAN_DRIFT_FIELD: metrics_dict[MEAN_DRIFT_FIELD],
                        MEAN_ABSOLUTE_DRIFT_FIELD: metrics_dict[MEAN_ABSOLUTE_DRIFT_FIELD],
                        MEAN_EXTREMITY_CHANGE_FIELD: metrics_dict[MEAN_EXTREMITY_CHANGE_FIELD],
                        ASSORTATIVITY_FIELD: metrics_dict[ASSORTATIVITY_FIELD],
                        CLUSTERING_FIELD: metrics_dict[CLUSTERING_FIELD],
                    }
                )

    return per_run_rows


def _count_total_experiment_configurations():
    """
    Count how many repeated experiment configurations will run in total.
    """
    return (
        len(EXPERIMENT_START_POLICIES)
        * len(EXPERIMENT_STEP_COUNTS)
        * EXPERIMENT_SEED_COUNT
    )


def _estimate_total_experiment_walks(
    G,
    valid_start_nodes,
    seed,
    score_attr=SCORE_ATTRIBUTE,
):
    """
    Estimate how many walks the repeated experiment will simulate in total.

    WHY THIS EXISTS:
        A progress bar needs a denominator before the loop starts. The count of
        selected starts is fixed for each policy even when the balanced policy
        samples different actual node IDs across seeds, so we can compute the
        total number of walks up front.
    """
    total_walks = 0

    for start_policy in EXPERIMENT_START_POLICIES:
        selected_start_nodes, _ = _select_experiment_start_nodes(
            G,
            valid_start_nodes,
            start_policy,
            random.Random(seed),
            score_attr=score_attr,
        )

        walks_per_configuration = len(selected_start_nodes) * EXPERIMENT_WALKS_PER_START
        total_walks += (
            walks_per_configuration
            * len(EXPERIMENT_STEP_COUNTS)
            * EXPERIMENT_SEED_COUNT
        )

    return total_walks


def _summarize_experiment_results(per_run_rows):
    """
    Turn the per-run experiment rows into grouped and presentation-friendly tables.

    BIG PICTURE:
        The repeated loop above produces many rows because each seed gets its
        own simulation result. That level of detail is useful for checking
        stability, but it is too noisy for a presentation slide.

    WHY THIS HELPER EXISTS:
        We need one place that translates technical run-level output into two
        easier layers:
            1. a grouped summary for analysis
            2. a plain-English headline table for non-technical audiences

        This is the bridge from raw repeated runs to the final question:
            "Do recommendation paths change ideology direction, and do they
             increase ideological extremity?"

        The actual CSV writing still happens in visualize.py. This helper only
        prepares the rows so the reporting layer can stay simple.
    """
    grouped_summary_rows = []
    presentation_rows = []
    rows_by_group = {}

    for row in per_run_rows:
        group_key = (
            row["start_policy"],
            row["start_policy_label"],
            row["step_count"],
        )
        rows_by_group.setdefault(group_key, []).append(row)

    for start_policy in EXPERIMENT_START_POLICIES:
        start_policy_label = EXPERIMENT_START_POLICY_LABELS[start_policy]

        for step_count in EXPERIMENT_STEP_COUNTS:
            group_rows = rows_by_group.get((start_policy, start_policy_label, step_count), [])
            if not group_rows:
                continue

            signed_drifts = [
                row[MEAN_DRIFT_FIELD]
                for row in group_rows
                if row[MEAN_DRIFT_FIELD] is not None
            ]
            extremity_changes = [
                row[MEAN_EXTREMITY_CHANGE_FIELD]
                for row in group_rows
                if row[MEAN_EXTREMITY_CHANGE_FIELD] is not None
            ]

            signed_drift_mean = statistics.fmean(signed_drifts) if signed_drifts else None
            signed_drift_std = (
                statistics.stdev(signed_drifts) if len(signed_drifts) > 1 else 0.0
            ) if signed_drifts else None
            signed_drift_min = min(signed_drifts) if signed_drifts else None
            signed_drift_max = max(signed_drifts) if signed_drifts else None

            extremity_change_mean = (
                statistics.fmean(extremity_changes) if extremity_changes else None
            )
            extremity_change_std = (
                statistics.stdev(extremity_changes) if len(extremity_changes) > 1 else 0.0
            ) if extremity_changes else None
            extremity_change_min = min(extremity_changes) if extremity_changes else None
            extremity_change_max = max(extremity_changes) if extremity_changes else None

            grouped_summary_rows.append(
                {
                    "start_policy": start_policy,
                    "start_policy_label": start_policy_label,
                    "step_count": step_count,
                    "runs_aggregated": len(group_rows),
                    "available_start_nodes": group_rows[0]["available_start_nodes"],
                    "selected_start_nodes": group_rows[0]["selected_start_nodes"],
                    "walks_per_start": group_rows[0]["walks_per_start"],
                    "signed_drift_mean": signed_drift_mean,
                    "signed_drift_std": signed_drift_std,
                    "signed_drift_min": signed_drift_min,
                    "signed_drift_max": signed_drift_max,
                    "extremity_change_mean": extremity_change_mean,
                    "extremity_change_std": extremity_change_std,
                    "extremity_change_min": extremity_change_min,
                    "extremity_change_max": extremity_change_max,
                }
            )

            presentation_rows.append(
                {
                    "start group": start_policy_label,
                    "steps per walk": step_count,
                    "signed ideological drift": signed_drift_mean,
                    "extremity change": extremity_change_mean,
                    "how to read signed ideological drift": (
                        "Positive values mean the network pushes Right overall; "
                        "negative values mean it pushes Left overall."
                    ),
                    "how to read extremity change": (
                        "Positive values mean walks end farther from the center; "
                        "negative values mean they end closer to the center."
                    ),
                }
            )

    return grouped_summary_rows, presentation_rows


def _build_experiment_metrics_summary(per_run_rows):
    """
    Build one experiment-level headline summary from all repeated runs.

    WHY THIS EXISTS:
        The baseline run has one obvious metrics dictionary because it is one
        simulation. Experiment mode has many repeated runs, so the CLI needs a
        compact rolled-up summary that is clearly different from the baseline
        pass above.
    """
    total_trajectories = sum(row[TRAJECTORY_COUNT_FIELD] for row in per_run_rows)
    total_valid_drifts = sum(row[VALID_DRIFT_COUNT_FIELD] for row in per_run_rows)

    weighted_mean_drift = None
    if total_valid_drifts:
        weighted_mean_drift = sum(
            row[MEAN_DRIFT_FIELD] * row[VALID_DRIFT_COUNT_FIELD]
            for row in per_run_rows
            if row[MEAN_DRIFT_FIELD] is not None
        ) / total_valid_drifts

    weighted_mean_absolute_drift = None
    if total_valid_drifts:
        weighted_mean_absolute_drift = sum(
            row[MEAN_ABSOLUTE_DRIFT_FIELD] * row[VALID_DRIFT_COUNT_FIELD]
            for row in per_run_rows
            if row[MEAN_ABSOLUTE_DRIFT_FIELD] is not None
        ) / total_valid_drifts

    weighted_mean_extremity_change = None
    if total_trajectories:
        weighted_mean_extremity_change = sum(
            row[MEAN_EXTREMITY_CHANGE_FIELD] * row[TRAJECTORY_COUNT_FIELD]
            for row in per_run_rows
            if row[MEAN_EXTREMITY_CHANGE_FIELD] is not None
        ) / total_trajectories

    signed_drift_values = [
        row[MEAN_DRIFT_FIELD]
        for row in per_run_rows
        if row[MEAN_DRIFT_FIELD] is not None
    ]
    extremity_change_values = [
        row[MEAN_EXTREMITY_CHANGE_FIELD]
        for row in per_run_rows
        if row[MEAN_EXTREMITY_CHANGE_FIELD] is not None
    ]

    first_row = per_run_rows[0] if per_run_rows else {}

    return {
        TRAJECTORY_COUNT_FIELD: total_trajectories,
        VALID_DRIFT_COUNT_FIELD: total_valid_drifts,
        MEAN_DRIFT_FIELD: weighted_mean_drift,
        MEAN_ABSOLUTE_DRIFT_FIELD: weighted_mean_absolute_drift,
        MEAN_EXTREMITY_CHANGE_FIELD: weighted_mean_extremity_change,
        ASSORTATIVITY_FIELD: first_row.get(ASSORTATIVITY_FIELD),
        CLUSTERING_FIELD: first_row.get(CLUSTERING_FIELD),
        "signed_drift_min": min(signed_drift_values) if signed_drift_values else None,
        "signed_drift_max": max(signed_drift_values) if signed_drift_values else None,
        "extremity_change_min": (
            min(extremity_change_values) if extremity_change_values else None
        ),
        "extremity_change_max": (
            max(extremity_change_values) if extremity_change_values else None
        ),
    }


def run_pipeline(
    nodes_path=DEFAULT_NODES_PATH,
    edges_path=DEFAULT_EDGES_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    num_steps=DEFAULT_NUM_STEPS,
    walks_per_start=DEFAULT_WALKS_PER_START,
    seed=DEFAULT_RANDOM_SEED,
    mode=DEFAULT_MODE,
    show_progress=None,
):
    """
    Execute the full project pipeline end to end.

    RETURNS:
        dict: A small run summary useful for CLI output and testing.
    """
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unsupported mode '{mode}'. Choose from: {sorted(VALID_MODES)}"
        )

    progress_enabled = _should_show_progress(show_progress, sys.stdout)

    # Build the graph and attach ideology scores.
    graph = prepare_graph(nodes_path, edges_path)

    # Decide where our simulated walks are allowed to begin.
    start_nodes = choose_start_nodes(graph)

    # If the list is empty, we stop early with a clear error message.
    # Raising an error means: stop the program here and explain why.
    if not start_nodes:
        raise ValueError(
            "No valid start nodes were found. "
            "The graph needs scored nodes with outgoing edges."
        )

    # random.Random(seed) creates a random-number generator.
    # The seed makes the results reproducible.
    rng = random.Random(seed)
    graph_metrics = compute_graph_metrics(graph)

    baseline_progress_bar = _CliProgressBar(
        total=len(start_nodes) * walks_per_start,
        label="Baseline simulation",
        stream=sys.stdout,
        enabled=progress_enabled,
    )
    baseline_progress_bar.set_context(
        current_configuration_index=1,
        total_configurations=1,
        start_policy_label="Baseline full-start run",
        step_count=num_steps,
        seed=seed,
        selected_start_nodes=len(start_nodes),
        available_start_nodes=len(start_nodes),
        walks_per_start=walks_per_start,
    )

    # Simulate the recommendation-following behavior.
    trajectories = simulate_walks(
        graph,
        start_nodes=start_nodes,
        num_steps=num_steps,
        walks_per_start=walks_per_start,
        rng=rng,
        progress_callback=baseline_progress_bar.update if progress_enabled else None,
    )
    baseline_progress_bar.finish("completed")

    # Convert the graph + walks into summary numbers.
    metrics_dict = compute_all_metrics(
        graph,
        trajectories,
        graph_metrics=graph_metrics,
    )

    # Write the figures and CSV output files to disk.
    generate_all_figures(graph, trajectories, metrics_dict, output_dir=str(output_dir))

    # The baseline summary is the "single-run answer" that already existed in
    # the project. In experiment mode we keep these same keys at the top level
    # so older calling code still sees the familiar baseline-style results.
    baseline_summary = {
        "mode": DEFAULT_MODE,
        "graph": graph,
        "trajectories": trajectories,
        "metrics": metrics_dict,
        "num_start_nodes": len(start_nodes),
        "num_walks": len(trajectories),
        "output_dir": Path(output_dir),
    }

    if mode == DEFAULT_MODE:
        return baseline_summary

    # Experiment mode intentionally starts from the already-computed baseline
    # graph and valid start nodes above. That keeps the workflow easy to teach:
    # same graph -> same simulator -> more repeated runs -> extra summary tables.
    experiment_total_walks = _estimate_total_experiment_walks(graph, start_nodes, seed)
    experiment_configuration_count = _count_total_experiment_configurations()
    experiment_progress_bar = _CliProgressBar(
        total=experiment_total_walks,
        label="Experiment simulation",
        stream=sys.stdout,
        enabled=progress_enabled,
    )
    per_run_rows = _run_repeated_experiments(
        graph,
        start_nodes,
        seed,
        graph_metrics=graph_metrics,
        progress_bar=experiment_progress_bar if progress_enabled else None,
    )
    experiment_progress_bar.finish("completed")
    grouped_summary_rows, presentation_rows = _summarize_experiment_results(per_run_rows)

    generate_experiment_outputs(
        per_run_rows,
        grouped_summary_rows,
        presentation_rows,
        output_dir=str(output_dir),
    )

    experiment_metrics = _build_experiment_metrics_summary(per_run_rows)

    return {
        "mode": EXPERIMENT_MODE,
        "graph": graph,
        "trajectories": trajectories,
        "metrics": experiment_metrics,
        "num_start_nodes": len(start_nodes),
        "num_walks": experiment_total_walks,
        "output_dir": Path(output_dir),
        "baseline_summary": baseline_summary,
        "per_run_rows": per_run_rows,
        "grouped_summary_rows": grouped_summary_rows,
        "presentation_rows": presentation_rows,
        "experiment_total_walks": experiment_total_walks,
        "experiment_configuration_count": experiment_configuration_count,
        "experiment_max_start_nodes_per_policy": EXPERIMENT_MAX_START_NODES_PER_POLICY,
    }


def build_argument_parser():
    """
    Create the command-line parser.

    "Command-line arguments" are the extra options you can type after a
    command in the terminal.

    Example:
        python3 src/run_pipeline.py --num-steps 15 --seed 123

    In that example:
        --num-steps 15
    and
        --seed 123
    are command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run the full ideological-drift pipeline from CSV inputs to "
            "generated figures and summary metrics."
        )
    )

    parser.add_argument(
        "--nodes-path",
        default=str(DEFAULT_NODES_PATH),
        help="Path to vis_channel_stats.csv",
    )
    parser.add_argument(
        "--edges-path",
        default=str(DEFAULT_EDGES_PATH),
        help="Path to vis_channel_recs2.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where results/figures and results/tables are written",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=DEFAULT_NUM_STEPS,
        help="Maximum number of moves per walk",
    )
    parser.add_argument(
        "--walks-per-start",
        type=int,
        default=DEFAULT_WALKS_PER_START,
        help="How many walks to run from each starting node",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Random seed used for reproducible walks",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default=DEFAULT_MODE,
        help=(
            "baseline = current single run; "
            "experiment = baseline output plus repeated experiment tables"
        ),
    )

    return parser


def main(argv=None):
    """
    Main entrypoint for this script.

    In plain English, this function is the "start the engine" function.
    Another file can call this function so the user does not need to know how
    the rest of the pipeline is wired together.
    """
    # Build the parser object that knows which arguments are allowed.
    parser = build_argument_parser()

    # Parse the actual values the user typed in the terminal.
    # If the user typed nothing extra, the defaults are used.
    args = parser.parse_args(argv)

    # Run the real project using either the defaults or the user's overrides.
    summary = run_pipeline(
        nodes_path=args.nodes_path,
        edges_path=args.edges_path,
        output_dir=args.output_dir,
        num_steps=args.num_steps,
        walks_per_start=args.walks_per_start,
        seed=args.seed,
        mode=args.mode,
        show_progress=True,
    )

    # Pull the metrics dictionary out of the returned summary so the code below
    # is shorter and easier to read.
    # Print a simple human-readable summary in the terminal.
    print("Pipeline completed successfully.")
    print(f"Mode: {summary['mode']}")
    print(f"Start nodes used: {summary['num_start_nodes']}")
    print(f"Output directory: {summary['output_dir']}")
    if summary["mode"] == EXPERIMENT_MODE:
        metrics_dict = summary["metrics"]
        baseline_metrics = summary["baseline_summary"]["metrics"]
        figures_dir = summary["output_dir"] / "figures"
        tables_dir = summary["output_dir"] / "tables"
        print(
            "Baseline reference: "
            f"{summary['baseline_summary']['num_walks']} walks, "
            f"mean drift {baseline_metrics['mean_drift']}, "
            "mean extremity change "
            f"{baseline_metrics['mean_extremity_change']}"
        )
        print(f"Repeated experiment walks generated: {summary['num_walks']:,}")
        print(
            "Experiment weighted mean drift across repeated runs: "
            f"{metrics_dict['mean_drift']}"
        )
        print(
            "Experiment weighted mean extremity change across repeated runs: "
            f"{metrics_dict['mean_extremity_change']}"
        )
        print(
            "Experiment signed drift range across repeated runs: "
            f"{metrics_dict['signed_drift_min']} to {metrics_dict['signed_drift_max']}"
        )
        print(
            "Experiment extremity-change range across repeated runs: "
            f"{metrics_dict['extremity_change_min']} to "
            f"{metrics_dict['extremity_change_max']}"
        )
        print(
            "Shared graph structure stats: "
            f"assortativity {metrics_dict['ideology_assortativity']}, "
            f"average clustering {metrics_dict['average_clustering']}"
        )
        print(
            "Experiment plan: "
            f"{summary['experiment_configuration_count']} configurations, "
            f"{summary['experiment_total_walks']:,} repeated walks"
        )
        print(
            "Experiment start-node cap per policy: "
            f"{summary['experiment_max_start_nodes_per_policy']:,}"
        )
        print(f"Repeated experiment runs: {len(summary['per_run_rows'])}")
        print("Experiment figures written:")
        print(f"  - {figures_dir / 'experiment_signed_drift_summary.png'}")
        print(f"  - {figures_dir / 'experiment_extremity_change_summary.png'}")
        print("Experiment tables written:")
        print(f"  - {tables_dir / 'experiment_per_run.csv'}")
        print(f"  - {tables_dir / 'experiment_grouped_summary.csv'}")
        print(f"  - {tables_dir / 'presentation_headline_metrics.csv'}")
    else:
        metrics_dict = summary["metrics"]
        print(f"Walks generated: {summary['num_walks']}")
        print(f"Mean drift: {metrics_dict['mean_drift']}")
        print(f"Mean extremity change: {metrics_dict['mean_extremity_change']}")
        print(f"Ideology assortativity: {metrics_dict['ideology_assortativity']}")
        print(f"Average clustering: {metrics_dict['average_clustering']}")


if __name__ == "__main__":
    # This still lets advanced users run this file directly if they want to,
    # but the simpler beginner-facing entrypoint is the root-level run.py file.
    main()
