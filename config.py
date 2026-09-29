"""Impostazioni centrali dell'app. Modifica qui calendari, ruote e premi."""
from datetime import time

TZ_NAME = "Europe/Rome"

# Codici ruota -> nome
WHEELS = {
    "BA": "Bari", "CA": "Cagliari", "FI": "Firenze", "GE": "Genova",
    "MI": "Milano", "NA": "Napoli", "PA": "Palermo", "RM": "Roma",
    "TO": "Torino", "VE": "Venezia", "RN": "Nazionale",
}
DEFAULT_WHEEL = "RM"

# Alias per riconoscere la ruota nei file (codice o nome, maiuscolo)
WHEEL_ALIASES = {code: code for code in WHEELS}
WHEEL_ALIASES.update({name.upper(): code for code, name in WHEELS.items()})

# Calendario estrazioni (lun=0 ... dom=6). VERIFICA sul sito ufficiale:
# gli orari/giorni possono cambiare.
LOTTO_DRAW_WEEKDAYS = (1, 3, 4, 5)          # mar, gio, ven, sab
LOTTO_DRAW_TIME = time(20, 0)
MILLIONDAY_DRAW_TIMES = (time(13, 0), time(20, 30))

# Margine di sicurezza (minuti) prima dell'estrazione entro cui giocare
CUTOFF_MINUTES = 30

# Vincite Lotto per 1 euro su una ruota (tabella ufficiale)
LOTTO_PAYOUT = {"ambata": 11.23, "ambo": 250.0}

# Parametri statistici
LAG_MIN, LAG_MAX = 60, 100          # fascia ritardatari intermedi
MIN_LOTTO_HISTORY = 110             # estrazioni minime per ruota
MIN_MD_HISTORY = 30

DAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
