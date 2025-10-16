

from glob import glob
import os
import pandas as pd

WKD = os.path.dirname(os.path.abspath(__file__))

def test_len():
    all_files = sorted(glob(os.path.join(WKD, "..", "data", "raw", f"ticker_profiles.parquet")))
    for file in all_files:
        df = pd.read_parquet(file)
        print(len(df))

test_len()
