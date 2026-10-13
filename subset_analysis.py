"""Part 4: baseline subset of melanoma PBMC samples from miraclib-treated patients.

Usage: python subset_analysis.py
Writes outputs/baseline_samples.csv and outputs/baseline_summary.csv.
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
OUT_DIR = ROOT / "outputs"

BASELINE_QUERY = """
SELECT
    s.sample_id     AS sample,
    sub.subject_id  AS subject,
    sub.project_id  AS project,
    sub.response    AS response,
    sub.sex         AS sex
FROM samples s
JOIN subjects sub USING (subject_id)
WHERE sub.condition = 'melanoma'
  AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND s.time_from_treatment_start = 0
ORDER BY s.sample_id
"""

# Melanoma males, any sample type and treatment, responders at time 0.
B_CELL_QUERY = """
SELECT AVG(c.count)
FROM cell_counts c
JOIN populations p USING (population_id)
JOIN samples s USING (sample_id)
JOIN subjects sub USING (subject_id)
WHERE p.name = 'b_cell'
  AND sub.condition = 'melanoma'
  AND sub.sex = 'M'
  AND sub.response = 'yes'
  AND s.time_from_treatment_start = 0
"""


def baseline_samples(conn):
    """Melanoma PBMC samples at baseline from miraclib-treated patients."""
    return pd.read_sql_query(BASELINE_QUERY, conn)


def summarize(df):
    """Samples per project, and responders/non-responders and males/females
    counted by distinct subject."""
    subjects = df.drop_duplicates("subject")
    parts = [
        ("samples per project", df.project.value_counts()),
        ("subjects by response", subjects.response.map({"yes": "responder", "no": "non-responder"}).value_counts()),
        ("subjects by sex", subjects.sex.map({"M": "male", "F": "female"}).value_counts()),
    ]
    return pd.concat(
        [s.sort_index().rename_axis("group").reset_index(name="count").assign(category=c) for c, s in parts]
    )[["category", "group", "count"]]


def avg_b_cells_male_responders(conn):
    return conn.execute(B_CELL_QUERY).fetchone()[0]


def main():
    conn = sqlite3.connect(DB_PATH)
    df = baseline_samples(conn)
    avg_b = avg_b_cells_male_responders(conn)
    conn.close()

    summary = summarize(df)

    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "baseline_samples.csv", index=False)
    summary.to_csv(OUT_DIR / "baseline_summary.csv", index=False)

    print(f"{len(df)} baseline melanoma PBMC samples from miraclib-treated patients\n")
    print(summary.to_string(index=False))
    print(f"\nAverage B cells, melanoma male responders at time 0: {avg_b:.2f}")


if __name__ == "__main__":
    main()
