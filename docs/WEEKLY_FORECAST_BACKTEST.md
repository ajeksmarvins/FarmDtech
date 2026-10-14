# Weekly FEWS NET forecast backtest (historical research)

This experiment supports the capstone's **one-week prediction task** using the cleaned FEWS NET dataset downloaded by your group. It is **not a current price feed**. The source ends 2024-05-15.

## Run locally

Use the project root in VS Code. The file `data/processed/fews_weekly_prices.csv` must exist (100,541 rows).

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q tests/test_weekly_forecast.py
python scripts/train_weekly_forecasts.py
```

This creates **locally**:
- `models/weekly_historical_metrics.json`: per-crop scores and dates;
- `data/processed/weekly_historical_backtest.csv`: held-out historic weekly predictions.

Neither output supplies current market quotes. Do not mix with the separate monthly World Bank data or send these results as farmer trading recommendations.

## Model integrity

- Group on state, market, crop variety, retail/wholesale, and product origin (Local/Import), never mixing them.
- Convert original timestamps into calendar weeks beginning Monday; within-week duplicates are combined by median, **not** cross-market averaging.
- Build price lag features only from precisely 1, 2, 3 and 4 calendar weeks before the target. Missing weeks are not forward-filled or counted as consecutive.
- Use 26 latest calendar weeks for a chronological holdout (rather than dataset's randomized train/test split).
- Compare XGBoost to the prior week's observed price, with MAE and WMAPE.
- The test is a one-step-ahead historical rolling-origin evaluation: later test weeks may use truly observed previous weeks, but **never future-week prices**.

## First test run (historical)

| Crop | XGBoost WMAPE | Last-week baseline WMAPE | Better |
|---|---:|---:|---|
| Maize | 7.96% | **4.54%** | Baseline |
| Beans | 15.70% | **5.81%** | Baseline |
| Rice | 14.35% | **3.99%** | Baseline |

**The baseline beats XGBoost on every crop.** We should improve data handling, feature selection and evaluation before representing the AI model as helpful for live trading.

## Scope and future work

Source coverage: 16 target-crop markets in 13 states; **no FCT market prices**. Some observations have outlier/extreme values and need source checking. For present-day recommendations, obtain newly reported market prices with independent verification. This weekly backtest is kept outside the live Streamlit market advisor until clearly labelled historical functionality is added.
