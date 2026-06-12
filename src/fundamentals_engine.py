from config.endpoint_config import (STATEMENT_ENDPOINTS, QUARTER_LIMIT, STYPES, RATE_LIMIT, LIMIT_SECONDS, REQ_PER_TICKER_FUNDAMENTALS)

from config.data_paths import fundamentals_path_ind, PROFILE_CLEAN

from utils.url_utils import url_builder
from utils.normalize import normalize_statements

import asyncio
import aiohttp
import pandas as pd


async def fetch_one(session, symbol: str) -> None:

    async def _fetch(stype: str):
        # limit = QUARTER_LIMIT
        limit=5  # --------------------------------------------------------------------------------------------
        statement = STATEMENT_ENDPOINTS[stype]

        url = url_builder(statement, {"symbol":symbol, "period":"quarter", "limit":limit})

        try:
            async with session.get(url) as response:
                data = await response.json()
                if isinstance(data, list) and len(data) > 0:
                    return stype, data
                else:
                    return stype, [{"symbol":symbol, "error":"no data"}]

        except Exception as e:
            print(e)
            return stype, [{"symbol":symbol, "error": str(e)}]

    results = await asyncio.gather(*[_fetch(stype) for stype in STYPES])
    results = dict(results)

    r = normalize_statements(results)
    r.to_parquet(fundamentals_path_ind(symbol), index=False)


async def fetch_all(tickers: list[str]) -> None:
    rate = RATE_LIMIT // REQ_PER_TICKER_FUNDAMENTALS
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), rate):
            batch = tickers[i: i+rate]
            print(f"Fetching batch {i} to {i+rate}")

            tasks = [fetch_one(session, ticker) for ticker in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            print(f"Saving batch {i} to {i+rate}")
            # await asyncio.sleep(LIMIT_SECONDS) --------------------------------------------------------


def fundamentals_data_engine() -> None:
    """
    Main entry point for fundamental data ingestion.

    Loads ticker list from PROFILE_CLEAN and triggers asynchronous data fetch.
    """

    # tickers = pd.read_parquet(PROFILE_CLEAN)["symbol"].tolist()--------------------------------------------
    # AAPL, PM, PYPL
    tickers = ["AAPL", "MRNA", "PYPL"]
    asyncio.run(fetch_all(tickers))


fundamentals_data_engine()