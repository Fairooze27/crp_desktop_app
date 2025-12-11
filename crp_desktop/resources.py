
# Constants and identifier mapping.

IDENTIFIER_MAP = {
    'p': ('Instrument #', None),
    'q': ('DateTime', None),
    'u': ('ID', None),
    's': ('MeasurementsPerDay', None),
    '!': ('WBC', '10^3/uL'),
    '2': ('RBC', '10^6/uL'),
    '3': ('HGB', 'g/dL'),
    '4': ('HCT', '%'),
    '5': ('MCV', 'fL'),
    '6': ('MCH', 'pg'),
    '7': ('MCHC', 'g/dL'),
    '8': ('RDW', '%'),
    '@': ('PLT', '10^3/uL'),
    'A': ('MPV', 'fL'),
    'B': ('PCT', '%'),
    'C': ('PDW', '%'),
    '#': ('%LYM', '%'),
    '%': ('%MON', '%'),
    "'": ('%GRA', '%'),
    '"': ('#LYM', '10^3/uL'),
    '$': ('#MON', '10^3/uL'),
    '&': ('#GRA', '10^3/uL'),
    'K': ('CRP', 'mg/dL'),
    'W': ('WBC_HIST', None),
    'X': ('RBC_HIST', None),
    'Y': ('PLT_HIST', None),
    '_': ('PLT_THRESHOLD', None),
    ']': ('WBC_THRESHOLDS', None),
}

# Serial / DB defaults
DB_PATH = "crp_results.db"
BAUD_RATES = [9600, 4800, 19200, 38400]
READ_TIMEOUT = 1.0
BUFFER_RESET_TIMEOUT = 5.0
