# Immune cell response analysis

Loads immune cell counts from a clinical trial (`cell-count.csv`) into a SQLite database, then:

- calculates each cell population's relative frequency per sample,
- compares responders and non-responders to the drug miraclib, with boxplots and statistical tests,
- summarizes the baseline melanoma samples from miraclib-treated patients,

and shows the results in an interactive Streamlit dashboard.

## Running the code

In GitHub Codespaces, from the repository root:

```bash
make setup      # install dependencies
make pipeline   # build cell_counts.db and write results to outputs/
make dashboard  # start the dashboard
```

## Dashboard

http://localhost:8501 (after `make dashboard`; in Codespaces, open port 8501 from the **Ports** tab).
