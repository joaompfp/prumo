"""Indicator metadata catalog — loaded from catalog.json."""
import json
import os

_HERE = os.path.dirname(__file__)

with open(os.path.join(_HERE, "catalog.json"), encoding="utf-8") as f:
    CATALOG = json.load(f)
