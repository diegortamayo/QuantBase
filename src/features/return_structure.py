from config.features_config import *
import numpy as np


def return_structure_features(df):
    def draw(x, per):
        return x / x.rolling(per, min_periods=1)
    def max_draw(x):
        return (x / x.cummax() - 1).min()

    df["ret_1d"] = df["close"].pct_change()
    df["log_r_1d"] = np.log(1 + df["dailyReturn"])
    for period in MULTI_HORIZONS:
        df[f"ret_{period}d"] = df["close"].pct_change(period)
        df[f"cum_ret_{period}d"] = (1 + df[f"ret_1d"]).rolling(period).apply(np.prod, raw=True)
        df[f"log_r_{period}d"] = df["log_r_1d"].rolling(period).sum()
        df[f"distance_high_{period}d"] = draw(df["close"], period).max() - 1
        df[f"distance_low_{period}d"] = draw(df["close"], period).min() - 1
        df[f"max_dd_{period}d"] = df["close"].rolling(period, min_periods=1).apply(max_draw, raw=True)
        df[f"hit_ratio_{period}d"] = df["ret_1d"].rolling(period, min_periods=1).apply(lambda x: (x>0).mean(), raw=True)
        if period != 5:
            df[f"skew_{period}d"] = df["ret_1d"].rolling(period).skew()
            df[f"kurt_{period}d"] = df["ret_1d"].rolling(period).kurt()
            df[f"autocorr_{period}d"] = df["ret_1d"].rolling(period).apply(lambda x: x.autocorr(lag=1))

    return df
