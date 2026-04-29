# ==============================================================================
# MODULE: visualize.py
# PURPOSE: Generate publication-quality figures and summary tables from the
#          pipeline's graph, trajectories, and metrics.
# ==============================================================================
#
# This is the FIFTH and FINAL module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#                                                                           ^^^^^^^^^^^^
#
# WHAT THIS MODULE DOES:
#   At this point in the pipeline, we have:
#     1. A recommendation graph with ideology scores on every node
#     2. Simulated user trajectories (random walks through the graph)
#     3. Numerical summaries (drift, extremity change, assortativity, clustering)
#
#   But numbers alone are not enough for a research presentation.
#   An academic committee or policy audience needs FIGURES — visual evidence
#   that makes patterns immediately obvious.
#
#   This module turns the pipeline's outputs into four figures and one table:
#
#     A. IDEOLOGY DISTRIBUTION (bar chart)
#        Shows how many channels are Left, Center, and Right.
#        This is the first thing a reader wants to know about the dataset:
#        "What does the landscape look like?"
#
#     B. DRIFT DISTRIBUTION (histogram)
#        Shows the distribution of ideological drift across all walks.
#        Drift = final_score − initial_score for each simulated walk.
#        If the histogram is centered around zero → no systematic drift.
#        If it leans positive → users tend to move Right over time.
#        If it leans negative → users tend to move Left over time.
#
#     C. TRAJECTORY SAMPLE (line plot)
#        Plots a sample of individual walks: ideology score (y-axis) vs.
#        step number (x-axis). This lets the audience SEE how individual
#        users move through the network over time.
#
#     D. EXTREMITY DISTRIBUTION (histogram)
#        Shows whether walks tend to push users AWAY from the center
#        (toward ideological extremes) or TOWARD the center.
#        Extremity change = |final_score| − |initial_score|.
#        Positive values mean the user ended farther from center.
#
#     E. SUMMARY METRICS TABLE (CSV)
#        A single-row CSV file with all computed metrics, suitable for
#        inclusion in a paper or presentation slide.
#
# WHY NOT DRAW THE FULL NETWORK GRAPH?
#   With 7,079 nodes and ~400,000 edges, a node-and-edge network diagram
#   becomes an unreadable "hairball." The bar chart in (A) conveys the
#   structural breakdown of the network far more clearly.
#
# DESIGN DECISIONS:
#   - matplotlib.use("Agg") is called at the module level. "Agg" is a
#     backend that renders figures to image files without needing a screen
#     or GUI window. This makes the code work on servers, CI systems, and
#     headless environments.
#   - Every plotting function accepts an explicit output_path parameter.
#     This means tests can write to a temporary directory (tmp_path) and
#     the real pipeline can write to results/figures/.
#   - seaborn is used for default styling (sns.set_theme). It makes
#     matplotlib plots look more polished with minimal effort.
#   - Each function saves the figure and then closes it with plt.close().
#     This prevents memory leaks when generating many plots in sequence.
#   - generate_all_figures() is a convenience wrapper. It calls every
#     plotting function and the table saver in one shot, creating output
#     directories if they do not exist.
#
# ==============================================================================


import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")  # Headless backend — must be set BEFORE importing pyplot.

import matplotlib.pyplot as plt
import seaborn as sns

from src.ideology import SCORE_ATTRIBUTE
from src.metrics import (
	compute_walk_drift,
	compute_walk_extremity_change,
	TRAJECTORY_COUNT_FIELD,
	VALID_DRIFT_COUNT_FIELD,
	MEAN_DRIFT_FIELD,
	MEAN_ABSOLUTE_DRIFT_FIELD,
	MEAN_EXTREMITY_CHANGE_FIELD,
	ASSORTATIVITY_FIELD,
	CLUSTERING_FIELD,
)
from src.simulator import SCORE_FIELD, STEP_FIELD


# --- STYLING ------------------------------------------------------------------

# Apply seaborn's default theme to all plots created by this module.
# "whitegrid" adds subtle horizontal grid lines that help readers
# estimate values without cluttering the figure.
sns.set_theme(style="whitegrid")


# --- CONSTANTS ----------------------------------------------------------------

