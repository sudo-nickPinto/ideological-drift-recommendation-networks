# ==============================================================================
# MODULE: metrics.py
# PURPOSE: Compute numerical summaries of ideological drift and network
#          structure from the simulator's trajectories and the graph itself.
# ==============================================================================
#
# This is the FOURTH module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#                                                             ^^^^^^^^^^
#
# WHAT THIS MODULE DOES:
#   Up to this point, the pipeline can:
#     1. Build a graph of recommendations
#     2. Attach ideology scores to nodes
#     3. Simulate user paths through that graph
#
#   But simulation output by itself is still just raw data.
#   A trajectory like this:
#
#       [
#           {"step": 0, "node_id": "ch_L1", "ideology_score": -1.0},
#           {"step": 1, "node_id": "ch_C1", "ideology_score":  0.0},
#           {"step": 2, "node_id": "ch_R1", "ideology_score":  1.0},
#       ]
#
#   is informative, but it is still just one example path. Research needs
#   summaries that can be compared across many walks and many graphs.
#
#   That is the job of metrics.py.
#
# WHAT WE MEASURE HERE:
#
#   A. DRIFT METRICS (path-based)
#      These use the simulator's trajectories.
#
#      1. Walk drift
#         final_score - initial_score
#         Example: -1.0 → +1.0 gives drift = +2.0
#
#      2. Extremity change
#         |final_score| - |initial_score|
#         Example: 0.0 → +1.0 gives extremity change = +1.0
#         Why absolute values? Because both -1 and +1 are ideological
#         extremes, just in opposite directions.
#
#      3. Trajectory summary
#         Average the drift values across many walks to estimate the
#         typical direction and magnitude of movement.
#
#   B. STRUCTURAL METRICS (graph-based)
#      These use the graph itself, independent of simulated paths.
#
#      1. Ideology assortativity
#         Measures whether nodes tend to connect to other nodes with
#         similar ideology scores.
#
#      2. Average clustering coefficient
#         Measures whether the graph tends to form tightly connected
#         neighborhoods (echo-chamber-like local clusters).
#
# WHY SPLIT PATH METRICS FROM GRAPH METRICS?
#   Because they answer different questions:
#     - Path metrics ask: "What happens to a user as they move?"
#     - Graph metrics ask: "What is the structure of the whole network?"
#
#   A network can be highly clustered but still not push users toward
#   ideological extremes. Or it can show drift even when clustering is weak.
#   We want both perspectives.
#
# DESIGN DECISIONS:
#   - Functions are small and single-purpose. This keeps the math readable
#     and makes testing easier.
#   - Missing ideology scores produce None for drift calculations instead of
#     fake numeric answers. Silent substitution would hide data problems.
#   - Clustering is computed on an undirected version of the graph.
#     Why? Because the beginner-friendly interpretation of clustering is:
#     "If A is connected to B and C, are B and C also connected?"
#     That local triangle idea is easiest to explain on undirected graphs.
#
# ==============================================================================


import math
import random
import statistics

import networkx as nx

from src.ideology import SCORE_ATTRIBUTE
from src.simulator import SCORE_FIELD


# --- CONSTANTS ----------------------------------------------------------------

# Field names used in the summary dictionary returned by summarize_trajectories()
# and compute_all_metrics(). Centralizing them reduces typo risk.
TRAJECTORY_COUNT_FIELD = "num_trajectories"
VALID_DRIFT_COUNT_FIELD = "num_valid_drifts"
MEAN_DRIFT_FIELD = "mean_drift"
MEAN_ABSOLUTE_DRIFT_FIELD = "mean_absolute_drift"
MEAN_EXTREMITY_CHANGE_FIELD = "mean_extremity_change"
MEAN_RIGHT_SHARE_FIELD = "mean_right_share"
MEAN_LEFT_SHARE_FIELD = "mean_left_share"
MEAN_CENTER_SHARE_FIELD = "mean_center_share"
MEAN_EXTREME_SHARE_FIELD = "mean_extreme_share"
EXTREME_HIT_RATE_FIELD = "extreme_hit_rate"
RIGHT_ENDPOINT_RATE_FIELD = "right_endpoint_rate"
LEFT_ENDPOINT_RATE_FIELD = "left_endpoint_rate"
CENTER_ENDPOINT_RATE_FIELD = "center_endpoint_rate"
ASSORTATIVITY_FIELD = "ideology_assortativity"
CLUSTERING_FIELD = "average_clustering"

