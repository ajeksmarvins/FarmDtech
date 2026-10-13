"""Validate a second independent dataset, such as verified user or NGO reports.

Input CSV columns: date,crop,market,state,latitude,longitude,price_ngn,unit_kg,source
Output: data/processed/external_prices_pending.csv (NOT merged as verified truth).
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"date", "crop", "market", "state", "latitude", "longitude", "price_ngn", "unit_kg", "source"}

def validate(file: Path) -> pd.DataFrame:
    df = pd.read_csv(file)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df.date, errors='coerce')
    df["crop"] = df.crop.astype(str).str.title().str.strip()
    df["price_ngn"] = pd.to_numeric(df.price_ngn, errors='coerce')
    df["unit_kg"] = pd.to_numeric(df.unit_kg, errors='coerce')
    df["latitude"] = pd.to_numeric(df.latitude, errors='coerce')
    df["longitude"] = pd.to_numeric(df.longitude, errors='coerce')
    df = df[df.crop.isin({"Beans", "Maize", "Rice"}) & df.price_ngn.gt(0) & df.unit_kg.gt(0)
            & df.latitude.between(4, 14.5) & df.longitude.between(2, 15)]
    df = df.dropna(subset=['date', 'market', 'state', 'source'])
    df['price_ngn_per_kg'] = df.price_ngn / df.unit_kg
    df['verified'] = False
    df['date'] = df.date.dt.strftime('%Y-%m-%d')
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', type=Path)
    args = parser.parse_args()
    validated = validate(args.csv_file)
    output = ROOT / 'data/processed/external_prices_pending.csv'
    validated.to_csv(output, index=False)
    print(f'Saved {len(validated)} UNVERIFIED records for independent review:', output)
