"""Part 3: compare population relative frequencies between responders and
non-responders among melanoma patients treated with miraclib (PBMC samples only).

Usage: python response_analysis.py
Writes outputs/response_boxplots.png and outputs/response_stats.csv.
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import false_discovery_control, mannwhitneyu

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
OUT_DIR = ROOT / "outputs"

ALPHA = 0.05

QUERY = """
SELECT
    s.sample_id                                                 AS sample,
    sub.subject_id                                              AS subject,
    sub.response                                                AS response,
    p.name                                                      AS population,
    100.0 * c.count / SUM(c.count) OVER (PARTITION BY c.sample_id) AS percentage
FROM cell_counts c
JOIN populations p USING (population_id)
JOIN samples s USING (sample_id)
JOIN subjects sub USING (subject_id)
WHERE sub.condition = 'melanoma'
  AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND sub.response IS NOT NULL
ORDER BY p.population_id, s.sample_id
"""


def load_frequencies(conn):
    """Per-sample relative frequencies for the Part 3 cohort."""
    return pd.read_sql_query(QUERY, conn)


def compare_groups(df):
    """Mann-Whitney U test per population, responders vs non-responders,
    with Benjamini-Hochberg correction across populations."""
    rows = []
    for population, grp in df.groupby("population", sort=False):
        yes = grp.loc[grp.response == "yes", "percentage"]
        no = grp.loc[grp.response == "no", "percentage"]
        stat, p = mannwhitneyu(yes, no, alternative="two-sided")
        rows.append(
            {
                "population": population,
                "n_responders": len(yes),
                "n_non_responders": len(no),
                "median_responders": yes.median(),
                "median_non_responders": no.median(),
                "median_difference": yes.median() - no.median(),
                "u_statistic": stat,
                "p_value": p,
            }
        )
    stats = pd.DataFrame(rows)
    stats["q_value"] = false_discovery_control(stats.p_value, method="bh")
    stats["significant"] = stats.q_value < ALPHA
    return stats


def subject_level(df):
    """Average each subject's samples so every subject counts once, avoiding
    repeated measures from the same patient inflating significance."""
    return df.groupby(["subject", "response", "population"], sort=False, as_index=False)[
        "percentage"
    ].mean()


def plot_boxplots(df, stats):
    populations = list(stats.population)
    fig, axes = plt.subplots(1, len(populations), figsize=(4 * len(populations), 5))
    for ax, population in zip(axes, populations):
        grp = df[df.population == population]
        data = [grp.loc[grp.response == r, "percentage"] for r in ("yes", "no")]
        ax.boxplot(data, tick_labels=["Responder", "Non-responder"], widths=0.6)
        q = stats.set_index("population").at[population, "q_value"]
        ax.set_title(f"{population}\nq = {q:.3g}{' *' if q < ALPHA else ''}")
        ax.set_ylabel("Relative frequency (%)")
    fig.suptitle("Melanoma, miraclib, PBMC: responders vs non-responders")
    fig.tight_layout()
    return fig


def main():
    conn = sqlite3.connect(DB_PATH)
    df = load_frequencies(conn)
    conn.close()

    stats = compare_groups(df)
    subject_stats = compare_groups(subject_level(df))

    OUT_DIR.mkdir(exist_ok=True)
    stats.to_csv(OUT_DIR / "response_stats.csv", index=False)
    subject_stats.to_csv(OUT_DIR / "response_stats_by_subject.csv", index=False)
    fig = plot_boxplots(df, stats)
    fig.savefig(OUT_DIR / "response_boxplots.png", dpi=150)
    plt.close(fig)

    cols = ["population", "median_responders", "median_non_responders", "p_value", "q_value", "significant"]
    with pd.option_context("display.width", 200, "display.precision", 4):
        print("Sample-level (Mann-Whitney U, BH-corrected):")
        print(stats[cols].to_string(index=False))
        print("\nSubject-level (mean per subject):")
        print(subject_stats[cols].to_string(index=False))


if __name__ == "__main__":
    main()
