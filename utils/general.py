from config.endpoint_config import PROFILE_FIELDS


def normalize_profile(p):
    return {field: p.get(field, None) for field in PROFILE_FIELDS}