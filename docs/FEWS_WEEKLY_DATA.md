# FEWS NET weekly historical data — FarmDtech

Source: [Electric Sheep Africa mirror of FEWS NET Nigerian weekly prices](https://huggingface.co/datasets/electricsheepafrica/africa-fewsnet-staple-food-price-data-for-nigeria-weekly-6837).

## Actual inspected dataset
- Two Parquet files together: **305,288** rows covering 2003-10-29 to 2024-05-15.
- Target crops: maize white/yellow, rice milled/5% broken, beans = cowpeas white/brown.
- Target crop rows: **122,552**; missing price fields excluded: **22,011**.
- Usable price rows: **100,541**, 16 source-priced markets in 13 states. **No FCT target-crop market quotes**.
- Prices in kg/50_kg/100_kg normalized to NGN/kg. Retail and wholesale stay separate, as do crop varieties and origin (Local/Import).
- Some extreme observed prices require outlier review before model training.

## Rebuild the cleaned file
1. Download BOTH Parquet files from the source and put them unchanged in `data/raw/fews_weekly/`.
2. Ensure pyarrow is installed: `python -m pip install pyarrow`.
3. Run `python scripts/prepare_fews_weekly.py`.
4. Outputs: `data/processed/fews_weekly_prices.csv` and `data/processed/fews_weekly_profile.json`.

The prepared CSV should **not** be mixed into `data/processed/prices_long.csv` (World Bank monthly estimated prices). App market advice must not label 2024 records as current.

## Later forecasting
Rebuild chronological training/test splits instead of Hugging Face's randomized train/test labels. Use only earlier observed dates for lag features, respect market + variety + retail/wholesale + product origin, evaluate on a later held-out period, and compare weekly predictions with a last-week-price baseline. Source independent current market observations before serving real-time sale recommendations.

## Data rights
Credit original FEWS NET observations and the mirror; review source terms and attribution before redistributing the original data.
