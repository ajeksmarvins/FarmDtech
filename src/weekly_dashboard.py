"""Historical weekly forecast dashboard, separate from current market advice.

The dashboard reports retrospective prediction errors from observations through
May 2024. It never presents 2024 backtests as current 2026 prices.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

BACKTEST_COLUMNS = [
    "crop_name", "state", "market", "variety", "price_type",
    "product_origin", "week_start", "price_ngn_per_kg",
    "xgboost_forecast_ngn_per_kg", "last_week_baseline_ngn_per_kg",
]


def load_historical_backtest(root: Path):
    """Prefer lightweight GitHub-deployed demo assets; accept local artifacts."""
    metrics = {}
    for path in (
        root / "data/demo/weekly_historical_metrics.json",
        root / "models/weekly_historical_metrics.json",
    ):
        if path.exists():
            metrics = json.loads(path.read_text(encoding="utf-8"))
            break
    rows = pd.DataFrame(columns=BACKTEST_COLUMNS)
    for path in (
        root / "data/demo/weekly_backtest_demo.csv",
        root / "data/processed/weekly_historical_backtest.csv",
    ):
        if path.exists():
            rows = pd.read_csv(path, parse_dates=["week_start"])
            missing = set(BACKTEST_COLUMNS) - set(rows.columns)
            if missing:
                raise ValueError(f"Backtest is missing columns: {sorted(missing)}")
            rows = rows[BACKTEST_COLUMNS]
            if not rows.empty and rows.week_start.max() > pd.Timestamp("2024-12-31"):
                raise ValueError("Unexpected later data in historical FEWS NET experiment")
            break
    return metrics, rows


def render_historical_weekly_dashboard(root: Path):
    import plotly.graph_objects as go
    import streamlit as st

    st.subheader("Historical weekly forecasting experiment")
    st.warning(
        "Research demonstration only — NOT current market prices. The source ends "
        "in 2024. The forecasts shown here target past weeks, not 2026 buying offers."
    )
    try:
        metrics, backtest = load_historical_backtest(root)
    except Exception as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    if not metrics:
        st.info(
            "Historical backtest results are not deployed yet. Run the weekly "
            "training and export scripts locally, then commit the two files "
            "generated in data/demo. The live Market advisor is unaffected."
        )
        return

    summary = []
    for crop, report in metrics.items():
        summary.append({
            "Crop": crop,
            "XGBoost WMAPE (%)": report["model"]["wmape_percent"],
            "Last-week baseline WMAPE (%)": report["last_week_baseline"]["wmape_percent"],
            "Backtest observations": report["model"]["records"],
            "First test week": report["test_first_week"],
            "Last test week": report["test_last_week"],
        })
    st.dataframe(pd.DataFrame(summary), hide_index=True, width="stretch")
    st.caption("WMAPE means weighted mean absolute percentage error; lower is "
               "better. The previous-week baseline outperformed XGBoost in "
               "the original historical evaluation.")

    if backtest.empty:
        st.info(
            "The deployment preview CSV is not present. Run the export script "
            "and commit both generated files under data/demo to enable charts."
        )
        return

    crop = st.selectbox("Historical crop", sorted(backtest.crop_name.dropna().unique()),
                        key="hist_weekly_crop")
    subset = backtest.loc[backtest.crop_name.eq(crop)].copy()
    if subset.empty:
        st.info("No historical backtest records for this crop.")
        return
    for field, label in (
        ("state", "State with historical records"),
        ("market", "Historical market"),
        ("variety", "Crop variety"),
        ("price_type", "Price type"),
        ("product_origin", "Product origin"),
    ):
        options = sorted(subset[field].dropna().unique())
        if not len(options):
            st.info("No historical records match these filters.")
            return
        chosen = st.selectbox(label, options, key="hist_weekly_" + field)
        subset = subset.loc[subset[field].eq(chosen)]
    subset = subset.sort_values("week_start")
    if subset.empty:
        st.info("No historical records match the selected series.")
        return

    report = metrics.get(crop)
    if report:
        first, second, third = st.columns(3)
        first.metric("XGBoost WMAPE", f"{report['model']['wmape_percent']:.2f}%")
        second.metric("Last-week baseline WMAPE",
                      f"{report['last_week_baseline']['wmape_percent']:.2f}%")
        third.metric("Historical observations shown", str(len(subset)))
        if report["model"]["wmape_percent"] >= report["last_week_baseline"]["wmape_percent"]:
            st.warning(
                "XGBoost did not beat the prior-week baseline on this crop's "
                "test set. Do not use these historical forecasts for selling decisions."
            )

    fig = go.Figure()
    for field, name, color in (
        ("price_ngn_per_kg", "Historical observed price", "#177245"),
        ("last_week_baseline_ngn_per_kg", "Previous-week baseline", "#7e8790"),
        ("xgboost_forecast_ngn_per_kg", "Historical XGBoost prediction", "#bd7830"),
    ):
        fig.add_trace(go.Scatter(
            x=subset.week_start, y=subset[field], name=name,
            mode="lines+markers", line={"color": color},
        ))
    fig.update_layout(
        title="One-week-ahead historical backtest",
        xaxis_title="Week in historical dataset", yaxis_title="NGN per kilogram",
        height=420, margin={"t": 55, "b": 15, "l": 15, "r": 15},
        legend={"orientation": "h", "y": -0.3},
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Comparisons use the same market, commodity variety, price type and origin. "
        "Previous actual observed weeks may inform later backtest weeks. "
        "FEWS NET data ends in 2024; there is no verified FCT price in this subset."
    )
    columns = [
        "week_start", "price_ngn_per_kg",
        "last_week_baseline_ngn_per_kg", "xgboost_forecast_ngn_per_kg",
    ]
    st.dataframe(subset[columns].sort_values("week_start", ascending=False),
                 hide_index=True, width="stretch")
    st.download_button(
        "Download selected historical backtest",
        subset[columns].to_csv(index=False),
        file_name="farmdtech_historical_weekly_backtest.csv",
        mime="text/csv",
    )
