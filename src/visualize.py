import csv
import os
import statistics

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

from src.ideology import SCORE_ATTRIBUTE
from src.metrics import (
    ASSORTATIVITY_FIELD,
    CLUSTERING_FIELD,
    MEAN_ABSOLUTE_DRIFT_FIELD,
    MEAN_DRIFT_FIELD,
    MEAN_EXTREMITY_CHANGE_FIELD,
    TRAJECTORY_COUNT_FIELD,
    VALID_DRIFT_COUNT_FIELD,
    compute_walk_drift,
    compute_walk_extremity_change,
)
from src.simulator import SCORE_FIELD, STEP_FIELD


sns.set_theme(style="whitegrid")

IDEOLOGY_LABELS = ["Left (−1)", "Center (0)", "Right (+1)"]
IDEOLOGY_COLORS = ["#4472C4", "#A5A5A5", "#C0504D"]
FIGURE_SIZE = (8, 5)


def plot_ideology_distribution(G, output_path):
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

    counts = [left_count, center_count, right_count]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.bar(IDEOLOGY_LABELS, counts, color=IDEOLOGY_COLORS, edgecolor="black")

    for i, count in enumerate(counts):
        ax.text(
            i,
            count + max(counts) * 0.02 if counts else 0,
            str(count),
            ha="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_xlabel("Ideology Category", fontsize=12)
    ax.set_ylabel("Number of Channels", fontsize=12)
    ax.set_title("Ideology Distribution of Channels in the Network", fontsize=14)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_drift_distribution(trajectories, output_path):
    drifts = []
    for trajectory in trajectories:
        drift = compute_walk_drift(trajectory)
        if drift is not None:
            drifts.append(drift)

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    if drifts:
        ax.hist(drifts, bins="auto", color="#4472C4", edgecolor="black", alpha=0.7)
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
        ax.text(
            0.5,
            0.5,
            "No valid drift data available",
            ha="center",
            va="center",
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
    if len(trajectories) <= max_lines:
        sample = trajectories
    else:
        step = len(trajectories) // max_lines
        sample = trajectories[::step][:max_lines]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    for trajectory in sample:
        steps = [record[STEP_FIELD] for record in trajectory]
        scores = [record[SCORE_FIELD] for record in trajectory]
        ax.plot(steps, scores, alpha=0.5, linewidth=1.0)

    ax.axhline(-1.0, color="#4472C4", linestyle=":", alpha=0.4, label="Left (−1)")
    ax.axhline(0.0, color="#A5A5A5", linestyle=":", alpha=0.4, label="Center (0)")
    ax.axhline(1.0, color="#C0504D", linestyle=":", alpha=0.4, label="Right (+1)")

    ax.set_xlabel("Step Number", fontsize=12)
    ax.set_ylabel("Ideology Score", fontsize=12)
    ax.set_title(f"Sample of {len(sample)} Walk Trajectories", fontsize=14)
    ax.set_ylim(-1.3, 1.3)
    ax.legend(loc="upper right", fontsize=9)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_extremity_distribution(trajectories, output_path):
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
            0.5,
            0.5,
            "No valid extremity data available",
            ha="center",
            va="center",
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
        writer.writerow(columns)
        writer.writerow([metrics_dict.get(col, "N/A") for col in columns])


def generate_all_figures(G, trajectories, metrics_dict, output_dir="results"):
    figures_dir = os.path.join(output_dir, "figures")
    tables_dir = os.path.join(output_dir, "tables")
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)

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
    save_metrics_table(
        metrics_dict,
        os.path.join(tables_dir, "summary_metrics.csv"),
    )
