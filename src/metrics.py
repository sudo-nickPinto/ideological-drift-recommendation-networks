# ==============================================================================
# MODULE: metrics.py
# PURPOSE: Compute the numerical summaries that answer the research question.
# ==============================================================================
#
# This is the FOURTH module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#                                                            ^^^^^^^^^^
#
# WHAT THIS MODULE DOES:
#   By the time data reaches metrics.py, two important things already exist:
#
#   1. A recommendation graph G
#      - built by graph_builder.py
#      - scored by ideology.py so every node has IDEOLOGY_SCORE
#
#   2. A collection of simulated trajectories
#      - produced by simulator.py
#      - each trajectory is a list of step dictionaries
#      - each step dictionary stores the node_id and ideology_score
#
#   This module turns those objects into NUMBERS we can interpret.
#
# RESEARCH QUESTIONS TRANSLATED INTO METRICS:
#
#   A. "Do walks move left or right overall?"
#      → compute_walk_drift()
#      Drift = final ideology score − initial ideology score
#
#   B. "Do walks move away from the center toward extremes?"
#      → compute_walk_extremity_change()
#      Extremity change = |final| − |initial|
#
#   C. "Does the graph connect similar ideologies to each other?"
#      → compute_ideology_assortativity()
#      High positive assortativity means like tends to recommend like.
#
#   D. "How tightly clustered is the network?"
#      → compute_average_clustering()
#      Higher clustering means nodes tend to form local triangles/groups.
#
#   E. "Can we package all of that into one summary table?"
#      → compute_all_metrics()
#
# DESIGN DECISIONS:
#   - Per-walk calculations are split into tiny functions. This keeps the math
#     transparent and makes each piece easy to test in isolation.
#   - Missing endpoint scores return None instead of a fake numeric value.
#     Returning 0.0 would silently distort averages. None makes the missing
#     data explicit so summary functions can skip those trajectories.
#   - Assortativity filters out nodes whose ideology score is None before
#     calling NetworkX. NetworkX cannot meaningfully compare "unknown"
#     ideology values, and mixing None with numbers would produce errors.
#   - Clustering is computed on an undirected copy of the graph. The classic
#     average clustering coefficient is easiest to explain in undirected terms:
#     "if A connects to B and C, do B and C also connect to each other?"
#
# ==============================================================================


import math
import statistics

import networkx as nx

from src.ideology import SCORE_ATTRIBUTE
from src.simulator import SCORE_FIELD


# --- CONSTANTS ----------------------------------------------------------------

# Field names used by compute_all_metrics().
# Keeping them in constants avoids typos and guarantees that visualize.py,
# tests, and CSV outputs all agree on the exact column names.
TRAJECTORY_COUNT_FIELD = "num_trajectories"
VALID_DRIFT_COUNT_FIELD = "num_valid_drifts"
MEAN_DRIFT_FIELD = "mean_drift"
MEAN_ABSOLUTE_DRIFT_FIELD = "mean_absolute_drift"
MEAN_EXTREMITY_CHANGE_FIELD = "mean_extremity_change"
ASSORTATIVITY_FIELD = "ideology_assortativity"
CLUSTERING_FIELD = "average_clustering"


# --- HELPERS ------------------------------------------------------------------

def _get_endpoint_scores(trajectory, score_field=SCORE_FIELD):
	"""
	Read the first and last ideology scores from one trajectory.

	PARAMETERS:
		trajectory (list[dict]): One walk returned by simulator.py.
		score_field (str): Dictionary key holding the ideology score.

	RETURNS:
		tuple(initial_score, final_score) or (None, None):
			- Returns the two endpoint scores if the trajectory exists
			- Returns (None, None) if the trajectory is empty

	WHY A HELPER?
		Both drift and extremity change need the exact same two values:
		the ideology score at the start and the ideology score at the end.
		Pulling that logic into one helper avoids repeating the same code
		in multiple functions.
	"""
	if not trajectory:
		return None, None

	initial_score = trajectory[0].get(score_field)
	final_score = trajectory[-1].get(score_field)
	return initial_score, final_score


def _mean_or_none(values):
	"""
	Return the arithmetic mean of a non-empty list, else None.

	This small helper keeps the summary functions readable and gives them
	one shared rule for handling empty inputs.
	"""
	if not values:
		return None
	return statistics.fmean(values)


