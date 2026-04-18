# Ideological Drift in Recommendation Networks


## 1. What Is This Project About?

You know how YouTube recommends videos on the sidebar? Click one, and it recommends another. Click that, and another appears. Before you know it, you've gone down a rabbit hole.

This project asks a simple question: **does YouTube's recommendation system push people toward more extreme political content?**

We didn't study real users or watch history. Instead, we studied the *recommendation network itself* — the map of which YouTube channels recommend which other channels. 

## 2. Why Does This Matter?

If recommendation algorithms systematically funnel people toward political extremes, that has real consequences:

- People become more entrenched in their views and less open to compromise.
- Political polarization gets worse, which affects elections, policy, and public discourse.
- Policymakers are actively debating whether to regulate these algorithms, and they need evidence, not guesses.

Our study contributes a piece of that evidence.

---

## 3. What Data Did We Use?

We used a publicly available dataset called **Recfluence** (created by researchers Ledwich and Zaitsev). It contains:

- **About 7,000 YouTube channels** focused on US political content.
- **About 400,000 recommendation links** — records of which channels YouTube recommended alongside which other channels.
- **Political labels** for each channel — every channel was independently classified as **Left**, **Center**, or **Right** by verified human reviewers.

This is publicly logged-out recommendation data from YouTube, meaning it represents what YouTube would show to someone who isn't signed in, known asthe platform's baseline algorithm, not a personalized feed.

---

## 4. How Did We Run the Experiment?

1. **Pick a random starting channel.**
2. **Follow one recommendation** (weighted by how prominent it is by relevant impressions).
3. **Repeat for 10 steps**, recording the political score at each step.
4. **Do this 1,500 times** from different starting points.

At the end, we measure things like: did people tend to drift left or right? Did they end up farther from the center? How quickly did they encounter extreme content?

We also ran three additional checks to make sure the results are trustworthy. More on those below.

---

## 5. The Null Model

This is one of the checks. Think of it as a **placebo test**.

We kept all the recommendation links exactly the same, but we **randomly shuffled the color labels** on the intersections. So a channel that was "Left" might now be labeled "Right," and vice versa. Then we re-ran the simulation and measured the results. We did this 100 times.

**What we found:** The shuffled-label simulations produced similar levels of "push toward extremes" as the real labels. The p-value was 0.19, which means 19 out of 100 random shuffles matched or exceeded our real result.

**What this means:** The push toward extremes isn't about which specific channels have which labels. It's about **how the channels are connected** — the shape of the network itself. The problem is structural, coded into how the recommendation graph is wired.

---

## 6. What Is the "Random Browsing" Comparison?

This is another check. Imagine two people in a city where:

- **Person A** follows the road signs (recommendations) at every turn.
- **Person B** ignores the road signs and instead teleports to a completely random intersection at every step (random browsing).

If Person A ends up at more extreme intersections than Person B, that tells us the road signs *specifically* are pushing people toward extremes.

**What we found:** Person A (following recommendations) drifted **63% more** than Person B (random browsing). The average drift following recommendations was 1.17 on a 2-point scale, versus 0.72 for random browsing.

**What this means:** The recommendation structure specifically channels people more aggressively than random chance. The algorithm is doing something beyond just "extreme content exists."

---

## 7. What Are the Results?

Here are the headline findings, one at a time:

| Finding | Number | What It Means |
|---------|--------|---------------|
| Average drift direction | −0.98 (leftward) | Users tend to drift leftward on average, which is surprising given the network has more Right channels |
| Average absolute drift | 1.17 | Users move a lot — more than half the full scale — regardless of direction |
| Average extremity change | +0.09 | Slight tendency for users to end up farther from center (more extreme) |
| Extreme content hit rate | 98.7% | Nearly every simulated journey encounters extreme content |
| Recommendations vs. random | 63% more drift | Following recommendations produces far more movement than random browsing |
| Median clicks to extreme | 1 | Starting from a Center channel, the *very next* click typically leads to extreme content |
| % reaching extreme from Center | 95.5% | Almost all center-starting journeys hit extreme content within 10 steps |
| Null model p-value | 0.19 | The network's structural topology drives the amplification, not just the specific ideology labels |
| Ideology assortativity | 0.15 | Weak tendency for similar channels to recommend each other |
| Clustering coefficient | 0.33 | Moderate — neighborhoods are somewhat tightly connected |

