"""
Utility functions for schema normalization of profile, OHLCV, and statement data.

Ensure that all expected fields are present in each record, filling missing values with None.
"""
import pandas as pd

from config.endpoint_config import PROFILE_FIELDS, OHLCV_FIELDS, HEADER_KEYS, STATEMENT_SUFFIXES


def normalize_profile(p: dict) -> dict:
    """
    Normalize a single company profile dictionary to the configured PROFILE_FIELDS schema.

    Args:
        p: Raw profile dictionary.

    Returns:
        Normalized profile with missing fields filled as None.
    """
    return {field: p.get(field, None) for field in PROFILE_FIELDS}


def _is_error_record(record: dict) -> bool:
    """Return True when an API payload record represents a fetch or data error."""
    return bool(record.get("error"))


def _split_error_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate error records from records that should continue through normalization."""
    clean_records = []
    error_records = []

    for record in records:
        if _is_error_record(record):
            error_records.append(record)
        else:
            clean_records.append(record)

    return clean_records, error_records


def normalize_ohlcv(ohlcv: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Normalize a list of OHLCV dictionaries to the configured OHLCV_FIELDS schema.

    Args:
        ohlcv: List of raw OHLCV records.

    Returns:
        Tuple of normalized OHLCV dictionaries and raw error records.
    """
    def _normalize(ohlcv_dict: dict) -> dict:
        """Normalize a single OHLCV record to the configured field schema."""
        return {field: ohlcv_dict.get(field, None) for field in OHLCV_FIELDS}
    clean_records, error_records = _split_error_records(ohlcv)
    return [_normalize(ohlcv_dict) for ohlcv_dict in clean_records], error_records


def _suffix_overlapping_columns(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Rename non-header line items that appear on more than one statement with the
    owning statement's suffix from STATEMENT_SUFFIXES (income -> _is, cash -> _cf,
    balance -> _bs), so the merge keeps every statement's own value instead of
    colliding into ambiguous pandas _x/_y suffixes.

    Args:
        dfs: Mapping from statement type to its raw statement DataFrame.

    Returns:
        Mapping with the overlapping columns renamed per statement.
    """
    counts = {}
    for df in dfs.values():
        for column in df.columns:
            if column not in HEADER_KEYS:
                counts[column] = counts.get(column, 0) + 1
    overlapping = {column for column, n in counts.items() if n > 1}

    return {
        stype: df.rename(columns={
            column: column + STATEMENT_SUFFIXES.get(stype, f"_{stype}")
            for column in df.columns if column in overlapping
        })
        for stype, df in dfs.items()
    }


def normalize_statements(statements: dict[str, list[dict]]) -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    """
    Merge normalized financial statement payloads into one tabular dataset.

    Line items shared by more than one statement are suffixed with the owning
    statement's tag (_is/_cf/_bs) before the merge; see _suffix_overlapping_columns.

    Args:
        statements: Mapping from statement type to raw statement records.

    Returns:
        Tuple containing:
            - DataFrame containing clean statements outer-joined on shared header fields.
            - Mapping from statement type to raw error records excluded from the merge.
    """
    clean_statements = {}
    error_records = {}

    for stype, records in statements.items():
        clean_records, stype_errors = _split_error_records(records)
        clean_statements[stype] = clean_records
        if stype_errors:
            error_records[stype] = stype_errors

    dfs = {
        stype: pd.DataFrame(records)
        for stype, records in clean_statements.items()
        if records
    }

    if not dfs:
        return pd.DataFrame(columns=HEADER_KEYS), error_records

    dfs = _suffix_overlapping_columns(dfs)

    stypes = list(dfs.keys())

    merged = dfs[stypes[0]]

    for stype in stypes[1:]:
        df = dfs[stype]
        existing_header = [k for k in HEADER_KEYS if k in merged.columns and k in df.columns]
        non_header = [c for c in df.columns if c not in HEADER_KEYS]

        if not existing_header:
            merged = pd.concat([merged, df[non_header]], axis=1)
            continue

        merged = merged.merge(df[existing_header + non_header], on=existing_header, how="outer")
        
    return merged, error_records