# --- NEW CONSTANTS (Enhancement Phase) ----------------------------------------
# These support the three experiment-strengthening additions:
#   1. Steps-to-extreme metric (how fast do walkers reach extreme content?)
#   2. Null model comparison (is the drift real or just noise?)

STEPS_TO_EXTREME_FIELD = "mean_steps_to_extreme"
MEDIAN_STEPS_TO_EXTREME_FIELD = "median_steps_to_extreme"
PCT_REACHING_EXTREME_FIELD = "pct_reaching_extreme"
NULL_MODEL_P_VALUE_FIELD = "null_model_p_value"

# We use explicit labels for the three ideology buckets because the project's
# scoring system is intentionally simple and discrete: Left = -1, Center = 0,
# Right = +1. These labels become keys in the stratified summary dictionary.
LEFT_START_GROUP = "start_left"
CENTER_START_GROUP = "start_center"
RIGHT_START_GROUP = "start_right"
UNKNOWN_START_GROUP = "start_unknown"


# --- FUNCTIONS ----------------------------------------------------------------

def compute_walk_drift(trajectory, score_field=SCORE_FIELD):
	"""
	Compute the net ideology change across one trajectory.

	FORMULA:
		drift = final_score - initial_score

	INTERPRETATION:
		- Positive drift  → movement to the Right
		- Negative drift  → movement to the Left
		- Zero drift      → no net ideological change

	PARAMETERS:
		trajectory (list[dict]): One simulator trajectory.
		score_field (str): Dictionary key containing the ideology score.

	RETURNS:
		float or None:
			- float if the first and last scores both exist
			- None if either endpoint score is missing

	RAISES:
		ValueError: If trajectory is empty.
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	initial_score = trajectory[0].get(score_field)
	final_score = trajectory[-1].get(score_field)

	if initial_score is None or final_score is None:
		return None

	return float(final_score) - float(initial_score)


def compute_walk_extremity_change(trajectory, score_field=SCORE_FIELD):
	"""
	Compute how much a walk moves toward or away from ideological extremes.

	FORMULA:
		extremity_change = |final_score| - |initial_score|

	WHY ABSOLUTE VALUE?
		The absolute value removes left/right direction and keeps only
		distance from the center. On our scale:
			-1.0 and +1.0 are both extreme
			 0.0 is the center

		So this metric answers:
			"Did the user end farther from the center than they started?"

	RETURNS:
		float or None, following the same rules as compute_walk_drift().
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	initial_score = trajectory[0].get(score_field)
	final_score = trajectory[-1].get(score_field)

	if initial_score is None or final_score is None:
		return None

	return abs(float(final_score)) - abs(float(initial_score))


