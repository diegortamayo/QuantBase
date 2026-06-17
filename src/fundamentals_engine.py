"""
Fetch and persist per-symbol fundamental statement data.

Uses asynchronous requests against configured statement endpoints, normalizes the
returned payloads, and writes one parquet file per ticker symbol.
"""

from config.endpoint_config import (STATEMENT_ENDPOINTS, QUARTER_LIMIT, STYPES, RATE_LIMIT, LIMIT_SECONDS, REQ_PER_TICKER_FUNDAMENTALS)

from config.data_paths import fundamentals_path_ind, PROFILE_CLEAN, FUNDAMENTAL_ERRORS

from utils.url_utils import url_builder
from utils.normalize import normalize_statements

import asyncio
import aiohttp
import pandas as pd


async def fetch_one(session, symbol: str) -> list[dict]:
    """
    Fetch all configured statement types for a single symbol and save normalized data.

    Args:
        session: aiohttp client session used for HTTP requests.
        symbol: Ticker symbol to fetch.
    """

    async def _fetch(stype: str):
        """
        Fetch one configured statement endpoint for the enclosing ticker symbol.

        Args:
            stype: Statement type key from STYPES.

        Returns:
            Tuple of statement type and raw statement records, or an error record.
        """
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

    r, errors = normalize_statements(results)
    if errors:
        error_count = sum(len(records) for records in errors.values())
        print(f"Skipping {error_count} fundamental error record(s) for {symbol}: {errors}")

    r.to_parquet(fundamentals_path_ind(symbol), index=False)
    return [
        {"statementType": stype, **record}
        for stype, records in errors.items()
        for record in records
    ]


async def fetch_all(tickers: list[str]) -> None:
    """
    Fetch fundamental statements for tickers in rate-limited asynchronous batches.

    Args:
        tickers: Ticker symbols to fetch.
    """
    rate = RATE_LIMIT // REQ_PER_TICKER_FUNDAMENTALS
    all_errors = []

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tickers), rate):
            batch = tickers[i: i+rate]
            print(f"Fetching batch {i} to {i+rate}")

            tasks = [fetch_one(session, ticker) for ticker in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for symbol, result in zip(batch, results):
                if isinstance(result, Exception):
                    all_errors.append({"symbol": symbol, "statementType": None, "error": str(result)})
                else:
                    all_errors.extend(result)

            print(f"Saving batch {i} to {i+rate}")
            # await asyncio.sleep(LIMIT_SECONDS) --------------------------------------------------------

    pd.DataFrame(all_errors, columns=["symbol", "statementType", "error"]).to_csv(FUNDAMENTAL_ERRORS, index=False)


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
