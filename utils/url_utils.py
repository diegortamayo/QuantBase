from config.endpoint_config import FMP_BASE_URL, SETKEY


def url_builder(endpoint: str, params=None) -> str:
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