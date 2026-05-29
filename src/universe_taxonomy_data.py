"""
QuantBase Universe Taxonomy and Profile Data Pipeline.

Fetches, cleans, and maps ticker, sector, and industry data from configured endpoints.
Implements asynchronous profile retrieval, batch persistence, and cleaning of company
profiles for downstream universe construction.

Functions:
    fetch_tickers(): Fetch full ticker list and save raw JSON.
    clean_tickers(): Extract ticker symbols from raw JSON and save clean list.
    get_sectors(): Retrieve list of available sectors from endpoint.
    get_industries(): Retrieve list of available industries from endpoint.
    get_industry_sectors(): Fetch both sectors and industries as tuple.
    clean_classification_map(): Build bidirectional sector-industry mapping and save.
    get_profile(session, ticker): Async fetch and normalize profile for one ticker.
    get_all_profiles(tickers): Async batch fetch of all ticker profiles with rate limits.
    save_raw_profiles(): Run full profile download, merge batches into single Parquet.
    clean_profiles(): Filter and sanitize company profiles, keeping only valid equities.
"""


from config.data_paths import *
from config.endpoint_config import *
from utils.url_utils import url_builder
from utils.normalize import normalize_profile

import requests
import json

import pandas as pd
import asyncio
import aiohttp


def fetch_tickers() -> None:
    """
    Fetch full ticker list from endpoint, save in raw JSON.
    """
    url = url_builder(ALL_SYMBOLS_ENDPOINT)
    request = requests.get(url)
    req = request.json()
    with open(TICKERS_WITH_FINANCIALS_RAW, "w") as f:
        json.dump(req, f, indent=4)


def clean_tickers() -> None:
    """
    Extract ticker list from raw JSON and save in clean JSON.
    :return:
    """
    with open(TICKERS_WITH_FINANCIALS_RAW, "r") as f:
        req = json.load(f)
        tickers = [d["symbol"] for d in req]
    with open(TICKERS_WITH_FINANCIALS_CLEAN, "w") as f:
        json.dump(tickers, f, indent=4)


def get_sectors() -> list[dict]:
    """
    Get available sectors from endpoint.
    """
    url = url_builder(AVAILABLE_SECTOR_ENDPOINT)
    response = requests.get(url)
    sectors = response.json()
    return sectors


def get_industries() -> list[dict]:
    """
    Get available industries from endpoint.
    """
    url = url_builder(AVAILABLE_INDUSTRY_ENDPOINT)
    response = requests.get(url)
    industries = response.json()
    return industries


def get_industry_sectors() -> tuple[list[dict], list[dict]]:
    """
    Get sector-industry tuple.
    """
    sectors = get_sectors()
    industries = get_industries()
    return sectors, industries


def clean_classification_map() -> None:
    """
    Creates bidirectional sector-industry, industry-sector mapping and saves to JSON.
    """
    with open(CLASSIFICATION_MAP_RAW, "r") as f:
        sector_industries = json.load(f)

    industry_sectors = {industry: sector
                        for sector, industries in sector_industries.items()
                        for industry in industries}
    bi_map = {
        "sector_to_industry": sector_industries,
        "industry_to_sectors": industry_sectors,
    }

    with open(CLASSIFICATION_MAP_CLEAN, "w") as f:
        json.dump(bi_map, f, indent=4)


async def get_profile(session, ticker) -> dict:
    """
    Fetch and normalize a single company profile asynchronously.

    Args:
        session: Active aiohttp session.
        ticker: Symbol string to query.

    Returns:
        Normalized profile dict. Contains error field if request or response fails.
    """

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


async def get_all_profiles(tickers) -> None:
    """
    Fetch all company profiles asynchronously in rate-limited batches.

    Args:
        tickers: List of symbol strings to query.

    Saves:
        Individual batch Parquet files to disk.
    """

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), RATE_LIMIT):
            batch = tickers[i:i + RATE_LIMIT]
            print(f"Fetching batch {i} to {i + RATE_LIMIT}")

            tasks = [get_profile(session, tick) for tick in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)


            individual_paths = individual_profiles(str(i))
            df = pd.DataFrame(batch_results)
            df.to_parquet(individual_paths, index=False)
            print(f"Finished batch {i} to {i + RATE_LIMIT}")

            await asyncio.sleep(LIMIT_SECONDS)


def save_raw_profiles() -> None:
    """
    Run full asynchronous profile download and merge batches into a single Parquet file.

    Reads cleaned tickers, fetches all profiles, and concatenates individual batch files
    into PROFILE_RAW for downstream cleaning.
    """

    with open(TICKERS_WITH_FINANCIALS_CLEAN, "r") as f:
        req = json.load(f)
    asyncio.run(get_all_profiles(req))
    batch_files = select_all(RAW_BASE, filename="ticker_profiles", extension=".parquet", und="_")  ######### PATH INEFFICIENCY
    print(batch_files)
    if batch_files:
        print(f"Merging {len(batch_files)} files to {PROFILE_RAW}")
        df = pd.concat([pd.read_parquet(f) for f in batch_files], ignore_index=True)
        df.to_parquet(PROFILE_RAW, index=False)


def clean_profiles() -> None:
    """
    Clean and filter raw company profiles.

    Loads PROFILE_RAW, filters invalid equities, converts and sanitizes fields, and saves the cleaned dataset in PROFILE_CLEAN.
    :return:
    """
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
    cleaned["ipoDate"] = pd.to_datetime(cleaned["ipoDate"], errors="coerce")
    cleaned.to_parquet(PROFILE_CLEAN, index=False)
    print(f"Cleaned {len(cleaned)} profiles")
