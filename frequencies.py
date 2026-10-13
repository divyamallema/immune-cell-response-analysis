"""Part 2: relative frequency of each cell population in each sample.

Usage: python frequencies.py
Writes outputs/relative_frequencies.csv.
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
OUT_PATH = ROOT / "outputs" / "relative_frequencies.csv"

COLUMNS = ["sample", "total_count", "population", "count", "percentage"]

QUERY = """
SELECT
    c.sample_id                                         AS sample,
    SUM(c.count) OVER (PARTITION BY c.sample_id)        AS total_count,
    p.name                                              AS population,
    c.count                                             AS count,
    100.0 * c.count / SUM(c.count) OVER (PARTITION BY c.sample_id) AS percentage
FROM cell_counts c
JOIN populations p USING (population_id)
ORDER BY c.sample_id, p.population_id
"""


def relative_frequencies(conn):
    """Return rows of (sample, total_count, population, count, percentage)."""
    return conn.execute(QUERY).fetchall()


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = relative_frequencies(conn)
    conn.close()

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(r[:4] + (round(r[4], 2),) for r in rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
