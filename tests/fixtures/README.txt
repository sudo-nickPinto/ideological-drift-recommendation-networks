# ==============================================================================
# TEST FIXTURES — Synthetic Data for Automated Testing
# ==============================================================================
#
# WHAT IS A "FIXTURE"?
#   In software testing, a "fixture" is any pre-arranged data or state that
#   tests rely on. Think of it like a lab experiment: before you run the
#   experiment, you set up the beakers, chemicals, and instruments the same
#   way every time. Fixtures are the beakers — consistent, controlled inputs
#   so your tests produce reliable, repeatable results.
#
# WHY SYNTHETIC DATA INSTEAD OF REAL DATA?
#   1. The real dataset has 7,079 nodes and 401,384 edges. You cannot verify
#      correctness by hand on data that large.
#   2. Synthetic data lets us design specific scenarios (self-loops, isolated
#      nodes, known L→C→R chains) so we can test edge cases deliberately.
#   3. Tests run instantly — no loading hundreds of thousands of rows.
#   4. Tests don't depend on external files that might move or change.
#
# FILES IN THIS DIRECTORY:
#   test_nodes.csv  — 10 fake YouTube channels (the graph's nodes)
#   test_edges.csv  — 16 fake recommendation links (the graph's edges)
#
# DESIGNED-IN PROPERTIES
# ======================
# Each property below was deliberately built into the synthetic data so that
# a specific piece of our code can be tested. Without these properties, we
# would have no way to verify that each module does what it claims to do.
#
#
# PROPERTY 1: Exactly 10 nodes
# WHY WE NEED IT:
#   This is the most basic sanity check for graph_builder.py. After loading
#   data and constructing the graph, we assert:
#       assert G.number_of_nodes() == 10
#   If the loader is skipping rows, duplicating rows, or failing to parse
#   a line, the count will be wrong and this test catches it immediately.
#   With the real data (7,079 nodes), you'd never notice one missing row.
#   With 10, every node is accounted for.
#
#
# PROPERTY 2: Exactly 16 edges, including 1 self-loop → 15 after filtering
# WHY WE NEED IT:
#   The real dataset contains 6,942 self-loops (a channel recommending
#   itself). Self-loops are meaningless for our analysis — following a
#   recommendation to the same channel you're already on doesn't represent
#   real user navigation. Our graph_builder must filter them out.
#   By including exactly 1 self-loop (ch_R1 → ch_R1), we can assert:
#       assert raw_edge_count == 16          # before filtering
#       assert G.number_of_edges() == 15     # after filtering
#   If both pass, the self-loop filter works correctly.
#
#
# PROPERTY 3: All three ideology labels present (L, C, R)
# WHY WE NEED IT:
#   The ideology.py module maps L→−1, C→0, R→+1. If we only had L and R
#   nodes, we'd never know if the code handles C correctly. Including all
#   three labels (3 Left, 3 Center, 3 Right + 1 Center isolated) means we
#   can verify every branch of the mapping logic. Our test will assert:
#       assert G.nodes["ch_L1"]["ideology_score"] == -1
#       assert G.nodes["ch_C1"]["ideology_score"] ==  0
#       assert G.nodes["ch_R1"]["ideology_score"] == +1
#
#
# PROPERTY 4: One isolated node (ch_island) with zero edges
# WHY WE NEED IT:
#   An "isolated node" is a channel that neither recommends nor gets
#   recommended by anyone. Real data might have channels like this
#   (they were classified by reviewers but have no recommendation links).
#   Code that isn't written defensively might crash when it tries to:
#     - compute outgoing edges for a node with none
#     - start a random walk from a node with no neighbors
#     - divide by zero when calculating "percent of recommendations"
#   By including ch_island, our tests verify the code handles this
#   gracefully instead of crashing.
#
#
# PROPERTY 5: A deliberate drift chain (L→C→R→R)
# WHY WE NEED IT:
#   The entire research question is: "Do recommendations push users toward
#   more extreme content?" To test whether the simulator detects this, we
#   need a path where drift DEFINITELY occurs and we know the answer in
#   advance.
#   The chain ch_L1 → ch_C1 → ch_R1 → ch_R2 has ideology scores:
#       Step 0: −1 (Left)
#       Step 1:  0 (Center)
#       Step 2: +1 (Right)
#       Step 3: +1 (Right)
#   That's clear rightward drift. If our drift measurement code is given
#   this path and doesn't detect positive drift, we know the code is wrong.
#   This is the single most important test property in the whole project.
#
#
# PROPERTY 6: Within-ideology clusters (echo chambers)
# WHY WE NEED IT:
#   The Left nodes (ch_L1, ch_L2, ch_L3) recommend each other heavily:
#       ch_L1→ch_L2 (weight 200), ch_L1→ch_L3 (weight 120),
#       ch_L2→ch_L1 (weight 150), ch_L2→ch_L3 (weight 60)
#   The Right nodes form a cycle: ch_R1→ch_R2→ch_R3→ch_R1.
#   These clusters let us test:
#     - ASSORTATIVITY: a graph metric that measures whether nodes connect
#       to similar nodes. High assortativity = like connects to like
#       (echo chambers). Our metrics.py will compute this, and we can
#       verify it's positive on this test data.
#     - CLUSTERING COEFFICIENT: how tightly connected local neighborhoods
#       are. The Right cycle (R1→R2→R3→R1) forms a triangle, which should
#       produce a high clustering coefficient.
#
#
# PROPERTY 7: Cross-ideology bridges (4 edges that cross L↔C↔R boundaries)
# WHY WE NEED IT:
#   Not all recommendations stay within one ideology. The test data includes:
#       ch_L1→ch_C1  (Left → Center,  weight 30)
#       ch_C1→ch_R1  (Center → Right, weight 50)
#       ch_R2→ch_C2  (Right → Center, weight 40)
#       ch_C3→ch_L3  (Center → Left,  weight 60)
#       ch_R3→ch_C2  (Right → Center, weight 20)
#       ch_C2→ch_L2  (Center → Left,  weight 10)
#   These are WEAKER than within-cluster edges (lower weights). This mirrors
#   the real-world hypothesis: the algorithm recommends similar content more
#   strongly. Our tests can verify:
#     - The graph is NOT fully siloed (cross-edges exist)
#     - Cross-edges have lower weights than within-cluster edges on average
#     - A random walker CAN cross boundaries, just less frequently
#
#
# PROPERTY 8: Varying edge weights (10.0 to 200.0)
# WHY WE NEED IT:
#   The simulator will do WEIGHTED random walks. At each step, the walker
#   chooses the next channel based on edge weights — higher weight = higher
#   probability of being chosen. If all edges had the same weight, every
#   neighbor would be equally likely, which wouldn't reflect reality.
#   By varying weights, we can test that:
#     - The simulator respects weights (a 200-weight edge is chosen more
#       often than a 30-weight edge over many trials)
#     - The walker tends to stay in clusters (within-cluster edges are
#       heavier) rather than crossing ideology boundaries
#   Example: From ch_L1, the choices are:
#       ch_L2 (weight 200) — 57% probability
#       ch_L3 (weight 120) — 34% probability
#       ch_C1 (weight  30) —  9% probability
#   So a walker leaving ch_L1 has a 91% chance of staying Left.
#
#
# COLUMN STRUCTURE:
#   Both files match the exact column names of the real Recfluence data
#   (vis_channel_stats.csv and vis_channel_recs2.csv) so the same loader
#   code works on both test and real data without modification.
# ==============================================================================
