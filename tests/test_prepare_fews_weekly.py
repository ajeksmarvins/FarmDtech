"""Checks that FEWS NET weekly price data are cleaned without fabricating prices."""
import pandas as pd
import pytest
from scripts.prepare_fews_weekly import clean_weekly_prices

def sample():
    return pd.DataFrame({
        "country":["Nigeria"]*4,
        "market":["Aba"]*4, "admin_1":["Abia"]*4,
        "latitude":[5.1]*4, "longitude":[7.3]*4,
        "product":["Maize Grain (White)","Maize Grain (White)",
                   "Rice (Milled)","Cowpeas (Brown)"],
        "period_date":["2024-01-03","2024-01-10","2024-01-03","2024-01-03"],
        "price_type":["Wholesale","Wholesale","Retail","Retail"],
        "product_source":["Local"]*4,
        "unit":["100_kg","100_kg","kg","kg"],
        "currency":["NGN"]*4,
        "value":[20000,None,350.0,200.0]
    })

def test_unit_conversions_and_missing_values():
    clean, profile = clean_weekly_prices(sample())
    assert len(clean)==3 and profile["excluded_target_rows"]==1
    assert clean.loc[clean.crop.eq("Maize"),"price_ngn_per_kg"].iloc[0]==200
    assert clean.loc[clean.crop.eq("Rice"),"price_ngn_per_kg"].iloc[0]==350

def test_varieties_stay_separate():
    df=sample()
    df.loc[1,"value"]=24000
    df.loc[1,"product"]="Maize Grain (Yellow)"
    clean,_=clean_weekly_prices(df)
    assert set(clean.query("crop=='Maize'").variety)=={"Maize Grain (White)","Maize Grain (Yellow)"}

def test_conflicting_prices_raise_error():
    df=sample().iloc[[0]].copy()
    other=df.copy()
    other.loc[:,"value"]=21000
    with pytest.raises(ValueError,match="Conflicting"):
        clean_weekly_prices(pd.concat([df,other],ignore_index=True))

def test_fct_not_invented():
    clean,_=clean_weekly_prices(sample())
    assert "FCT (Abuja)" not in clean.state.unique()
    assert set(clean.price_kind)=={"reported_historical"}
