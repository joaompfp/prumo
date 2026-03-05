The Prumo database (`cae-data.duckdb`) is not shipped with the Docker image by default.

To get started, you can either:
1. Provide your own fully populated DuckDB file by mounting it to `/data/cae-data.duckdb`.
2. Run the included data collection scripts to populate the database from scratch:
   docker exec -it prumo ./scripts/cae-collect

If you're seeing this file, it means the startup script did not find an existing DuckDB database and skipped initialization. Check the container logs for guidance.