def compute_walk_score_shares(trajectory, score_field=SCORE_FIELD):
	"""
	Compute what fraction of a walk is spent in Left, Center, Right,
	and extreme content.

	WHY THIS METRIC EXISTS:
		The current project mainly compares the first score to the last score.
		That is useful, but it misses an important question:

			"Where did the user spend most of the journey?"

		A walk could start Right, spend many steps in extreme Right channels,
		and then end in the Center. Endpoint-only summaries would miss that.
		Share-based metrics keep the full path visible.

	DEFINITIONS:
		- right_share   = fraction of valid scored steps where score == +1.0
		- left_share    = fraction of valid scored steps where score == -1.0
		- center_share  = fraction of valid scored steps where score ==  0.0
		- extreme_share = fraction of valid scored steps where |score| == 1.0

	PARAMETERS:
		trajectory (list[dict]): One simulator trajectory.
		score_field (str): Dictionary key containing the ideology score.

	RETURNS:
		dict or None:
			- A dictionary of four shares if at least one valid score exists
			- None if every step has a missing ideology score

	RAISES:
		ValueError: If trajectory is empty.
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	valid_scores = []
	for record in trajectory:
		score = record.get(score_field)
		if score is not None:
			valid_scores.append(float(score))

	if not valid_scores:
		return None

	total_steps = len(valid_scores)
	left_steps = sum(score == -1.0 for score in valid_scores)
	center_steps = sum(score == 0.0 for score in valid_scores)
	right_steps = sum(score == 1.0 for score in valid_scores)
	extreme_steps = sum(abs(score) == 1.0 for score in valid_scores)

	return {
		MEAN_LEFT_SHARE_FIELD: left_steps / total_steps,
		MEAN_CENTER_SHARE_FIELD: center_steps / total_steps,
		MEAN_RIGHT_SHARE_FIELD: right_steps / total_steps,
		MEAN_EXTREME_SHARE_FIELD: extreme_steps / total_steps,
	}


def compute_walk_hits_extreme(trajectory, score_field=SCORE_FIELD):
	"""
	Determine whether a walk ever visits an ideological extreme.

	WHAT COUNTS AS "EXTREME"?
		On this project's scale, both -1.0 and +1.0 are extremes because they
		are the two endpoints of the Left/Center/Right encoding.

	WHY THIS MATTERS:
		A user does not need to END on an extreme channel for the recommendation
		system to have exposed them to extreme content. This metric asks the
		simpler yes/no question:

			"Did the walk ever reach either ideological edge at all?"

	RETURNS:
		bool or None:
			- True if at least one valid step has absolute score 1.0
			- False if valid scores exist and none are extreme
			- None if every score in the trajectory is missing

	RAISES:
		ValueError: If trajectory is empty.
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	has_valid_score = False
	for record in trajectory:
		score = record.get(score_field)
		if score is None:
			continue

		has_valid_score = True
		if abs(float(score)) == 1.0:
			return True

	if not has_valid_score:
		return None

	return False