# The three ideology categories and their matching colors.
# Blue is traditionally associated with liberal/left politics in US media.
# Red is traditionally associated with conservative/right politics.
# Gray signals neutrality for center.
IDEOLOGY_LABELS = ["Left (−1)", "Center (0)", "Right (+1)"]
IDEOLOGY_COLORS = ["#4472C4", "#A5A5A5", "#C0504D"]

# Default figure size in inches (width, height).
# 8×5 is a good default for wide charts that fit well in slides.
FIGURE_SIZE = (8, 5)

# The pipeline only owns a small set of generated file types inside results/.
# We clean these up before every run so repeated Play-button executions update
# the same artifacts instead of leaving stale screenshots behind.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


def _remove_files_with_extensions(directory, extensions):
	"""
	Delete files in one directory when their extension matches the set.

	WHY THIS EXISTS:
		The user wants repeated runs to refresh the same result bundle rather
		than accumulate old images or CSV files. This helper gives the cleanup
		logic one small, testable job: scan a directory and delete only the
		file types the pipeline itself owns.
	"""
	if not os.path.isdir(directory):
		return

	for filename in os.listdir(directory):
		filepath = os.path.join(directory, filename)
		_, extension = os.path.splitext(filename)

		if os.path.isfile(filepath) and extension.lower() in extensions:
			os.remove(filepath)


def prepare_output_directories(output_dir):
	"""
	Create the results folders and clear stale generated outputs.

	WHAT GETS REMOVED:
		- image files directly inside output_dir
		- image files inside output_dir/figures
		- table files are intentionally preserved

	WHY THIS IS SAFE:
		The project treats results/ as a generated-output area. Cleaning only
		the image bundle keeps repeated baseline runs tidy without touching the
		actual source data, project code, or older CSV tables the user may want
		to compare later.

	RETURNS:
		tuple(str, str): The figures directory path and the tables directory
		path so the caller can immediately write the new outputs.
	"""
	figures_dir = os.path.join(output_dir, "figures")
	tables_dir = os.path.join(output_dir, "tables")

	os.makedirs(output_dir, exist_ok=True)
	os.makedirs(figures_dir, exist_ok=True)
	os.makedirs(tables_dir, exist_ok=True)

	_remove_files_with_extensions(output_dir, IMAGE_EXTENSIONS)
	_remove_files_with_extensions(figures_dir, IMAGE_EXTENSIONS)

	return figures_dir, tables_dir


def save_rows_table(rows, output_path, fieldnames):
	"""
	Save a list of dictionaries as a CSV table with a fixed column order.

	WHY THIS HELPER EXISTS:
		The original pipeline wrote only one summary row. The experiment mode
		needs several tables with many rows, but we still want the output code
		to stay easy to read: define the columns once, then write rows in that
		exact order.
	"""
	with open(output_path, "w", newline="") as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
		for row in rows:
			writer.writerow({field: row.get(field, "") for field in fieldnames})


