"""Interactive dashboard for Parts 2-4, read from the database built by the pipeline.

Usage: streamlit run dashboard.py   (or: make dashboard)
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from frequencies import COLUMNS, relative_frequencies
from response_analysis import ALPHA, compare_groups, load_frequencies, plot_boxplots, subject_level
from subset_analysis import avg_b_cells_male_responders, baseline_samples, summarize

DB_PATH = Path(__file__).resolve().parent / "cell_counts.db"

st.set_page_config(page_title="Loblaw Bio: miraclib", layout="wide")

if not DB_PATH.exists():
    st.error("cell_counts.db not found. Run `make pipeline` first.")
    st.stop()


@st.cache_data
def load():
    conn = sqlite3.connect(DB_PATH)
    freqs = pd.DataFrame(relative_frequencies(conn), columns=COLUMNS)
    cohort = load_frequencies(conn)
    baseline = baseline_samples(conn)
    avg_b = avg_b_cells_male_responders(conn)
    conn.close()
    return freqs, cohort, baseline, avg_b


freqs, cohort, baseline, avg_b = load()

st.title("Miraclib clinical trial: immune cell populations")

tab2, tab3, tab4 = st.tabs(
    ["Part 2: Relative frequencies", "Part 3: Responders vs non-responders", "Part 4: Baseline subset"]
)

with tab2:
    st.markdown("Relative frequency of each cell population as a percentage of the sample's total cell count.")
    c1, c2 = st.columns(2)
    populations = c1.multiselect("Populations", freqs.population.unique(), default=list(freqs.population.unique()))
    sample_filter = c2.text_input("Filter by sample ID (substring)")
    view = freqs[freqs.population.isin(populations)]
    if sample_filter:
        view = view[view["sample"].str.contains(sample_filter, case=False)]
    st.caption(f"{len(view):,} rows")
    st.dataframe(view.round({"percentage": 2}), hide_index=True, width="stretch")
    st.download_button("Download CSV", view.to_csv(index=False), "relative_frequencies.csv")

with tab3:
    st.markdown(
        "Melanoma patients treated with miraclib, PBMC samples only. "
        "Mann-Whitney U test per population with Benjamini-Hochberg correction across the five populations "
        f"(significant if q < {ALPHA})."
    )
    stats = compare_groups(cohort)
    subject_stats = compare_groups(subject_level(cohort))

    sig = stats.loc[stats.significant, "population"].tolist()
    if sig:
        st.success(f"Significant difference: {', '.join(sig)}")
    else:
        top = stats.sort_values("q_value").iloc[0]
        st.info(
            f"**No population differs significantly after multiple-testing correction.** "
            f"The strongest signal is {top.population} (median {top.median_responders:.2f}% in responders vs "
            f"{top.median_non_responders:.2f}% in non-responders, p = {top.p_value:.3f}, q = {top.q_value:.3f}): "
            "suggestive but not significant, and the distributions overlap heavily, so no single population "
            "is a strong predictor of response on its own."
        )

    st.pyplot(plot_boxplots(cohort, stats))

    fmt = {c: "{:.4f}" for c in ["median_responders", "median_non_responders", "median_difference", "p_value", "q_value"]}
    st.subheader("Sample-level statistics")
    st.dataframe(stats.style.format(fmt), hide_index=True, width="stretch")
    st.subheader("Subject-level statistics (mean of each subject's samples)")
    st.caption(
        "Each subject contributes up to three samples (days 0, 7, 14). Averaging per subject removes "
        "repeated-measures inflation and checks that sample-level results are robust."
    )
    st.dataframe(subject_stats.style.format(fmt), hide_index=True, width="stretch")

with tab4:
    st.markdown(
        "Melanoma PBMC samples at baseline (time_from_treatment_start = 0) from patients treated with miraclib."
    )
    summary = summarize(baseline)
    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline samples", len(baseline))
    m2.metric("Subjects", baseline.subject.nunique())
    m3.metric("Avg B cells, melanoma male responders, t=0*", f"{avg_b:.2f}")
    st.caption("*All sample types and treatments.")

    cols = st.columns(3)
    for col, (category, grp) in zip(cols, summary.groupby("category", sort=False)):
        col.subheader(category.capitalize())
        col.dataframe(grp[["group", "count"]], hide_index=True, width="stretch")

    with st.expander("Baseline samples"):
        st.dataframe(baseline, hide_index=True, width="stretch")
