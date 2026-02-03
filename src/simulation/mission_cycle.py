from dataclasses import dataclass
from .debris_environment import DebrisEnvParams, OrbitState, catastrophic_prob_from_flux


@dataclass(frozen=True)
class CycleParams:
    # probability this cycle enters a risky phase
    p_risk: float = 0.1

    # risky exposure time during the cycle (hours)
    risky_hours: float = 1.5

    # mean captured mass if success (kg)
    mean_mass_kg: float = 50.0

    # environment/risk inputs
    alt_km: float = 700.0
    area_m2: float = 10.0
    direction: str = "ram"
    env_params: DebrisEnvParams = DebrisEnvParams()


@dataclass(frozen=True)
class CycleResult:
    outcome: str           # "SUCCESS", "ABORT", "CATASTROPHIC"
    risky_hours: float     # hours of risky exposure actually incurred
    mass_kg: float         # debris mass captured (kg)


def simulate_one_cycle(rng, D: float, params: CycleParams) -> CycleResult:
    """
    Simulate one debris capture cycle.

    D is the current debris density index from the environment model.
    """

    # Step 1: decide whether this cycle enters a risky phase at all
    if rng.random() > params.p_risk:
        return CycleResult(outcome="SUCCESS", risky_hours=0.0, mass_kg=params.mean_mass_kg)

    # Step 2: compute catastrophic probability from ORDEM-like flux
    orbit = OrbitState(alt_km=params.alt_km)
    p_cat = catastrophic_prob_from_flux(
        orbit=orbit,
        D=D,
        area_m2=params.area_m2,
        duration_hours=params.risky_hours,
        params=params.env_params,
        direction=params.direction,
    )

    # Step 3: sample outcome for risky cycle
    u = rng.random()

    if u < p_cat:
        return CycleResult(outcome="CATASTROPHIC", risky_hours=params.risky_hours, mass_kg=0.0)

    # keep a simple abort rule for now (conditional on not catastrophic)
    p_abort = 0.10
    if u < p_cat + p_abort:
        return CycleResult(outcome="ABORT", risky_hours=params.risky_hours, mass_kg=0.0)

    # success
    return CycleResult(outcome="SUCCESS", risky_hours=params.risky_hours, mass_kg=params.mean_mass_kg)





