"""Approximate reference positions for Nigeria's 36 states and FCT.

Coordinates are administrative *representative points*, NOT individual farms,
road-routing points or evidence of local crop-price availability.
Source: Open Admin Data Nigeria https://openadmindata.org/ng/
Original administrative-source attribution: OCHA COD-AB (HDX) + INEC Nigeria.
"""
from __future__ import annotations

# State/FCT representative points (latitude, longitude), rounded to 3 decimals.
# These are used only as approximate farmer origins for distance comparisons.
STATE_REFERENCE_POINTS: dict[str, tuple[float, float]] = {
    "Abia": (5.432, 7.488),
    "Adamawa": (9.163, 12.292),
    "Akwa Ibom": (4.990, 7.796),
    "Anambra": (6.249, 6.938),
    "Bauchi": (10.998, 9.326),
    "Bayelsa": (4.827, 5.951),
    "Benue": (7.301, 8.812),
    "Borno": (11.870, 13.428),
    "Cross River": (5.791, 8.403),
    "Delta": (5.757, 5.500),
    "Ebonyi": (6.240, 8.067),
    "Edo": (6.665, 5.874),
    "Ekiti": (7.695, 5.298),
    "Enugu": (6.520, 7.393),
    "FCT (Abuja)": (9.013, 7.191),
    "Gombe": (10.431, 11.225),
    "Imo": (5.566, 7.033),
    "Jigawa": (11.981, 9.625),
    "Kaduna": (10.257, 7.859),
    "Kano": (11.573, 8.543),
    "Katsina": (12.236, 7.500),
    "Kebbi": (11.691, 3.966),
    "Kogi": (7.636, 6.849),
    "Kwara": (9.093, 4.567),
    "Lagos": (6.535, 3.712),
    "Nasarawa": (8.589, 8.211),
    "Niger": (9.774, 5.711),
    "Ogun": (7.127, 3.263),
    "Ondo": (6.824, 4.869),
    "Osun": (7.538, 4.521),
    "Oyo": (8.135, 3.613),
    "Plateau": (9.380, 9.628),
    "Rivers": (5.023, 6.836),
    "Sokoto": (12.739, 5.237),
    "Taraba": (8.059, 10.386),
    "Yobe": (11.974, 11.524),
    "Zamfara": (12.013, 6.051),
}


def price_state_name(origin_label: str) -> str:
    """Use dataset-compatible state label for same-state price comparison."""
    if origin_label not in STATE_REFERENCE_POINTS:
        raise ValueError(f"Unsupported Nigerian origin: {origin_label}")
    return "Federal Capital Territory" if origin_label == "FCT (Abuja)" else origin_label


def local_net_reference(ranked_markets, origin_label: str) -> float | None:
    """Highest indicative net among priced markets in the user's state.

    Returns None when there is no same-state *market quote*; never substitutes
    a national average or guesses a home-market price.
    """
    local = ranked_markets[ranked_markets["state"] == price_state_name(origin_label)]
    return float(local["net_ngn"].max()) if not local.empty else None
