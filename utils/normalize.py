"""
Utility functions for schema normalization of profile and OHLCV data.

Ensure that all expected fields are present in each record, filling missing values with None.
"""
import pandas as pd

from config.endpoint_config import PROFILE_FIELDS, OHLCV_FIELDS, HEADER_KEYS


def normalize_profile(p: dict) -> dict:
    """
    Normalize a single company profile dictionary to the configured PROFILE_FIELDS schema.

    Args:
        p: Raw profile dictionary.

    Returns:
        Normalized profile with missing fields filled as None.
    """
    return {field: p.get(field, None) for field in PROFILE_FIELDS}


def normalize_ohlcv(ohlcv: list) -> list:
    """
    Normalize a list of OHLCV dictionaries to the configured OHLCV_FIELDS schema.

    Args:
        ohlcv: List of raw OHLCV records.

    Returns:
        List of normalized OHLCV dictionaries with consistent field structure.
    """
    def _normalize(ohlcv_dict: dict) -> dict:
        return {field: ohlcv_dict.get(field, None) for field in OHLCV_FIELDS}
    return [_normalize(ohlcv_dict) for ohlcv_dict in ohlcv]


def normalize_statements(statements: dict[str, list[dict]]) -> pd.DataFrame:
    dfs = {stype: pd.DataFrame(records) for stype, records in statements.items()}
    stypes = list(dfs.keys())

    merged = dfs[stypes[0]]

    for stype in stypes[1:]:
        df = dfs[stype]
        existing_header = [k for k in HEADER_KEYS if k in df.columns]
        non_header = [c for c in df.columns if c not in HEADER_KEYS]

        merged = merged.merge(df[existing_header + non_header], on=existing_header, how="outer")
        
    return merged