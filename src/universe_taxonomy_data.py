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
    flag_profile_exclusions(profiles): Add per-rule exclusion flags and exclude_reason.
    filter_common_stock_universe(raw_profiles): Reduce profiles to U.S. common stocks.
    clean_profiles(): Load raw profiles, filter to common stocks, save clean Parquet.
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


def flag_profile_exclusions(profiles: pd.DataFrame) -> pd.DataFrame:
    """
    Add one boolean diagnostic column per exclusion rule, plus a combined
    exclude_reason column, without dropping any rows.

    Args:
        profiles: Raw profile DataFrame with the PROFILE_FIELDS schema.

    Returns:
        Copy of the input with the EXCLUSION_FLAGS columns and exclude_reason added.
    """
    flagged = profiles.copy()
    name = flagged["companyName"].fillna("")
    symbol = flagged["symbol"].fillna("")
    industry = flagged["industry"].fillna("")

    flagged["exclude_profile_error"] = flagged["error"].notna()
    # Missing exchange is excluded (isin -> False); missing ETF/ADR flags are kept:
    # eq(True) is False for None and the fillna covers nullable-boolean NA.
    flagged["exclude_bad_exchange"] = ~flagged["exchange"].isin(TRADED_EXCHANGES)
    flagged["exclude_etf"] = flagged["isEtf"].eq(True).fillna(False).astype(bool)
    flagged["exclude_adr"] = flagged["isAdr"].eq(True).fillna(False).astype(bool)
    flagged["exclude_shell"] = (industry.isin(INDUSTRY_EXCLUSIONS) |
                                name.str.contains(SHELL_NAME_REGEX, case=False))

    # Trust names are excluded unless FMP's industry marks the row as a REIT;
    # see TRUST_NAME_REGEX in endpoint_config for the tradeoff.
    trust_non_reit = (name.str.contains(TRUST_NAME_REGEX, case=False) &
                      ~industry.str.contains(REIT_INDUSTRY_REGEX, case=False))
    flagged["exclude_bad_name"] = name.str.contains(NAME_EXCLUSION_REGEX, case=False) | trust_non_reit
    flagged["exclude_bad_symbol"] = symbol.str.contains(SYMBOL_EXCLUSION_REGEX)

    flagged["exclude_reason"] = flagged[EXCLUSION_FLAGS].apply(
        lambda row: ",".join(flag.removeprefix("exclude_") for flag in EXCLUSION_FLAGS if row[flag]),
        axis=1)
    return flagged


def filter_common_stock_universe(raw_profiles: pd.DataFrame,
                                 return_diagnostics: bool = False
                                 ) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """
    Reduce raw FMP profiles to U.S.-listed common stocks.

    Drops profile errors, non-NYSE/NASDAQ listings, ETFs, ADRs, shell/SPAC
    vehicles, and non-common-stock instruments (preferreds, warrants, units,
    rights, debt, ETNs, funds) by company name and symbol convention, then
    dedupes multi-class listings and parses ipoDate.

    Args:
        raw_profiles: Raw profile DataFrame with the PROFILE_FIELDS schema.
        return_diagnostics: When True, also return the excluded rows with their
            per-rule exclusion flags and exclude_reason for inspection.

    Returns:
        Cleaned DataFrame, or (cleaned, excluded) when return_diagnostics is True.
    """
    flagged = flag_profile_exclusions(raw_profiles)
    excluded_mask = flagged[EXCLUSION_FLAGS].any(axis=1)

    cleaned = flagged.loc[~excluded_mask, CLEAN_PROFILE_FILEDS].copy()
    # Keep one listing per company, preferring the shortest symbol (primary class).
    cleaned["symbol_len"] = cleaned["symbol"].str.len()
    cleaned = (cleaned.sort_values("symbol_len")
               .drop_duplicates(subset=["companyName"], keep="first")
               .drop(columns=["symbol_len"]))
    cleaned["ipoDate"] = pd.to_datetime(cleaned["ipoDate"], errors="coerce")

    if return_diagnostics:
        excluded = flagged.loc[excluded_mask, CLEAN_PROFILE_FILEDS + EXCLUSION_FLAGS + ["exclude_reason"]]
        return cleaned, excluded
    return cleaned


def clean_profiles(return_diagnostics: bool = False
                   ) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and filter raw company profiles into a U.S. common-stock universe.

    Loads PROFILE_RAW, runs filter_common_stock_universe, and saves the cleaned
    dataset to PROFILE_CLEAN.

    Args:
        return_diagnostics: When True, also return the excluded rows with their
            per-rule exclusion flags and exclude_reason.

    Returns:
        Cleaned DataFrame, or (cleaned, excluded) when return_diagnostics is True.
    """
    raw_profiles = pd.read_parquet(PROFILE_RAW)
    result = filter_common_stock_universe(raw_profiles, return_diagnostics=return_diagnostics)
    cleaned = result[0] if return_diagnostics else result
    cleaned.to_parquet(PROFILE_CLEAN, index=False)
    print(f"Cleaned {len(cleaned)} profiles ({len(raw_profiles) - len(cleaned)} excluded)")
    return result
