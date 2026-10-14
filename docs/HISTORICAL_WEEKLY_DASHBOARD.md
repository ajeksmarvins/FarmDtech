# Historical Weekly Forecast tab — deployment instructions

This feature is a **research demonstration**, not a present-day price source. The FEWS NET historical subset ends in May 2024. The existing World Bank Market Advisor and monthly Price Forecast tabs are unchanged.

## Step 1: Merge the dashboard feature branch

Review the pull request, merge it to main, then in VS Code (FarmDtech root):

    git pull origin main

## Step 2: Export a small set of historical backtest results

Your existing local machine already has cleaned weekly prices and ran:

    python scripts/train_weekly_forecasts.py

Now run:

    python scripts/export_weekly_dashboard.py

This produces:

- data/demo/weekly_backtest_demo.csv (roughly 380 KB; held-out historical predictions only)
- data/demo/weekly_historical_metrics.json (roughly 2 KB; historical error metrics)

The exporter verifies that all three crops have historical results and rejects non-historical dates or current-price claims. The full 100,541-record CSV stays on your local machine; it is not necessary for the dashboard.

## Step 3: Make the demo results available to deployed Streamlit

Read and review the two generated files, then in VS Code:

    git add data/demo/weekly_backtest_demo.csv data/demo/weekly_historical_metrics.json
    git commit -m "Add historical weekly backtest demonstration results"
    git push origin main

If Git returns "nothing to commit", run git status and confirm both files exist in data/demo and are not excluded.

Streamlit Community Cloud should redeploy from main. Open https://farmdtech.streamlit.app/ and choose **Weekly research**. Filter by crop, state, market, variety, retail/wholesale and product origin. The chart shows held-out 2023–2024 actual prices and retrospective predictions.

### Data caveats

- Original FEWS NET observations mirrored by Electric Sheep Africa, https://huggingface.co/datasets/electricsheepafrica/africa-fewsnet-staple-food-price-data-for-nigeria-weekly-6837 ; retain source attribution.
- The original Hugging Face split was not chronological; the code creates a calendar-based final 26-week test split.
- Scores are calculated on *historical* observed price records, not verified live quotes or farmer-gate offers.
- In the initial evaluation, the last-week baseline beats XGBoost across maize, rice and beans. This comparison must remain visible in any presentation.
- There are no new FCT market-price observations from this dataset. The FCT farmer origin selector is a separate feature.
- Historical backtests must never be joined to the 2026 market-advice dataset or sent as live SMS selling recommendations.

## Testing

    python -m pytest -q

The calendar-week timedelta compatibility warnings are resolved in the source and related tests by using explicit days. If the Weekly research tab shows an "artifacts not deployed" message, export and push both data/demo files; that state is intentionally nonfatal.
