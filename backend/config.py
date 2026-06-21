import os

# Centralized Path Definitions
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

TEMP_DIR = os.path.join(ROOT_DIR, "temp")
TEMP_UPLOADS = os.path.join(TEMP_DIR, "uploads")
TEMP_REPORTS = os.path.join(TEMP_DIR, "reports")
TEMP_CHARTS = os.path.join(TEMP_DIR, "charts")
TEMP_EXPORTS = os.path.join(TEMP_DIR, "exports")
TEMP_CACHE = os.path.join(TEMP_DIR, "cache")

def ensure_temp_dirs():
    for d in [TEMP_DIR, TEMP_UPLOADS, TEMP_REPORTS, TEMP_CHARTS, TEMP_EXPORTS, TEMP_CACHE]:
        os.makedirs(d, exist_ok=True)
