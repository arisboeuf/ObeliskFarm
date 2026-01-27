"""
Headless Archaeology simulator helpers.

WHY:
- The main `ArchaeologySimulatorWindow` is GUI-first (Tk) and builds a window
  on init. For DOE experiments we want to reuse the exact same math without
  creating UI objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .simulator import ArchaeologySimulatorWindow


class _BoolVar:
    """Minimal `.get()` compatible stand-in for `tk.BooleanVar`."""

    def __init__(self, value: bool):
        self._value = bool(value)

    def get(self) -> bool:
        return self._value

    def set(self, value: bool) -> None:
        self._value = bool(value)


@dataclass(frozen=True)
class ArchBuild:
    """UI-free build definition for headless evaluation."""

    # Core inputs
    starting_floor: int

    # Skill points
    skill_points: Dict[str, int]

    # Upgrades
    gem_upgrades: Dict[str, int]
    fragment_upgrade_levels: Dict[str, int]

    # Cards and toggles
    misc_card_level: int = 0
    block_cards: Optional[Dict[Tuple[str, int], int]] = None
    enrage_enabled: bool = True
    flurry_enabled: bool = True
    quake_enabled: bool = True
    avada_keda_enabled: bool = False
    block_bonker_enabled: bool = False

    # For Block Bonker bonus computation (depends on "goal stage" semantics)
    # The GUI uses `current_stage` and interprets "Goal Stage N" as optimizing
    # for Stage N-1. For headless runs we keep this explicit and set
    # `current_stage` to `starting_floor` by default.
    current_stage: Optional[int] = None


class HeadlessArchaeologySimulator(ArchaeologySimulatorWindow):
    """
    Reuse `ArchaeologySimulatorWindow` math without creating Tk windows.

    Implementation strategy:
    - Do NOT call the GUI `__init__`.
    - Initialize core state via `reset_to_level1()` (pure-python).
    - Overwrite state with the provided build.
    """

    def __init__(self, build: ArchBuild):
        # Intentionally do not call `super().__init__` (would create a Tk window).
        self.reset_to_level1()

        # Stage / floor context
        self.current_stage = int(build.current_stage or build.starting_floor)

        # Skill points and upgrades
        self.skill_points = {k: int(v) for k, v in build.skill_points.items()}
        self.gem_upgrades = {k: int(v) for k, v in build.gem_upgrades.items()}
        self.fragment_upgrade_levels = {k: int(v) for k, v in build.fragment_upgrade_levels.items()}

        # Cards
        self.misc_card_level = int(build.misc_card_level)
        if build.block_cards is not None:
            # Keep defaults from reset_to_level1, then overlay provided values.
            for key, val in build.block_cards.items():
                self.block_cards[key] = int(val)

        # Toggle vars expected by the calculation code (`.get()` API).
        self.enrage_enabled = _BoolVar(build.enrage_enabled)
        self.flurry_enabled = _BoolVar(build.flurry_enabled)
        self.quake_enabled = _BoolVar(build.quake_enabled)
        self.avada_keda_enabled = _BoolVar(build.avada_keda_enabled)
        self.block_bonker_enabled = _BoolVar(build.block_bonker_enabled)

    def eval_floors_per_run(self, starting_floor: int) -> float:
        stats = self.get_total_stats()
        return float(self.calculate_floors_per_run(stats, starting_floor=starting_floor))

