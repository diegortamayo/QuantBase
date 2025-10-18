from config.endpoint_config import *
from utils.url_utils import url_builder
from utils.general import normalize_profile

import requests
import json
import os
from glob import glob

import pandas as pd
import asyncio
import aiohttp


WKD = os.path.dirname(os.path.abspath(__file__))
TWFRAW_PATH = os.path.join(WKD, "..", "data", "raw", "tickers.json")
PROFILE_RAW = os.path.join(WKD, "..", "data", "raw", "ticker_profiles.parquet")
TWFCLEAN_PATH = os.path.join(WKD, "..", "data", "clean", "tickers.json")


def fetch_tickers():
    url = url_builder(ALL_SYMBOLS_ENDPOINT)
    request = requests.get(url)
    req = request.json()
    with open(TWFRAW_PATH, "w") as f:
        json.dump(req, f, indent=4)


def clean_tickers():
    with open(TWFRAW_PATH, "r") as f:
        req = json.load(f)
        tickers = [d["symbol"] for d in req]
    with open(TWFCLEAN_PATH, "w") as f:
        json.dump(tickers, f, indent=4)


def get_sectors():
    url = url_builder(AVAILABLE_SECTOR_ENDPOINT)
    response = requests.get(url)
    sectors = response.json()
    return sectors


def get_industries():
    url = url_builder(AVAILABLE_INDUSTRY_ENDPOINT)
    response = requests.get(url)
    industries = response.json()
    return industries


def get_industry_sectors():
    sectors = get_sectors()
    industries = get_industries()
    return sectors, industries


def clean_classification_map():
    file = os.path.join(WKD, "..", "data", "raw", "classification_map.json")
    with open(file, "r") as f:
        sector_industries = json.load(f)

    industry_sectors = {industry: sector
                        for sector, industries in sector_industries.items()
                        for industry in industries}
    bi_map = {
        "sector_to_industry": sector_industries,
        "industry_to_sectors": industry_sectors,
    }

    file_clean = os.path.join(WKD, "..", "data", "clean", "classification_map.json")
    with open(file_clean, "w") as f:
        json.dump(bi_map, f, indent=4)

clean_classification_map()


async def get_profile(session, ticker):
    url = url_builder(PROFILE_ENDPOINT, {"symbol": ticker})
    try:
        async with session.get(url) as response:
            try:
                data = await response.json()
            except Exception as e:
                print(e)
                return normalize_profile({"symbol": ticker, "error": str(e)})
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    profile = data[0]
                else:
                    profile = {"symbol": ticker, "error": "empty_or_invalid_response"}
            else:
                profile = {"symbol": ticker, "error": "empty_or_invalid_response"}
    except Exception as e:
        print(e)
        profile = {"symbol": ticker, "error": str(e)}

    return normalize_profile(profile)


async def get_all_profiles(tickers):
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), RATE_LIMIT):
            batch = tickers[i:i + RATE_LIMIT]
            print(f"Fetching batch {i} to {i + RATE_LIMIT}")

            tasks = [get_profile(session, tick) for tick in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)


            individual_paths = os.path.join(WKD, "..", "data", "raw", f"ticker_profiles_{i}.parquet")
            df = pd.DataFrame(batch_results)
            df.to_parquet(individual_paths, index=False)
            print(f"Finished batch {i} to {i + RATE_LIMIT}")

            await asyncio.sleep(LIMIT_SECONDS)


def save_raw_profiles():
    with open(TWFCLEAN_PATH, "r") as f:
        req = json.load(f)
    asyncio.run(get_all_profiles(req))
    batch_files = sorted(glob(os.path.join(WKD, "..", "data", "raw", "ticker_profiles_*.parquet")))
    print(batch_files)
    if batch_files:
        print(f"Merging {len(batch_files)} files to {PROFILE_RAW}")
        df = pd.concat([pd.read_parquet(f) for f in batch_files], ignore_index=True)
        df.to_parquet(PROFILE_RAW, index=False)


def clean_profiles():
    raw_profiles = pd.read_parquet(PROFILE_RAW)
    cleaned = (raw_profiles.loc[raw_profiles["error"].isna() &
                               (raw_profiles["isActivelyTrading"] == ACTIVE_TRADING_FLAG) &
                               (raw_profiles["isEtf"] == False) &
                               (raw_profiles["isAdr"] == False) &
                               (raw_profiles["exchange"].isin(TRADED_EXCHANGES)) &
                               (~raw_profiles["industry"].isin(INDUSTRY_EXLCUSIONS)) &
                               (raw_profiles["averageVolume"] > 10_000) &
                                (~raw_profiles["companyName"].str.contains("|".join(EXCLUSION_TERMS), case=False, na=False)) &
                                (~raw_profiles["symbol"].str.contains("-", na=False)) &
                                (~raw_profiles["companyName"].str.contains("%", na=False)) &
                                (~raw_profiles["companyName"].str.contains(r"\d.\d", na=False)) &
                                 (raw_profiles["marketCap"] > 0),
                                CLEAN_PROFILE_FILEDS])
    cleaned["symbol_len"] = cleaned["symbol"].str.len()
    cleaned = cleaned.sort_values("symbol_len").drop_duplicates(subset=["companyName"], keep="first").drop(columns=["symbol_len"])
    profile_clean = os.path.join(WKD, "..", "data", "clean", "ticker_profiles.parquet")
    cleaned.to_parquet(profile_clean, index=False)
    print(f"Cleaned {len(cleaned)} profiles")
