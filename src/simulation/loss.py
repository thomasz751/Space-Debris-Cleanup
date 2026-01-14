import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class LossParams:
    insured_value: float = 50_000_000.0  # $50M per satellite
    downtime_cost_per_abort: float = 50_000.0
    partial_loss_prob_after_success: float = 0.02  # success but causes degradation
    partial_loss_min_frac: float = 0.05
    partial_loss_max_frac: float = 0.25

def loss_for_attempt(rng: np.random.Generator, outcome: str, lp: LossParams) -> float:
    if outcome == "CATASTROPHIC":
        return float(lp.insured_value)
    if outcome == "ABORT":
        return float(lp.downtime_cost_per_abort)

    # SUCCESS: sometimes still causes wear/degradation -> partial loss
    if rng.random() < lp.partial_loss_prob_after_success:
        frac = rng.uniform(lp.partial_loss_min_frac, lp.partial_loss_max_frac)
        return float(frac * lp.insured_value)

    return 0.0
