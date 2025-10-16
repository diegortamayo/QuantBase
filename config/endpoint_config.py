from config.keys import FMP_KEY


FMP_BASE_URL = "https://financialmodelingprep.com/stable/"
FMP_API_KEY = FMP_KEY

SETKEY = f"apikey={FMP_API_KEY}"

AVAILABLE_SECTOR_ENDPOINT = "available-sectors"
AVAILABLE_INDUSTRY_ENDPOINT = "available-industries"
FIN_STATEMENT_SYMBOLS_ENDPOINT = "financial-statement-symbol-list"
PROFILE_ENDPOINT = "profile"

RATE_LIMIT = 290


PROFILE_FIELDS = [
    "symbol","price","marketCap","beta","lastDividend","range","change","changePercentage","volume","averageVolume",
    "companyName","currency","cik","isin","cusip","exchangeFullName","exchange","industry","website","description",
    "ceo","sector","country","fullTimeEmployees","phone","address","city","state","zip","image","ipoDate",
    "defaultImage","isEtf","isActivelyTrading","isAdr","isFund","error"
]