def plot_experiment_metric_summary(
	summary_rows,
	output_path,
	metric_field,
	title,
	y_label,
):
	"""
	Plot one experiment-wide summary figure for a single headline metric.

	WHAT THIS FIGURE SHOWS:
		Each line is one start-node strategy. The x-axis is the number of steps
		per walk. The y-axis is the average result for the chosen metric after
		combining the repeated runs across seeds.

	WHY THIS MATTERS:
		The user wants to present only two simple questions to a non-technical
		audience. These summary figures stay tightly focused on those questions
		instead of reproducing the whole technical figure bundle.
	"""
	strategy_labels = []
	for row in summary_rows:
		label = row["start_policy_label"]
		if label not in strategy_labels:
			strategy_labels.append(label)

	colors = ["#4472C4", "#A5A5A5", "#C0504D"]
	color_map = {
		label: colors[index % len(colors)]
		for index, label in enumerate(strategy_labels)
	}

	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	for strategy_label in strategy_labels:
		strategy_rows = [
			row for row in summary_rows
			if row["start_policy_label"] == strategy_label
		]
		strategy_rows.sort(key=lambda row: row["step_count"])

		steps = [row["step_count"] for row in strategy_rows]
		values = [row[metric_field] for row in strategy_rows]

		ax.plot(
			steps,
			values,
			marker="o",
			linewidth=2,
			color=color_map[strategy_label],
			label=strategy_label,
		)

	ax.axhline(0.0, color="black", linestyle="--", linewidth=1, alpha=0.6)
	ax.set_xlabel("Steps per walk", fontsize=12)
	ax.set_ylabel(y_label, fontsize=12)
	ax.set_title(title, fontsize=14)
	ax.legend(fontsize=10)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_experiment_step_trend_summary(
	summary_rows,
	output_path,
	metric_field,
	std_field,
	title,
	y_label,
):
	"""
	Plot a step-by-step repeated-experiment trend figure with uncertainty bands.

	WHAT THIS FIGURE SHOWS:
		Each line is one start-node strategy. The x-axis is the step index within
		the walk, and the y-axis is the average value of the chosen metric at that
		step relative to the starting node. The shaded band shows plus/minus one
		standard deviation across repeated seeds.

	WHY THIS MATTERS:
		This figure is the answer to the reasonable question, "Did you only look
		at the final node?" It uses the intermediate trajectory steps directly,
		so the audience can see how the average walk changes over time rather than
		seeing only the endpoint summary.
	"""
	strategy_labels = []
	for row in summary_rows:
		label = row["start_policy_label"]
		if label not in strategy_labels:
			strategy_labels.append(label)

	colors = ["#4472C4", "#A5A5A5", "#C0504D"]
	color_map = {
		label: colors[index % len(colors)]
		for index, label in enumerate(strategy_labels)
	}
	longest_step_count = max(row["step_count"] for row in summary_rows)

	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	for strategy_label in strategy_labels:
		strategy_rows = [
			row for row in summary_rows
			if row["start_policy_label"] == strategy_label
			and row["step_count"] == longest_step_count
		]
		strategy_rows.sort(key=lambda row: row["step_index"])

		steps = [row["step_index"] for row in strategy_rows]
		values = [row[metric_field] for row in strategy_rows]
		standard_deviations = [row[std_field] or 0.0 for row in strategy_rows]
		lower_bound = [
			value - standard_deviation
			for value, standard_deviation in zip(values, standard_deviations)
		]
		upper_bound = [
			value + standard_deviation
			for value, standard_deviation in zip(values, standard_deviations)
		]
		line_color = color_map[strategy_label]

		ax.plot(
			steps,
			values,
			marker="o",
			linewidth=2,
			color=line_color,
			label=strategy_label,
		)
		ax.fill_between(
			steps,
			lower_bound,
			upper_bound,
			color=line_color,
			alpha=0.18,
		)

	ax.axhline(0.0, color="black", linestyle="--", linewidth=1, alpha=0.6)
	ax.set_xlabel("Step number within walk", fontsize=12)
	ax.set_ylabel(y_label, fontsize=12)
	ax.set_title(f"{title} ({longest_step_count}-step runs)", fontsize=14)
	ax.legend(fontsize=10)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def generate_experiment_outputs(
	per_run_rows,
	grouped_summary_rows,
	presentation_rows,
	step_trend_summary_rows,
	output_dir="results",
):
	"""
	Write the repeated-experiment outputs in one place.

	OUTPUTS CREATED:
		1. Two endpoint summary figures, one for each headline question
		2. Two step-by-step trend figures that use the intermediate walk steps
		3. A per-run CSV with one row per strategy/step/seed combination
		4. A grouped summary CSV averaged across seeds
		5. A step-trend summary CSV averaged across seeds
		6. A plain-English presentation CSV focused on the two main findings

	This mirrors generate_all_figures(), but for the repeated experiment
	mode instead of the single baseline run.
	"""
	figures_dir = os.path.join(output_dir, "figures")
	tables_dir = os.path.join(output_dir, "tables")
	os.makedirs(figures_dir, exist_ok=True)
	os.makedirs(tables_dir, exist_ok=True)

	plot_experiment_metric_summary(
		grouped_summary_rows,
		os.path.join(figures_dir, "experiment_signed_drift_summary.png"),
		metric_field="signed_drift_mean",
		title="Average Ideology Direction Change Across Repeated Simulations",
		y_label="Average ideology direction change",
	)

	plot_experiment_metric_summary(
		grouped_summary_rows,
		os.path.join(figures_dir, "experiment_extremity_change_summary.png"),
		metric_field="extremity_change_mean",
		title="Average Extremity Change Across Repeated Simulations",
		y_label="Average extremity change",
	)

	plot_experiment_step_trend_summary(
		step_trend_summary_rows,
		os.path.join(figures_dir, "experiment_stepwise_signed_drift.png"),
		metric_field="signed_drift_mean",
		std_field="signed_drift_std",
		title="Step-by-Step Mean Signed Drift Across Repeated Simulations",
		y_label="Mean signed drift from start",
	)

	plot_experiment_step_trend_summary(
		step_trend_summary_rows,
		os.path.join(figures_dir, "experiment_stepwise_extremity_change.png"),
		metric_field="extremity_change_mean",
		std_field="extremity_change_std",
		title="Step-by-Step Mean Extremity Change Across Repeated Simulations",
		y_label="Mean extremity change from start",
	)

	save_rows_table(
		per_run_rows,
		os.path.join(tables_dir, "experiment_per_run.csv"),
		fieldnames=[
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
		],
	)

	save_rows_table(
		grouped_summary_rows,
		os.path.join(tables_dir, "experiment_grouped_summary.csv"),
		fieldnames=[
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
		],
	)

	save_rows_table(
		step_trend_summary_rows,
		os.path.join(tables_dir, "experiment_step_trend_summary.csv"),
		fieldnames=[
			"start_policy",
			"start_policy_label",
			"step_count",
			"step_index",
			"runs_aggregated",
			"mean_valid_observation_count",
			"signed_drift_mean",
			"signed_drift_std",
			"extremity_change_mean",
			"extremity_change_std",
		],
	)

	save_rows_table(
		presentation_rows,
		os.path.join(tables_dir, "presentation_headline_metrics.csv"),
		fieldnames=[
			"start group",
			"steps per walk",
			"signed ideological drift",
			"extremity change",
			"how to read signed ideological drift",
			"how to read extremity change",
		],
	)


