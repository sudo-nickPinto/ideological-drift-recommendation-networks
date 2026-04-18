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
	EXTREME_HIT_RATE_FIELD,
	ASSORTATIVITY_FIELD,
	CLUSTERING_FIELD,
	STEPS_TO_EXTREME_FIELD,
	MEDIAN_STEPS_TO_EXTREME_FIELD,
	PCT_REACHING_EXTREME_FIELD,
	NULL_MODEL_P_VALUE_FIELD,
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
	total = sum(counts)

	# Create the figure and one set of axes (the plotting area).
	# fig is the overall canvas; ax is the coordinate system inside it.
	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	# Draw the bar chart.
	# ax.bar() takes:
	#   - x positions (the label strings)
	#   - heights (the counts)
	#   - color (one color per bar)
	ax.bar(IDEOLOGY_LABELS, counts, color=IDEOLOGY_COLORS, edgecolor="black")

	# Add count AND percentage labels on top of each bar so readers
	# immediately see both the raw number and what fraction it represents.
	for i, count in enumerate(counts):
		pct = count / total * 100 if total else 0
		ax.text(
			i,
			count + max(counts) * 0.02,
			f"{count:,}\n({pct:.0f}%)",
			ha="center",
			fontsize=11,
			fontweight="bold",
		)

	ax.set_xlabel("Ideology Category", fontsize=12)
	ax.set_ylabel("Number of Channels", fontsize=12)
	ax.set_title("What Does the YouTube Landscape Look Like?", fontsize=14)

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
			label=f"Average = {mean_drift:+.2f}",
		)
		ax.legend(fontsize=11)

		# Plain-English interpretation for non-technical readers.
		direction = "leftward" if mean_drift < 0 else "rightward" if mean_drift > 0 else "neither direction"
		ax.text(
			0.97, 0.95,
			f"Bottom Line: On average,\nusers drifted {direction}\nby {abs(mean_drift):.2f} points.",
			transform=ax.transAxes,
			ha="right", va="top",
			fontsize=10,
			bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"),
		)
	else:
		# If there are no valid drifts, show a message instead of an empty plot.
		ax.text(
			0.5, 0.5,
			"No valid drift data available",
			ha="center", va="center",
			transform=ax.transAxes,
			fontsize=14,
		)

	ax.set_xlabel("Direction of Movement (← leftward · rightward →)", fontsize=12)
	ax.set_ylabel("Number of Walks", fontsize=12)
	ax.set_title("Which Direction Do Users Drift?", fontsize=14)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_trajectory_sample(trajectories, output_path, max_lines=20):
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

	ax.set_xlabel("Step Number (each step = 1 recommendation click)", fontsize=12)
	ax.set_ylabel("Ideology Score", fontsize=12)
	ax.set_title("What Do Individual User Journeys Look Like?", fontsize=14)
	ax.set_ylim(-1.3, 1.3)  # Slight padding beyond the score range.
	ax.legend(loc="upper right", fontsize=9)

	# Interpretive text box so the audience knows how to read the chart.
	ax.text(
		0.03, 0.05,
		"Each line = one simulated user\nfollowing recommendations.\n"
		"Flat lines = stuck in one area.\n"
		"Jagged lines = bouncing around.",
		transform=ax.transAxes,
		ha="left", va="bottom",
		fontsize=9,
		bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
		          edgecolor="gray", alpha=0.9),
	)

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
			label=f"Average = {mean_change:+.2f}",
		)
		ax.legend(fontsize=11)

		# Plain-English interpretation.
		if mean_change > 0:
			verdict = "users ended FARTHER\nfrom center (more extreme)"
		elif mean_change < 0:
			verdict = "users ended CLOSER\nto center (less extreme)"
		else:
			verdict = "no net change\nin extremity"
		ax.text(
			0.97, 0.95,
			f"Bottom Line:\n{verdict}",
			transform=ax.transAxes,
			ha="right", va="top",
			fontsize=10,
			bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"),
		)
	else:
		ax.text(
			0.5, 0.5,
			"No valid extremity data available",
			ha="center", va="center",
			transform=ax.transAxes,
			fontsize=14,
		)

	ax.set_xlabel("Movement Toward Extremes (positive = pushed away from center)", fontsize=11)
	ax.set_ylabel("Number of Walks", fontsize=12)
	ax.set_title("Do Users End Up at More Extreme Content?", fontsize=14)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def save_metrics_table(rows, output_path):
	"""
	Save a human-readable summary table as a 3-column CSV.

	WHAT THIS PRODUCES:
		A multi-row CSV with three columns:
			Metric        — the human-readable name of what was measured
			Value         — the number, rounded and formatted for readability
			What It Means — a plain-English explanation for non-experts

		This format is designed to be opened in Excel or Google Sheets and
		immediately understood by a non-technical audience. Every row is
		one finding, and the third column removes all ambiguity.

	PARAMETERS:
		rows (list[tuple]): Each tuple has three strings:
			(metric_name, formatted_value, plain_english_interpretation).
			Built by generate_all_figures() from all available pipeline data.
		output_path (str): Full file path where the CSV will be saved.

	RETURNS:
		None — the table is saved to disk.
	"""
	with open(output_path, "w", newline="") as csvfile:
		writer = csv.writer(csvfile)
		writer.writerow(["Metric", "Value", "What It Means"])
		for row in rows:
			writer.writerow(row)


