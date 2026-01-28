"""
Monte Carlo Optimizer for Event Budget Optimizer.
Generates random upgrade sequences and finds the best one through simulation.
"""

import random
import math
from typing import Any, Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass

from .constants import COSTS, MAX_LEVELS, CAP_UPGRADES, PRESTIGE_UNLOCKED
from .stats import PlayerStats, EnemyStats
from .simulation import apply_upgrades, run_full_simulation
from .optimizer import UpgradeState, calculate_player_stats, get_max_level_with_caps, is_upgrade_unlocked


@dataclass
class MCOptimizationResult:
    """Result from Monte Carlo optimization"""
    best_state: UpgradeState
    best_wave: float
    best_time: float
    materials_spent: Dict[int, float]
    materials_remaining: Dict[int, float]
    player_stats: PlayerStats
    enemy_stats: EnemyStats
    all_results: List[Tuple[UpgradeState, float, float]]  # (state, wave, time)
    statistics: Dict[str, float]  # mean, median, std_dev, etc.


def _build_candidate_state(
    budget: Dict[int, float],
    prestige: int,
    initial_state: UpgradeState,
    *,
    rng: random.Random,
    epsilon_greedy: float = 0.0,
) -> UpgradeState:
    """
    Generate a candidate upgrade state by buying upgrades until budget is exhausted.

    This function is *fast* (no simulation) and only constructs a feasible state.
    """
    state = initial_state.copy()
    remaining = {tier: float(budget[tier]) for tier in range(1, 5)}

    # Available upgrades (unlocked at this prestige)
    available_upgrades = []
    for tier in range(1, 5):
        for idx in range(len(COSTS[tier])):
            if is_upgrade_unlocked(tier, idx, prestige):
                available_upgrades.append((tier, idx))

    # A lightweight priority table (same ordering intent as greedy optimizer).
    # This is used only to bias sampling; it does not guarantee optimality.
    tier_priority_score = {
        1: {0: 100, 9: 95, 6: 90, 1: 80, 2: 70, 4: 65, 3: 60, 5: 50, 7: 40, 8: 30},
        2: {2: 100, 0: 90, 1: 85, 4: 80, 3: 70, 5: 50, 6: 40},
        3: {0: 100, 4: 95, 7: 90, 1: 85, 3: 80, 2: 60, 6: 50, 5: 40},
        4: {4: 100, 7: 95, 1: 90, 3: 85, 0: 80, 2: 70, 5: 50, 6: 40},
    }

    max_iterations = 2000
    for _ in range(max_iterations):
        affordable = []
        for tier, idx in available_upgrades:
            current_level = state.get_level(tier, idx)
            max_level = get_max_level_with_caps(tier, idx, state)
            if current_level >= max_level:
                continue

            base_cost = COSTS[tier][idx]
            next_cost = round(base_cost * (1.25 ** current_level))
            if next_cost <= remaining[tier]:
                # Bias: higher priority and better cost efficiency.
                prio = float(tier_priority_score.get(tier, {}).get(idx, 10))
                eff = prio / (float(next_cost) + 1.0) ** 0.35
                affordable.append((tier, idx, next_cost, eff))

        if not affordable:
            break

        if epsilon_greedy > 0.0 and rng.random() >= epsilon_greedy:
            # Greedy step: pick best score.
            tier, idx, cost, _ = max(affordable, key=lambda x: x[3])
        else:
            # Exploratory step: weighted pick by score.
            weights = [max(1e-6, a[3]) for a in affordable]
            tier, idx, cost, _ = rng.choices(affordable, weights=weights, k=1)[0]

        state.set_level(tier, idx, state.get_level(tier, idx) + 1)
        remaining[tier] -= float(cost)

    return state


def _evaluate_state_serial(
    state: UpgradeState,
    prestige: int,
    *,
    runs: int,
    seed: int,
) -> Tuple[float, float]:
    """
    Evaluate a candidate state using Monte Carlo simulation (serial fallback).
    """
    import random as _random

    _random.seed(int(seed) & 0x7FFFFFFF)
    player, enemy = calculate_player_stats(state, prestige)
    _res, avg_wave, avg_time = run_full_simulation(player, enemy, runs=max(1, int(runs)))
    return float(avg_wave), float(avg_time)


