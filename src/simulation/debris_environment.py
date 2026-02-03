from dataclasses import dataclass, field
from typing import Dict
import math


@dataclass(frozen = True)
class DebrisEnvParams:
    #init debris density
    D0: float = 1.0

    #debris addition each year
    source_s: float = 0.02
    cascade_a: float = 0.005  # nonlinear growth term (Kessler-like) scales D^2
    # removal factor, orbital decay etc
    decay_b: float = 0.03
    # effects of our removal
    removal_c: float = 0.002

    # Risk mapping: how strongly debris density increases collision risk
    risk_k: float = 0.75

    # Stability clamps
    D_min: float = 0.0
    D_max: float = 10.0
    mult_max: float = 10.0  # cap on risk multiplier

    # Probability cap (helps keep things sane)
    p_cap: float = 0.99

    baseline_flux_per_m2_year: Dict[str, float] = field(default_factory=lambda: {
        "lt_1mm": 200.0,
        "1_10mm": 20.0,
        "1_10cm": 0.2,
        "gt_10cm": 0.01,
    })
    # how D scales with flux
    flux_scale_alpha: float = 0.5

    direction_multiplier: Dict[str, float] = field(default_factory=lambda: {
        "ram": 1.6,
        "wake": 0.6,
        "zenith": 1.0,
        "nadir": 1.0,
        "north": 0.9,
        "south": 0.9,
    })


# Orbital State
@dataclass(frozen=True)
class OrbitState:
    alt_km: float



def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def direction_factor(direction: str, params: DebrisEnvParams) -> float:
    """
    Returns a multiplier for flux based on direction bin.
    Unknown direction -> error (so you catch typos early).
    """
    if direction not in params.direction_multiplier:
        raise ValueError(f"Unknown direction: {direction}. Valid: {list(params.direction_multiplier.keys())}")
    return float(params.direction_multiplier[direction])


def update_density(D: float, removals: int, params: DebrisEnvParams, dt_years: float = 1.0) -> float:
    """
    Update debris density index forward by dt_years.

    D_{t+1} = D_t + s + a*D_t^2 - b*D_t - c*removals

    Args:
        D: current debris density index (unitless)
        removals: number of successful debris removals in this time step
        params: DebrisEnvParams
        dt_years: time step size in years (default 1 year)

    Returns:
        Next debris density index, clamped to [D_min, D_max].
    """
    D = float(D)
    removals = int(removals)

    # Core dynamics (simple, interpretable)
    dD = (
        params.source_s * dt_years
        + params.cascade_a * (D ** 2) * dt_years
        - params.decay_b * D * dt_years
        - params.removal_c * removals
    )

    D_next = D + dD
    return clamp(D_next, params.D_min, params.D_max)

# converting our density jawn to flux based
def flux_per_m2_year(orbit: OrbitState, D: float, size_bin: str, params: DebrisEnvParams, direction: str = "ram") -> float:
    """
    ORDEM-like output: debris flux (impacts per m^2 per year) for a given orbit and size bin.

    - baseline comes from params.baseline_flux_per_m2_year[size_bin]
    - altitude factor is a simple proxy (higher alt -> debris persists longer)
    - debris density index D scales flux: flux *= (1 + flux_scale_alpha * D)
    """
    if size_bin not in params.baseline_flux_per_m2_year:
        raise ValueError(f"Unknown size_bin: {size_bin}. Valid: {list(params.baseline_flux_per_m2_year.keys())}")

    base = float(params.baseline_flux_per_m2_year[size_bin])

    # Simple altitude proxy (you can refine later)
    # Example: below 600 km a bit less persistent; above 900 km a bit more persistent.
    alt = float(orbit.alt_km)
    if alt < 600:
        alt_factor = 0.8
    elif alt < 900:
        alt_factor = 1.0
    else:
        alt_factor = 1.2
    dir_factor = direction_factor(direction, params)

    # Scale by debris density index D (unitless)
    # Clamp so D doesnt hike our flux to unrealistic numbers
    D = clamp(float(D), params.D_min, params.D_max)
    flux_scale = 1.0 + params.flux_scale_alpha * D
    #call our clamp before so it doesnt explode
    flux_scale = clamp(flux_scale, 1.0, params.mult_max)
    flux = base * alt_factor * flux_scale * dir_factor

    return max(flux, 0.0)


# Poisson Functions
def expected_impacts(flux_per_m2_year_value: float, area_m2: float, duration_years: float) -> float:
    """
    Expected number of impacts in a time window:
        lambda = flux * area * time
    """
    flux = float(flux_per_m2_year_value)
    area = float(area_m2)
    t = float(duration_years)
    if area < 0 or t < 0:
        raise ValueError("area_m2 and duration_years must be nonnegative")
    return flux * area * t


def hit_probability(lambda_hits: float) -> float:
    """
    Poisson probability of >=1 hit:
        P(hit) = 1 - exp(-lambda)
    """
    lam = float(lambda_hits)
    if lam <= 0:
        return 0.0
    return 1.0 - math.exp(-lam)

#new risk modeling
def catastrophic_prob_from_flux(
    orbit: OrbitState,
    D: float,
    area_m2: float,
    duration_hours: float,
    params: DebrisEnvParams,
    direction: str = "ram",
    catastrophic_size_bin: str = "gt_10cm"
) -> float:
    """
    Compute per-attempt catastrophic probability from ORDEM-like flux.

    Steps:
    1) Get flux for catastrophic-sized debris (impacts/m^2/year)
    2) Convert exposure duration into years
    3) lambda = flux * area * time
    4) p = 1 - exp(-lambda)
    5) cap at params.p_cap
    """
    duration_years = float(duration_hours) / (365.25 * 24.0)

    flux = flux_per_m2_year(orbit, D, catastrophic_size_bin, params, direction=direction)
    lam = expected_impacts(flux, area_m2, duration_years)
    p = hit_probability(lam)
    return min(p, params.p_cap)



def risk_multiplier(D: float, params: DebrisEnvParams) -> float:
    """
    Map debris density index to a multiplier on per-attempt catastrophic risk.

    Simple mapping: mult = 1 + risk_k * D, capped at mult_max.
    """
    D = float(D)
    mult = 1.0 + params.risk_k * D
    return clamp(mult, 1.0, params.mult_max)

# legacy design
def scaled_catastrophic_prob(p_base: float, D: float, params: DebrisEnvParams) -> float:
    """
    Scale a base per-attempt catastrophic probability by debris density.

    p_cat = min(p_base * risk_multiplier(D), p_cap)
    """
    p = float(p_base) * risk_multiplier(D, params)
    return min(p, params.p_cap)