# --- PER-WALK METRICS ---------------------------------------------------------

def compute_walk_drift(trajectory, score_field=SCORE_FIELD):
	"""
	Compute ideology drift for one trajectory.

	FORMULA:
		drift = final_score - initial_score

	INTERPRETATION:
		Positive drift  → walk ended farther to the Right
		Negative drift  → walk ended farther to the Left
		Zero drift      → walk ended at the same ideology score it started

	PARAMETERS:
		trajectory (list[dict]): One simulated walk trajectory.
		score_field (str): Key holding ideology scores inside each step dict.

	RETURNS:
		float or None:
			- float if both endpoint scores are present
			- None if the trajectory is empty or an endpoint score is missing
	"""
	initial_score, final_score = _get_endpoint_scores(trajectory, score_field)

	if initial_score is None or final_score is None:
		return None

	return float(final_score) - float(initial_score)


def compute_walk_extremity_change(trajectory, score_field=SCORE_FIELD):
	"""
	Compute how much a walk moves toward or away from ideological extremes.

	FORMULA:
		extremity change = |final_score| - |initial_score|

	WHY ABSOLUTE VALUE?
		The sign of the ideology score tells us LEFT vs RIGHT.
		The absolute value tells us DISTANCE FROM THE CENTER.

		Examples:
			-1.0 and +1.0 are both equally extreme because both are 1 step
			away from the center value 0.0.

	INTERPRETATION:
		Positive value  → ended farther from center (more extreme)
		Negative value  → ended closer to center (less extreme)
		Zero            → same extremity as where it started

	PARAMETERS:
		trajectory (list[dict]): One simulated walk trajectory.
		score_field (str): Key holding ideology scores inside each step dict.

	RETURNS:
		float or None:
			- float if both endpoint scores are present
			- None if the trajectory is empty or an endpoint score is missing
	"""
	initial_score, final_score = _get_endpoint_scores(trajectory, score_field)

	if initial_score is None or final_score is None:
		return None

	return abs(float(final_score)) - abs(float(initial_score))


def compute_mean_drift(trajectories, score_field=SCORE_FIELD):
	"""
	Compute the average drift across many trajectories.

	Invalid trajectories (those whose drift is None) are skipped.
	"""
	drifts = []

	for trajectory in trajectories:
		drift = compute_walk_drift(trajectory, score_field=score_field)
		if drift is not None:
			drifts.append(drift)

	return _mean_or_none(drifts)


def compute_mean_absolute_drift(trajectories, score_field=SCORE_FIELD):
	"""
	Compute the average MAGNITUDE of drift, ignoring direction.

	WHY THIS EXISTS:
		Mean drift can cancel itself out. For example:
			one walk = +1.0
			one walk = -1.0
			mean drift = 0.0

		That does NOT mean nothing happened. It means the movement balanced
		out across directions. Mean absolute drift captures how much movement
		happened overall, regardless of left vs right direction.
	"""
	absolute_drifts = []

	for trajectory in trajectories:
		drift = compute_walk_drift(trajectory, score_field=score_field)
		if drift is not None:
			absolute_drifts.append(abs(drift))

	return _mean_or_none(absolute_drifts)


def compute_mean_extremity_change(trajectories, score_field=SCORE_FIELD):
	"""
	Compute the average extremity change across many trajectories.

	Invalid trajectories (those whose extremity change is None) are skipped.
	"""
	extremity_changes = []

	for trajectory in trajectories:
		change = compute_walk_extremity_change(trajectory, score_field=score_field)
		if change is not None:
			extremity_changes.append(change)

	return _mean_or_none(extremity_changes)


# --- GRAPH-LEVEL METRICS ------------------------------------------------------