# ==============================================================================
# ENHANCEMENT: THREE NEW CHART FUNCTIONS
# ==============================================================================
#
# These three visualizations correspond to the three experiment-strengthening
# additions we made in metrics.py. Each chart turns an abstract statistical
# result into a picture that a non-technical audience can immediately grasp.
#
#   1. Null Model Comparison — "Is this result real or just noise?"
#   2. Recommendation vs. Random — "Are recommendations worse than chance?"
#   3. Steps to Extreme — "How many clicks to reach extreme content?"
#
# ==============================================================================


def plot_null_model_comparison(real_extremity, null_extremities, p_value, output_path):
	"""
	Histogram of null model extremity changes with a red line for the real value.

	WHAT THIS FIGURE SHOWS:
		Gray bars = the extremity change values produced by 100 trials
		where we SHUFFLED the ideology labels on the graph. Each trial
		had the same graph structure but randomly assigned "Left," "Center,"
		and "Right" labels.

		Red vertical line = the extremity change from the REAL labels.

		If the red line is far to the RIGHT of the gray bars, that means
		the real network pushes users toward extremes MORE than random
		label assignment would explain. This is strong evidence that the
		network's ideology layout — which channels recommend which other
		channels — genuinely matters.

		The p-value annotation tells exactly how unusual the real result
		is: p = 0.02 means only 2 out of 100 random trials matched or
		exceeded the real result.

	PARAMETERS:
		real_extremity (float): The observed mean extremity change from the
			actual experiment.
		null_extremities (list[float]): The mean extremity change values
			from each shuffled-label trial (typically 100 values).
		p_value (float): The p-value computed by compute_null_model_p_value().
		output_path (str): Full file path where the PNG will be saved.

	RETURNS:
		None — the figure is saved to disk.
	"""
	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	# Draw the histogram of null model values (the "placebo" distribution).
	# Light gray bars represent what happens under random label assignment.
	ax.hist(
		null_extremities,
		bins=20,
		color="#BBBBBB",
		edgecolor="black",
		alpha=0.8,
		label="Shuffled labels (null model)",
	)

	# Draw a red vertical dashed line at the REAL observed value.
	# This is the "experimental" result we are testing.
	ax.axvline(
		real_extremity,
		color="red",
		linestyle="--",
		linewidth=2.5,
		label=f"Real result = {real_extremity:.2f}",
	)

	# Plain-English explanation of the p-value so a non-technical
	# audience can immediately understand the takeaway.
	if p_value < 0.05:
		verdict = "Statistically significant —\nthis pattern is unlikely\nto be coincidence."
	else:
		verdict = "Not statistically significant —\nthis pattern could happen\nby chance alone."
	ax.text(
		0.97, 0.95,
		f"p-value = {p_value:.2f}\n\n{verdict}",
		transform=ax.transAxes,
		ha="right", va="top",
		fontsize=11,
		fontweight="bold",
		bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"),
	)

	ax.set_xlabel("Extremity Change From Shuffled Labels (the \"placebo\")", fontsize=11)
	ax.set_ylabel("Number of Shuffled Trials", fontsize=12)
	ax.set_title("Is This Pattern Real, or Just Coincidence?", fontsize=14)
	ax.legend(fontsize=10)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_recommendation_vs_random(rec_summary, random_summary, output_path):
	"""
	Grouped bar chart comparing recommendations vs. random browsing.

	WHAT THIS FIGURE SHOWS:
		Three pairs of bars, each comparing a key metric between two
		conditions:

		Blue bar = "Following Recommendations" (the real experiment,
			where walkers follow actual recommendation edges)
		Gray bar = "Random Browsing" (the control, where walkers
			teleport to any random scored channel at each step)

		The three metrics displayed:
		1. Mean Absolute Drift — how far users move from their starting
		   ideology on average (regardless of direction)
		2. Mean Extremity Change — whether users end up further from center
		3. Extreme Hit Rate — what fraction of walks visited an extreme
		   channel (|score| = 1.0) at any point

		If the blue bars are consistently taller than the gray bars,
		it means RECOMMENDATIONS SPECIFICALLY cause more drift than
		random browsing — the recommendation algorithm is responsible,
		not just the fact that extreme channels exist in the network.

	PARAMETERS:
		rec_summary (dict): Summary metrics from the recommendation walk
			experiment (output of summarize_trajectories).
		random_summary (dict): Summary metrics from the uniform random
			walk experiment (output of summarize_trajectories).
		output_path (str): Full file path where the PNG will be saved.

	RETURNS:
		None — the figure is saved to disk.
	"""
	import numpy as np

	# Define which metrics to compare and their human-readable labels.
	metric_keys = [
		MEAN_ABSOLUTE_DRIFT_FIELD,
		MEAN_EXTREMITY_CHANGE_FIELD,
		EXTREME_HIT_RATE_FIELD,
	]
	metric_labels = [
		"Mean Absolute\nDrift",
		"Mean Extremity\nChange",
		"Extreme Hit\nRate",
	]

	# Extract values for each condition. Use 0.0 as fallback for missing keys.
	rec_values = [rec_summary.get(key, 0.0) or 0.0 for key in metric_keys]
	random_values = [random_summary.get(key, 0.0) or 0.0 for key in metric_keys]

	# Set up the bar positions.
	# np.arange(3) gives positions [0, 1, 2] for the three metric groups.
	# Each group has two bars side by side, separated by bar_width.
	x = np.arange(len(metric_labels))
	bar_width = 0.35

	fig, ax = plt.subplots(figsize=(9, 5))

	# Draw the two sets of bars.
	# The first set (recommendation) is shifted left by half a bar width.
	# The second set (random) is shifted right by half a bar width.
	ax.bar(
		x - bar_width / 2,
		rec_values,
		bar_width,
		label="Following Recommendations",
		color="#4472C4",
		edgecolor="black",
	)
	ax.bar(
		x + bar_width / 2,
		random_values,
		bar_width,
		label="Random Browsing",
		color="#A5A5A5",
		edgecolor="black",
	)

	# Add value labels on top of each bar.
	for i in range(len(metric_labels)):
		ax.text(
			i - bar_width / 2, rec_values[i] + 0.01,
			f"{rec_values[i]:.3f}",
			ha="center", fontsize=9, fontweight="bold",
		)
		ax.text(
			i + bar_width / 2, random_values[i] + 0.01,
			f"{random_values[i]:.3f}",
			ha="center", fontsize=9, fontweight="bold",
		)

	ax.set_xticks(x)
	ax.set_xticklabels(metric_labels, fontsize=11)
	ax.set_ylabel("Metric Value", fontsize=12)
	ax.set_title("Does Following Recommendations Make Drift Worse?", fontsize=14)
	ax.legend(fontsize=10, loc="upper left")

	# Bottom-line annotation comparing the two conditions.
	rec_drift_val = rec_values[0]
	rand_drift_val = random_values[0]
	if rand_drift_val > 0:
		pct_diff = (rec_drift_val - rand_drift_val) / rand_drift_val * 100
		ax.text(
			0.97, 0.95,
			f"Bottom Line: Recommendations\ncause {abs(pct_diff):.0f}% {'more' if pct_diff > 0 else 'less'} drift\nthan random browsing.",
			transform=ax.transAxes,
			ha="right", va="top",
			fontsize=10,
			bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"),
		)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def plot_steps_to_extreme(steps_list, median_val, pct_reaching, output_path):
	"""
	Histogram of how many clicks it takes to reach extreme content.

	WHAT THIS FIGURE SHOWS:
		Orange bars show the distribution of steps-to-extreme: for each
		walk that DID reach extreme content, how many clicks did it take?

		A red dashed line marks the median — the "typical" number of clicks.

		A text annotation shows both the median and the percentage of walks
		that reached extreme content at all.

		This is the most visceral finding in the study. A non-technical
		person immediately understands: "Starting from a moderate channel,
		you are 3 clicks away from extreme content."

	WHY ONLY WALKS THAT REACHED EXTREME?
		Walks that NEVER reached extreme content cannot contribute a
		steps-to-extreme count (they would be infinity). Including them
		would distort the histogram. Instead, we report them separately
		as part of the pct_reaching annotation.

	PARAMETERS:
		steps_list (list[int]): The step number at which each walk first
			reached extreme content. Only includes walks that DID reach
			an extreme. Can be empty if no walks reached extreme.
		median_val (float or None): The median of steps_list. None if
			steps_list is empty.
		pct_reaching (float or None): Fraction (0–1) of all walks that
			reached extreme content. None if unavailable.
		output_path (str): Full file path where the PNG will be saved.

	RETURNS:
		None — the figure is saved to disk.
	"""
	fig, ax = plt.subplots(figsize=FIGURE_SIZE)

	if steps_list:
		# Determine appropriate bin edges.
		# Since steps are integers, we want bins centered on each integer.
		max_steps = max(steps_list)
		bins = list(range(0, max_steps + 2))  # +2 so the last bin includes max

		ax.hist(
			steps_list,
			bins=bins,
			color="#E89C4A",
			edgecolor="black",
			alpha=0.8,
		)

		# Draw the median line.
		if median_val is not None:
			ax.axvline(
				median_val,
				color="red",
				linestyle="--",
				linewidth=2.5,
				label=f"Median = {median_val:.1f} clicks",
			)

		# Build the annotation text.
		annotation_parts = []
		if median_val is not None:
			annotation_parts.append(f"Median: {median_val:.1f} clicks")
		if pct_reaching is not None:
			annotation_parts.append(f"{pct_reaching * 100:.1f}% of walks\nreached extreme")
		annotation_text = "\n".join(annotation_parts)

		ax.text(
			0.97, 0.95,
			annotation_text,
			transform=ax.transAxes,
			ha="right", va="top",
			fontsize=12,
			fontweight="bold",
			bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray"),
		)

		ax.legend(fontsize=10)
	else:
		ax.text(
			0.5, 0.5,
			"No walks reached extreme content",
			ha="center", va="center",
			transform=ax.transAxes,
			fontsize=14,
		)

	ax.set_xlabel("Number of Steps (Clicks)", fontsize=12)
	ax.set_ylabel("Number of Walks", fontsize=12)
	ax.set_title("How Many Clicks to Reach Extreme Content?", fontsize=14)

	fig.tight_layout()
	fig.savefig(output_path, dpi=150)
	plt.close(fig)


