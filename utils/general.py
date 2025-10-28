"""
Utility functions for schema normalization of profile and OHLCV data.

Ensure that all expected fields are present in each record, filling missing values with None.
"""
from config.endpoint_config import PROFILE_FIELDS, OHLCV_FIELDS


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
