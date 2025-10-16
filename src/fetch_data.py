from config.endpoint_config import *
from utils.url_utils import url_builder

import requests
import json
import os
from glob import glob

import pandas as pd
import asyncio
import aiohttp


WKD = os.path.dirname(os.path.abspath(__file__))
TWFRAW_PATH = os.path.join(WKD, "..", "data", "raw", "tickers_with_financials.json")
PROFILE_RAW = os.path.join(WKD, "..", "data", "raw", "ticker_profiles.parquet")
TWFCLEAN_PATH = os.path.join(WKD, "..", "data", "clean", "tickers_with_financials.json")


def normalize_profile(p):
    return {field: p.get(field, None) for field in PROFILE_FIELDS}


def fetch_tickers_with_financials():
    url = url_builder(FIN_STATEMENT_SYMBOLS_ENDPOINT)
    request = requests.get(url)
    req = request.json()
    with open(TWFRAW_PATH, "w") as f:
        json.dump(req, f, indent=4)


def clean_tickers_with_financials():
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

            await asyncio.sleep(60)


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


# save_raw_profiles()
