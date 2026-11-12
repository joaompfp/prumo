"""`python -m ingest ...` -> ingest.cli.main (argparse + printing live there)."""
from ingest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