def compute_ideology_assortativity(G, score_attr=SCORE_ATTRIBUTE):
	"""
	Compute assortativity of the graph by ideology score.

	WHAT ASSORTATIVITY MEANS:
		Assortativity measures whether similar nodes tend to connect.

		In this project, the "attribute" is ideology score.
		So this metric asks:
			"Do Left nodes tend to recommend Left nodes,
			 Center nodes tend to recommend Center nodes,
			 and Right nodes tend to recommend Right nodes?"

	INTERPRETATION:
		+1.0  → perfect like-to-like connection pattern
		 0.0  → no relationship between ideology and connections
		-1.0  → opposite types systematically connect to each other

	PARAMETERS:
		G (networkx.DiGraph): Scored recommendation graph.
		score_attr (str): Node attribute holding ideology score.

	RETURNS:
		float or None:
			- float if the metric is defined
			- None if there is not enough valid scored structure to compute it
	"""
	valid_nodes = [
		node_id
		for node_id, attrs in G.nodes(data=True)
		if attrs.get(score_attr) is not None
	]

	# Build a subgraph containing only nodes with known ideology scores.
	filtered_graph = G.subgraph(valid_nodes).copy()

	if filtered_graph.number_of_edges() == 0:
		return None

	try:
		assortativity = nx.numeric_assortativity_coefficient(
			filtered_graph,
			score_attr,
		)
	except (ZeroDivisionError, nx.NetworkXError):
		return None

	if math.isnan(assortativity):
		return None

	return float(assortativity)


def compute_average_clustering(G):
	"""
	Compute the average clustering coefficient of the graph.

	WHAT CLUSTERING MEASURES:
		If node A connects to B and C, clustering asks whether B and C are
		also connected to each other. In plain language: do recommendations
		stay inside tight local neighborhoods?

	WHY WE CONVERT TO UNDIRECTED:
		The beginner-friendly version of clustering is easiest to explain
		on an undirected graph. We care about whether local triangles exist,
		not about the direction of each triangle edge.

	PARAMETERS:
		G (networkx.DiGraph): Recommendation graph.

	RETURNS:
		float or None:
			- float if the graph has at least one node
			- None if the graph is empty
	"""
	if G.number_of_nodes() == 0:
		return None

	undirected_graph = G.to_undirected()
	return float(nx.average_clustering(undirected_graph))


# --- SUMMARY WRAPPER ----------------------------------------------------------

def compute_graph_metrics(G, score_attr=SCORE_ATTRIBUTE):
	"""
	Compute the graph-level metrics that do not depend on any trajectory set.

	WHY THIS EXISTS:
		In experiment mode the same recommendation graph is reused across many
		trajectory batches. Assortativity and clustering are properties of that
		graph itself, so recalculating them for every seed and step count is
		unnecessary work.
	"""
	return {
		ASSORTATIVITY_FIELD: compute_ideology_assortativity(
			G,
			score_attr=score_attr,
		),
		CLUSTERING_FIELD: compute_average_clustering(G),
	}


def compute_all_metrics(
	G,
	trajectories,
	score_attr=SCORE_ATTRIBUTE,
	score_field=SCORE_FIELD,
	graph_metrics=None,
):
	"""
	Compute the full summary dictionary used by the reporting layer.

	PARAMETERS:
		G (networkx.DiGraph): Scored recommendation graph.
		trajectories (list[list[dict]]): Collection of simulated walks.
		score_attr (str): Node attribute holding ideology score.
		score_field (str): Step-dictionary key holding ideology score.
		graph_metrics (dict or None): Optional precomputed graph-only metrics
			containing ASSORTATIVITY_FIELD and CLUSTERING_FIELD.

	RETURNS:
		dict: Summary metrics keyed by the constants defined at the top of
			  this module. The returned dictionary is designed to be written
			  directly to CSV by visualize.save_metrics_table().
	"""
	valid_drifts = []

	for trajectory in trajectories:
		drift = compute_walk_drift(trajectory, score_field=score_field)
		if drift is not None:
			valid_drifts.append(drift)

	if graph_metrics is None:
		graph_metrics = compute_graph_metrics(G, score_attr=score_attr)

	return {
		TRAJECTORY_COUNT_FIELD: len(trajectories),
		VALID_DRIFT_COUNT_FIELD: len(valid_drifts),
		MEAN_DRIFT_FIELD: compute_mean_drift(trajectories, score_field=score_field),
		MEAN_ABSOLUTE_DRIFT_FIELD: compute_mean_absolute_drift(
			trajectories,
			score_field=score_field,
		),
		MEAN_EXTREMITY_CHANGE_FIELD: compute_mean_extremity_change(
			trajectories,
			score_field=score_field,
		),
		ASSORTATIVITY_FIELD: graph_metrics[ASSORTATIVITY_FIELD],
		CLUSTERING_FIELD: graph_metrics[CLUSTERING_FIELD],
	}
