import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class AttemptParams:
    p_success: float = 0.94
    p_abort: float = 0.05
    p_catastrophic: float = 0.01  # collision / unrecoverable

def simulate_one_attempt(rng: np.random.Generator, params: AttemptParams) -> str:
    """
    Returns one of: 'SUCCESS', 'ABORT', 'CATASTROPHIC'
    """
    u = rng.random()
    if u < params.p_catastrophic:
        return "CATASTROPHIC"
    if u < params.p_catastrophic + params.p_abort:
        return "ABORT"
    return "SUCCESS"
