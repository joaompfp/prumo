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

CUSTOM_LENS_DEFAULT = os.environ.get(
    "CAE_CUSTOM_LENS_DEFAULT",
    "Komenta es dados na kriolu di São Vicente (variante barlavento, sintaxe ALUPEC) y komenta es indikadores. Bo debe termina ku vivas pa Falcões do Norte (klube di São Vicente, Mindelo), na kriolu, klaru y sinjifikativu, sin traduson pa portuges."
)
