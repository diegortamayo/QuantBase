"""
Tests for the common-stock universe filter in src.universe_taxonomy_data.

Runs under pytest, or standalone with the project venv:
    .venv/bin/python tests/test_universe_cleaning.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pandas as pd

from src.universe_taxonomy_data import (
    EXCLUSION_FLAGS,
    filter_common_stock_universe,
    flag_profile_exclusions,
)


def make_profile(symbol, company_name, exchange="NYSE", industry="Banks - Diversified",
                 error=None, is_etf=False, is_adr=False):
    return {
        "symbol": symbol,
        "companyName": company_name,
        "exchange": exchange,
        "industry": industry,
        "error": error,
        "isEtf": is_etf,
        "isAdr": is_adr,
        "cik": "0000000000",
        "isin": "US0000000000",
        "sector": "Financial Services",
        "country": "US",
        "ipoDate": "2000-01-01",
        "marketCap": 1_000_000_000,
        "price": 10.0,
        "averageVolume": 100_000,
    }


KEEP_PROFILES = [
    make_profile("AAPL", "Apple Inc.", exchange="NASDAQ", industry="Consumer Electronics"),
    # Hyphenated share classes must survive (the old blanket hyphen rule dropped them).
    make_profile("BRK-B", "Berkshire Hathaway Inc.", industry="Insurance - Diversified"),
    make_profile("BF-B", "Brown-Forman Corporation", industry="Beverages - Wineries & Distilleries"),
    # REIT with "Trust" in the name is exempt from the trust exclusion.
    make_profile("CPT", "Camden Property Trust", industry="REIT - Residential"),
    # Missing ETF/ADR flags must not drop the row.
    make_profile("NULLF", "Nullflag Industries Inc.", exchange="NASDAQ",
                 industry="Software - Application", is_etf=None, is_adr=None),
]

# symbol -> exclusion reasons that must all be flagged for that row.
EXCLUDE_PROFILES = {
    "ERR1": (make_profile("ERR1", None, exchange=None, industry=None, error="timeout"),
             ["profile_error"]),
    "OTCX": (make_profile("OTCX", "Overthecounter Inc.", exchange="OTC"), ["bad_exchange"]),
    "AMXX": (make_profile("AMXX", "Amexlisted Inc.", exchange="AMEX"), ["bad_exchange"]),
    "SPY": (make_profile("SPY", "SPDR S&P 500 ETF Trust", exchange="AMEX", is_etf=True),
            ["etf"]),
    "BABA": (make_profile("BABA", "Alibaba Group Holding Limited", is_adr=True), ["adr"]),
    "SHEL1": (make_profile("SHEL1", "Empty Vehicle Inc.", industry="Shell Companies"),
              ["shell"]),
    "AJAX": (make_profile("AJAX", "Ajax Capital Acquisition Corp.", exchange="NASDAQ"),
             ["shell"]),
    "PACHU": (make_profile("PACHU", "Pioneer Acquisition I Corp Units", exchange="NASDAQ"),
              ["shell", "bad_name", "bad_symbol"]),
    "BAC-PB": (make_profile("BAC-PB", "Bank of America Corporation Preferred Series GG"),
               ["bad_name", "bad_symbol"]),
    # Real case: warrant whose company name carries no warrant language at all.
    "BSLKW": (make_profile("BSLKW", "Bolt Projects Holdings, Inc.", exchange="NASDAQ",
                           industry="Specialty Chemicals"), ["bad_symbol"]),
    "ASPCR": (make_profile("ASPCR", "A SPAC III Acquisition Corp.", exchange="NASDAQ"),
              ["shell", "bad_symbol"]),
    "ABC-WT": (make_profile("ABC-WT", "Alphabet Soup Holdings Warrant"),
               ["bad_name", "bad_symbol"]),
    "DEF-UN": (make_profile("DEF-UN", "Defiant Holdings Inc."), ["bad_symbol"]),
    "GHI-RI": (make_profile("GHI-RI", "Ghiro Industries Right"), ["bad_name", "bad_symbol"]),
    "XYZN": (make_profile("XYZN", "XYZ Inc. 5.25% Senior Notes due 2027"), ["bad_name"]),
    "EVF": (make_profile("EVF", "Eaton Vance Closed-End Income Fund",
                         industry="Asset Management"), ["bad_name"]),
    "PBT": (make_profile("PBT", "Permian Basin Royalty Trust",
                         industry="Oil & Gas Midstream"), ["bad_name"]),
    "VXX": (make_profile("VXX", "iPath Series B S&P 500 VIX ETN",
                         industry="Asset Management"), ["bad_name"]),
    "DLR-PJ": (make_profile("DLR-PJ", "Digital Realty Trust Depositary Shares",
                            industry="REIT - Specialty"), ["bad_name", "bad_symbol"]),
}


def build_fixture() -> pd.DataFrame:
    rows = KEEP_PROFILES + [profile for profile, _ in EXCLUDE_PROFILES.values()]
    return pd.DataFrame(rows)


def test_keeps_valid_common_stock():
    cleaned = filter_common_stock_universe(build_fixture())
    kept = set(cleaned["symbol"])
    expected = {p["symbol"] for p in KEEP_PROFILES}
    assert kept == expected, f"kept {kept}, expected {expected}"


def test_excludes_each_category_with_reason():
    _, excluded = filter_common_stock_universe(build_fixture(), return_diagnostics=True)
    excluded = excluded.set_index("symbol")
    for symbol, (_, reasons) in EXCLUDE_PROFILES.items():
        assert symbol in excluded.index, f"{symbol} was not excluded"
        row_reasons = excluded.loc[symbol, "exclude_reason"].split(",")
        for reason in reasons:
            assert reason in row_reasons, f"{symbol}: expected {reason} in {row_reasons}"


def test_hyphenated_share_classes_survive():
    cleaned = filter_common_stock_universe(build_fixture())
    assert {"BRK-B", "BF-B"} <= set(cleaned["symbol"])


def test_null_etf_adr_flags_are_kept():
    flagged = flag_profile_exclusions(build_fixture())
    row = flagged.loc[flagged["symbol"] == "NULLF"].iloc[0]
    assert not row["exclude_etf"]
    assert not row["exclude_adr"]
    assert row["exclude_reason"] == ""


def test_reit_trust_kept_but_royalty_trust_dropped():
    flagged = flag_profile_exclusions(build_fixture())
    reit = flagged.loc[flagged["symbol"] == "CPT"].iloc[0]
    royalty = flagged.loc[flagged["symbol"] == "PBT"].iloc[0]
    assert not reit["exclude_bad_name"]
    assert royalty["exclude_bad_name"]


def test_return_diagnostics_shapes():
    fixture = build_fixture()
    cleaned_only = filter_common_stock_universe(fixture)
    assert isinstance(cleaned_only, pd.DataFrame)

    cleaned, excluded = filter_common_stock_universe(fixture, return_diagnostics=True)
    assert len(cleaned) + len(excluded) == len(fixture)
    for flag in EXCLUSION_FLAGS:
        assert flag in excluded.columns
    assert (excluded["exclude_reason"] != "").all()


if __name__ == "__main__":
    import traceback

    failures = 0
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
