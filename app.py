"""FarmDtech | Crop Price Intelligence & Advisory | Streamlit dashboard.

Start with: streamlit run app.py
The project uses real, HISTORICAL/model-estimated World Bank prices.
It does not claim to offer verified current market quotations.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from alerts import format_advice, send_to_n8n
from src.cleaning import CROPS, latest_prices
from src.recommend import rank_markets, haversine_km
from src.locations import STATE_REFERENCE_POINTS, local_net_reference
from src.weekly_dashboard import render_historical_weekly_dashboard
from src.cloud_prices import fetch_private_prices, CloudPriceError

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data/processed/prices_long.csv"
FORECASTS = ROOT / "data/processed/next_month_forecasts.csv"
METRICS = ROOT / "models/metrics.json"

st.set_page_config(page_title="FarmDtech — Ask. Receive. Decide.", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; max-width: 1250px; }
[data-testid='stMetric'] {background:#ebf5ec;padding:14px;border-radius:14px;border:1px solid #cfe3d1;}
.hero {padding:21px 25px;border-radius:18px;background:linear-gradient(110deg,#0b4b36,#337b38);color:white;margin-bottom:20px;}
.hero h1{font-size:2.2rem;color:white;margin:0 0 .25rem 0;}
.hero p{color:#e3f1e0;margin:.2rem 0 0 0;}
.note{padding:10px 14px;border-left:4px solid #9ac96f;background:#f0f6ed;color:#29412c;border-radius:6px;margin:8px 0 12px 0;}
[data-testid="stSidebar"] {background:#f1f7ef;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=1800, show_spinner="Loading market price data…")
def load_data(
    project_url: str = "",
    publishable_key: str = "",
    reader_email: str = "",
    reader_password: str = "",
) -> tuple[pd.DataFrame, str, str]:
    """Read historical prices from private Supabase or fall back to local CSV.

    A dedicated Supabase Auth account with SELECT-only RLS signs in on the
    Streamlit server. This function caches the data for 30 minutes.
    """
    failure = ""
    if all((project_url, publishable_key, reader_email, reader_password)):
        try:
            data = fetch_private_prices(
                project_url, publishable_key, reader_email, reader_password
            )
            return data, "Private Supabase reader (historical World Bank prices)", ""
        except (CloudPriceError, ValueError) as exc:
            failure = str(exc)
    elif any((project_url, publishable_key, reader_email, reader_password)):
        failure = "Private Supabase reader configuration is incomplete"
    if DATA.exists():
        data = pd.read_csv(DATA, low_memory=False, parse_dates=["date"])
        return data, "Bundled historical CSV (fallback)" if failure else "Bundled historical CSV", failure
    raise RuntimeError("No usable cloud prices and bundled CSV is missing" + (f": {failure}" if failure else ""))

@st.cache_data(show_spinner=False)
def load_forecasts() -> pd.DataFrame:
    return pd.read_csv(FORECASTS) if FORECASTS.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_metrics() -> dict:
    return json.loads(METRICS.read_text(encoding="utf-8")) if METRICS.exists() else {}


def ngn(v):
    return f"₦{float(v):,.0f}"


def config(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""

st.markdown('<div class="hero"><h1>🌱 FarmDtech</h1><p>Ask. Receive. Decide. &nbsp;|&nbsp; Crop price intelligence for Nigerian farmers</p></div>', unsafe_allow_html=True)
try:
    prices, price_source, cloud_warning = load_data(
        config("SUPABASE_URL"),
        config("SUPABASE_PUBLISHABLE_KEY"),
        config("SUPABASE_READER_EMAIL"),
        config("SUPABASE_READER_PASSWORD"),
    )
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.caption(f"Price database: {price_source}. Data are historical/model-estimated, NOT real-time offers.")
if cloud_warning:
    st.warning("Private Supabase access is unavailable or not configured. FarmDtech is using the bundled historical CSV. " + cloud_warning)
with st.sidebar:
    st.header("🧺 Farmer details")
    crop = st.selectbox("Crop", list(CROPS), index=1, help="The app uses one consistent source series for each crop.")
    kind_label = st.radio("Price evidence", ["World Bank estimated series", "Observed surveys only"], index=0,
                          help="Estimated is modelled, not a live market quote. Observed data may be much older.")
    kind = "estimated" if kind_label.startswith("World Bank") else "observed"
    pool = latest_prices(prices, crop, kind)
    # Your home state/FCT is independent of the set of markets with price data.
    home_options = sorted(STATE_REFERENCE_POINTS)
    home_state = st.selectbox("Where is your farm? (State / FCT)", home_options,
                              index=home_options.index("FCT (Abuja)"),
                              help="All 36 states and FCT are supported as origins. A state choice does not imply local prices are available.")
    origin_lat, origin_lon = STATE_REFERENCE_POINTS[home_state]
    use_exact_location = st.checkbox("Use a more precise origin (coordinates)", value=False,
                                      help="Optional: use your farm's approximate coordinates instead of the state representative point.")
    if use_exact_location:
        origin_lat = st.number_input("Latitude (°N)", min_value=4.0, max_value=14.0,
                                     value=float(origin_lat), step=0.01, format="%.4f")
        origin_lon = st.number_input("Longitude (°E)", min_value=2.0, max_value=15.0,
                                     value=float(origin_lon), step=0.01, format="%.4f")
        st.caption("Custom coordinates improve straight-line estimates but are not road distances.")
    else:
        st.caption("Using an approximate state/FCT reference point, not your farm or Abuja city centre. Select custom coordinates for better distance estimates.")
    # Selling markets still come ONLY from the real source dataset.
    markets = prices.loc[(prices.crop == crop) & (prices.price_kind == "estimated"),
                         ["market_id", "market", "state", "latitude", "longitude"]].drop_duplicates("market_id")
    markets = markets.sort_values(["state", "market"]).reset_index(drop=True)
    market_options = (markets.state + " · " + markets.market).tolist()
    quantity = st.number_input("Quantity to sell (kg)", min_value=1.0, max_value=250000.0, value=1000.0, step=50.0)
    per_km = st.number_input("Estimated transport cost (₦ per km)", min_value=0.0, value=200.0, step=25.0)
    fixed_fee = st.number_input("Market/loading fees (₦)", min_value=0.0, value=5000.0, step=500.0)
    radius = st.slider("Max straight-line distance (km)", min_value=50, max_value=1500, value=400, step=50)
    st.caption("Costs are your assumptions. Distances are straight-line estimates, **not road distances**.")
    st.divider()
    st.caption("Research prototype · Historical & model-estimated prices · Not investment or guaranteed sales advice")

panel1, panel2, panel5, panel3, panel4 = st.tabs(["📍 Market advisor", "📈 Price forecast", "🧪 Weekly research", "🗂 Data quality", "ℹ️ How it works"])

with panel1:
    st.subheader(f"Where could you sell {crop.lower()}?")
    st.markdown('<div class="note">⚠️ Prices below are historical survey values or World Bank <b>modelled estimates</b>, not verified real-time buying offers. Always confirm current buyer prices, crop grade and transportation costs.</div>', unsafe_allow_html=True)
    st.caption(f"Farm origin: {home_state}. The map uses an approximate location; only source-backed market prices are compared.")
    results = rank_markets(pool, float(origin_lat), float(origin_lon), quantity, per_km, fixed_fee, radius)
    if results.empty:
        st.warning(f"No {crop.lower()} market records of this evidence type are available within {radius} straight-line km of {home_state}. Try a wider radius or a different evidence type. This does not mean that local markets do not exist.")
    else:
        winner = results.iloc[0]
        baseline = local_net_reference(results, home_state)
        a,b,c,d = st.columns(4)
        a.metric("Best indicative market", str(winner.market))
        b.metric("Estimated price / kg", ngn(winner.price_ngn_per_kg))
        c.metric("Indicative net proceeds", ngn(winner.net_ngn))
        d.metric("Gain vs best same-state market", ngn(max(0.0, float(winner.net_ngn) - baseline)) if baseline is not None else "Unavailable")
        if baseline is None:
            st.info(f"There is no {kind} {crop.lower()} price record for a qualifying market in {home_state}. No local market price or gain comparison has been invented.")
        st.caption(f"Based on {kind} prices. Winning market: {winner.market}, {winner.state}; data month: {pd.to_datetime(winner.date).strftime('%b %Y')}. All comparisons use identical commodity and price-source type.")
        if bool(results.stale.any()):
            st.warning("One or more results are older than 65 days. Check the individual data dates before making a selling decision.")
        cols = ["market", "state", "date", "price_ngn_per_kg", "distance_km", "gross_ngn", "transport_ngn", "net_ngn", "stale"]
        view = results[cols].copy()
        view.columns = ["Market", "State", "Data month", "₦/kg", "Straight-line km", "Gross ₦", "Costs ₦", "Net ₦", "Older than 65 days"]
        st.dataframe(view, use_container_width=True, hide_index=True, column_config={
            "₦/kg": st.column_config.NumberColumn(format="₦ %.2f"),
            "Straight-line km": st.column_config.NumberColumn(format="%.1f"),
            "Gross ₦": st.column_config.NumberColumn(format="₦ %.0f"),
            "Costs ₦": st.column_config.NumberColumn(format="₦ %.0f"),
            "Net ₦": st.column_config.NumberColumn(format="₦ %.0f"),
        })
        st.download_button("⬇️ Download market comparison CSV", results.to_csv(index=False).encode("utf-8"), file_name=f"farmdtech_{crop.lower()}_markets.csv", mime="text/csv")
        with st.expander("🗺️ Show selected market locations"):
            try:
                st.map(results.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])
            except Exception:
                st.caption("Map requires an active connection; the full market table above works offline.")
        st.divider()
        st.subheader("Optional n8n advisory handoff")
        st.caption("The webhook can acknowledge the message. Actual SMS/WhatsApp delivery requires connecting a provider and testing it separately.")
        webhook = config("N8N_WEBHOOK_URL")
        if webhook:
            phone = st.text_input("Phone in international format (optional provider integration)", placeholder="+2348012345678")
            if st.button("Send recommendation to n8n", type="primary"):
                if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
                    st.error("Enter a valid phone number, such as +2348012345678")
                else:
                    payload = {"phone": phone, "crop": crop, "market": str(winner.market),
                               "price_ngn_per_kg": round(float(winner.price_ngn_per_kg),2),
                               "price_kind": kind, "data_month": pd.to_datetime(winner.date).strftime('%Y-%m'),
                               "recommendation": format_advice(crop, str(winner.market), float(winner.price_ngn_per_kg), pd.to_datetime(winner.date).strftime('%Y-%m'), kind == 'estimated')}
                    try:
                        response = send_to_n8n(payload, webhook, config("N8N_WEBHOOK_TOKEN"))
                        st.success("n8n acknowledged the advisory request. This does NOT confirm SMS delivery.")
                        st.json(response)
                    except Exception as exc:
                        st.error(f"Webhook request failed: {exc}")
        else:
            st.info("Webhook is not configured. To activate, set N8N_WEBHOOK_URL and N8N_WEBHOOK_TOKEN after importing the workflow in n8n.")

with panel2:
    st.subheader(f"{crop} — next-month price forecast")
    st.info("**Important:** The source is monthly. Forecasts are for next **month**, not next week. Model performance is measured against held-out World Bank *estimated* data, not independently observed prices.")
    forecasts = load_forecasts()
    metrics = load_metrics()
    if forecasts.empty or crop not in metrics:
        st.warning("Forecast models not found. Run `python scripts/train_models.py` and refresh the application.")
    else:
        # Select a priced market for forecasting; a farmer's home state need not
        # have a local price observation or a prediction.
        nearest_forecast_market = min(range(len(markets)), key=lambda i: haversine_km(
            float(origin_lat), float(origin_lon), float(markets.iloc[i].latitude), float(markets.iloc[i].longitude)))
        forecast_market_label = st.selectbox("Market to forecast (markets with data only)", market_options,
                                             index=nearest_forecast_market,
                                             help="This is a selling market with source data, not necessarily your home state.")
        forecast_market = markets.iloc[market_options.index(forecast_market_label)]
        if home_state == "FCT (Abuja)":
            st.caption("FCT/Abuja is available as your origin; this dataset currently has no verified FCT market price.")
        forecast = forecasts[(forecasts.crop == crop) & (forecasts.market_id == forecast_market.market_id)]
        if forecast.empty:
            st.warning("No forecast exists for this market.")
        else:
            f = forecast.iloc[0]
            c1,c2,c3 = st.columns(3)
            c1.metric("Latest modelled price / kg", ngn(f.last_price_ngn_per_kg))
            c2.metric(f"Forecast for {pd.to_datetime(f.forecast_month).strftime('%b %Y')}", ngn(f.forecast_ngn_per_kg))
            c3.metric("Projected monthly change", f"{f.change_percent:+.1f}%")
            history = prices[(prices.crop == crop) & (prices.market_id == forecast_market.market_id)].copy()
            history = history.sort_values("date")
            history = history[history.date >= history.date.max() - pd.DateOffset(months=35)]
            history["Evidence"] = history.price_kind.map({"observed": "Observed survey", "estimated": "World Bank modelled"})
            fig = px.line(history[history.price_kind == "estimated"], x="date", y="price_ngn_per_kg", markers=True,
                          title=f"Price history — {forecast_market.market}, {forecast_market.state}", labels={"date":"Month", "price_ngn_per_kg":"NGN per kg"})
            observed = history[history.price_kind == "observed"]
            if not observed.empty:
                fig.add_scatter(x=observed.date, y=observed.price_ngn_per_kg, mode="markers", name="Observed survey", marker={"symbol": "diamond", "size":9, "color":"#ed9b4d"})
            fig.add_scatter(x=[pd.to_datetime(f.forecast_month)], y=[f.forecast_ngn_per_kg], mode="markers", name="Next-month ML forecast", marker={"symbol":"star", "size":15,"color":"#b55836"})
            fig.update_layout(height=390, margin={"t": 55, "b": 15, "l": 15, "r": 15}, legend_orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        score = metrics[crop]
        a,b,c = st.columns(3)
        a.metric("XGBoost test MAE", ngn(score["model"]["mae_ngn_per_kg"]))
        b.metric("XGBoost test WMAPE", f"{score['model']['wmape_percent']:.1f}%")
        c.metric("Last-month baseline WMAPE", f"{score['naive_last_month_baseline']['wmape_percent']:.1f}%")
        st.caption(f"Chronological held-out test: {score['test_first_month']} through {score['test_last_month']}, {score['model']['n_test']} market-month records. These scores do not independently validate buyer prices.")
        if score['model']['wmape_percent'] >= score['naive_last_month_baseline']['wmape_percent']:
            st.warning("The XGBoost model did not beat the simple last-month baseline in held-out evaluation. Do not present it as more accurate.")
        st.download_button("⬇️ Download all forecasts", forecasts[forecasts.crop == crop].to_csv(index=False).encode(), file_name=f"farmdtech_{crop.lower()}_forecasts.csv", mime="text/csv")

with panel5:
    render_historical_weekly_dashboard(ROOT)

with panel3:
    st.subheader("Source transparency and data quality")
    st.write("Source: World Bank Real-Time Food Prices (RTFP), Nigeria, monthly 2007–2026. This app does not fetch live prices, and 'World Bank estimated' records are algorithmically estimated.")
    st.markdown(f"**Coverage:** {prices.market_id.nunique()} physical market identifiers in {prices.state.nunique()} state labels after removing national/geopolitical aggregates.")
    st.markdown(f"**Latest month in prepared data:** {pd.to_datetime(prices.date.max()).strftime('%B %Y')}")
    coverage = prices.groupby(["crop", "price_kind"]).agg(records=("date", "count"), markets=("market_id", "nunique"), first_month=("date", "min"), last_month=("date", "max")).reset_index()
    st.dataframe(coverage, use_container_width=True, hide_index=True)
    a,b = st.columns(2)
    with a:
        st.plotly_chart(px.bar(coverage, x="crop", y="records", color="price_kind", barmode="group", title="Available price records by evidence type"), use_container_width=True)
    with b:
        subset = prices[(prices.crop == crop) & (prices.price_kind == "observed")]
        by_state = subset.groupby("state").size().sort_values().reset_index(name="observed_records")
        st.plotly_chart(px.bar(by_state, x="observed_records", y="state", orientation="h", title=f"Observed {crop.lower()} records by state"), use_container_width=True)
    st.warning("Origin selection supports 36 states plus FCT, but PRICE COVERAGE does not. State representative coordinates are not evidence of local market prices; obtain independently verified sources for nationwide expansion.")
    st.caption("When adding external farmer or trader prices, verify source, market, units, crop grade and date before merging with official observed data.")

with panel4:
    st.subheader("How recommendations are calculated")
    st.latex(r"\text{Estimated net proceeds} = (\text{NGN/kg} \times \text{quantity kg}) - (\text{distance km}\times\text{transport NGN/km} + \text{fees})")
    st.write("The app chooses the market with the highest **indicative** net proceeds among the markets in your distance limit. It is a decision-support demo, not a firm buyer offer.")
    st.write("**Model:** XGBoost trained on 3 previous months of estimated price history, month seasonality and market coordinates. The last six months are held out chronologically for evaluation against a simple last-month baseline. For production, obtain verified weekly observed prices and validate on independent market observations.")
    st.write("**Data integrity:** The World Bank c_* fields represent estimated closing-price series; observed survey fields remain separate. Beans basket values are divided by 2.5 kg. Maize and the selected rice FAO series are already 1 kg. Aggregate zones and national averages are excluded from geographic recommendations.")
    st.write("**Origin locations:** All 36 states and FCT are selectable as approximate starting points using representative administrative coordinates from Open Admin Data Nigeria (https://openadmindata.org/ng/). Selecting a state does NOT add a crop-price observation. A farmer can optionally enter more precise coordinates for distance estimates.")
    st.write("**Limitations:** Prices may be outdated, sampled or estimated; market survey definitions may differ; real routes and transport expenses can differ from straight-line estimates; transaction prices depend on grade, moisture, volume and negotiations.")
    st.markdown("[World Bank Nigeria RTFP dataset](https://microdata.worldbank.org/catalog/4503) · [Source project](https://microdata.worldbank.org/catalog/4503/get-microdata)")
    st.caption("© FarmDtech / PYCODE Team — educational research prototype")
