"""Quick runner script: executes the full 5-stage pipeline on real data."""

import random

from src.graph_builder import load_nodes, load_edges, build_graph
from src.ideology import assign_ideology_scores, SCORE_ATTRIBUTE
from src.simulator import simulate_walks, simulate_walks_uniform
from src.metrics import (
    compute_all_metrics,
    compute_null_model_p_value,
    compute_steps_to_extreme,
    run_null_model,
    summarize_steps_to_extreme,
    summarize_trajectories,
    MEAN_EXTREMITY_CHANGE_FIELD,
)
from src.visualize import generate_all_figures

# Stage 1: Build graph
print("Stage 1: Building graph...")
nodes_df = load_nodes("data/vis_channel_stats.csv")
edges_df = load_edges("data/vis_channel_recs2.csv")
G = build_graph(nodes_df, edges_df)
print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

# Stage 2: Assign ideology scores
print("Stage 2: Assigning ideology scores...")
G = assign_ideology_scores(G)

# Stage 3: Simulate walks (sample 500 scored start nodes for speed)
print("Stage 3: Simulating walks...")
rng = random.Random(42)
scored_nodes = [
    n for n, d in G.nodes(data=True)
    if d.get(SCORE_ATTRIBUTE) is not None and G.out_degree(n) > 0
]
start_sample = rng.sample(scored_nodes, min(500, len(scored_nodes)))
trajectories = simulate_walks(
    G, start_sample, num_steps=10, walks_per_start=3, rng=rng
)
print(f"  Trajectories: {len(trajectories)}")

# Stage 4: Compute metrics
print("Stage 4: Computing metrics...")
metrics = compute_all_metrics(G, trajectories)
for key, val in metrics.items():
    print(f"  {key}: {val}")

# Stage 4a: Null model comparison
# Run the same experiment 100 times with shuffled ideology labels.
# This tells us whether the observed extremity change is statistically
# significant or could happen by chance from the graph structure alone.
print("Stage 4a: Running null model (100 rounds)...")
real_extremity = metrics.get(MEAN_EXTREMITY_CHANGE_FIELD, 0.0)
null_extremities = run_null_model(
    G, start_sample, num_steps=10, walks_per_start=3, n_rounds=100, rng=rng
)
null_p_value = compute_null_model_p_value(real_extremity, null_extremities)
print(f"  Real extremity change: {real_extremity:.4f}")
print(f"  Null model p-value: {null_p_value:.4f}")

# Stage 4b: Random browsing baseline
# Instead of following recommendation edges, walkers teleport to any
# random scored node at each step. This isolates whether RECOMMENDATIONS
# specifically cause drift, or whether drift is just a property of the
# dataset composition.
print("Stage 4b: Running random browsing baseline...")
random_trajectories = simulate_walks_uniform(
    G, start_sample, num_steps=10, walks_per_start=3, rng=rng
)
random_summary = summarize_trajectories(random_trajectories)
rec_summary = summarize_trajectories(trajectories)
print(f"  Recommendation mean abs drift: {rec_summary.get('mean_absolute_drift', 'N/A'):.4f}")
print(f"  Random mean abs drift:         {random_summary.get('mean_absolute_drift', 'N/A'):.4f}")

# Stage 4c: Steps to extreme
# For walks that started from Center (score 0.0), how many clicks to
# first reach extreme content (|score| = 1.0)?
print("Stage 4c: Computing steps to extreme...")
from src.simulator import SCORE_FIELD
center_trajectories = [
    t for t in trajectories
    if t and t[0].get(SCORE_FIELD) == 0.0
]
steps_summary = summarize_steps_to_extreme(center_trajectories)
# Collect individual step counts for the histogram
steps_list = []
for t in center_trajectories:
    s = compute_steps_to_extreme(t)
    if s is not None:
        steps_list.append(s)
print(f"  Center-starting walks: {len(center_trajectories)}")
print(f"  Median steps to extreme: {steps_summary.get('median_steps_to_extreme', 'N/A')}")
print(f"  Pct reaching extreme: {steps_summary.get('pct_reaching_extreme', 'N/A')}")

# Stage 5: Generate all figures
print("Stage 5: Generating figures...")
generate_all_figures(
    G, trajectories, metrics, output_dir="results",
    null_extremities=null_extremities,
    null_p_value=null_p_value,
    real_extremity=real_extremity,
    rec_summary=rec_summary,
    random_summary=random_summary,
    steps_to_extreme_data={
        "steps_list": steps_list,
        "median": steps_summary.get("median_steps_to_extreme"),
        "pct_reaching": steps_summary.get("pct_reaching_extreme"),
    },
)
print("Done! Check results/figures/ and results/tables/")
