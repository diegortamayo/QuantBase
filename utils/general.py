from config.endpoint_config import PROFILE_FIELDS, OHLCV_FIELDS


def normalize_profile(p: dict) -> dict:
    return {field: p.get(field, None) for field in PROFILE_FIELDS}



def normalize_ohlcv(ohlcv: list) -> list:
    def _normalize(ohlcv_dict: dict) -> dict:
        return {field: ohlcv_dict.get(field, None) for field in OHLCV_FIELDS}
    return [_normalize(ohlcv_dict) for ohlcv_dict in ohlcv]
