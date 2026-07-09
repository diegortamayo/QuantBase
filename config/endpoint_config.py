"""
Centralize Financial Modeling Prep API endpoints, request limits, and schemas.

Defines reusable endpoint names, rate-limit settings, response field lists, and
filter flags used by the data ingestion and normalization pipelines.
"""

from config.keys import FMP_KEY


# --------------- BASE API SETTINGS ---------------------
FMP_BASE_URL = "https://financialmodelingprep.com/stable/"
FMP_API_KEY = FMP_KEY

SETKEY = f"apikey={FMP_API_KEY}"

RATE_LIMIT = 290
LIMIT_SECONDS = 60


# --------------- ENDPOINTS ---------------------
AVAILABLE_SECTOR_ENDPOINT = "available-sectors"
AVAILABLE_INDUSTRY_ENDPOINT = "available-industries"
FIN_STATEMENT_SYMBOLS_ENDPOINT = "financial-statement-symbol-list"
ALL_SYMBOLS_ENDPOINT = "stock-list"
PROFILE_ENDPOINT = "profile"

FIVEMIN_MARKET_ENDPOINT = "historical-chart/5min"
DAILY_MARKET_ENDPOINT = "historical-price-eod/full"
START_DATE = "2017-01-01"

# Financial statements
INCOME_STATEMENT_ENDPOINT = "income-statement"
BALANCE_SHEET_ENDPOINT = "balance-sheet-statement"
CASH_FLOW_STATEMENT_ENDPOINT = "cash-flow-statement"



# FUNDAMENTAL ENDPOINT SETTINGS
YEARS_LIMIT = 8
QUARTER_LIMIT = YEARS_LIMIT*4


STYPES = ["income", "cash", "balance"]
STATEMENT_ENDPOINTS = {
    STYPES[0]: INCOME_STATEMENT_ENDPOINT,
    STYPES[1]: CASH_FLOW_STATEMENT_ENDPOINT,
    STYPES[2]: BALANCE_SHEET_ENDPOINT
}

REQ_PER_TICKER_FUNDAMENTALS = 3
HEADER_KEYS = ["date", "symbol", "reportedCurrency", "cik", "filingDate", "acceptedDate", "fiscalYear", "period"]

# Suffix appended to line items that appear on more than one statement, so each
# statement keeps its own value through the merge (the cash-flow copies are period
# deltas while balance-sheet copies are levels, so they genuinely differ).
STATEMENT_SUFFIXES = {
    STYPES[0]: "_is",
    STYPES[1]: "_cf",
    STYPES[2]: "_bs",
}



# --------------- FIELDS ---------------------
PROFILE_FIELDS = [
    "symbol","price","marketCap","beta","lastDividend","range","change","changePercentage","volume","averageVolume",
    "companyName","currency","cik","isin","cusip","exchangeFullName","exchange","industry","website","description",
    "ceo","sector","country","fullTimeEmployees","phone","address","city","state","zip","image","ipoDate",
    "defaultImage","isEtf","isActivelyTrading","isAdr","isFund","error"
]

CLEAN_PROFILE_FILEDS = ["symbol", "cik", "isin", "exchange", "sector", "industry", "country", "ipoDate", "marketCap", "price", "averageVolume", "companyName"]

OHLCV_FIELDS = ["symbol", "date", "open", "high", "low", "close", "volume", "changePercent", "vwap", "error"]


# --------------- UNIVERSE FILTERS ---------------------
ACTIVE_TRADING_FLAG = True
ADR_FLAG = False
ETF_FLAG = False
TRADED_EXCHANGES = [
    "NYSE",
    "NASDAQ",
]

# FMP industries that mark a profile as a shell/SPAC vehicle.
INDUSTRY_EXCLUSIONS = ["Shell Companies"]

# Company-name fragments that identify SPAC / blank-check shells. Kept separate
# from NAME_EXCLUSION_TERMS so shells get their own diagnostic flag. The optional
# roman/arabic numeral covers serial SPACs like "Pioneer Acquisition I Corp".
SHELL_NAME_TERMS = [
    r"\bacquisition\s+(?:[ivx0-9]+\s+)?corp(?:oration)?\b",
    r"\bspac\b",
    r"\bspecial purpose acquisition\b",
    r"\bblank check\b",
    r"\bshell compan(?:y|ies)\b",
]
SHELL_NAME_REGEX = "|".join(SHELL_NAME_TERMS)

# Company-name fragments that identify non-common-stock instruments
# (preferreds, warrants, units, rights, debt, ETNs, funds). All terms are
# word-bounded so e.g. "United"/"Bright"/"Fundamental" are not caught.
NAME_EXCLUSION_TERMS = [
    r"\bpreferred\b",
    r"\bpreference\b",
    r"\bdepositary shares?\b",
    r"\bwarrants?\b",
    r"\brights?\b",
    r"\bunits?\b",
    r"\bnotes?\b",                    # also covers "senior notes" / "subordinated notes"
    r"\bbonds?\b",
    r"\bdebentures?\b",
    r"\bsubordinated\b",
    r"\betns?\b",
    r"\bexchange[- ]traded notes?\b",
    r"\bclosed[- ]end\b",
    r"\bfund\b",
    r"%",                             # coupon in the name, e.g. "5.25% Notes due 2027"
]
NAME_EXCLUSION_REGEX = "|".join(NAME_EXCLUSION_TERMS)

# "Trust" catches closed-end funds and royalty trusts, but many legitimate REITs
# also carry "Trust" in their name, so trust matches are exempted when the FMP
# industry marks the row as a REIT. Tradeoff: a REIT-like trust misclassified by
# FMP's industry field is dropped, and a fund trust tagged as a REIT slips through.
TRUST_NAME_REGEX = r"\btrust\b"
REIT_INDUSTRY_REGEX = r"\bREIT\b"

# FMP symbol suffix conventions (observed in the stock-list payload):
# preferred series "-P"/"-PA".."-PZ", warrants "-WT"/"-WTA"/"-WTB", units "-UN",
# rights "-RI". Single-letter dash suffixes (BRK-B, BF-B, HEI-A) are real share
# classes and must survive, so hyphens alone are NOT an exclusion signal.
# NASDAQ additionally encodes the type in the 5th letter of unhyphenated
# 5-letter symbols (W = warrant, R = right, U = unit), e.g. BSLKW / ASPCR / PACHU.
SYMBOL_EXCLUSION_PATTERNS = [
    r"-P[A-Z]?$",
    r"-WT[A-Z]?$",
    r"-UN$",
    r"-RI$",
    r"^[A-Z]{4}[WRU]$",
]
SYMBOL_EXCLUSION_REGEX = "|".join(SYMBOL_EXCLUSION_PATTERNS)

# Diagnostic columns added by flag_profile_exclusions; a row is dropped from the
# universe when any of them is True.
EXCLUSION_FLAGS = [
    "exclude_profile_error",
    "exclude_bad_exchange",
    "exclude_etf",
    "exclude_adr",
    "exclude_shell",
    "exclude_bad_name",
    "exclude_bad_symbol",
]
