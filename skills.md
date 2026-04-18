# Project Skills Context

- Pipeline order: graph_builder.py -> ideology.py -> simulator.py -> metrics.py -> visualize.py.
- graph_builder.py builds a NetworkX DiGraph from vis_channel_stats.csv and vis_channel_recs2.csv.
- ideology.py maps LR labels to IDEOLOGY_SCORE with L=-1.0, C=0.0, R=1.0.
- simulator.py should use weighted random walks based on RELEVANT_IMPRESSIONS_DAILY.
- metrics.py should consume walk trajectories plus graph structure for drift and network metrics.
- metrics.py public API now includes compute_walk_drift, compute_walk_extremity_change, compute_mean_drift, compute_mean_absolute_drift, compute_mean_extremity_change, compute_ideology_assortativity, compute_average_clustering, and compute_all_metrics.
- metrics.py summary field names are fixed for downstream CSV/reporting: num_trajectories, num_valid_drifts, mean_drift, mean_absolute_drift, mean_extremity_change, ideology_assortativity, average_clustering.
- metrics.py filters out nodes with missing IDEOLOGY_SCORE before assortativity, and computes clustering on an undirected copy of the graph for a simpler teachable interpretation.
- Tests use pytest and synthetic fixtures in tests/fixtures/.
- Preferred teaching style: explain every step, assume beginner-level background, define basic terms.
- Keep code heavily commented in the tutorial style already used in graph_builder.py and ideology.py.
- Use minimal, modular functions so each file stays teachable.
- Existing venv command: source .venv/bin/activate
- Common test commands:
  - python3 -m pytest tests/test_graph_builder.py -v
  - python3 -m pytest tests/test_ideology.py -v
  - python3 -m pytest tests/test_simulator.py -v
  - python3 -m pytest tests/test_metrics.py tests/test_visualize.py -v