# --- FUNCTIONS ----------------------------------------------------------------

def plot_ideology_distribution(G, output_path):
	"""
	Create a bar chart showing how many nodes belong to each ideology category.

	WHAT THIS FIGURE SHOWS:
		Three bars — one for Left, one for Center, one for Right — showing
		the count of channels in each category. This reveals the composition
		of the recommendation network at a glance.

	WHY THIS MATTERS:
		The Recfluence dataset has a notable right-skew (more Right channels
		than Left). Before interpreting any drift results, the audience needs
		to understand this baseline asymmetry.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph. Each node is
			expected to have an IDEOLOGY_SCORE attribute (float or None).
		output_path (str): Full file path where the PNG will be saved.
			Example: "results/figures/ideology_distribution.png"

	RETURNS:
		None — the figure is saved to disk.
	"""
	# Count how many nodes have each ideology score.
	# We iterate over every node's attributes and check IDEOLOGY_SCORE.
	#
	# G.nodes(data=True) returns pairs of (node_id, attribute_dict).
	# We only care about the attribute_dict to read the score.
	left_count = 0
	center_count = 0
	right_count = 0

	for _, attrs in G.nodes(data=True):
		score = attrs.get(SCORE_ATTRIBUTE)
		if score == -1.0:
			left_count += 1
		elif score == 0.0:
			center_count += 1
		elif score == 1.0:
			right_count += 1
		# Nodes with score = None (unknown ideology) are not counted.
		# They are excluded rather than silently placed in a category.

	counts = [left_count, center_count, right_count]

	# Create the figure and one set of axes (the plotting area).
	# fig is the overall canvas; ax is the coordinate system inside it.
	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	# Draw the bar chart.
	# ax.bar() takes:
	#   - x positions (the label strings)
	#   - heights (the counts)
	#   - color (one color per bar)
	ax.bar(IDEOLOGY_LABELS, counts, color=IDEOLOGY_COLORS, edgecolor="black")

	# Add a count label on top of each bar so readers can see exact values.
	for i, count in enumerate(counts):
		ax.text(
			i,                    # x position: the bar's index
			count + max(counts) * 0.02,  # y position: slightly above the bar
			str(count),           # the text: the count as a string
			ha="center",          # horizontally centered over the bar
			fontsize=11,
			fontweight="bold",
		)

	ax.set_xlabel("Ideology Category", fontsize=12)
	ax.set_ylabel("Number of Channels", fontsize=12)
	ax.set_title("Ideology Distribution of Channels in the Network", fontsize=14)

	# tight_layout() adjusts padding so labels and titles don't get clipped.
	fig.tight_layout()

	# Save the figure to the specified path.
	# dpi=150 gives a resolution suitable for both slides and print.
	fig.savefig(output_path, dpi=150)

	# Close the figure to free memory.
	# Without this, matplotlib keeps every figure in memory, which adds up
	# quickly when generating multiple plots in sequence.
	plt.close(fig)


