from config.endpoint_config import *
from config.data_paths import PROFILE_CLEAN, market_path_ind
from utils.url_utils import url_builder
from utils.general import normalize_ohlcv

import pandas as pd
import asyncio
import aiohttp



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
    df.to_parquet(market_path_ind(symbol), index=False)


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
    tickers = pd.read_parquet(PROFILE_CLEAN)["symbol"].tolist()

    asyncio.run(fetch_all(tickers))
