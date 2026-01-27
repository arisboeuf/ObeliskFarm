"""
DOE experiment runner for Archaeology simulation (Arch-Sim).

Proposal implemented:
- Stage 1: 3-level full factorial screening on coded variables (-1, 0, +1)
- Stage 2: RSM refinement by fitting a quadratic model and taking a local
  stationary-point step (with bounds) + a small axial validation design.

This is intentionally dependency-light (no numpy/scipy) so it can run in the
same environment as the calculator.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .headless import ArchBuild, HeadlessArchaeologySimulator


SKILLS = ("strength", "agility", "perception", "intellect", "luck")


@dataclass(frozen=True)
class Factor:
    """A single coded factor \(x in [-1, 1]\) with a step size."""

    name: str
    # We use symmetric coding: x=-1,0,+1 maps to -step,0,+step in the factor space.
    step: float


def _softmax(xs: Sequence[float]) -> List[float]:
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


def _round_to_sum(values: Sequence[float], total: int) -> List[int]:
    """
    Largest remainder method to round floats to integers that sum to `total`.
    """
    floors = [int(math.floor(v)) for v in values]
    missing = total - sum(floors)
    if missing == 0:
        return floors
    remainders = [(values[i] - floors[i], i) for i in range(len(values))]
    remainders.sort(reverse=True)
    out = floors[:]
    for _, idx in remainders[: max(0, missing)]:
        out[idx] += 1
    return out


def allocate_skill_points_simplex(
    *,
    total_points: int,
    base_skill_points: Dict[str, int],
    deltas: Dict[str, float],
) -> Dict[str, int]:
    """
    Convert continuous DOE variables into a valid skill point allocation.

    We model 4 independent "log-weight deltas" for skills (luck is the reference).
    Then we softmax to probabilities and allocate `total_points` exactly.
    """
    total_points = int(total_points)
    eps = 1e-6
    base = {s: max(eps, float(base_skill_points.get(s, 0))) for s in SKILLS}

    # Use luck as reference (logit 0). Others get baseline log-odds + delta.
    ref = math.log(base["luck"])
    logits: Dict[str, float] = {"luck": 0.0}
    for s in ("strength", "agility", "perception", "intellect"):
        logits[s] = (math.log(base[s]) - ref) + float(deltas.get(s, 0.0))

    probs = _softmax([logits[s] for s in SKILLS])
    raw = [p * total_points for p in probs]
    alloc = _round_to_sum(raw, total_points)
    return {SKILLS[i]: int(alloc[i]) for i in range(len(SKILLS))}


def full_factorial_3level(num_factors: int) -> List[List[float]]:
    """
    3-level full factorial design in coded space: {-1, 0, +1}^k.
    """
    levels = (-1.0, 0.0, 1.0)
    design: List[List[float]] = [[]]
    for _ in range(num_factors):
        design = [row + [lvl] for row in design for lvl in levels]
    return design


def _design_row_to_deltas(factors: Sequence[Factor], x: Sequence[float]) -> Dict[str, float]:
    return {factors[i].name: float(x[i]) * factors[i].step for i in range(len(factors))}


def _quadratic_terms(x: Sequence[float]) -> List[float]:
    """
    Quadratic model basis:
    [1,
     x1..xk,
     x1^2..xk^2,
     x1*x2, x1*x3, ...]
    """
    k = len(x)
    terms = [1.0]
    terms.extend(float(v) for v in x)
    terms.extend(float(v) * float(v) for v in x)
    for i in range(k):
        for j in range(i + 1, k):
            terms.append(float(x[i]) * float(x[j]))
    return terms


def _solve_linear_system(a: List[List[float]], b: List[float]) -> List[float]:
    """
    Solve A x = b by Gauss-Jordan elimination (dense, small systems).
    """
    n = len(a)
    # Build augmented matrix
    m = [row[:] + [b[i]] for i, row in enumerate(a)]

    for col in range(n):
        # Pivot
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("Singular system")
        m[col], m[pivot] = m[pivot], m[col]

        # Normalize row
        div = m[col][col]
        for c in range(col, n + 1):
            m[col][c] /= div

        # Eliminate
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col]
            if factor == 0:
                continue
            for c in range(col, n + 1):
                m[r][c] -= factor * m[col][c]

    return [m[i][n] for i in range(n)]


def fit_quadratic(xs: Sequence[Sequence[float]], ys: Sequence[float]) -> List[float]:
    """
    Least-squares fit of quadratic model coefficients using normal equations.
    """
    if not xs:
        raise ValueError("No samples")
    phi0 = _quadratic_terms(xs[0])
    p = len(phi0)
    # Compute normal equations: (X^T X) beta = X^T y
    xtx = [[0.0 for _ in range(p)] for _ in range(p)]
    xty = [0.0 for _ in range(p)]

    for x, y in zip(xs, ys):
        phi = _quadratic_terms(x)
        for i in range(p):
            xty[i] += phi[i] * float(y)
            for j in range(p):
                xtx[i][j] += phi[i] * phi[j]

    return _solve_linear_system(xtx, xty)


def predict_quadratic(beta: Sequence[float], x: Sequence[float]) -> float:
    phi = _quadratic_terms(x)
    return float(sum(beta[i] * phi[i] for i in range(len(beta))))


def stationary_point(beta: Sequence[float], k: int) -> Optional[List[float]]:
    """
    Compute the stationary point of the fitted quadratic (in coded space).

    Model is:
      y = b0 + sum(bi xi) + sum(bii xi^2) + sum(bij xi xj)
    Gradient:
      dy/dxi = bi + 2*bii*xi + sum_{j!=i} bij*xj
    """
    # beta layout: [b0, b1..bk, b11..bkk, b12, b13, ...]
    b_lin = list(beta[1 : 1 + k])
    b_sq = list(beta[1 + k : 1 + 2 * k])

    # Build symmetric matrix for quadratic interactions
    b_int = [[0.0 for _ in range(k)] for _ in range(k)]
    idx = 1 + 2 * k
    for i in range(k):
        for j in range(i + 1, k):
            bij = float(beta[idx])
            b_int[i][j] = bij
            b_int[j][i] = bij
            idx += 1

    # Linear system: (2*diag(b_sq) + b_int) x = -b_lin
    a = [[0.0 for _ in range(k)] for _ in range(k)]
    for i in range(k):
        for j in range(k):
            a[i][j] = b_int[i][j]
        a[i][i] += 2.0 * b_sq[i]

    try:
        x = _solve_linear_system(a, [-v for v in b_lin])
        return [float(v) for v in x]
    except ValueError:
        return None


def clamp_box(x: Sequence[float], lo: float = -1.0, hi: float = 1.0) -> List[float]:
    return [max(lo, min(hi, float(v))) for v in x]


def run_two_stage_doe(
    *,
    build_base: ArchBuild,
    total_points: int,
    base_skill_points: Dict[str, int],
    factors: Sequence[Factor],
    center_reps: int = 3,
    axial_step: float = 0.5,
    seed: int = 0,
    out_csv: Optional[Path] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_cb: Optional[Callable[[], bool]] = None,
) -> Dict[str, object]:
    """
    Execute:
    - Full factorial (3-level) on coded space
    - Quadratic fit + stationary point
    - Axial refinement around the stationary point (validation & refit)
    """
    rng = random.Random(seed)

    # Total evaluations for progress reporting
    design1 = full_factorial_3level(len(factors))
    refine_count = 1 + 2 * len(factors) + 6  # center + axial +/- for each factor + jitter points
    total_evals = len(design1) + max(0, int(center_reps)) + refine_count
    eval_idx = 0

    def _tick(phase: str) -> None:
        nonlocal eval_idx
        eval_idx += 1
        if progress_cb is not None:
            progress_cb(eval_idx, total_evals, phase)

    def eval_at(x_coded: Sequence[float]) -> float:
        if cancel_cb is not None and cancel_cb():
            raise RuntimeError("Cancelled")
        deltas = _design_row_to_deltas(factors, x_coded)
        sp = allocate_skill_points_simplex(
            total_points=total_points,
            base_skill_points=base_skill_points,
            deltas=deltas,
        )
        sim = HeadlessArchaeologySimulator(
            ArchBuild(
                starting_floor=build_base.starting_floor,
                current_stage=build_base.current_stage,
                skill_points=sp,
                gem_upgrades=build_base.gem_upgrades,
                fragment_upgrade_levels=build_base.fragment_upgrade_levels,
                misc_card_level=build_base.misc_card_level,
                block_cards=build_base.block_cards,
                enrage_enabled=build_base.enrage_enabled,
                flurry_enabled=build_base.flurry_enabled,
                quake_enabled=build_base.quake_enabled,
                avada_keda_enabled=build_base.avada_keda_enabled,
                block_bonker_enabled=build_base.block_bonker_enabled,
            )
        )
        return sim.eval_floors_per_run(build_base.starting_floor)

    # Stage 1: screening
    xs: List[List[float]] = []
    ys: List[float] = []

    for row in design1:
        y = eval_at(row)
        _tick("DOE Phase 1: Full factorial (3-level) screening...")
        xs.append(list(row))
        ys.append(float(y))

    # Center reps (pure error estimate, noise check)
    for _ in range(max(0, int(center_reps))):
        row = [0.0 for _ in factors]
        # Random jitter is intentionally NOT used here; center reps should be identical inputs.
        y = eval_at(row)
        _tick("DOE Phase 1: Center repeats...")
        xs.append(row)
        ys.append(float(y))

    beta1 = fit_quadratic(xs, ys)
    x_star = stationary_point(beta1, len(factors))
    if x_star is None:
        # Fallback: pick best observed
        best_idx = max(range(len(ys)), key=lambda i: ys[i])
        x_star = xs[best_idx][:]
    x_star = clamp_box(x_star)

    # Stage 2: local refinement around x_star (axial points + center)
    refine: List[List[float]] = []
    refine.append(x_star[:])
    for i in range(len(factors)):
        xp = x_star[:]
        xm = x_star[:]
        xp[i] = max(-1.0, min(1.0, xp[i] + axial_step))
        xm[i] = max(-1.0, min(1.0, xm[i] - axial_step))
        refine.append(xp)
        refine.append(xm)

    # Add a few random points around x_star to stabilize the fit (small jitter)
    for _ in range(6):
        refine.append(
            [
                max(-1.0, min(1.0, x_star[i] + rng.uniform(-axial_step, axial_step)))
                for i in range(len(factors))
            ]
        )

    for row in refine:
        y = eval_at(row)
        _tick("DOE Phase 2: RSM refinement / validation points...")
        xs.append(list(row))
        ys.append(float(y))

    beta2 = fit_quadratic(xs, ys)
    x_star2 = stationary_point(beta2, len(factors))
    if x_star2 is None:
        best_idx = max(range(len(ys)), key=lambda i: ys[i])
        x_star2 = xs[best_idx][:]
    x_star2 = clamp_box(x_star2)

    # Convert best coded point to actual skill points for reporting
    deltas_best = _design_row_to_deltas(factors, x_star2)
    sp_best = allocate_skill_points_simplex(
        total_points=total_points,
        base_skill_points=base_skill_points,
        deltas=deltas_best,
    )
    best_build = ArchBuild(
        starting_floor=build_base.starting_floor,
        current_stage=build_base.current_stage,
        skill_points=sp_best,
        gem_upgrades=build_base.gem_upgrades,
        fragment_upgrade_levels=build_base.fragment_upgrade_levels,
        misc_card_level=build_base.misc_card_level,
        block_cards=build_base.block_cards,
        enrage_enabled=build_base.enrage_enabled,
        flurry_enabled=build_base.flurry_enabled,
        quake_enabled=build_base.quake_enabled,
        avada_keda_enabled=build_base.avada_keda_enabled,
        block_bonker_enabled=build_base.block_bonker_enabled,
    )
    best_sim = HeadlessArchaeologySimulator(best_build)
    best_y = best_sim.eval_floors_per_run(best_build.starting_floor)

    if out_csv is not None:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([f"x_{fac.name}" for fac in factors] + ["floors_per_run"])
            for row, y in zip(xs, ys):
                w.writerow([f"{v:.6f}" for v in row] + [f"{y:.6f}"])

    return {
        "factors": [f.name for f in factors],
        "x_star_stage1": x_star,
        "x_star_stage2": x_star2,
        "best_skill_points": sp_best,
        "best_floors_per_run": float(best_y),
        "num_evals": len(ys),
    }


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DOE + RSM runner for Arch-Sim (floors/run).")
    p.add_argument("--starting-floor", type=int, default=12, help="Starting floor (stage) for evaluation.")
    p.add_argument("--total-points", type=int, default=50, help="Total skill points to allocate.")
    p.add_argument("--seed", type=int, default=0, help="Random seed for refinement jitter.")
    p.add_argument("--csv", type=str, default="", help="Optional output CSV path.")

    # Baseline skill points (for simplex baseline)
    p.add_argument("--base-str", type=int, default=20)
    p.add_argument("--base-agi", type=int, default=10)
    p.add_argument("--base-per", type=int, default=10)
    p.add_argument("--base-int", type=int, default=5)
    p.add_argument("--base-luc", type=int, default=5)

    # Factor step sizes (log-weight deltas)
    p.add_argument("--step", type=float, default=0.7, help="Delta step size per factor (log-weight space).")
    p.add_argument("--center-reps", type=int, default=3)
    p.add_argument("--axial-step", type=float, default=0.5)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)

    base_skill_points = {
        "strength": args.base_str,
        "agility": args.base_agi,
        "perception": args.base_per,
        "intellect": args.base_int,
        "luck": args.base_luc,
    }

    # Baseline build: keep upgrades/cards off by default (user can extend this script).
    build_base = ArchBuild(
        starting_floor=int(args.starting_floor),
        current_stage=int(args.starting_floor),
        skill_points=base_skill_points,
        gem_upgrades={"stamina": 0, "xp": 0, "fragment": 0, "arch_xp": 0},
        fragment_upgrade_levels={},
        misc_card_level=0,
        block_cards=None,
        enrage_enabled=True,
        flurry_enabled=True,
        quake_enabled=True,
        avada_keda_enabled=False,
        block_bonker_enabled=False,
    )

    factors = [
        Factor("strength", step=float(args.step)),
        Factor("agility", step=float(args.step)),
        Factor("perception", step=float(args.step)),
        Factor("intellect", step=float(args.step)),
        # Luck is the reference skill (implicit); keep factor count at 4 for 81-run screening.
    ]

    out_csv = Path(args.csv) if args.csv else None
    result = run_two_stage_doe(
        build_base=build_base,
        total_points=int(args.total_points),
        base_skill_points=base_skill_points,
        factors=factors,
        center_reps=int(args.center_reps),
        axial_step=float(args.axial_step),
        seed=int(args.seed),
        out_csv=out_csv,
    )

    print("DOE + RSM result (Arch-Sim)")
    print(f"  Evals: {result['num_evals']}")
    print(f"  Best floors/run: {result['best_floors_per_run']:.3f}")
    print("  Best skill points:")
    for k in SKILLS:
        print(f"    {k:10s}: {result['best_skill_points'][k]}")
    if out_csv:
        print(f"  Wrote CSV: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

