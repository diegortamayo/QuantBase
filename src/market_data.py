from config.endpoint_config import *
from utils.url_utils import url_builder
from utils.general import normalize_ohlcv

import os

import pandas as pd
import asyncio
import aiohttp


WKD = os.path.dirname(os.path.abspath(__file__))
MARKET_DATA_DIR = os.path.join(WKD, "..", "data", "market")
TICKERS = os.path.join(WKD, "..", "data", "clean", "ticker_profiles.parquet")


async def fetch(session, symbol):
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
    df.to_parquet(os.path.join(MARKET_DATA_DIR, f"{symbol}.parquet"), index=False)


async def fetch_all(tickers):
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), RATE_LIMIT):
            batch = tickers[i:i + RATE_LIMIT]
            print(f"Fetching batch {i} to {i + RATE_LIMIT}")

            tasks = [fetch(session, ticker) for ticker in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            print(f"Saved batch {i} to {i + RATE_LIMIT}")
            await asyncio.sleep(LIMIT_SECONDS)


def market_data_engine():
    tickers = pd.read_parquet(TICKERS)["symbol"].tolist()

    asyncio.run(fetch_all(tickers))

market_data_engine()
