from ..database import fetch_series


def build_energia():
    """Build /api/energia response with energy data."""
    result = {}

    # 1. Electricity prices (DGEG, semestral)
    elec_indicators = ["industrial_band_ic_excl_taxes", "industrial_band_ic_incl_taxes",
                       "industrial_band_id_excl_taxes", "industrial_band_id_incl_taxes"]
    elec_data = {}
    for ind in elec_indicators:
        rows = fetch_series("DGEG", ind)
        if rows:
            elec_data[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["electricity_prices"] = elec_data

    # 2. Fuel prices (DGEG, weekly — long series)
    fuel_data = {}
    for ind in ["price_diesel_pvp", "price_diesel_pretax", "price_gasoline_95_pvp", "price_gasoline_95_pretax"]:
        rows = fetch_series("DGEG", ind)
        if rows:
            fuel_data[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["fuel_prices"] = fuel_data

    # 3. Energy mix (REN, monthly)
    mix_data = {}
    for ind in ["electricity_hydro", "electricity_wind", "electricity_solar",
                "electricity_natural_gas", "electricity_biomass",
                "electricity_production_renewable", "electricity_production_non_renewable",
                "electricity_production_total", "electricity_consumption"]:
        rows = fetch_series("REN", ind)
        if rows:
            mix_data[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["energy_mix"] = mix_data

    # 4. Commodities (FRED)
    commodities = {}
    for ind in ["brent_oil", "natural_gas", "aluminum", "copper"]:
        rows = fetch_series("FRED", ind)
        if rows:
            commodities[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["commodities"] = commodities

    # 5. Renewable share
    ren_share = {}
    for ind in ["renewable_share_electricity", "renewable_share_total"]:
        rows = fetch_series("DGEG", ind)
        if rows:
            ren_share[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["renewable_share"] = ren_share

    # 6. Energy dependence + intensity
    energy_ind = {}
    for ind in ["energy_dependence", "energy_intensity", "energy_intensity_industry"]:
        rows = fetch_series("DGEG", ind)
        if rows:
            energy_ind[ind] = [{"period": r["period"], "value": r["value"]} for r in rows]
    result["energy_indicators"] = energy_ind

    return result
