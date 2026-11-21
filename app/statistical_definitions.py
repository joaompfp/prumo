"""Pure statistical identity helpers shared by authored country comparisons and import checks."""


def native_parts(native_code: str | None) -> tuple[str, dict[str, str]] | None:
    """Parse an unambiguous dataset/dimension identity without reinterpreting tokens."""
    if not isinstance(native_code, str):
        return None
    dataset, separator, rest = native_code.partition(":")
    if not separator or not dataset or not rest:
        return None
    dimensions = {}
    for part in rest.split(","):
        key, equals, value = part.partition("=")
        if not equals or not key or not value or key in dimensions:
            return None
        dimensions[key] = value
    return dataset, dimensions


def country_signature(row: dict) -> tuple | None:
    """Same concept and native dimensions, except geography, for a between-country group.

    Eurostat dimension identities are explicit. Other publishers' identity formats stay with
    their adapters; their validated indicator family remains the comparable concept here.
    """
    native = native_parts(row["native_code"])
    if row["source"] == "eurostat" and native is None:
        return None
    dimensions = None
    if native is not None:
        dataset, parts = native
        if parts.get("geo") not in (None, row["geography"]):
            return None
        dimensions = (dataset, tuple(sorted((k, v) for k, v in parts.items() if k != "geo")))
    return (row["source"], row["family"], row["frequency"], row["unit"], row["multiplier"],
            row["base_year"], row["seasonal_adjustment"], dimensions)