def plot_drift_distribution(trajectories, output_path):
	"""
	Create a histogram of per-walk ideology drift values.

	WHAT THIS FIGURE SHOWS:
		Each bar represents how many walks had a drift value in that range.
		Drift = final_score − initial_score.

		If the histogram clusters around zero → recommendations do not
		systematically push users left or right.
		If the histogram shifts right → users tend to drift rightward.
		A vertical dashed line marks the mean drift for quick reference.

	PARAMETERS:
		trajectories (list[list[dict]]): Collection of walk trajectories.
		output_path (str): Full file path where the PNG will be saved.

	RETURNS:
		None — the figure is saved to disk.
	"""
	# Compute drift for every trajectory, skipping any where the endpoints
	# have missing ideology scores (drift = None).
	drifts = []
	for trajectory in trajectories:
		drift = compute_walk_drift(trajectory)
		if drift is not None:
			drifts.append(drift)

	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	if drifts:
		# Draw the histogram.
		# bins="auto" lets matplotlib choose a sensible number of bins
		# based on the data range and sample size.
		ax.hist(drifts, bins="auto", color="#4472C4", edgecolor="black", alpha=0.7)

		# Draw a vertical dashed line at the mean drift.
		# This gives the audience one number to anchor their reading:
		# "On average, walks drifted by X."
		mean_drift = statistics.mean(drifts)
		ax.axvline(
			mean_drift,
			color="red",
			linestyle="--",
			linewidth=2,
			label=f"Mean drift = {mean_drift:.4f}",
		)
		ax.legend(fontsize=11)
	else:
		# If there are no valid drifts, show a message instead of an empty plot.
		ax.text(
			0.5, 0.5,
			"No valid drift data available",
			ha="center", va="center",
			transform=ax.transAxes,
			fontsize=14,
		)

	ax.set_xlabel("Ideology Drift (final − initial)", fontsize=12)
	ax.set_ylabel("Number of Walks", fontsize=12)
	ax.set_title("Distribution of Ideology Drift Across All Walks", fontsize=14)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_trajectory_sample(trajectories, output_path, max_lines=3):
	"""
	Plot a sample of individual walk trajectories as line plots.

	WHAT THIS FIGURE SHOWS:
		Each line represents one simulated user navigating the recommendation
		network. The x-axis is the step number (0, 1, 2, ...) and the y-axis
		is the ideology score at that step.

		This is the most intuitive figure in the analysis. It shows the
		audience EXACTLY what a "random walk through the recommendation
		network" looks like.

	WHY SAMPLE INSTEAD OF PLOTTING ALL?
		If the pipeline generates 1,500 trajectories, plotting every one
		creates an unreadable mess of overlapping lines. A sample of 20
		gives a representative view without visual clutter.

	PARAMETERS:
		trajectories (list[list[dict]]): Collection of walk trajectories.
		output_path (str): Full file path where the PNG will be saved.
		max_lines (int): Maximum number of trajectories to display.
			Default is 3. If fewer trajectories exist, all are shown.

	RETURNS:
		None — the figure is saved to disk.
	"""
	# The presentation version of this figure is intentionally small.
	# Three walks are enough to show the idea without turning the chart
	# into a tangle of overlapping lines.
	if max_lines < 1:
		raise ValueError("max_lines must be at least 1.")

	# Select the sample.
	# If there are fewer trajectories than max_lines, use all of them.
	# Otherwise, take an evenly spaced sample using list slicing.
	#
	# Why evenly spaced instead of random? Because this function should
	# produce the same figure every time for reproducibility.
	# A random sample would change with every run.
	if len(trajectories) <= max_lines:
		sample = trajectories
	else:
		# Calculate the step size to get approximately max_lines items.
		# For example, if we have 1500 trajectories and want 20:
		#   step = 1500 // 20 = 75
		#   sample = trajectories[::75] → picks every 75th trajectory
		step = len(trajectories) // max_lines
		sample = trajectories[::step][:max_lines]

	fig, ax = plt.subplots(figsize=FIGURE_SIZE)
	walk_colors = ["#1F77B4", "#FF7F0E", "#2CA02C"]
	walk_handles = []

	for walk_number, trajectory in enumerate(sample, start=1):
		# Extract the step numbers and ideology scores from the trajectory.
		# Each trajectory is a list of dictionaries like:
		#   [{"step": 0, "node_id": "ch_L1", "ideology_score": -1.0}, ...]
		steps = [record[STEP_FIELD] for record in trajectory]
		scores = [record[SCORE_FIELD] for record in trajectory]
		walk_color = walk_colors[(walk_number - 1) % len(walk_colors)]

		# Plot one line per trajectory.
		# The walk legend is separate from the ideology legend so the viewer
		# can tell both "which line is which walk" and "what the reference
		# ideology levels mean" without the two ideas being mixed together.
		(walk_line,) = ax.plot(
			steps,
			scores,
			alpha=0.95,
			linewidth=2.5,
			marker="o",
			markersize=4,
			color=walk_color,
			label=f"Walk {walk_number}",
		)
		walk_handles.append(walk_line)

	# Draw horizontal reference lines at the three ideology levels.
	# These help the audience see whether paths cluster near one level.
	left_line = ax.axhline(
		-1.0,
		color="#4472C4",
		linestyle=":",
		alpha=0.6,
		linewidth=1.5,
		label="Left (−1)",
	)
	center_line = ax.axhline(
		0.0,
		color="#7F7F7F",
		linestyle=":",
		alpha=0.6,
		linewidth=1.5,
		label="Center (0)",
	)
	right_line = ax.axhline(
		1.0,
		color="#C0504D",
		linestyle=":",
		alpha=0.6,
		linewidth=1.5,
		label="Right (+1)",
	)

	ax.set_xlabel("Step Number", fontsize=12)
	ax.set_ylabel("Ideology Score", fontsize=12)
	ax.set_title(f"Sample of {len(sample)} Walk Trajectories", fontsize=14)
	ax.set_ylim(-1.3, 1.3)  # Slight padding beyond the score range.

	walk_legend = ax.legend(
		handles=walk_handles,
		title="Walk Key",
		loc="upper left",
		bbox_to_anchor=(1.02, 1.0),
		fontsize=9,
		title_fontsize=10,
		framealpha=0.95,
	)
	ax.add_artist(walk_legend)
	ax.legend(
		handles=[left_line, center_line, right_line],
		title="Ideology Key",
		loc="lower left",
		bbox_to_anchor=(1.02, 0.0),
		fontsize=9,
		title_fontsize=10,
		framealpha=0.95,
	)

	fig.tight_layout(rect=(0.0, 0.0, 0.82, 1.0))
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_extremity_distribution(trajectories, output_path):
	"""
	Create a histogram of per-walk extremity change values.

	WHAT THIS FIGURE SHOWS:
		Extremity change = |final_score| − |initial_score|.
		Positive values mean the user ended farther from the ideological
		center than they started (moved toward an extreme).
		Negative values mean the user ended closer to center.

		This is a more nuanced metric than raw drift. A user could drift
		from Left to Right (large drift) but stay the same distance from
		center (zero extremity change). Extremity change isolates the
		"radicalization" question: are users pushed toward ANY extreme?

	PARAMETERS:
		trajectories (list[list[dict]]): Collection of walk trajectories.
		output_path (str): Full file path where the PNG will be saved.

	RETURNS:
		None — the figure is saved to disk.
	"""
	extremity_changes = []
	for trajectory in trajectories:
		change = compute_walk_extremity_change(trajectory)
		if change is not None:
			extremity_changes.append(change)

	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	if extremity_changes:
		ax.hist(
			extremity_changes,
			bins="auto",
			color="#6AAB9C",
			edgecolor="black",
			alpha=0.7,
		)

		mean_change = statistics.mean(extremity_changes)
		ax.axvline(
			mean_change,
			color="red",
			linestyle="--",
			linewidth=2,
			label=f"Mean extremity change = {mean_change:.4f}",
		)
		ax.legend(fontsize=11)
	else:
		ax.text(
			0.5, 0.5,
			"No valid extremity data available",
			ha="center", va="center",
			transform=ax.transAxes,
			fontsize=14,
		)

	ax.set_xlabel("Extremity Change ( |final| − |initial| )", fontsize=12)
	ax.set_ylabel("Number of Walks", fontsize=12)
	ax.set_title("Distribution of Extremity Change Across All Walks", fontsize=14)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def save_metrics_table(metrics_dict, output_path):
	"""
	Save the summary metrics dictionary as a CSV file.

	WHAT THIS PRODUCES:
		A two-row CSV: one header row with metric names, and one data row
		with values. This format is easy to open in Excel, Google Sheets,
		or any data tool, and can be directly pasted into a report.

	PARAMETERS:
		metrics_dict (dict): The dictionary returned by compute_all_metrics().
			Expected keys: num_trajectories, num_valid_drifts, mean_drift,
			mean_absolute_drift, mean_extremity_change, ideology_assortativity,
			average_clustering.
		output_path (str): Full file path where the CSV will be saved.
			Example: "results/tables/summary_metrics.csv"

	RETURNS:
		None — the table is saved to disk.
	"""
	# Define the column order explicitly so the output is always consistent.
	# This uses the constant names imported from metrics.py.
	columns = [
		TRAJECTORY_COUNT_FIELD,
		VALID_DRIFT_COUNT_FIELD,
		MEAN_DRIFT_FIELD,
		MEAN_ABSOLUTE_DRIFT_FIELD,
		MEAN_EXTREMITY_CHANGE_FIELD,
		ASSORTATIVITY_FIELD,
		CLUSTERING_FIELD,
	]

	with open(output_path, "w", newline="") as csvfile:
		writer = csv.writer(csvfile)
		# Write the header row.
		writer.writerow(columns)
		# Write the data row.
		# For each column, look up the value in the dictionary.
		# If a key is missing (shouldn't happen, but safety first), write "N/A".
		writer.writerow([metrics_dict.get(col, "N/A") for col in columns])


