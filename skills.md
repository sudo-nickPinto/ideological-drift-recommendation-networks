# Project Skills Context

- Pipeline order: graph_builder.py -> ideology.py -> simulator.py -> metrics.py -> visualize.py.
- graph_builder.py builds a NetworkX DiGraph from vis_channel_stats.csv and vis_channel_recs2.csv.
- ideology.py maps LR labels to IDEOLOGY_SCORE with L=-1.0, C=0.0, R=1.0.
- simulator.py should use weighted random walks based on RELEVANT_IMPRESSIONS_DAILY.
- metrics.py should consume walk trajectories plus graph structure for drift and network metrics.
- Tests use pytest and synthetic fixtures in tests/fixtures/.
- Preferred teaching style: explain every step, assume beginner-level background, define basic terms.
- Keep code heavily commented in the tutorial style already used in graph_builder.py and ideology.py.
- Use minimal, modular functions so each file stays teachable.
- Existing venv command: source .venv/bin/activate
- Common test commands:
  - python3 -m pytest tests/test_graph_builder.py -v
  - python3 -m pytest tests/test_ideology.py -v
  - python3 -m pytest tests/test_simulator.py -v
