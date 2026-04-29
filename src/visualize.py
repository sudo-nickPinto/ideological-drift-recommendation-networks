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


def plot_trajectory_sample(trajectories, output_path, max_lines=10):
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
			Default is 20. If fewer trajectories exist, all are shown.

	RETURNS:
		None — the figure is saved to disk.
	"""
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

	for trajectory in sample:
		# Extract the step numbers and ideology scores from the trajectory.
		# Each trajectory is a list of dictionaries like:
		#   [{"step": 0, "node_id": "ch_L1", "ideology_score": -1.0}, ...]
		steps = [record[STEP_FIELD] for record in trajectory]
		scores = [record[SCORE_FIELD] for record in trajectory]

		# Plot one line per trajectory.
		# alpha=0.5 makes lines semi-transparent so overlapping paths
		# are still distinguishable.
		ax.plot(steps, scores, alpha=0.5, linewidth=1.0)

	# Draw horizontal reference lines at the three ideology levels.
	# These help the audience see whether paths cluster near one level.
	ax.axhline(-1.0, color="#4472C4", linestyle=":", alpha=0.4, label="Left (−1)")
	ax.axhline(0.0, color="#A5A5A5", linestyle=":", alpha=0.4, label="Center (0)")
	ax.axhline(1.0, color="#C0504D", linestyle=":", alpha=0.4, label="Right (+1)")

	ax.set_xlabel("Step Number", fontsize=12)
	ax.set_ylabel("Ideology Score", fontsize=12)
	ax.set_title(f"Sample of {len(sample)} Walk Trajectories", fontsize=14)
	ax.set_ylim(-1.3, 1.3)  # Slight padding beyond the score range.
	ax.legend(loc="upper right", fontsize=9)

	fig.tight_layout()
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
	# Create the output directories if they do not already exist.
	# os.makedirs with exist_ok=True is safe to call even if the
	# directories already exist — it simply does nothing in that case.
	figures_dir = os.path.join(output_dir, "figures")
	tables_dir = os.path.join(output_dir, "tables")
	os.makedirs(figures_dir, exist_ok=True)
	os.makedirs(tables_dir, exist_ok=True)

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