def classify_start_group(trajectory, score_field=SCORE_FIELD):
	"""
	Assign one trajectory to a start-ideology group based on step 0.

	WHY STRATIFY BY START?
		The current project averages all walks together. That can hide
		important asymmetries. For example:
			- Right-starting walks may move toward Center
			- Center-starting walks may move toward Right
			- Left-starting walks may move strongly toward Right

		If we pool those together too early, the overall average can become
		misleading. Grouping by start ideology lets us compare like with like.

	RETURNS:
		str: One of the four group labels defined above.

	RAISES:
		ValueError: If trajectory is empty.
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	start_score = trajectory[0].get(score_field)

	if start_score == -1.0:
		return LEFT_START_GROUP
	if start_score == 0.0:
		return CENTER_START_GROUP
	if start_score == 1.0:
		return RIGHT_START_GROUP

	return UNKNOWN_START_GROUP


def summarize_trajectories(trajectories, score_field=SCORE_FIELD):
	"""
	Aggregate drift statistics across many trajectories.

	PARAMETERS:
		trajectories (list[list[dict]]): Collection of simulator trajectories.
		score_field (str): Dictionary key containing ideology score.

	RETURNS:
		dict: Summary statistics for the full set of trajectories.

	SUMMARY FIELDS:
		- num_trajectories: how many walks were provided
		- num_valid_drifts: how many had usable endpoint scores
		- mean_drift: average final-minus-initial score
		- mean_absolute_drift: average of absolute drift magnitudes
		- mean_extremity_change: average movement away from/toward center
	"""
	drifts = []
	extremity_changes = []
	left_shares = []
	center_shares = []
	right_shares = []
	extreme_shares = []
	extreme_hits = []
	left_endpoints = 0
	center_endpoints = 0
	right_endpoints = 0
	valid_endpoints = 0

	for trajectory in trajectories:
		drift = compute_walk_drift(trajectory, score_field=score_field)
		extremity_change = compute_walk_extremity_change(
			trajectory,
			score_field=score_field,
		)
		score_shares = compute_walk_score_shares(trajectory, score_field=score_field)
		hit_extreme = compute_walk_hits_extreme(trajectory, score_field=score_field)

		final_score = trajectory[-1].get(score_field) if trajectory else None

		if drift is not None:
			drifts.append(drift)

		if extremity_change is not None:
			extremity_changes.append(extremity_change)

		if score_shares is not None:
			left_shares.append(score_shares[MEAN_LEFT_SHARE_FIELD])
			center_shares.append(score_shares[MEAN_CENTER_SHARE_FIELD])
			right_shares.append(score_shares[MEAN_RIGHT_SHARE_FIELD])
			extreme_shares.append(score_shares[MEAN_EXTREME_SHARE_FIELD])

		if hit_extreme is not None:
			extreme_hits.append(hit_extreme)

		if final_score is not None:
			valid_endpoints += 1
			if float(final_score) == -1.0:
				left_endpoints += 1
			elif float(final_score) == 0.0:
				center_endpoints += 1
			elif float(final_score) == 1.0:
				right_endpoints += 1

	summary = {
		TRAJECTORY_COUNT_FIELD: len(trajectories),
		VALID_DRIFT_COUNT_FIELD: len(drifts),
		MEAN_DRIFT_FIELD: None,
		MEAN_ABSOLUTE_DRIFT_FIELD: None,
		MEAN_EXTREMITY_CHANGE_FIELD: None,
		MEAN_LEFT_SHARE_FIELD: None,
		MEAN_CENTER_SHARE_FIELD: None,
		MEAN_RIGHT_SHARE_FIELD: None,
		MEAN_EXTREME_SHARE_FIELD: None,
		EXTREME_HIT_RATE_FIELD: None,
		LEFT_ENDPOINT_RATE_FIELD: None,
		CENTER_ENDPOINT_RATE_FIELD: None,
		RIGHT_ENDPOINT_RATE_FIELD: None,
	}

	if drifts:
		summary[MEAN_DRIFT_FIELD] = statistics.mean(drifts)
		summary[MEAN_ABSOLUTE_DRIFT_FIELD] = statistics.mean(abs(value) for value in drifts)

	if extremity_changes:
		summary[MEAN_EXTREMITY_CHANGE_FIELD] = statistics.mean(extremity_changes)

	if left_shares:
		summary[MEAN_LEFT_SHARE_FIELD] = statistics.mean(left_shares)
		summary[MEAN_CENTER_SHARE_FIELD] = statistics.mean(center_shares)
		summary[MEAN_RIGHT_SHARE_FIELD] = statistics.mean(right_shares)
		summary[MEAN_EXTREME_SHARE_FIELD] = statistics.mean(extreme_shares)

	if extreme_hits:
		summary[EXTREME_HIT_RATE_FIELD] = statistics.mean(extreme_hits)

	if valid_endpoints > 0:
		summary[LEFT_ENDPOINT_RATE_FIELD] = left_endpoints / valid_endpoints
		summary[CENTER_ENDPOINT_RATE_FIELD] = center_endpoints / valid_endpoints
		summary[RIGHT_ENDPOINT_RATE_FIELD] = right_endpoints / valid_endpoints

	return summary


def summarize_trajectories_by_start(trajectories, score_field=SCORE_FIELD):
	"""
	Summarize trajectories separately for Left, Center, Right, and unknown starts.

	WHY THIS FUNCTION EXISTS:
		The overall mean can hide asymmetric behavior. This helper groups the
		walks by their starting ideology and then reuses summarize_trajectories()
		inside each group. That keeps the formulas consistent while giving a more
		honest comparison across starting positions.

	RETURNS:
		dict[str, dict]:
			A dictionary whose keys are start-group labels and whose values are
			the same kind of summary dictionary returned by summarize_trajectories().
	"""
	grouped_trajectories = {
		LEFT_START_GROUP: [],
		CENTER_START_GROUP: [],
		RIGHT_START_GROUP: [],
		UNKNOWN_START_GROUP: [],
	}

	for trajectory in trajectories:
		group_name = classify_start_group(trajectory, score_field=score_field)
		grouped_trajectories[group_name].append(trajectory)

	group_summaries = {}
	for group_name, group_trajectories in grouped_trajectories.items():
		group_summaries[group_name] = summarize_trajectories(
			group_trajectories,
			score_field=score_field,
		)

	return group_summaries


def compute_ideology_assortativity(G, score_attr=SCORE_ATTRIBUTE):
	"""
	Compute ideology assortativity for the graph.

	WHAT IS ASSORTATIVITY?
		Assortativity measures whether similar nodes tend to connect to each
		other. Here, "similar" means "having similar ideology scores."

		Rough interpretation:
			+1  → strong like-connects-to-like structure
			 0  → no strong pattern
			-1  → opposite-connects-to-opposite structure

	IMPORTANT DATA CLEANING STEP:
		NetworkX's numeric assortativity needs valid numeric attributes.
		If a node has score None, it cannot contribute meaningfully.
		So we build a filtered subgraph containing only nodes with numeric
		ideology scores.

	RETURNS:
		float or None:
			- float if assortativity can be computed
			- None if the graph does not contain enough valid information
	"""
	valid_nodes = [
		node_id
		for node_id, attrs in G.nodes(data=True)
		if attrs.get(score_attr) is not None
	]

	filtered_graph = G.subgraph(valid_nodes).copy()

	# No edges means there is no relationship structure to measure.
	if filtered_graph.number_of_edges() == 0:
		return None

	# If every node has the same score, there is no variance. Correlation-like
	# statistics become undefined in that situation.
	unique_scores = {
		filtered_graph.nodes[node_id].get(score_attr)
		for node_id in filtered_graph.nodes
	}
	if len(unique_scores) < 2:
		return None

	assortativity = nx.numeric_assortativity_coefficient(filtered_graph, score_attr)

	if math.isnan(assortativity):
		return None

	return assortativity


def compute_average_clustering(G):
	"""
	Compute the average clustering coefficient of the graph.

	WHAT IS CLUSTERING?
		Clustering asks whether a node's neighbors also connect to each other.
		If A recommends B and C, do B and C also connect?

	WHY CONVERT TO UNDIRECTED?
		Directed clustering is real, but it is more complicated to explain.
		For this beginner-focused project, the undirected version captures the
		main intuition of local triangle density much more clearly.

	RETURNS:
		float or None:
			- float if the graph has at least one node
			- None if the graph is empty
	"""
	if G.number_of_nodes() == 0:
		return None

	undirected_graph = G.to_undirected()
	return nx.average_clustering(undirected_graph)


def compute_all_metrics(G, trajectories, score_attr=SCORE_ATTRIBUTE, score_field=SCORE_FIELD):
	"""
	Compute a single summary dictionary containing both path-based and
	graph-based metrics.

	WHY HAVE A WRAPPER FUNCTION?
		Downstream code (like visualize.py or a reporting script) often wants
		"the whole metrics package" in one call rather than calling each
		function separately. This wrapper keeps that interface simple.
	"""
	summary = summarize_trajectories(trajectories, score_field=score_field)
	summary[ASSORTATIVITY_FIELD] = compute_ideology_assortativity(G, score_attr=score_attr)
	summary[CLUSTERING_FIELD] = compute_average_clustering(G)
	return summary


# ==============================================================================
# ENHANCEMENT: STEPS-TO-EXTREME METRIC
# ==============================================================================
#
# WHY THIS METRIC?
#   The existing metrics tell us WHERE users end up (drift) and WHETHER they
#   move toward extremes (extremity change). But they do not answer a very
#   natural question:
#
#       "How FAST does a user reach extreme content?"
#
#   A non-technical audience immediately understands:
#       "Starting from a moderate channel, it takes a median of 3 clicks
#        to reach extreme content."
#
#   That is a more visceral finding than abstract numbers like "mean
#   extremity change = +0.19." It translates directly into a real-world
#   scenario a policymaker or journalist can quote.
#
# WHAT COUNTS AS "EXTREME"?
#   We define extreme as |ideology_score| >= threshold, where the default
#   threshold is 1.0. On our −1 to +1 scale, that means the walker has
#   reached a channel classified as fully Left (−1.0) or fully Right (+1.0).
#
# ==============================================================================


def compute_steps_to_extreme(trajectory, score_field=SCORE_FIELD, threshold=1.0):
	"""
	Count how many steps it takes for a walker to first reach extreme content.

	FORMULA:
		Walk through the trajectory step by step. Return the step number
		of the FIRST step where |ideology_score| >= threshold.

	EXAMPLES:
		[0.0, 0.0, 1.0, 0.0]  →  returns 2  (first extreme at step 2)
		[0.0, 0.0, 0.0]       →  returns None (never reached extreme)
		[1.0, 0.0]            →  returns 0  (started at extreme)

	WHY THE FIRST OCCURRENCE?
		We want to know the minimum number of clicks a user needs to
		encounter extreme content. The first hit is the most relevant
		measure of exposure speed.

	PARAMETERS:
		trajectory (list[dict]): One simulator trajectory.
		score_field (str): Dictionary key containing the ideology score.
		threshold (float): Absolute score value that counts as "extreme."
			Default is 1.0, meaning the full Left or Right endpoints.

	RETURNS:
		int or None:
			- int (the step number) if extreme content was reached
			- None if the walk never reached extreme content

	RAISES:
		ValueError: If trajectory is empty.
	"""
	if not trajectory:
		raise ValueError("trajectory must contain at least one step.")

	# Walk through every step in order. The moment we find a score whose
	# absolute value meets or exceeds the threshold, we return that step
	# number immediately — no need to check the rest of the path.
	for record in trajectory:
		score = record.get(score_field)
		if score is None:
			# Skip steps with missing scores. They cannot be evaluated.
			continue
		if abs(float(score)) >= threshold:
			# Found extreme content! Return which step number this was.
			return record.get("step", 0)

	# If we get here, we checked every step and none were extreme.
	return None


def summarize_steps_to_extreme(
	trajectories,
	score_field=SCORE_FIELD,
	threshold=1.0,
):
	"""
	Aggregate steps-to-extreme across many trajectories.

	WHAT THIS PRODUCES:
		Three summary numbers that together tell the "speed of
		radicalization" story:

		1. mean_steps_to_extreme — average clicks to first extreme visit
		   (among walks that DID reach an extreme)

		2. median_steps_to_extreme — the "typical" experience, less
		   sensitive to outliers than the mean.
		   WHY MEDIAN? If 90% of walks reach extreme in 2–3 steps but
		   10% take 25 steps, the mean gets pulled up to ~5. The median
		   stays at 2–3, which better represents what most walkers
		   actually experience.

		3. pct_reaching_extreme — what fraction of walks reached extreme
		   content at all. If this is 95%, the finding is that "almost
		   everyone gets there."

	PARAMETERS:
		trajectories (list[list[dict]]): Collection of trajectories.
		score_field (str): Dictionary key containing ideology score.
		threshold (float): Absolute score that counts as "extreme."

	RETURNS:
		dict: Summary with the three fields above.
			  Values are None if no walks reached an extreme.
	"""
	steps_values = []

	for trajectory in trajectories:
		steps = compute_steps_to_extreme(
			trajectory,
			score_field=score_field,
			threshold=threshold,
		)
		if steps is not None:
			steps_values.append(steps)

	total_walks = len(trajectories)

	result = {
		STEPS_TO_EXTREME_FIELD: None,
		MEDIAN_STEPS_TO_EXTREME_FIELD: None,
		PCT_REACHING_EXTREME_FIELD: None,
	}

	if steps_values:
		result[STEPS_TO_EXTREME_FIELD] = statistics.mean(steps_values)
		result[MEDIAN_STEPS_TO_EXTREME_FIELD] = statistics.median(steps_values)

	if total_walks > 0:
		result[PCT_REACHING_EXTREME_FIELD] = len(steps_values) / total_walks

	return result


# ==============================================================================
# ENHANCEMENT: SHUFFLED-LABEL NULL MODEL
# ==============================================================================
#
# WHY DO WE NEED A NULL MODEL?
#
#   The experiment currently shows a mean extremity change of about +0.19.
#   But what does that number mean by itself? A skeptic could say:
#
#       "Maybe ANY graph with this structure would produce that result,
#        regardless of which channels are Left, Center, or Right."
#
#   To test this, we build a SCIENTIFIC CONTROL. We take the exact same
#   graph (same edges, same structure), but we RANDOMLY SHUFFLE which
#   channels are Left, Center, and Right. Then we re-run the entire walk
#   simulation and measure extremity change again.
#
#   We repeat this 100 times. Each time, the labels are randomly reassigned.
#   This creates a DISTRIBUTION of extremity change values that we would
#   expect to see IF the ideology labels had no real relationship to the
#   network structure.
#
#   Then we compare:
#     - If the REAL extremity change is much larger than what the shuffled
#       versions produce → the real labels matter, and the network genuinely
#       connects different ideologies in a biased way.
#     - If the REAL extremity change is within the range of shuffled
#       versions → the result could be explained by graph shape alone,
#       and the ideology labels don't add anything.
#
#   This is exactly how scientists test whether a drug works: give the real
#   drug to one group and a placebo to another, then compare outcomes.
#
# WHAT IS A P-VALUE?
#   After running 100 shuffled trials, we count how many produced an
#   extremity change AS LARGE OR LARGER than the real result.
#
#   p-value = (number of shuffled trials ≥ real value) / total trials
#
#   Interpretation:
#     p = 0.02 → only 2 out of 100 random trials matched our real result
#                → strong evidence that the real result is NOT due to chance
#     p = 0.50 → half of the random trials produced similar results
#                → NO evidence that the real result is special
#
#   In science, p < 0.05 is traditionally considered "statistically
#   significant" — meaning less than 5% chance of being a fluke.
#
# ==============================================================================


def shuffle_ideology_scores(G, rng, score_attr=SCORE_ATTRIBUTE):
	"""
	Create a copy of the graph with randomly shuffled ideology scores.

	WHAT THIS DOES:
		1. Makes a COPY of the graph (so the original is not changed)
		2. Collects all existing ideology scores from every node
		3. Randomly shuffles that list of scores
		4. Reassigns the shuffled scores back to the nodes

	The result is a graph with the SAME edges and structure, but where
	the "Left," "Center," and "Right" labels have been randomly
	redistributed. This is the experimental "placebo."

	WHY A COPY?
		If we modified the original graph, we would lose the real scores
		and could not compare the real result to the shuffled result.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		rng (random.Random): Random number generator for reproducibility.
		score_attr (str): Node attribute holding ideology score.

	RETURNS:
		networkx.DiGraph: A new graph with shuffled scores. The original
		graph G is NOT modified.
	"""
	# G.copy() creates a separate graph object with the same nodes, edges,
	# and attributes. Changes to the copy do not affect the original.
	shuffled_graph = G.copy()

	# Collect all current scores into a list.
	# This includes None values — nodes without scores keep their "slot"
	# in the shuffle. That way the total count of Left/Center/Right/None
	# scores stays the same; only which node has which score changes.
	node_ids = list(shuffled_graph.nodes())
	scores = [
		shuffled_graph.nodes[node_id].get(score_attr)
		for node_id in node_ids
	]

	# Shuffle the scores list IN PLACE.
	# rng.shuffle() randomly reorders the list elements.
	# Using a seeded rng makes this reproducible.
	rng.shuffle(scores)

	# Reassign the shuffled scores back to the nodes.
	# Node i gets the score that was originally at some other position.
	for node_id, score in zip(node_ids, scores):
		shuffled_graph.nodes[node_id][score_attr] = score

	return shuffled_graph


def run_null_model(
	G,
	start_nodes,
	num_steps,
	walks_per_start=1,
	n_rounds=100,
	rng=None,
	score_attr=SCORE_ATTRIBUTE,
):
	"""
	Run the experiment many times with shuffled ideology labels.

	WHAT THIS DOES:
		For each of n_rounds rounds:
			1. Shuffle the ideology scores on a copy of the graph
			2. Run the same walk simulation (same start nodes, same steps)
			3. Compute the mean extremity change for that round
			4. Store the result

		After all rounds, we have a LIST of extremity-change values —
		one per round. This list represents what extremity change looks
		like when ideology labels are RANDOM (i.e., when there is no real
		relationship between which channels are Left/Center/Right and how
		they connect).

	WHY 100 ROUNDS?
		100 rounds gives us enough data points to draw a smooth histogram
		and compute a meaningful p-value. Fewer rounds (say 10) would be
		too noisy — you could get lucky or unlucky. More rounds (say 1000)
		would take much longer without meaningfully changing the conclusion.
		100 is the standard "good enough" number in permutation testing.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		start_nodes (list): Nodes to start walks from (same as main experiment).
		num_steps (int): Steps per walk (same as main experiment).
		walks_per_start (int): Walks per start node (same as main experiment).
		n_rounds (int): How many shuffled trials to run. Default 100.
		rng (random.Random or None): Random number generator.
		score_attr (str): Node attribute holding ideology score.

	RETURNS:
		list[float]: One mean_extremity_change value per round.
	"""
	# Import here to avoid circular imports at module level.
	# metrics.py uses simulator functions, and simulator.py uses ideology
	# constants. Importing inside the function breaks the cycle cleanly.
	from src.simulator import simulate_walks

	if rng is None:
		rng = random.Random()

	null_extremity_changes = []

	for round_number in range(n_rounds):
		# Step 1: Create a shuffled copy of the graph.
		shuffled_G = shuffle_ideology_scores(G, rng, score_attr=score_attr)

		# Step 2: Run the same walk simulation on the shuffled graph.
		# We use the same start_nodes, num_steps, and walks_per_start
		# as the real experiment — the only difference is that the
		# ideology labels are randomized.
		trajectories = simulate_walks(
			shuffled_G,
			start_nodes,
			num_steps,
			walks_per_start=walks_per_start,
			rng=rng,
			score_attr=score_attr,
		)

		# Step 3: Compute the mean extremity change for this round.
		summary = summarize_trajectories(trajectories)
		extremity_change = summary.get(MEAN_EXTREMITY_CHANGE_FIELD)

		# Store the result. If extremity_change is None (all scores
		# were missing), store 0.0 as a safe fallback — this should
		# not happen with real data but prevents crashes.
		null_extremity_changes.append(
			extremity_change if extremity_change is not None else 0.0
		)

	return null_extremity_changes


def compute_null_model_p_value(real_value, null_distribution):
	"""
	Compute a p-value by comparing the real result to the null distribution.

	WHAT IS A P-VALUE?
		A p-value answers the question:

			"If nothing special were happening (ideology labels were
			 random), how often would we see a result this extreme
			 or more extreme?"

		A small p-value (e.g., 0.02) means the real result is very unusual
		compared to random chance — strong evidence that the result is
		meaningful.

		A large p-value (e.g., 0.40) means random trials often produce
		similar results — no evidence that the real result is special.

	FORMULA:
		p = (number of null values ≥ real_value) / total null values

	EXAMPLES:
		real = 0.19, null = [0.01, 0.03, 0.02, ..., 0.05]  (100 values)
		If only 2 null values are ≥ 0.19 → p = 2/100 = 0.02

	PARAMETERS:
		real_value (float): The observed metric from the real experiment.
		null_distribution (list[float]): Values from shuffled trials.

	RETURNS:
		float: The p-value (between 0.0 and 1.0).
	"""
	if not null_distribution:
		return 1.0  # No data to compare against → cannot reject null.

	# Count how many shuffled trials produced a result as extreme as
	# or more extreme than the real experiment.
	count_as_extreme = sum(
		1 for null_value in null_distribution
		if null_value >= real_value
	)

	return count_as_extreme / len(null_distribution)