def monte_carlo_optimize_guided(
    budget: Dict[int, float],
    prestige: int,
    initial_state: Optional[UpgradeState] = None,
    num_runs: int = 2000,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    event_runs_per_combination: int = 5,
    *,
    seed_base: Optional[int] = None,
) -> MCOptimizationResult:
    """
    Guided single-core Monte Carlo optimization (no multiprocessing, no 2-phase refinement).

    Differences vs old MC:
    - Uses the same biased/epsilon-greedy candidate generation as the parallel optimizer.
    - Includes a greedy seed candidate.

    Differences vs new parallel MC:
    - Evaluates *all* candidates with the full `event_runs_per_combination` (no screen+refine).
    - Runs serially (single-core), but is deterministic if `seed_base` is provided.
    """
    import time

    if initial_state is None:
        initial_state = UpgradeState()

    n_candidates = max(1, int(num_runs))
    runs = max(1, int(event_runs_per_combination))

    seed_base_local = int(seed_base) & 0x7FFFFFFF if seed_base is not None else (int(time.time() * 1000) & 0x7FFFFFFF)

    candidates: List[UpgradeState] = []
    try:
        from .optimizer import greedy_optimize

        greedy_res = greedy_optimize(budget=budget, prestige=prestige, initial_state=initial_state)
        candidates.append(greedy_res.upgrades.copy())
    except Exception:
        pass

    for i in range(n_candidates):
        rng = random.Random(seed_base_local + i)
        eps = 0.20 if (i % 5 != 0) else 1.0
        candidates.append(
            _build_candidate_state(
                budget,
                prestige,
                initial_state,
                rng=rng,
                epsilon_greedy=eps,
            )
        )

    all_results: List[Tuple[UpgradeState, float, float]] = []
    best_state = None
    best_wave = -1.0
    best_time = float("inf")

    for idx, cand in enumerate(candidates, start=1):
        wave, t = _evaluate_state_serial(cand, prestige, runs=runs, seed=seed_base_local + 10_000 + idx)
        all_results.append((cand, wave, t))

        if wave > best_wave or (wave == best_wave and t < best_time):
            best_wave = wave
            best_time = t
            best_state = cand.copy()

        if progress_callback:
            try:
                progress_callback(idx, len(candidates), wave, best_wave)
            except Exception:
                pass

    waves = [r[1] for r in all_results]
    times = [r[2] for r in all_results]

    waves_sorted = sorted(waves)
    times_sorted = sorted(times)
    n = len(waves)

    mean_wave = sum(waves) / n if n > 0 else 0.0
    mean_time = sum(times) / n if n > 0 else 0.0

    if n > 1:
        wave_variance = sum((w - mean_wave) ** 2 for w in waves) / (n - 1)
        time_variance = sum((t - mean_time) ** 2 for t in times) / (n - 1)
        std_dev_wave = math.sqrt(wave_variance)
        std_dev_time = math.sqrt(time_variance)
    else:
        std_dev_wave = 0.0
        std_dev_time = 0.0

    median_wave = waves_sorted[n // 2] if n > 0 else 0.0
    median_time = times_sorted[n // 2] if n > 0 else 0.0
    p5_wave = waves_sorted[int(n * 0.05)] if n > 0 else 0.0
    p95_wave = waves_sorted[int(n * 0.95)] if n > 0 else 0.0

    best_state = best_state or initial_state

    # Calculate materials spent for best_state
    materials_spent = {tier: 0.0 for tier in range(1, 5)}
    materials_remaining = {tier: float(budget[tier]) for tier in range(1, 5)}

    for tier in range(1, 5):
        for uidx in range(len(COSTS[tier])):
            initial_level = initial_state.get_level(tier, uidx)
            final_level = best_state.get_level(tier, uidx)
            for level in range(initial_level, final_level):
                cost = round(COSTS[tier][uidx] * (1.25 ** level))
                materials_spent[tier] += cost
                materials_remaining[tier] -= cost

    player, enemy = calculate_player_stats(best_state, prestige)

    statistics = {
        "mean_wave": float(mean_wave),
        "median_wave": float(median_wave),
        "std_dev_wave": float(std_dev_wave),
        "min_wave": float(min(waves) if waves else 0.0),
        "max_wave": float(max(waves) if waves else 0.0),
        "p5_wave": float(p5_wave),
        "p95_wave": float(p95_wave),
        "mean_time": float(mean_time),
        "median_time": float(median_time),
        "std_dev_time": float(std_dev_time),
    }

    return MCOptimizationResult(
        best_state=best_state,
        best_wave=float(best_wave),
        best_time=float(best_time),
        materials_spent=materials_spent,
        materials_remaining=materials_remaining,
        player_stats=player,
        enemy_stats=enemy,
        all_results=all_results,
        statistics=statistics,
    )


def monte_carlo_optimize_parallel(
    budget: Dict[int, float],
    prestige: int,
    initial_state: Optional[UpgradeState] = None,
    num_runs: int = 2000,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    event_runs_per_combination: int = 5,
    *,
    screening_runs_per_combination: Optional[int] = None,
    top_k_ratio: float = 0.20,
    seed_base: Optional[int] = None,
) -> MCOptimizationResult:
    """
    Best-quality Monte Carlo optimization using a parallel, two-phase approach.

    Phase 1 (screening):
      - Generate `num_runs` candidate states cheaply (no simulation).
      - Evaluate each with a small number of event runs (low variance, fast).

    Phase 2 (refinement):
      - Re-evaluate only the top-K candidates with the full `event_runs_per_combination`.

    Notes:
    - Uses `ProcessPoolExecutor` (multi-core) when available; falls back to serial evaluation.
    - Candidate generation is "epsilon-greedy" biased (more signal than pure random).
    """
    import os
    import time
    from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

    if initial_state is None:
        initial_state = UpgradeState()

    n_candidates = max(1, int(num_runs))
    final_runs = max(1, int(event_runs_per_combination))
    screening_runs = (
        max(1, int(screening_runs_per_combination))
        if screening_runs_per_combination is not None
        else max(1, min(3, final_runs))
    )

    # Build candidate pool (include a strong deterministic seed).
    candidates: List[UpgradeState] = []
    try:
        from .optimizer import greedy_optimize

        greedy_res = greedy_optimize(budget=budget, prestige=prestige, initial_state=initial_state)
        candidates.append(greedy_res.upgrades.copy())
    except Exception:
        # If greedy fails for any reason, continue with stochastic candidates.
        pass

    seed_base_local = int(seed_base) & 0x7FFFFFFF if seed_base is not None else (int(time.time() * 1000) & 0x7FFFFFFF)
    for i in range(n_candidates):
        rng = random.Random(seed_base_local + i)
        # Mix exploration and exploitation.
        eps = 0.20 if (i % 5 != 0) else 1.0  # 80% of candidates are epsilon-greedy, 20% pure random
        candidates.append(
            _build_candidate_state(
                budget,
                prestige,
                initial_state,
                rng=rng,
                epsilon_greedy=eps,
            )
        )

    # Helper: submit payload for pickling
    def _payload(s: UpgradeState) -> Tuple[Dict[int, List[int]], List[int]]:
        levels = {tier: s.levels[tier].copy() for tier in range(1, 5)}
        return levels, s.gem_levels.copy()

    # Phase 1: screening evaluation (parallel if possible)
    all_results: List[Tuple[UpgradeState, float, float]] = []

    def _update_progress(done: int, total: int, current_wave: float, best_wave: float) -> None:
        if progress_callback:
            try:
                progress_callback(done, total, current_wave, best_wave)
            except Exception:
                pass

    best_wave_screen = -1.0
    best_time_screen = float("inf")
    best_state_screen = None

    screening_scores: List[Tuple[int, float, float]] = []  # (idx, wave, time)

    max_workers = os.cpu_count() or 1
    max_pending = max(2, max_workers * 2)

    # Try process pool; fallback to serial if something goes wrong (Windows spawn edge cases).
    use_parallel = True
    try:
        from .mc_parallel import run_event_sims_summary
    except Exception:
        use_parallel = False
        run_event_sims_summary = None  # type: ignore[assignment]

    if use_parallel:
        executor = ProcessPoolExecutor(max_workers=max_workers)
        executor_shutdown = False

        def _shutdown_executor(cancel_futures: bool) -> None:
            nonlocal executor_shutdown
            if executor_shutdown:
                return
            try:
                executor.shutdown(wait=False, cancel_futures=cancel_futures)
            except TypeError:
                executor.shutdown(wait=False)
            except Exception:
                pass
            executor_shutdown = True

        pending: Dict[Any, int] = {}
        completed = 0
        try:
            for idx, cand in enumerate(candidates):
                levels, gem_levels = _payload(cand)
                fut = executor.submit(
                    run_event_sims_summary,  # type: ignore[misc]
                    levels=levels,
                    gem_levels=gem_levels,
                    prestige=prestige,
                    runs=screening_runs,
                    seed=seed_base_local + idx,
                )
                pending[fut] = idx

                if len(pending) >= max_pending:
                    done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                    for f in done:
                        cand_idx = pending.pop(f, None)
                        if cand_idx is None:
                            continue
                        completed += 1
                        try:
                            out = f.result()
                            wave = float(out.get("avg_wave", 0.0))
                            t = float(out.get("avg_time", 0.0))
                        except Exception:
                            continue

                        screening_scores.append((cand_idx, wave, t))
                        all_results.append((candidates[cand_idx], wave, t))

                        if wave > best_wave_screen or (wave == best_wave_screen and t < best_time_screen):
                            best_wave_screen = wave
                            best_time_screen = t
                            best_state_screen = candidates[cand_idx].copy()

                        _update_progress(completed, len(candidates), wave, best_wave_screen)

            while pending:
                done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                for f in done:
                    cand_idx = pending.pop(f, None)
                    if cand_idx is None:
                        continue
                    completed += 1
                    try:
                        out = f.result()
                        wave = float(out.get("avg_wave", 0.0))
                        t = float(out.get("avg_time", 0.0))
                    except Exception:
                        continue

                    screening_scores.append((cand_idx, wave, t))
                    all_results.append((candidates[cand_idx], wave, t))

                    if wave > best_wave_screen or (wave == best_wave_screen and t < best_time_screen):
                        best_wave_screen = wave
                        best_time_screen = t
                        best_state_screen = candidates[cand_idx].copy()

                    _update_progress(completed, len(candidates), wave, best_wave_screen)
        finally:
            _shutdown_executor(cancel_futures=False)
    else:
        for idx, cand in enumerate(candidates):
            wave, t = _evaluate_state_serial(cand, prestige, runs=screening_runs, seed=seed_base + idx)
            screening_scores.append((idx, wave, t))
            all_results.append((cand, wave, t))
            if wave > best_wave_screen or (wave == best_wave_screen and t < best_time_screen):
                best_wave_screen = wave
                best_time_screen = t
                best_state_screen = cand.copy()
            _update_progress(idx + 1, len(candidates), wave, best_wave_screen)

    # Phase 2: refine top K with more runs
    if not screening_scores:
        # Total failure; fall back to the initial state.
        best_state = initial_state
        best_wave = 0.0
        best_time = 0.0
    else:
        screening_scores.sort(key=lambda x: (-x[1], x[2]))  # wave desc, time asc
        top_k = max(10, int(len(screening_scores) * float(top_k_ratio)))
        top_k = min(top_k, len(screening_scores))
        top_indices = [idx for idx, _w, _t in screening_scores[:top_k]]

        best_state = best_state_screen or candidates[top_indices[0]].copy()
        best_wave = -1.0
        best_time = float("inf")

        if use_parallel:
            # Re-open a new pool for refinement (simpler lifetime management)
            from .mc_parallel import run_event_sims_summary  # type: ignore[no-redef]

            executor = ProcessPoolExecutor(max_workers=max_workers)
            executor_shutdown = False

            def _shutdown_executor(cancel_futures: bool) -> None:
                nonlocal executor_shutdown
                if executor_shutdown:
                    return
                try:
                    executor.shutdown(wait=False, cancel_futures=cancel_futures)
                except TypeError:
                    executor.shutdown(wait=False)
                except Exception:
                    pass
                executor_shutdown = True

            pending: Dict[Any, int] = {}
            completed = 0
            try:
                for j, cand_idx in enumerate(top_indices):
                    cand = candidates[cand_idx]
                    levels, gem_levels = _payload(cand)
                    fut = executor.submit(
                        run_event_sims_summary,
                        levels=levels,
                        gem_levels=gem_levels,
                        prestige=prestige,
                        runs=final_runs,
                        seed=seed_base_local + 10_000 + j,
                    )
                    pending[fut] = cand_idx

                    if len(pending) >= max_pending:
                        done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                        for f in done:
                            idx2 = pending.pop(f, None)
                            if idx2 is None:
                                continue
                            completed += 1
                            try:
                                out = f.result()
                                wave = float(out.get("avg_wave", 0.0))
                                t = float(out.get("avg_time", 0.0))
                            except Exception:
                                continue

                            if wave > best_wave or (wave == best_wave and t < best_time):
                                best_wave = wave
                                best_time = t
                                best_state = candidates[idx2].copy()

                            _update_progress(completed, top_k, wave, best_wave)

                while pending:
                    done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                    for f in done:
                        idx2 = pending.pop(f, None)
                        if idx2 is None:
                            continue
                        completed += 1
                        try:
                            out = f.result()
                            wave = float(out.get("avg_wave", 0.0))
                            t = float(out.get("avg_time", 0.0))
                        except Exception:
                            continue

                        if wave > best_wave or (wave == best_wave and t < best_time):
                            best_wave = wave
                            best_time = t
                            best_state = candidates[idx2].copy()

                        _update_progress(completed, top_k, wave, best_wave)
            finally:
                _shutdown_executor(cancel_futures=False)
        else:
            for j, cand_idx in enumerate(top_indices):
                cand = candidates[cand_idx]
                wave, t = _evaluate_state_serial(cand, prestige, runs=final_runs, seed=seed_base_local + 10_000 + j)
                if wave > best_wave or (wave == best_wave and t < best_time):
                    best_wave = wave
                    best_time = t
                    best_state = cand.copy()
                _update_progress(j + 1, top_k, wave, best_wave)

    # Compute summary stats from screening results (stable, lots of samples)
    waves = [w for _idx, w, _t in screening_scores]
    times = [t for _idx, _w, t in screening_scores]
    waves_sorted = sorted(waves)
    times_sorted = sorted(times)
    n = len(waves_sorted)

    mean_wave = sum(waves) / n if n > 0 else 0.0
    mean_time = sum(times) / n if n > 0 else 0.0

    if n > 1:
        wave_variance = sum((w - mean_wave) ** 2 for w in waves) / (n - 1)
        time_variance = sum((t - mean_time) ** 2 for t in times) / (n - 1)
        std_dev_wave = math.sqrt(wave_variance)
        std_dev_time = math.sqrt(time_variance)
    else:
        std_dev_wave = 0.0
        std_dev_time = 0.0

    median_wave = waves_sorted[n // 2] if n > 0 else 0.0
    median_time = times_sorted[n // 2] if n > 0 else 0.0
    p5_wave = waves_sorted[int(n * 0.05)] if n > 0 else 0.0
    p95_wave = waves_sorted[int(n * 0.95)] if n > 0 else 0.0

    # Calculate materials spent for best_state
    materials_spent = {tier: 0.0 for tier in range(1, 5)}
    materials_remaining = {tier: float(budget[tier]) for tier in range(1, 5)}

    for tier in range(1, 5):
        for idx in range(len(COSTS[tier])):
            initial_level = initial_state.get_level(tier, idx)
            final_level = best_state.get_level(tier, idx)
            for level in range(initial_level, final_level):
                cost = round(COSTS[tier][idx] * (1.25 ** level))
                materials_spent[tier] += cost
                materials_remaining[tier] -= cost

    player, enemy = calculate_player_stats(best_state, prestige)

    statistics = {
        "mean_wave": float(mean_wave),
        "median_wave": float(median_wave),
        "std_dev_wave": float(std_dev_wave),
        "min_wave": float(min(waves) if waves else 0.0),
        "max_wave": float(max(waves) if waves else 0.0),
        "p5_wave": float(p5_wave),
        "p95_wave": float(p95_wave),
        "mean_time": float(mean_time),
        "median_time": float(median_time),
        "std_dev_time": float(std_dev_time),
    }

    return MCOptimizationResult(
        best_state=best_state,
        best_wave=float(best_wave),
        best_time=float(best_time),
        materials_spent=materials_spent,
        materials_remaining=materials_remaining,
        player_stats=player,
        enemy_stats=enemy,
        all_results=all_results,
        statistics=statistics,
    )


def generate_random_upgrade_sequence(
    budget: Dict[int, float],
    prestige: int,
    initial_state: UpgradeState,
    event_runs: int = 5
) -> Tuple[UpgradeState, float, float]:
    """Generate a random upgrade sequence and simulate it"""
    """
    Generate a random upgrade sequence and simulate it.
    
    Args:
        budget: Available materials per tier
        prestige: Current prestige level
        initial_state: Starting upgrade state
    
    Returns:
        (final_state, reached_wave, run_time)
    """
    state = initial_state.copy()
    remaining = {tier: budget[tier] for tier in range(1, 5)}
    
    # Collect all available upgrades
    available_upgrades = []
    for tier in range(1, 5):
        for idx in range(len(COSTS[tier])):
            if is_upgrade_unlocked(tier, idx, prestige):
                available_upgrades.append((tier, idx))
    
    # Randomly buy upgrades until budget exhausted
    max_iterations = 1000
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Filter upgrades we can afford and haven't maxed
        affordable = []
        for tier, idx in available_upgrades:
            current_level = state.get_level(tier, idx)
            max_level = get_max_level_with_caps(tier, idx, state)
            
            if current_level >= max_level:
                continue
            
            base_cost = COSTS[tier][idx]
            next_cost = round(base_cost * (1.25 ** current_level))
            
            if next_cost <= remaining[tier]:
                affordable.append((tier, idx, next_cost))
        
        if not affordable:
            break  # Can't afford anything
        
        # Randomly select one upgrade to buy
        tier, idx, cost = random.choice(affordable)
        
        # Buy it
        current_level = state.get_level(tier, idx)
        state.set_level(tier, idx, current_level + 1)
        remaining[tier] -= cost
    
    # Simulate the final state (fewer runs for speed - events have less variance)
    try:
        player, enemy = calculate_player_stats(state, prestige)
        # Events have less variance (only block/crit RNG), so fewer sims needed
        sim_results, avg_wave, avg_time = run_full_simulation(player, enemy, runs=event_runs)
    except Exception as e:
        # Fallback if simulation fails
        print(f"Warning: Simulation failed in generate_random_upgrade_sequence: {e}")
        avg_wave = 0.0
        avg_time = 0.0
    
    return state, avg_wave, avg_time


def monte_carlo_optimize(
    budget: Dict[int, float],
    prestige: int,
    initial_state: Optional[UpgradeState] = None,
    num_runs: int = 1000,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    event_runs_per_combination: int = 5,
    seed: Optional[int] = None,
) -> MCOptimizationResult:
    """
    Monte Carlo optimization: test random upgrade sequences and find the best.
    
    Args:
        budget: Available materials per tier
        prestige: Current prestige level
        initial_state: Starting upgrade state
        num_runs: Number of random sequences to test
        progress_callback: Optional callback(current_run, total_runs, current_wave, best_wave)
    
    Returns:
        MCOptimizationResult with best state and statistics
    """
    if seed is not None:
        random.seed(int(seed) & 0x7FFFFFFF)
    if initial_state is None:
        initial_state = UpgradeState()
    
    all_results = []
    best_state = None
    best_wave = -1
    best_time = float('inf')
    
    for run_num in range(1, num_runs + 1):
        # Generate random sequence and simulate
        try:
            state, wave, time = generate_random_upgrade_sequence(
                budget, prestige, initial_state, event_runs_per_combination
            )
        except Exception as e:
            print(f"Error in generate_random_upgrade_sequence (run {run_num}): {e}")
            import traceback
            traceback.print_exc()
            # Skip this run and continue
            continue
        
        all_results.append((state, wave, time))
        
        # Track best result
        if wave > best_wave or (wave == best_wave and time < best_time):
            best_wave = wave
            best_time = time
            best_state = state.copy()
        
        # Update progress (call from main thread if callback provided)
        if progress_callback:
            try:
                progress_callback(run_num, num_runs, wave, best_wave)
            except Exception as e:
                print(f"Error in progress_callback: {e}")
                pass  # Ignore callback errors
    
    # Calculate statistics
    waves = [r[1] for r in all_results]
    times = [r[2] for r in all_results]
    
    waves_sorted = sorted(waves)
    times_sorted = sorted(times)
    n = len(waves)
    
    # Calculate mean
    mean_wave = sum(waves) / n if n > 0 else 0
    mean_time = sum(times) / n if n > 0 else 0
    
    # Calculate std dev
    if n > 1:
        wave_variance = sum((w - mean_wave) ** 2 for w in waves) / (n - 1)
        time_variance = sum((t - mean_time) ** 2 for t in times) / (n - 1)
        std_dev_wave = math.sqrt(wave_variance)
        std_dev_time = math.sqrt(time_variance)
    else:
        std_dev_wave = 0
        std_dev_time = 0
    
    # Calculate percentiles
    median_wave = waves_sorted[n // 2] if n > 0 else 0
    median_time = times_sorted[n // 2] if n > 0 else 0
    p5_wave = waves_sorted[int(n * 0.05)] if n > 0 else 0
    p95_wave = waves_sorted[int(n * 0.95)] if n > 0 else 0
    
    # Calculate materials spent for best state
    materials_spent = {tier: 0.0 for tier in range(1, 5)}
    materials_remaining = {tier: budget[tier] for tier in range(1, 5)}
    
    if best_state:
        for tier in range(1, 5):
            for idx in range(len(COSTS[tier])):
                initial_level = initial_state.get_level(tier, idx)
                final_level = best_state.get_level(tier, idx)
                
                for level in range(initial_level, final_level):
                    cost = round(COSTS[tier][idx] * (1.25 ** level))
                    materials_spent[tier] += cost
                    materials_remaining[tier] -= cost
    
    # Get final stats
    if best_state:
        player, enemy = calculate_player_stats(best_state, prestige)
    else:
        player, enemy = PlayerStats(), EnemyStats()
    
    statistics = {
        'mean_wave': mean_wave,
        'median_wave': median_wave,
        'std_dev_wave': std_dev_wave,
        'min_wave': min(waves) if waves else 0,
        'max_wave': max(waves) if waves else 0,
        'p5_wave': p5_wave,
        'p95_wave': p95_wave,
        'mean_time': mean_time,
        'median_time': median_time,
        'std_dev_time': std_dev_time,
    }
    
    return MCOptimizationResult(
        best_state=best_state or initial_state,
        best_wave=best_wave,
        best_time=best_time,
        materials_spent=materials_spent,
        materials_remaining=materials_remaining,
        player_stats=player,
        enemy_stats=enemy,
        all_results=all_results,
        statistics=statistics
    )
