"""
Multiprocessing helpers for Archaeology Monte Carlo simulations.

Design goals:
- Windows-safe (spawn) -> all worker entrypoints are top-level and pickleable.
- Dependency-light, reuse existing simulation math.
- Chunk-friendly: workers can run many sims per call to reduce IPC overhead.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def run_stage_sims_summary(
    *,
    stats: Dict[str, Any],
    starting_floor: int,
    n_sims: int,
    use_crit: bool,
    enrage_enabled: bool,
    flurry_enabled: bool,
    quake_enabled: bool,
    block_cards: Optional[Dict[str, int]],
    seed: int,
) -> Dict[str, Any]:
    """
    Run `n_sims` archaeology simulations and return aggregated summary metrics.

    Returns dict:
      - avg_max_stage: float
      - fragments_per_hour: float
      - xp_per_hour: float
      - stage_counts: dict[int, int]  (int(max_stage_reached) -> count)
      - max_stage_seen: int
    """
    import random

    # Ensure deterministic, per-task RNG. The simulator uses the global `random` module.
    random.seed(int(seed) & 0x7FFFFFFF)

    from .monte_carlo_crit import MonteCarloCritSimulator

    sim = MonteCarloCritSimulator(seed=int(seed) & 0x7FFFFFFF)

    stage_counts: Dict[int, int] = {}
    max_stage_seen = 0

    sum_max_stage = 0.0
    sum_fragments = 0.0
    sum_xp = 0.0
    sum_run_duration = 0.0

    n_sims_i = max(0, int(n_sims))
    for _ in range(n_sims_i):
        result = sim.simulate_run(
            stats,
            int(starting_floor),
            use_crit=bool(use_crit),
            enrage_enabled=bool(enrage_enabled),
            flurry_enabled=bool(flurry_enabled),
            quake_enabled=bool(quake_enabled),
            block_cards=block_cards,
            return_metrics=True,
        )

        max_stage = float(result.get("max_stage_reached", 0.0))
        sum_max_stage += max_stage

        stage_int = int(max_stage)
        stage_counts[stage_int] = stage_counts.get(stage_int, 0) + 1
        if stage_int > max_stage_seen:
            max_stage_seen = stage_int

        sum_fragments += float(result.get("total_fragments", 0.0))
        sum_xp += float(result.get("xp_per_run", 0.0))
        sum_run_duration += float(result.get("run_duration_seconds", 1.0))

    if n_sims_i > 0:
        avg_max_stage = sum_max_stage / n_sims_i
        avg_fragments = sum_fragments / n_sims_i
        avg_xp = sum_xp / n_sims_i
        avg_run_duration = sum_run_duration / n_sims_i
    else:
        avg_max_stage = 0.0
        avg_fragments = 0.0
        avg_xp = 0.0
        avg_run_duration = 1.0

    fragments_per_hour = (avg_fragments * 3600.0 / avg_run_duration) if avg_run_duration > 0 else 0.0
    xp_per_hour = (avg_xp * 3600.0 / avg_run_duration) if avg_run_duration > 0 else 0.0

    return {
        "avg_max_stage": float(avg_max_stage),
        "fragments_per_hour": float(fragments_per_hour),
        "xp_per_hour": float(xp_per_hour),
        "stage_counts": stage_counts,
        "max_stage_seen": int(max_stage_seen),
    }


def run_stage_sims_detailed(
    *,
    stats: Dict[str, Any],
    starting_floor: int,
    n_sims: int,
    use_crit: bool,
    enrage_enabled: bool,
    flurry_enabled: bool,
    quake_enabled: bool,
    block_cards: Optional[Dict[str, int]],
    seed: int,
) -> Dict[str, Any]:
    """
    Run `n_sims` archaeology simulations and return per-run samples needed by the UI.

    Returns dict:
      - max_stage_samples: list[float]
      - metrics_samples: list[dict]
    """
    import random

    random.seed(int(seed) & 0x7FFFFFFF)

    from .monte_carlo_crit import MonteCarloCritSimulator

    sim = MonteCarloCritSimulator(seed=int(seed) & 0x7FFFFFFF)

    max_stage_samples: List[float] = []
    metrics_samples: List[Dict[str, Any]] = []

    n_sims_i = max(0, int(n_sims))
    for _ in range(n_sims_i):
        result = sim.simulate_run(
            stats,
            int(starting_floor),
            use_crit=bool(use_crit),
            enrage_enabled=bool(enrage_enabled),
            flurry_enabled=bool(flurry_enabled),
            quake_enabled=bool(quake_enabled),
            block_cards=block_cards,
            return_metrics=True,
        )

        max_stage_samples.append(float(result.get("max_stage_reached", 0.0)))
        metrics_samples.append(
            {
                "xp_per_run": float(result.get("xp_per_run", 0.0)),
                "total_fragments": float(result.get("total_fragments", 0.0)),
                "fragments": (result.get("fragments", {}) or {}).copy(),
                "floors_cleared": float(result.get("floors_cleared", 0.0)),
                "run_duration_seconds": float(result.get("run_duration_seconds", 1.0)),
            }
        )

    return {"max_stage_samples": max_stage_samples, "metrics_samples": metrics_samples}


def run_fragment_sims_summary(
    *,
    stats: Dict[str, Any],
    starting_floor: int,
    n_sims: int,
    use_crit: bool,
    enrage_enabled: bool,
    flurry_enabled: bool,
    quake_enabled: bool,
    block_cards: Optional[Dict[str, int]],
    target_frag: str,
    seed: int,
) -> Dict[str, Any]:
    """
    Run `n_sims` archaeology simulations and return average target-fragment/hour.

    Returns dict:
      - avg_frag_per_hour: float
    """
    import random

    random.seed(int(seed) & 0x7FFFFFFF)

    from .monte_carlo_crit import MonteCarloCritSimulator

    sim = MonteCarloCritSimulator(seed=int(seed) & 0x7FFFFFFF)

    tfrag = str(target_frag)
    sum_frags_per_hour = 0.0
    n_sims_i = max(0, int(n_sims))

    for _ in range(n_sims_i):
        result = sim.simulate_run(
            stats,
            int(starting_floor),
            use_crit=bool(use_crit),
            enrage_enabled=bool(enrage_enabled),
            flurry_enabled=bool(flurry_enabled),
            quake_enabled=bool(quake_enabled),
            block_cards=block_cards,
            return_metrics=True,
        )

        fragments = result.get("fragments", {}) or {}
        target_frag_count = float(fragments.get(tfrag, 0.0))
        run_duration_seconds = float(result.get("run_duration_seconds", 1.0))
        runs_per_hour = (3600.0 / run_duration_seconds) if run_duration_seconds > 0 else 0.0
        sum_frags_per_hour += target_frag_count * runs_per_hour

    avg_frag_per_hour = (sum_frags_per_hour / n_sims_i) if n_sims_i > 0 else 0.0
    return {"avg_frag_per_hour": float(avg_frag_per_hour)}

