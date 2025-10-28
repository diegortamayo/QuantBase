"""
Utility for building fully parameterized API request URLs for FMP endpoints.

Appends query parameters and API key to the base endpoint.
"""
from config.endpoint_config import FMP_BASE_URL, SETKEY


def url_builder(endpoint: str, params=None) -> str:
    """
    Build a complete FMP API request URL.

    Args:
        endpoint: Endpoint path relative to FMP_BASE_URL.
        params: Optional dictionary of query parameters.

    Returns:
        Fully constructed URL string with appended parameters and API key.
    """
    url = f"{FMP_BASE_URL}{endpoint}"
    if params:
        for i, (key, value) in enumerate(params.items()):
            if i == 0:
                url += f"?{key}={value}"
            else:
                url += f"&{key}={value}"
        url += f"&{SETKEY}"
    else:
        url += f"?{SETKEY}"
    return url