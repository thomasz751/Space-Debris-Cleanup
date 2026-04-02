from dataclasses import dataclass

import numpy as np
import pandas as pd

from .debris_environment import DebrisEnvParams, update_density
from .loss import LossParams, loss_for_attempt
from .mission_cycle import CycleParams, simulate_one_cycle


@dataclass(frozen=True)
class MissionParams:
    years: int = 3
    attempts_per_year: int = 40  # number of cycles/year


def simulate_one_satellite(
    seed: int,
    mission: MissionParams,
    cycle_params: CycleParams,
    loss_params: LossParams,
    env_params: DebrisEnvParams,
) -> dict:
    rng = np.random.default_rng(seed)

    D = env_params.D0
    D_history = []

    total_loss = 0.0
    successes = 0
    aborts = 0
    total_mass_kg = 0.0

    for year in range(mission.years):
        D_history.append(D)

        removals_this_year = 0

        for _ in range(mission.attempts_per_year):
            cycle = simulate_one_cycle(rng, D, cycle_params)
            outcome = cycle.outcome

            # Loss model still works if it expects these 3 labels
            total_loss += loss_for_attempt(rng, outcome, loss_params)

            if outcome == "SUCCESS":
                successes += 1
                removals_this_year += 1
                total_mass_kg += float(cycle.mass_kg)
            elif outcome == "ABORT":
                aborts += 1
            elif outcome == "CATASTROPHIC":
                return {
                    "ended": "CATASTROPHIC",
                    "successes": successes,
                    "aborts": aborts,
                    "loss": total_loss,
                    "D_end": D,
                    "mass_kg": total_mass_kg,
                    "years_simulated": year + 1,
                }

        # end of year environment update (count-based for now)
        D = update_density(D, removals_this_year, env_params)

    return {
        "ended": "COMPLETED",
        "successes": successes,
        "aborts": aborts,
        "loss": total_loss,
        "D_end": D,
        "mass_kg": total_mass_kg,
        "years_simulated": mission.years,
    }


def run_portfolio(
    n_sats: int,
    seed: int,
    mission: MissionParams,
    cycle_params: CycleParams,
    loss_params: LossParams,
    env_params: DebrisEnvParams,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seeds = rng.integers(0, 2**31 - 1, size=n_sats)

    rows = [
        simulate_one_satellite(int(s), mission, cycle_params, loss_params, env_params)
        for s in seeds
    ]
    return pd.DataFrame(rows)
