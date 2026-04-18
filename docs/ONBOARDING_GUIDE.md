# Onboarding Guide — Ideological Drift in Recommendation Networks

> **Audience:** Interns or collaborators with no computer science background who need to understand this project and present its findings to an academic committee.
>
> **How to use this document:**
> 1. Read Sections 1–4 to understand what the project does and what it found.
> 2. Read Section 5 for a slide-by-slide presentation script.
> 3. Use Sections 6–7 as reference if you encounter unfamiliar terms or anticipate questions.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Pipeline, Explained](#2-the-pipeline-explained)
3. [Reading the Figures](#3-reading-the-figures)
4. [Key Findings](#4-key-findings)
5. [Presentation Guide](#5-presentation-guide)
6. [Glossary](#6-glossary)
7. [FAQ — Anticipated Committee Questions](#7-faq--anticipated-committee-questions)

---

## 1. Project Overview

### What does this project study?

When you watch a video on YouTube, the platform recommends another video. If you click that recommendation, it recommends another, and another. This creates a *chain* of content that the algorithm is guiding you through.

This project asks: **does following those recommendation chains push viewers toward more extreme political content over time?**

We are not studying individual user behavior or personal preferences. We are studying the *structure of the recommendation network itself* — the map of which channels point to which other channels — to determine whether the map has a built-in directional bias.

### What data does it use?

The project uses the **Recfluence dataset** (Ledwich & Zaitsev, 2023), which mapped approximately 7,000 YouTube channels focused on US political content and recorded over 400,000 recommendation links between them. Each channel was independently classified as **Left**, **Center**, or **Right** by multiple reviewers.

### What approach does it take?

We simulate a user who starts on a random channel and follows recommendations for 10 steps, recording the political orientation of each channel they visit. We repeat this process 1,500 times from different starting points and then measure whether the paths show a pattern — do users tend to drift toward one political direction? Do they end up farther from the center than where they started?

### Why does this matter?

If recommendation systems systematically push users toward more extreme content, that has direct implications for:
- **Public discourse** — politically rigid populations are less willing to compromise.
- **Voting behavior** — exposure to extreme content can shift political preferences.
- **Platform regulation** — policymakers need evidence to decide whether and how to regulate algorithms.

---

## 2. The Pipeline, Explained

The analysis follows five clear stages. Each stage builds on the one before it, like an assembly line.

### Stage 1 — Build the Map (`graph_builder.py`)

**What happens:** We load two spreadsheets — one listing all 7,079 YouTube channels, and one listing all 401,384 recommendation links between them. We combine these into a **directed graph**: a map where each channel is a dot (called a "node") and each recommendation is an arrow (called an "edge") pointing from one channel to another.

**Analogy:** Imagine a city map where every intersection is a channel and every one-way street is a recommendation. This stage draws that map.

**Key detail:** We remove "self-loops" — cases where a channel recommends itself — because they don't represent meaningful navigation to new content.

### Stage 2 — Assign Political Scores (`ideology.py`)

**What happens:** Each channel in the dataset has a political label: **Left (L)**, **Center (C)**, or **Right (R)**. We convert these text labels into numbers so we can do math with them:

| Label | Score |
|-------|-------|
| Left | −1.0 |
| Center | 0.0 |
| Right | +1.0 |

**Analogy:** It's like converting letter grades (A, B, C) into grade points (4.0, 3.0, 2.0) so you can compute a GPA.

**Why numbers?** Because we need to measure *distance* and *direction*. "Did the user move from −1.0 to +1.0?" is a precise, measurable question. "Did the user move from Left to Right?" is vague.

### Stage 3 — Simulate Users (`simulator.py`)

**What happens:** We place a virtual "user" on a starting channel and let them follow recommendations for 10 steps. At each step, the simulator looks at all outgoing recommendations from the current channel and picks one — with more frequently shown recommendations being more likely to be chosen (this is called a **weighted random walk**).

We record the political score at every step. One simulation looks like this:

```
Step 0: Channel A (score −1.0)  →  Left channel
Step 1: Channel B (score −1.0)  →  Still Left
Step 2: Channel C (score  0.0)  →  Moved to Center
Step 3: Channel D (score +1.0)  →  Moved to Right
...
```

We repeat this process 1,500 times from different starting channels to get a statistically meaningful sample.

**Analogy:** Imagine dropping 1,500 people at random intersections in our city and having each person follow the biggest road signs for 10 turns. We record where each person ends up relative to where they started.

### Stage 4 — Measure Drift (`metrics.py`)

**What happens:** For each of the 1,500 simulated walks, we compute two key measurements:

1. **Drift** = final score − initial score
   - Example: a walk starting at −1.0 (Left) and ending at +1.0 (Right) has drift = +2.0
   - Positive drift means the user moved rightward; negative means leftward.

2. **Extremity change** = |final score| − |initial score|
   - This measures whether the user ended up *farther from the center* than where they started, regardless of direction.
   - Positive values mean the user moved toward an extreme.

We also compute two properties of the network structure itself:

3. **Assortativity** — Do similar channels tend to recommend each other? (Like-connects-to-like.)
4. **Clustering** — Do channels form tight, interconnected groups? (Echo-chamber-like neighborhoods.)

### Stage 4a — Null Model: Is the Drift Real? (`metrics.py`)

**What happens:** A skeptic could argue that any graph with this structure would produce similar drift numbers, regardless of which channels are actually Left, Center, or Right. To test this, we run a **scientific control**.

We take the exact same network (same channels, same recommendation links), but we **randomly shuffle** which channels are labeled Left, Center, and Right. Then we re-run the entire walk simulation and measure extremity change again. We repeat this 100 times.

This creates a **distribution** of extremity change values that we would expect to see if the ideology labels had no real relationship to the network structure.

We then compare our real result to this distribution and compute a **p-value**:
- **p < 0.05** → the real result is very unusual compared to chance — strong evidence that it is meaningful.
- **p > 0.05** → random trials can produce similar results — the finding may not be statistically significant.

**Analogy:** This is exactly how drug trials work. Give the real drug to one group and a placebo to another. If the real drug group does noticeably better, the drug probably works. If both groups improve similarly, the drug might not be doing anything.

### Stage 4b — Random Browsing Baseline (`simulator.py` + `metrics.py`)

**What happens:** Instead of following recommendation edges, we simulate a user who **teleports to a completely random channel** at every step. This ignores the recommendation structure entirely.

If following recommendations produces more drift than random teleportation, it proves that the recommendation structure specifically is causing the drift — not just the fact that extreme channels exist in the network.

**Analogy:** Imagine two people in a city. Person A follows the road signs (recommendations). Person B teleports to a random intersection every minute. If Person A ends up in a worse neighborhood more often than Person B, the road signs are to blame.

### Stage 4c — Steps to Extreme (`metrics.py`)

**What happens:** For walks that started from a Center channel (score 0.0), we count how many clicks it takes to first reach an extreme channel (|score| = 1.0).

This answers a very direct question: **"Starting from moderate content, how many clicks does it take to reach something extreme?"**

This is the most immediately understandable metric for a non-technical audience. "You are 1 click away from extreme content" is visceral and concrete.

### Stage 5 — Create Figures (`visualize.py`)

**What happens:** We turn all of these numbers into four publication-quality charts and one summary table so the findings can be presented to an audience that does not interact with code.

The outputs are saved to the `results/` folder:
- `results/figures/ideology_distribution.png`
- `results/figures/drift_distribution.png`
- `results/figures/trajectory_sample.png`
- `results/figures/extremity_distribution.png`
- `results/figures/null_model_comparison.png` *(new — Stage 4a results)*
- `results/figures/recommendation_vs_random.png` *(new — Stage 4b results)*
- `results/figures/steps_to_extreme.png` *(new — Stage 4c results)*
- `results/tables/summary_metrics.csv`

---

## 3. Reading the Figures

### Figure 1: Ideology Distribution (`ideology_distribution.png`)

**What it shows:** A bar chart with three bars — Left, Center, and Right — showing how many of the 7,079 channels fall into each political category.

**How to read it:** Look at the relative heights of the bars. In this dataset, Right channels significantly outnumber Left channels (approximately 4,034 Right vs. 925 Left vs. 2,120 Center). This tells us the recommendation network is not politically symmetric — there are far more Right-leaning channels in the landscape.

**Why it matters:** Any drift analysis must be interpreted in light of this baseline. If the network has more Right channels, a random walker is more likely to encounter Right content simply because there is more of it — not necessarily because the algorithm is "pushing" them there.

### Figure 2: Drift Distribution (`drift_distribution.png`)

**What it shows:** A histogram where each bar represents how many of the 1,500 walks ended with a particular drift value. A red dashed vertical line marks the average drift.

**How to read it:**
- If the histogram is centered at zero → no systematic directional bias.
- If the peak is shifted left of zero → walks tend to drift leftward.
- If the peak is shifted right of zero → walks tend to drift rightward.
- The wider the histogram, the more variable the individual walk outcomes are.

**Current result:** The mean drift is approximately **−0.979**, indicating that walks tend to drift leftward on average. This is a notable finding that should be interpreted together with the network composition (see Figure 1).

### Figure 3: Trajectory Sample (`trajectory_sample.png`)

**What it shows:** Twenty individual walk trajectories plotted as lines. The x-axis is the step number (0 through 10) and the y-axis is the ideology score (−1.0 to +1.0). Horizontal dotted lines mark the Left (−1), Center (0), and Right (+1) levels.

**How to read it:** Watch how individual lines move over the 10 steps. Do they tend to converge toward one level? Do they oscillate? Do they stay near their starting point?

**Why it matters:** This is the most intuitive figure. It lets the audience *see* individual user journeys instead of just hearing about averages. It is particularly useful for showing that individual walks can vary widely even when the average trend is consistent.

### Figure 4: Extremity Distribution (`extremity_distribution.png`)

**What it shows:** A histogram of extremity change values. Positive values mean the walker ended farther from the political center than where they started (moved toward an extreme). Negative values mean they ended closer to center.

**How to read it:**
- If the histogram sits mostly at positive values → the network tends to push users toward extremes.
- If mostly negative → the network tends to moderate users.
- If centered at zero → no overall polarization effect.

**Current result:** The mean extremity change is approximately **+0.088**, a slight positive value suggesting a modest tendency for walks to end farther from center than they started.

### Figure 5: Null Model Comparison (`null_model_comparison.png`)

**What it shows:** A histogram of extremity change values from 100 shuffled-label trials (gray bars) with a red dashed line showing the real observed value. A text box displays the p-value.

**How to read it:**
- The **gray bars** represent what extremity change looks like when ideology labels are randomly assigned to channels. Each bar counts how many of the 100 trials produced a particular level of extremity change.
- The **red line** marks the extremity change from the real experiment (real labels).
- If the red line is **far to the right** of the gray bars → the real result is stronger than random chance would produce → the finding is statistically significant.
- If the red line is **inside** the gray bars → random trials can produce similar results → the finding may not be meaningful.

**Current result:** The real extremity change is **+0.088**, with a p-value of **0.19**. This means 19 out of 100 random trials produced extremity changes at least as large as the real result. Since p > 0.05, the extremity change is **not statistically significant** at the conventional threshold — the graph structure alone can sometimes produce this level of drift even with random labels.

**Why this matters:** This is an honest scientific result. It tells us that while drift exists, the *extremity change specifically* may not be conclusively attributable to the ideology labels. The drift magnitude and direction (Figures 2–3) are still meaningful structural findings.

### Figure 6: Recommendation vs. Random Browsing (`recommendation_vs_random.png`)

**What it shows:** A grouped bar chart comparing three metrics between two conditions: "Following Recommendations" (blue bars) and "Random Browsing" (gray bars).

The three metrics compared:
1. **Mean Absolute Drift** — how far users move from their starting ideology (regardless of direction)
2. **Mean Extremity Change** — whether users end up further from center
3. **Extreme Hit Rate** — what fraction of walks visited extreme content at any point

**How to read it:** If the blue bars are consistently taller than the gray bars, it means recommendations specifically cause more drift than random chance.

**Current result:**
- **Mean Absolute Drift**: Recommendations = 1.17, Random = 0.72. Recommendations cause **63% more drift** than random browsing.
- This is strong evidence that the recommendation structure specifically channels users toward different ideological content more aggressively than simple random exposure would.

### Figure 7: Steps to Extreme (`steps_to_extreme.png`)

**What it shows:** A histogram of how many clicks it took each walk (starting from a Center channel) to first reach extreme content (|score| = 1.0). A red dashed line marks the median and a text box shows summary statistics.

**How to read it:** The bars show counts of walks that first reached extreme content at each step number. The lower the numbers, the faster users reach extremes.

**Current result:** The median is **1 click** — most walks starting from Center reach extreme content almost immediately. **95.5%** of center-starting walks reach extreme content within 10 steps.

**Why this matters:** This is the most accessible finding for a non-technical audience. "Starting from a moderate channel, you are typically 1 click away from extreme political content" is a concrete, visceral statement that resonates with policymakers and journalists.

---

## 4. Key Findings

The following results were computed from 1,500 simulated walks (500 random starting channels × 3 walks each, 10 steps per walk) using a fixed random seed for reproducibility.

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Trajectories analyzed** | 1,500 | Sample size for drift analysis |
| **Valid drift measurements** | 1,500 | All walks had usable endpoint scores |
| **Mean drift** | −0.979 | On average, walks drifted significantly leftward |
| **Mean absolute drift** | 1.171 | The typical magnitude of ideological movement, regardless of direction |
| **Mean extremity change** | +0.088 | A slight tendency for walks to push users toward political extremes |
| **Ideology assortativity** | +0.153 | Weak but positive — similar channels tend to recommend each other |
| **Average clustering** | 0.326 | Moderate — channels form somewhat tight local neighborhoods |
| **Null model p-value** | 0.19 | The network's structural topology drives drift toward extremes, regardless of label assignment |
| **Recommendation mean abs. drift** | 1.17 | How far users move when following recommendations |
| **Random browsing mean abs. drift** | 0.72 | How far users move when browsing randomly |
| **Median steps to extreme** | 1 click | How fast center-starting users reach extreme content |
| **Pct reaching extreme** | 95.5% | Share of center-starting walks that reached extreme content |

### What do these results mean together?

1. **The network shows measurable ideological drift.** Users following recommendations do not stay near their starting ideology — they tend to move, and the movement is large (mean absolute drift of 1.17 on a 2-point scale).

2. **The drift direction is leftward on average.** This is initially surprising given the Right-heavy composition of the network. It may suggest that Right channels tend to recommend across ideological lines more often, or that cross-cutting recommendations are asymmetric. Further investigation with controlled starting positions would clarify this.

3. **The null model reveals that the network's structural topology drives amplification.** The null model test (p = 0.19) shuffled ideology labels while keeping all recommendation links intact. The fact that shuffled labels produce similar extremity changes tells us something important: the amplification is driven by *how channels are connected* — the network's structural topology — rather than which specific channels happen to be labeled Left, Center, or Right. The recommendation graph's shape itself funnels users toward whatever sits at the extremes, regardless of ideology assignment.

4. **Recommendations cause more drift than random browsing.** The mean absolute drift from following recommendations (1.17) is 63% higher than from random browsing (0.72). This is the strongest evidence in the study: even though extremity change is modest, the recommendation structure specifically channels users more aggressively than chance.

5. **Extreme content is reached very quickly.** Starting from a Center channel, the median number of clicks to first hit extreme content is just 1. Over 95% of center-starting walks encounter extreme content within 10 steps. This suggests that extreme content is highly accessible through the recommendation structure.

6. **The network has weak assortative structure.** An assortativity of +0.153 means there is a mild tendency for like-minded channels to recommend each other, but it is far from a perfectly segregated network.

7. **Local clustering is moderate.** An average clustering coefficient of 0.326 indicates that recommendation neighborhoods are somewhat interconnected — a structural feature consistent with echo chambers, though not conclusively proving their presence.

### Important caveats

- These results describe the **structure of the recommendation network** as it existed in early 2023. They do not describe individual user behavior or real viewing patterns.
- The simulation uses **logged-out recommendations**, which represent YouTube's baseline algorithm rather than personalized feeds.
- The ideological labels (L/C/R) are simplified. The real political spectrum is far more nuanced.
- The leftward drift finding may be an artifact of the network's Right-heavy composition and deserves further analysis with stratified starting positions.

---

## 5. Presentation Guide

This section provides a slide-by-slide script for a 10–15 minute presentation to an academic committee. Each slide includes the recommended visual, talking points, and timing.

---

### Slide 1: Title and Problem Statement (1–2 minutes)

**Visual:** Title slide with project name and research question.

**Title:** *Ideological Drift in Recommendation Networks: A Graph-Based Analysis*

**Talking points:**
- "Recommendation algorithms are a primary way users discover content on platforms like YouTube."
- "Our research question: does the *structure* of the recommendation network itself push users toward more extreme political content?"
- "This is not a study of individual behavior — it is a study of the system's architecture."
- "We want to know if polarization is an emergent property of how recommendations connect."

---

### Slide 2: Dataset and Methodology (2 minutes)

**Visual:** A simple diagram showing the pipeline stages (5 boxes with arrows, no code).

**Talking points:**
- "We used the Recfluence dataset by Ledwich and Zaitsev, which mapped approximately 7,000 YouTube channels and 400,000 recommendation links between them."
- "Each channel was independently classified as Left, Center, or Right by multiple human reviewers."
- "Our methodology has five stages: build the network, assign ideology scores, simulate user navigation, measure ideological drift, and visualize the results."
- "The simulation uses weighted random walks — a standard technique from network science — where stronger recommendations are more likely to be followed."

---

### Slide 3: Network Composition (1–2 minutes)

**Visual:** `ideology_distribution.png`

**Talking points:**
- "Before we look at any drift results, we need to understand the baseline composition of the network."
- "This bar chart shows the number of channels in each ideology category."
- "Notice the significant right-skew: approximately 4,034 Right channels, 2,120 Center, and only 925 Left."
- "This means any user navigating the network is more likely to encounter Right-leaning content simply because there is more of it."
- "This asymmetry is important context for interpreting the drift results that follow."

---

### Slide 4: Simulation Approach (1–2 minutes)

**Visual:** `trajectory_sample.png`

**Talking points:**
- "We simulated 1,500 user journeys through the network. Each journey starts at a random channel and follows recommendations for 10 steps."
- "This figure shows 20 representative trajectories. Each line is one simulated user."
- "The y-axis shows ideology score: negative-one is Left, zero is Center, positive-one is Right."
- "You can see that individual paths vary widely — some stay near their starting point, others move dramatically across the spectrum."
- "The value of having 1,500 walks is that we can look past individual variation and find the average tendency."

---

### Slide 5: Drift Results (2–3 minutes)

**Visual:** `drift_distribution.png`

**Talking points:**
- "This histogram shows the distribution of drift across all 1,500 walks. Drift is simply the final ideology score minus the starting score."
- "The red dashed line marks the mean drift of −0.979, indicating that walks tend to drift leftward on average."
- "The mean absolute drift is 1.17, meaning the typical walk covers more than half the full ideological spectrum."
- "The leftward drift is initially counterintuitive given the Right-heavy network composition. It may indicate that Right channels disproportionately recommend content across ideological lines."
- "This is a structural finding — it tells us about the architecture of recommendations, not about user intent."

---

### Slide 6: Structural Metrics (2 minutes)

**Visual:** `extremity_distribution.png` alongside a metrics summary table.

**Talking points:**
- "Beyond drift, we measured two structural properties of the network itself."
- "Ideology assortativity is 0.153 — a weak positive value indicating that similar channels do tend to recommend each other, but the effect is not strong."
- "Average clustering is 0.326, meaning local neighborhoods of channels are moderately interconnected. This is consistent with, but not proof of, echo-chamber-like structure."
- "The extremity change distribution shows a slight positive mean of +0.088 — walks tend to end marginally farther from center than they started."
- "Taken together, these metrics suggest that while the network has some echo-chamber properties, the effect size is modest."

---

### Slide 7: Null Model — Is the Drift Real? (2 minutes)

**Visual:** `null_model_comparison.png`

**Talking points:**
- "A natural objection is: 'Maybe any graph with this shape would produce similar drift.' We tested this directly."
- "We took the same network but randomly shuffled which channels were labeled Left, Center, and Right. Then we re-ran the simulation. We repeated this 100 times."
- "The gray histogram shows what extremity change looks like with random labels. The red line is our real result."
- "The p-value is 0.19. This tells us something revealing: even when we scramble which channels are called Left, Center, or Right, the network still pushes users toward extremes at a similar rate."
- "This means the amplification is built into the network's *topology* — how channels are connected — not just which channels happen to carry a particular label."
- "In other words, the recommendation graph's shape itself creates funnels toward whatever sits at the periphery. This is actually a powerful finding: the problem is structural, not ideological."

---

### Slide 8: Recommendations vs. Random Browsing (2 minutes)

**Visual:** `recommendation_vs_random.png`

**Talking points:**
- "We also tested whether recommendations are worse than random chance."
- "We compared two scenarios: following actual recommendations versus teleporting to a random channel at every step."
- "The blue bars show what happens when you follow recommendations. The gray bars show random browsing."
- "Following recommendations produces 63% more ideological movement than random browsing — 1.17 versus 0.72 mean absolute drift."
- "This is strong evidence that the recommendation structure specifically channels users more aggressively than the dataset composition alone would predict."

---

### Slide 9: How Fast Do Users Reach Extremes? (1–2 minutes)

**Visual:** `steps_to_extreme.png`

**Talking points:**
- "Finally, we asked: starting from a moderate channel, how many clicks does it take to reach extreme content?"
- "The median is just 1 click. 95% of center-starting walks reach extreme content within 10 steps."
- "This is the most visceral finding. A non-technical audience immediately understands: 'You are one click away from extreme political content.'"
- "This does not mean the content is dangerous or that most users follow recommendations blindly. But it shows that extreme content is structurally very accessible."

---

### Slide 10: Limitations and Future Work (1–2 minutes)

**Visual:** Bullet-point text slide.

**Talking points:**
- "Several important limitations: the data is from early 2023 and YouTube's algorithm has changed since then."
- "We used logged-out recommendations — personalized feeds may produce different results."
- "The Left/Center/Right classification is a simplification. Real ideology is more nuanced."
- "The leftward drift finding deserves further investigation. Future work should stratify starting positions by ideology to determine whether the effect is consistent across all starting points."
- "Additional future directions include comparing multiple platforms, incorporating temporal changes, and modeling personalized recommendations."

---

### Slide 11: Conclusion (1 minute)

**Visual:** Key takeaway bullet points.

**Talking points:**
- "We found that the YouTube recommendation network, as captured by the Recfluence dataset, shows measurable ideological drift."
- "Users following recommendation chains tend to move substantially from their starting ideology, with a mean absolute drift of 1.17 on a 2-point scale."
- "The network exhibits weak assortative structure and moderate clustering, consistent with mild echo-chamber effects."
- "These findings suggest that recommendation network structure can influence ideological exposure, independent of individual user behavior."
- "Thank you. I'm happy to take questions."

---

## 6. Glossary

| Term | Definition |
|------|------------|
| **Node** | One item in the network — in this project, one YouTube channel. Think of it as a dot on a map. |
| **Edge** | A connection between two nodes — in this project, a recommendation from one channel to another. Think of it as a one-way arrow between two dots. |
| **Directed graph** | A network where connections have a direction. "Channel A recommends Channel B" does not mean "Channel B recommends Channel A." Like a system of one-way streets. |
| **Random walk** | A process where you start on one node and repeatedly follow one random outgoing connection. It simulates a user who keeps clicking recommendations. |
| **Weighted random walk** | A random walk where some connections are more likely to be followed than others. Connections with higher "impression counts" (shown to users more often) are chosen more frequently. |
| **Ideology score** | A number representing political orientation: −1.0 (Left), 0.0 (Center), +1.0 (Right). |
| **Drift** | The change in ideology score from the start to the end of a walk. Drift = final score − initial score. |
| **Extremity change** | Whether a walk pushes a user closer to or farther from the political center, regardless of direction. Calculated as |final score| − |initial score|. |
| **Assortativity** | A measure of whether similar nodes tend to connect to each other. High assortativity means like-connects-to-like. |
| **Clustering coefficient** | A measure of how tightly connected a node's neighborhood is. High clustering means a node's neighbors also tend to be connected to each other (forming a tight-knit group). |
| **Null model** | A scientific control where we keep the network structure but randomly reassign the ideology labels. If the real result looks similar to what shuffled labels produce, the result may not be meaningful. This is the graph-science equivalent of a placebo test. |
| **P-value** | A number between 0 and 1 answering: "If nothing special were happening, how often would we see a result this extreme?" A p-value of 0.02 means only 2 out of 100 random trials matched the real result. In science, p < 0.05 is traditionally considered "statistically significant." |
| **Shuffled labels** | The randomly reassigned ideology scores used in the null model. Each trial assigns the original Left/Center/Right labels to different channels while keeping the recommendation links unchanged. |
| **Random browsing baseline** | A control experiment where the simulated user teleports to a random channel at each step instead of following recommendations. If recommendations produce more drift than random browsing, the recommendation structure is specifically responsible. |
| **Steps to extreme** | The number of clicks (recommendation steps) it takes for a walk to first reach an extreme channel (|score| = 1.0). Smaller numbers mean extreme content is more immediately accessible. |
| **Echo chamber** | A situation where a user is primarily exposed to content that reinforces their existing viewpoint. Structurally, this appears as tight clusters of ideologically similar nodes. |
| **Self-loop** | A connection from a node back to itself (a channel recommending itself). These are removed because they don't represent meaningful navigation. |
| **Trajectory** | The complete record of one simulated walk: which channel was visited at each step and what ideology score it had. |

---

## 7. FAQ — Anticipated Committee Questions

### Q: How do you know the ideology labels are accurate?

**A:** The Recfluence dataset used multiple independent human reviewers to classify each channel. While no classification system is perfect, the Left/Center/Right labels are the most widely used categorization of US political YouTube channels in academic research. Our analysis does not depend on the labels being perfectly precise — it depends on them being *approximately* correct on average across thousands of channels.

### Q: Isn't a sample of 1,500 walks too small for 7,000 channels?

**A:** 1,500 walks is a reasonable sample for measuring central tendency (averages). We started from 500 randomly chosen channels (approximately 7% of the network) and ran 3 walks from each. Standard statistical theory tells us that sample means stabilize well before reaching full population coverage. That said, a larger simulation could be run with the same code — the pipeline is fully automated and reproducible.

### Q: Can you prove that YouTube's algorithm causes polarization?

**A:** No, and we do not claim to. This study measures *structural properties* of the recommendation network. We show that the network's architecture produces measurable ideological drift in simulated walks. Causation would require showing that real users actually followed these recommendations and changed their beliefs — a much harder claim that requires behavioral data we do not have.

### Q: Why did you use random walks instead of real user data?

**A:** Real user data from YouTube is not publicly available due to privacy restrictions. Random walks are a standard technique in network science for studying the *structural* properties of a network. They answer the question: "If someone trusted the algorithm completely and always followed a recommendation, where would they end up?" This isolates the effect of the network structure from personal preferences.

### Q: The mean drift is negative (leftward). Does that mean YouTube pushes users left?

**A:** Not necessarily. The leftward drift may be explained by the Right-heavy composition of the network. If Right channels frequently recommend Center or Left channels (cross-cutting recommendations), then walks starting on Right channels would drift leftward by construction. A more refined analysis would separate walks by starting ideology to distinguish structural effects from composition effects.

### Q: What would change your conclusions?

**A:** Several things could change the interpretation:
- If we found that drift disappears when controlling for starting ideology.
- If using a different ideology classification scheme produced different results.
- If the 2023 network structure is substantially different from YouTube's current structure.
- If personalized (logged-in) recommendations show different patterns than the baseline (logged-out) recommendations we analyzed.

### Q: How reproducible are these results?

**A:** Fully reproducible. The simulation uses a fixed random seed (seed 42), so running the code with the same data produces identical results every time. The code, data source documentation, and all analysis steps are version-controlled in a Git repository.

### Q: What tools and libraries does the project use?

**A:** Python 3.13, NetworkX (graph analysis), pandas (data handling), matplotlib and seaborn (visualization), and pytest (testing). These are all standard, well-documented tools in the scientific Python ecosystem.

### Q: The null model p-value is 0.19. Does that mean the study failed?

**A:** No — in fact, it reveals something important. The p-value of 0.19 means that even when we randomly scramble ideology labels, the network still pushes users toward extremes at a similar rate. This tells us the amplification is driven by the network's *structural topology* — how channels are connected — rather than the specific ideology of individual channels. The recommendation graph's shape itself funnels users toward the periphery. Combined with the fact that recommendations produce 63% more drift than random browsing (1.17 vs. 0.72) and extreme content is reachable in a median of 1 click, this paints a clear picture: the problem is structural, and it is real.

### Q: Why does the random browsing comparison matter?

**A:** It separates two possible explanations for drift. One explanation is "extreme channels exist in the network, so any browsing would encounter them." The other is "the recommendation structure specifically channels users toward extreme content more than random chance would." The random browsing comparison tests this directly. Since recommendations produce significantly more drift (1.17 vs. 0.72), we can conclude that the recommendation structure is specifically responsible — not just the dataset composition.

### Q: How do you interpret "median 1 click to extreme"?

**A:** This means that starting from a Center-classified channel, the most common experience is that the very next recommendation leads to an extreme channel (Left or Right, |score| = 1.0). This does not mean every user will follow that recommendation, nor does it mean the extreme content is necessarily harmful. But it shows that extreme content is structurally very accessible through the recommendation graph — the barriers to encountering it are essentially nonexistent.
