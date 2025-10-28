"""
Asynchronously fetch and store OHLCV market data for all cleaned profile tickers.

Fetches daily price data from configured endpoints in rate-limited batches and saves
normalized Parquet files to MARKET_BASE.
"""

from config.endpoint_config import *
from config.data_paths import PROFILE_CLEAN, market_path_ind
from utils.url_utils import url_builder
from utils.general import normalize_ohlcv

import pandas as pd
import asyncio
import aiohttp



async def fetch(session, symbol) -> None:
    """
    Fetch and normalize OHLCV data for a single ticker asynchronously.

    Args:
        session: Active aiohttp ClientSession.
        symbol: Ticker symbol to query.

    Saves:
        Normalized parquet file to market_path_ind(symbol).
    """

    url = url_builder(DAILY_MARKET_ENDPOINT, {"symbol": symbol})
    try:
        async with session.get(url) as response:

            data = await response.json()
            if isinstance(data, list) and len(data) > 0:
                ret = data
            else:
                ret = [{"symbol": symbol, "error": "no data"}]

    except Exception as e:
        print(e)
        ret = [{"symbol": symbol, "error": str(e)}]

    ret = normalize_ohlcv(ret)

    df = pd.DataFrame(ret)
    df.to_parquet(market_path_ind(symbol), index=False)


async def fetch_all(tickers) -> None:
    """
    Fetch OHLCV data for all tickers asynchronously in rate-limited batches.

    Args:
        tickers: List of ticker symbols to query.

    Uses RATE_LIMIT and LIMIT_SECONDS for request throttling.
    """

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), RATE_LIMIT):
            batch = tickers[i:i + RATE_LIMIT]
            print(f"Fetching batch {i} to {i + RATE_LIMIT}")

            tasks = [fetch(session, ticker) for ticker in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            print(f"Saved batch {i} to {i + RATE_LIMIT}")
            await asyncio.sleep(LIMIT_SECONDS)


def market_data_engine() -> None:
    """
    Main entry point for market data ingestion.

    Loads ticker list from PROFILE_CLEAN and triggers asynchronous data fetch.
    """

    tickers = pd.read_parquet(PROFILE_CLEAN)["symbol"].tolist()

    asyncio.run(fetch_all(tickers))
