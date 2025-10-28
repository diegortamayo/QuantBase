"""
Configurations and constants for features calculations
"""

MULTI_HORIZONS = [5, 21, 63, 126, 252, 504]
SHORT_HORIZONS = [5, 21]
MID_HORIZONS = [63, 126]
LONG_HORIZONS = [252, 504]

BATCH_SIZE = 50
N_WORKERS = 8
N_BATCH_COOLDOWN = 5
COOLDOWN_TIME = 10