def generate_all_figures(G, trajectories, metrics_dict, output_dir="results"):
	"""
	Generate all figures and the metrics table in one call.

	WHY A WRAPPER FUNCTION?
		The full pipeline runs all five stages in sequence. At the end,
		the caller has a graph, trajectories, and a metrics dictionary.
		This single function turns all of that into the complete set of
		output figures and tables, creating any necessary directories.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		trajectories (list[list[dict]]): All simulated walk trajectories.
		metrics_dict (dict): The summary from compute_all_metrics().
		output_dir (str): Root output directory. Figures go into
			output_dir/figures/ and tables go into output_dir/tables/.
			Default is "results".

	RETURNS:
		None — all outputs are saved to disk.
	"""
	# Create the output directories and clear stale generated outputs first.
	# This guarantees that repeated runs refresh the same result bundle instead
	# of leaving behind outdated screenshots or old CSV files.
	figures_dir, tables_dir = prepare_output_directories(output_dir)

	# Generate each figure, passing the full file path.
	plot_ideology_distribution(
		G,
		os.path.join(figures_dir, "ideology_distribution.png"),
	)

	plot_drift_distribution(
		trajectories,
		os.path.join(figures_dir, "drift_distribution.png"),
	)

	plot_trajectory_sample(
		trajectories,
		os.path.join(figures_dir, "trajectory_sample.png"),
	)

	plot_extremity_distribution(
		trajectories,
		os.path.join(figures_dir, "extremity_distribution.png"),
	)

	# Save the metrics summary table.
	save_metrics_table(
		metrics_dict,
		os.path.join(tables_dir, "summary_metrics.csv"),
	)
