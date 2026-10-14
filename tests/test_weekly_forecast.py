"""Check calendar-week lag correctness and backtest integrity."""
import pandas as pd
import pytest
from src.weekly_forecast import weekly_prices, make_weekly_features, split_chronologically, _metrics


def sample():
    dates = pd.date_range("2024-01-01", periods=8, freq="7D")
    return pd.DataFrame({
        "date":dates.astype(str), "state":"Kaduna", "market":"Saminaka",
        "crop":"Maize", "variety":"Maize Grain (White)",
        "price_type":"Wholesale", "product_origin":"Local",
        "latitude":10.3, "longitude":8.5, "price_kind":"reported_historical",
        "price_ngn_per_kg":range(100,108)
    })


def test_exact_weekly_lags_no_future_leakage():
    f=make_weekly_features(weekly_prices(sample()))
    assert len(f)==4
    assert f.iloc[0].price_ngn_per_kg==104
    assert [f.iloc[0][f"lag{i}"] for i in range(1,5)]==[103,102,101,100]


def test_gap_not_treated_as_consecutive_week():
    d=sample().drop(index=3)
    f=make_weekly_features(weekly_prices(d))
    assert not ((f.week_start==pd.Timestamp("2024-01-29")).any())


def test_price_types_do_not_mix():
    d=sample()
    d.loc[d.index[4]:, "price_type"]="Retail"
    assert make_weekly_features(weekly_prices(d)).empty


def test_chronological_split():
    d=pd.concat([sample().assign(date=(pd.to_datetime(sample().date) + pd.Timedelta(weeks=k)).astype(str)) for k in range(132)], ignore_index=True)
    d=d.drop_duplicates("date", keep="first")
    features=make_weekly_features(weekly_prices(d))
    train,test=split_chronologically(features,test_weeks=35)
    assert train.week_start.max()<test.week_start.min()
    assert len(test)>0


def test_report_baseline():
    assert _metrics([100,200],[100,200])["wmape_percent"] == 0


def test_reject_unapproved_estimated_source():
    d=sample();d["price_kind"]="estimated"
    assert weekly_prices(d).empty