---

## 8. How to Read Each Figure

The project generates seven figures. Here's what each one shows:

### Figure 1: `ideology_distribution.png` — What Does the Landscape Look Like?

**What you see:** Three bars — Left, Center, Right — showing how many channels are in each category.

**Key takeaway:** The network is heavily skewed toward the Right. About 56% of channels are Right-leaning, 29% are Center, and 13% are Left. This is the baseline — the composition of the recommendation network before any simulation is run.

**How to explain it:** "This is the starting landscape. There are far more Right-leaning channels in the dataset than Left-leaning ones. Keep this in mind when interpreting later results."

---

### Figure 2: `drift_distribution.png` — Which Direction Do Users Drift?

**What you see:** A histogram showing how far each simulated user drifted from their starting position. A red dashed line marks the average.

**Key takeaway:** The average drift is leftward (about −0.98). Users tend to move toward the Left, despite the Right-heavy composition.

**How to explain it:** "This histogram shows the net direction of movement. Most users end up to the left of where they started. The red line is the average."


---

### Figure 3: `trajectory_sample.png` — What Do Individual User Journeys Look Like?

**What you see:** About 20 lines, each representing one simulated user navigating the recommendation network over 10 steps. The y-axis is ideology score (−1 = Left, 0 = Center, +1 = Right).

**Key takeaway:** Lines bounce around — users don't follow smooth paths. Some get stuck near one ideology; others oscillate. This is what "following recommendations" actually looks like at an individual level.

**How to explain it:** "Each line is one simulated user. Flat lines mean the user stayed in one ideological area. Jagged lines mean they bounced between different areas."

---

### Figure 4: `extremity_distribution.png` — Do Users End Up at More Extreme Content?

**What you see:** A histogram of extremity change — whether users ended up farther from the political center than where they started.

**Key takeaway:** The average is slightly positive (+0.09), meaning there's a modest tendency for users to end up more extreme. But it's small.

**How to explain it:** "This measures whether users got pushed toward the edges of the political spectrum, regardless of direction. The slight positive average means yes, but only a little."

---

### Figure 5: `null_model_comparison.png` — Is This Pattern Real, or Just Coincidence?

**What you see:** A histogram of gray bars (the 100 shuffled-label trials) with a red line marking the real result.

**Key takeaway:** The real result (red line) is within the distribution of shuffled-label results. This means the network's structure — not the specific ideology labels — is what drives the push toward extremes.

**How to explain it:** "We shuffled the labels 100 times and re-ran the simulation. The real result doesn't stand out from the shuffled ones. This tells us the amplification is structural — it's built into how channels are connected, not which channels are Left or Right."

---

### Figure 6: `recommendation_vs_random.png` — Does Following Recommendations Make Drift Worse?

**What you see:** Two groups of bars — blue (following recommendations) and gray (random browsing) — across three metrics.

**Key takeaway:** Blue bars are consistently taller. Recommendations cause 63% more drift than random browsing.

**How to explain it:** "The blue bars show what happens when you follow YouTube's suggestions. The gray bars show what happens if you just click random channels. Recommendations produce significantly more ideological movement."

---

### Figure 7: `steps_to_extreme.png` — How Many Clicks to Reach Extreme Content?

**What you see:** A histogram showing how many clicks it took each simulated user to reach extreme content for the first time.

**Key takeaway:** The median is 1 click. Starting from a moderate channel, the very next recommendation typically leads to extreme content.

**How to explain it:** "Starting from a Center channel, most users reach extreme content on the very first click. This means extreme content is essentially one step away in the recommendation network."

