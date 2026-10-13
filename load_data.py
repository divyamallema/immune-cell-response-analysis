"""Initialize the SQLite database and load cell-count.csv into it.

Usage: python load_data.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
CREATE TABLE projects (
    project_id      TEXT PRIMARY KEY
);

-- Subject-level attributes are constant across all of a subject's samples.
CREATE TABLE subjects (
    subject_id      TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id),
    condition       TEXT NOT NULL,
    age             INTEGER,
    sex             TEXT CHECK (sex IN ('M', 'F')),
    treatment       TEXT NOT NULL,
    response        TEXT CHECK (response IN ('yes', 'no'))  -- NULL when not applicable
);

CREATE TABLE samples (
    sample_id                   TEXT PRIMARY KEY,
    subject_id                  TEXT NOT NULL REFERENCES subjects(subject_id),
    sample_type                 TEXT NOT NULL,
    time_from_treatment_start   INTEGER NOT NULL
);

-- Lookup table so new cell populations can be added without schema changes.
CREATE TABLE populations (
    population_id   INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE
);

-- Long format: one row per (sample, population).
CREATE TABLE cell_counts (
    sample_id       TEXT NOT NULL REFERENCES samples(sample_id),
    population_id   INTEGER NOT NULL REFERENCES populations(population_id),
    count           INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population_id)
);

CREATE INDEX idx_subjects_filter ON subjects(condition, treatment, response);
CREATE INDEX idx_samples_subject ON samples(subject_id);
CREATE INDEX idx_samples_filter ON samples(sample_type, time_from_treatment_start);
CREATE INDEX idx_cell_counts_population ON cell_counts(population_id);
"""


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    conn.executemany(
        "INSERT INTO populations (name) VALUES (?)", [(p,) for p in POPULATIONS]
    )
    pop_ids = dict(conn.execute("SELECT name, population_id FROM populations"))

    projects, subjects, samples, counts = set(), {}, [], []
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            projects.add(row["project"])
            subjects[row["subject"]] = (
                row["subject"],
                row["project"],
                row["condition"],
                int(row["age"]) if row["age"] else None,
                row["sex"] or None,
                row["treatment"],
                row["response"] or None,
            )
            samples.append(
                (
                    row["sample"],
                    row["subject"],
                    row["sample_type"],
                    int(row["time_from_treatment_start"]),
                )
            )
            counts.extend(
                (row["sample"], pop_ids[p], int(row[p])) for p in POPULATIONS
            )

    with conn:
        conn.executemany(
            "INSERT INTO projects VALUES (?)", [(p,) for p in sorted(projects)]
        )
        conn.executemany(
            "INSERT INTO subjects VALUES (?, ?, ?, ?, ?, ?, ?)", subjects.values()
        )
        conn.executemany("INSERT INTO samples VALUES (?, ?, ?, ?)", samples)
        conn.executemany("INSERT INTO cell_counts VALUES (?, ?, ?)", counts)
    conn.close()

    print(
        f"Loaded {len(projects)} projects, {len(subjects)} subjects, "
        f"{len(samples)} samples, {len(counts)} cell counts into {DB_PATH.name}"
    )


if __name__ == "__main__":
    main()
