import os

CAE_DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
ENERGY_DB_PATH = os.path.join(os.path.dirname(CAE_DB_PATH), "energy-data.db")
PORT = int(os.environ.get("CAE_PORT", "8080"))
BASE_PATH = os.environ.get("CAE_BASE_PATH", "").rstrip("/")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

ENERGY_SOURCES = {"DGEG", "ERSE"}

ANALYTICS_DB_PATH = os.environ.get("ANALYTICS_DB_PATH", "/data/analytics.db")

SKILLS_DIR = os.environ.get(
    "SKILLS_DIR",
    "/home/node/.openclaw/workspace/skills/cae-reports"
)