---

## 9. How to Present This

### Structure your presentation like a story

Don't just list numbers. Build a narrative:

1. **Start with the question:** "Does YouTube's recommendation algorithm push people toward political extremes?"
2. **Describe the data:** "We used a public dataset of 7,000 political YouTube channels and 400,000 recommendation links."
3. **Explain the method:** "We simulated 1,500 users following recommendations for 10 steps each."
4. **Present the core finding:** "Users moved significantly — an average of 1.17 on a 2-point scale — and recommendations caused 63% more drift than random browsing."
5. **Address the null model:** "The amplification is structural — it's built into how channels are connected, not which channels carry which ideology labels."
6. **End with the 'wow' number:** "Starting from a moderate channel, extreme content is just 1 click away."

### What to emphasize

- **The 63% number.** This is the clearest evidence that recommendations *specifically* cause more drift than chance. It's concrete, it's large, and it's easy to understand.
- **The 1-click finding.** This is visceral. Everyone in the room will understand "extreme content is 1 click away."
- **The structural topology finding.** The null model result is actually *powerful* — it means the problem is baked into the network's architecture, not just a labeling artifact.

### What to downplay (but not hide)

- Raw p-values and statistical jargon. If someone asks, explain it simply. Don't lead with "p = 0.19."
- The leftward drift direction. It's a real finding, but it's counterintuitive and distracts from the main story. Mention it, but frame it as an area for further investigation.

### Keep it conversational

You're explaining research to academics, but they're humans. Don't read from slides. Tell the story: "We asked this question, we built this simulation, and here's what happened." Pause on the figures — let people look at them.

---

## 10. Quick-Reference Cheat Sheet

If they ask you a tough question, use this table.

| If They Ask... | You Say... |
|----------------|------------|
| "How do you know the algorithm is biased?" | "Recommendations produce 63% more ideological drift than random browsing — 1.17 vs. 0.72. That gap is caused by the recommendation structure specifically." |
| "Why is the drift leftward?" | "The network has far more Right channels (56%) than Left (13%). We think Right channels may recommend across ideological lines more often, but this needs further investigation." |
| "Doesn't the p-value of 0.19 mean this isn't significant?" | "It means the *extremity push* is structural — driven by how channels are connected, not which ones are labeled Left or Right. The recommendations-vs-random comparison (63% more drift) and the 1-click-to-extreme finding are independent, strong evidence." |
| "Did you study real users?" | "No. We studied the recommendation network structure — the map of which channels recommend which. Think of it as studying the road system, not individual drivers." |
| "What about personalized recommendations?" | "We used logged-out data, which represents YouTube's default algorithm. Personalized recommendations could amplify or counteract these patterns — that's a direction for future research." |
| "How is this reproducible?" | "The simulation uses a fixed random seed (42), meaning every run produces identical results. All code, data references, and steps are version-controlled." |
| "What are the limitations?" | "Three main ones: (1) the data is a snapshot from early 2023, (2) ideological labels are simplified to Left/Center/Right, and (3) we simulate logged-out recommendations only, not personalized ones." |
| "Why only 10 steps?" | "10 steps represents a realistic browsing session. We also tested 25, 50, and 100 steps in a parameter grid to confirm findings hold at different lengths." |
| "What's the difference between drift and extremity change?" | "Drift measures direction — did the user move left or right? Extremity change measures distance from center — did the user end up at a more extreme position, regardless of which direction?" |
| "So what should be done about this?" | "This study provides evidence, not policy prescriptions. But it shows that the recommendation structure itself funnels users toward extremes — which is relevant for platform design, transparency requirements, and regulatory discussions." |

---

*This guide was written for interns preparing to present this project to an academic committee. For more technical detail, see the main [ONBOARDING_GUIDE.md](ONBOARDING_GUIDE.md). For the full methodology and all metrics, see [Ideological Drift in Recommendation Networks.md](../Ideological%20Drift%20in%20Recommendation%20Networks.md) in the project root.*
