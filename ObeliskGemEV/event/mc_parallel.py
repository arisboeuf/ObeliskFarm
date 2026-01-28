"""
Multiprocessing helpers for Event Monte Carlo optimization.

Design goals:
- Windows-safe (spawn) -> all worker entrypoints are top-level and pickleable.
- Keep worker payload small and pickle-friendly (plain dict/list inputs).
- Deterministic per-task RNG seeding (event simulator uses global `random`).
"""

from __future__ import annotations

from typing import Any, Dict, List


def run_event_sims_summary(
    *,
    levels: Dict[int, List[int]],
    gem_levels: List[int],
    prestige: int,
    runs: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Run `runs` event simulations for a concrete upgrade state and return averages.

    Returns dict:
      - avg_wave: float
      - avg_time: float
    """
    import random

    # Ensure deterministic, per-task RNG. The simulator uses the global `random` module.
    random.seed(int(seed) & 0x7FFFFFFF)

    from .optimizer import UpgradeState, calculate_player_stats
    from .simulation import run_full_simulation

    state = UpgradeState()
    for tier in range(1, 5):
        state.levels[tier] = list(levels.get(tier, []))
    state.gem_levels = list(gem_levels or [0, 0, 0, 0])

    player, enemy = calculate_player_stats(state, int(prestige))
    _results, avg_wave, avg_time = run_full_simulation(player, enemy, runs=max(1, int(runs)))

    return {"avg_wave": float(avg_wave), "avg_time": float(avg_time)}