def _build_summary_rows(
	G, metrics_dict, real_extremity=None, null_extremities=None,
	null_p_value=None, rec_summary=None, random_summary=None,
	steps_to_extreme_data=None,
):
	"""
	Build the list of (Metric, Value, What It Means) tuples for the CSV.

	This is a private helper called by generate_all_figures(). It gathers
	data from every stage of the pipeline and formats it into rows that
	any non-expert can read in Excel or Google Sheets.
	"""
	rows = []

	# --- Network overview ---
	rows.append((
		"Channels in network",
		f"{G.number_of_nodes():,}",
		"Total YouTube channels analyzed",
	))
	rows.append((
		"Recommendation links",
		f"{G.number_of_edges():,}",
		"Total recommendation connections between channels",
	))

	# Ideology breakdown.
	left = sum(1 for _, d in G.nodes(data=True) if d.get(SCORE_ATTRIBUTE) == -1.0)
	center = sum(1 for _, d in G.nodes(data=True) if d.get(SCORE_ATTRIBUTE) == 0.0)
	right = sum(1 for _, d in G.nodes(data=True) if d.get(SCORE_ATTRIBUTE) == 1.0)
	total_scored = left + center + right
	if total_scored > 0:
		rows.append((
			"Left-leaning channels",
			f"{left:,} ({left * 100 // total_scored}%)",
			"Channels scored as politically left (-1)",
		))
		rows.append((
			"Center channels",
			f"{center:,} ({center * 100 // total_scored}%)",
			"Channels scored as politically center (0)",
		))
		rows.append((
			"Right-leaning channels",
			f"{right:,} ({right * 100 // total_scored}%)",
			"Channels scored as politically right (+1)",
		))

	# --- Simulation results ---
	rows.append(("", "", ""))  # Blank separator row.

	n = metrics_dict.get(TRAJECTORY_COUNT_FIELD, 0)
	rows.append((
		"Simulated user journeys",
		f"{n:,}",
		"Number of random walks through the recommendation network",
	))

	md = metrics_dict.get(MEAN_DRIFT_FIELD, 0)
	direction = "leftward" if md < 0 else "rightward" if md > 0 else "neutral"
	rows.append((
		"Average drift",
		f"{md:+.2f}",
		f"Users drifted {direction} on average (scale: -2 to +2)",
	))

	mad = metrics_dict.get(MEAN_ABSOLUTE_DRIFT_FIELD, 0)
	rows.append((
		"Average absolute drift",
		f"{mad:.2f}",
		"How far users moved regardless of direction (0 = no movement)",
	))

	mec = metrics_dict.get(MEAN_EXTREMITY_CHANGE_FIELD, 0)
	if mec > 0:
		ext_interp = "Users ended farther from the center (more extreme)"
	elif mec < 0:
		ext_interp = "Users ended closer to the center (less extreme)"
	else:
		ext_interp = "No net change in extremity"
	rows.append(("Average extremity change", f"{mec:+.2f}", ext_interp))

	ehr = metrics_dict.get(EXTREME_HIT_RATE_FIELD, 0)
	rows.append((
		"Extreme content hit rate",
		f"{ehr * 100:.1f}%",
		"Percentage of journeys that visited extreme content (score = -1 or +1)",
	))

	# --- Network structure ---
	rows.append(("", "", ""))

	aa = metrics_dict.get(ASSORTATIVITY_FIELD, 0)
	if aa > 0:
		aa_interp = "Channels tend to recommend politically similar channels"
	else:
		aa_interp = "Channels tend to recommend politically different channels"
	rows.append(("Ideology assortativity", f"{aa:.2f}", aa_interp))

	cc = metrics_dict.get(CLUSTERING_FIELD, 0)
	rows.append((
		"Average clustering",
		f"{cc:.2f}",
		"How tightly connected neighborhoods are (1.0 = maximum echo chamber)",
	))

	# --- Enhancement: null model ---
	if null_p_value is not None:
		rows.append(("", "", ""))
		if null_p_value < 0.05:
			p_interp = (
				f"Only {null_p_value * 100:.0f}% chance this is coincidence"
				" — statistically significant"
			)
		else:
			p_interp = (
				f"{null_p_value * 100:.0f}% chance this could be coincidence"
				" — not significant at p < 0.05"
			)
		rows.append(("Null model p-value", f"{null_p_value:.2f}", p_interp))

	# --- Enhancement: recommendation vs. random ---
	if rec_summary is not None and random_summary is not None:
		rows.append(("", "", ""))
		rec_mad = rec_summary.get(MEAN_ABSOLUTE_DRIFT_FIELD, 0) or 0
		rand_mad = random_summary.get(MEAN_ABSOLUTE_DRIFT_FIELD, 0) or 0
		rows.append((
			"Drift from recommendations",
			f"{rec_mad:.2f}",
			"Average drift when following YouTube's suggestions",
		))
		rows.append((
			"Drift from random browsing",
			f"{rand_mad:.2f}",
			"Average drift when clicking channels at random",
		))
		if rand_mad > 0:
			pct_diff = (rec_mad - rand_mad) / rand_mad * 100
			more_or_less = "more" if pct_diff > 0 else "less"
			rows.append((
				"Recommendations vs. random",
				f"{pct_diff:+.0f}%",
				f"Recommendations cause {abs(pct_diff):.0f}% {more_or_less}"
				" drift than random browsing",
			))

	# --- Enhancement: steps to extreme ---
	if steps_to_extreme_data is not None:
		rows.append(("", "", ""))
		med = steps_to_extreme_data.get("median")
		pct = steps_to_extreme_data.get("pct_reaching")
		if med is not None:
			rows.append((
				"Median clicks to extreme",
				f"{med:.0f}",
				f"Starting from center, users typically reach extreme"
				f" content in {med:.0f} click(s)",
			))
		if pct is not None:
			rows.append((
				"% reaching extreme content",
				f"{pct * 100:.1f}%",
				f"Of center-starting journeys, {pct * 100:.1f}%"
				" encountered extreme content",
			))

	return rows


def generate_all_figures(
	G,
	trajectories,
	metrics_dict,
	output_dir="results",
	null_extremities=None,
	null_p_value=None,
	real_extremity=None,
	random_summary=None,
	rec_summary=None,
	steps_to_extreme_data=None,
):
	"""
	Generate all figures and the metrics table in one call.

	WHY A WRAPPER FUNCTION?
		The full pipeline runs all five stages in sequence. At the end,
		the caller has a graph, trajectories, and a metrics dictionary.
		This single function turns all of that into the complete set of
		output figures and tables, creating any necessary directories.

	ENHANCEMENT (backward-compatible):
		The three new optional parameters control whether the new charts
		are generated. If they are None (the default), those charts are
		simply skipped — so existing code that does not pass them still
		works exactly as before.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		trajectories (list[list[dict]]): All simulated walk trajectories.
		metrics_dict (dict): The summary from compute_all_metrics().
		output_dir (str): Root output directory. Figures go into
			output_dir/figures/ and tables go into output_dir/tables/.
			Default is "results".
		null_extremities (list[float] or None): Extremity-change values from
			the null model trials. If provided (along with null_p_value and
			real_extremity), the null model comparison chart is generated.
		null_p_value (float or None): The p-value for the null model test.
		real_extremity (float or None): The real mean extremity change.
		random_summary (dict or None): Summary metrics from random browsing.
			If provided (along with rec_summary), the recommendation vs.
			random comparison chart is generated.
		rec_summary (dict or None): Summary metrics from recommendation walks.
		steps_to_extreme_data (dict or None): Dictionary with keys:
			"steps_list" (list[int]), "median" (float), "pct_reaching" (float).
			If provided, the steps-to-extreme chart is generated.

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

	# Build and save the human-readable summary table.
	# This assembles ALL findings — from the core analysis plus the three
	# enhancements — into one clear CSV that a non-expert can understand.
	table_rows = _build_summary_rows(
		G, metrics_dict, real_extremity, null_extremities, null_p_value,
		rec_summary, random_summary, steps_to_extreme_data,
	)
	save_metrics_table(
		table_rows,
		os.path.join(tables_dir, "summary_metrics.csv"),
	)

	# --- NEW CHARTS (only generated when the caller provides the data) --------

	# Chart 5: Null Model Comparison
	# Shows whether the observed extremity change is statistically
	# significant by comparing it to shuffled-label trials.
	if null_extremities is not None and null_p_value is not None and real_extremity is not None:
		plot_null_model_comparison(
			real_extremity,
			null_extremities,
			null_p_value,
			os.path.join(figures_dir, "null_model_comparison.png"),
		)

	# Chart 6: Recommendation vs. Random Browsing
	# Shows whether following recommendations produces more drift than
	# randomly jumping to any channel in the network.
	if rec_summary is not None and random_summary is not None:
		plot_recommendation_vs_random(
			rec_summary,
			random_summary,
			os.path.join(figures_dir, "recommendation_vs_random.png"),
		)

	# Chart 7: Steps to Extreme
	# Shows how many clicks it takes to first reach extreme content.
	if steps_to_extreme_data is not None:
		plot_steps_to_extreme(
			steps_to_extreme_data.get("steps_list", []),
			steps_to_extreme_data.get("median"),
			steps_to_extreme_data.get("pct_reaching"),
			os.path.join(figures_dir, "steps_to_extreme.png"),
		)
