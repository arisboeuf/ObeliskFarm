"""
Freebie EV Calculator - Berechnet den Erwartungswert für Freebies
basierend auf den Spielparametern aus der README.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class GameParameters:
    """Spielparameter für die EV-Berechnung"""
    # Basis-Parameter
    freebie_gems_base: float = 9.0
    freebie_timer_minutes: float = 7.0
    
    # Skill Shards
    skill_shard_chance: float = 0.12  # 12%
    skill_shard_value_gems: float = 12.5
    
    # Stonks
    stonks_chance: float = 0.01  # 1%
    stonks_bonus_gems: float = 200.0
    
    # Jackpot
    jackpot_chance: float = 0.05  # 5%
    jackpot_rolls: int = 5
    
    # Refresh
    instant_refresh_chance: float = 0.05  # 5%
    
    # Founder
    founder_drop_interval_minutes: float = 58.0
    founder_gems_base: float = 10.0  # Feste Gems pro Drop
    founder_gems_chance: float = 0.01  # 1/100 Chance auf zusätzliche Gems
    obelisk_level: int = 26  # Obelisk Level für Founder Gem-Berechnung
    founder_speed_multiplier: float = 2.0
    founder_speed_duration_minutes: float = 5.0

    # Founder Bomb
    founder_bomb_interval_seconds: float = 87.0  # 1:27 min
    founder_bomb_charges_per_drop: float = 2.0  # 100% Chance auf 2 Charges
    founder_bomb_free_chance: float = 0.16  # 16% Chance auf free bomb (keine Charge verbraucht)
    founder_bomb_speed_chance: float = 0.10  # 10%
    founder_bomb_speed_multiplier: float = 2.0
    founder_bomb_speed_duration_seconds: float = 10.0


class FreebieEVCalculator:
    """
    Berechnet den Erwartungswert (EV) für Freebies pro Stunde.
    
    Implementiert alle Formeln aus der README:
    - Roll- und Claim-Logik
    - Jackpot-Multiplikator
    - Refresh-Kette
    - Stonks (nur auf erster Roll)
    - Skill Shards
    - Founder-Effekte
    """
    
    def __init__(self, params: GameParameters = None):
        """
        Initialisiert den Calculator mit Spielparametern.
        
        Args:
            params: GameParameters-Objekt. Wenn None, werden Standardwerte verwendet.
        """
        self.params = params or GameParameters()
    
    def calculate_expected_rolls_per_claim(self) -> float:
        """
        Berechnet die erwartete Anzahl Rolls pro Claim.
        
        Returns:
            Erwartete Rolls pro Claim (1.2 bei Standard-Parametern)
        """
        normal_rolls = 1.0
        jackpot_rolls = self.params.jackpot_rolls
        
        expected_rolls = (
            (1 - self.params.jackpot_chance) * normal_rolls +
            self.params.jackpot_chance * jackpot_rolls
        )
        return expected_rolls
    
    def calculate_refresh_multiplier(self) -> float:
        """
        Berechnet den Refresh-Multiplikator (geometrische Reihe).
        
        Returns:
            Erwartete Claims pro Start-Freebie (1.0526 bei Standard-Parametern)
        """
        if self.params.instant_refresh_chance >= 1.0:
            return float('inf')
        return 1.0 / (1.0 - self.params.instant_refresh_chance)
    
    def calculate_total_multiplier(self) -> float:
        """
        Berechnet den Gesamt-Multiplikator aus Jackpot und Refresh.
        
        Returns:
            Gesamt-Multiplikator (1.2632 bei Standard-Parametern)
        """
        jackpot_mult = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        return jackpot_mult * refresh_mult
    
    def calculate_freebies_per_hour(self) -> float:
        """
        Berechnet die Anzahl Freebies pro Stunde (ohne Founder-Speed).
        
        Returns:
            Freebies pro Stunde
        """
        minutes_per_hour = 60.0
        return minutes_per_hour / self.params.freebie_timer_minutes
    
    def calculate_gems_base_per_hour(self) -> float:
        """
        Berechnet Gems (Basis) pro Stunde.
        
        Returns:
            Gems pro Stunde aus Basis-Rolls
        """
        freebies_per_hour = self.calculate_freebies_per_hour()
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        gems_per_hour = (
            freebies_per_hour *
            refresh_mult *
            expected_rolls *
            self.params.freebie_gems_base
        )
        return gems_per_hour
    
    def calculate_stonks_ev_per_hour(self) -> float:
        """
        Berechnet Stonks EV pro Stunde.
        
        Wichtig: Stonks können nur auf der ersten Roll eines Claims auftreten,
        nicht auf Jackpot-Zusatzrolls.
        
        Returns:
            Stonks EV (Gems) pro Stunde
        """
        freebies_per_hour = self.calculate_freebies_per_hour()
        refresh_mult = self.calculate_refresh_multiplier()
        
        # Nur 1 Roll pro Claim kann Stonks triggern
        stonks_ev_per_claim = self.params.stonks_chance * self.params.stonks_bonus_gems
        
        stonks_ev_per_hour = (
            freebies_per_hour *
            refresh_mult *
            stonks_ev_per_claim
        )
        return stonks_ev_per_hour
    
    def calculate_skill_shards_ev_per_hour(self) -> float:
        """
        Berechnet Skill Shards EV pro Stunde (in Gem-Äquivalent).
        
        Returns:
            Skill Shards EV (Gems) pro Stunde
        """
        freebies_per_hour = self.calculate_freebies_per_hour()
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        # Alle Rolls können Skill Shards geben (inkl. Jackpot-Rolls)
        shards_per_roll = self.params.skill_shard_chance
        shard_value = self.params.skill_shard_value_gems
        
        shards_ev_per_hour = (
            freebies_per_hour *
            refresh_mult *
            expected_rolls *
            shards_per_roll *
            shard_value
        )
        return shards_ev_per_hour
    
    def calculate_founder_speed_boost_per_hour(self) -> float:
        """
        Berechnet den Founder Speed Boost pro Stunde (in Gem-Äquivalent).
        
        Der Speed-Effekt spart Zeit, was effektiv mehr Freebies pro Stunde bedeutet.
        
        Returns:
            Founder Speed Boost (Gems) pro Stunde
        """
        # 5 Minuten mit 2× Speed = 2,5 Minuten Zeitersparnis
        time_saved_per_drop = (
            self.params.founder_speed_duration_minutes /
            self.params.founder_speed_multiplier
        )
        
        # Founder Drops pro Stunde
        founder_drops_per_hour = 60.0 / self.params.founder_drop_interval_minutes
        
        # Zeitersparnis pro Stunde (in Minuten)
        time_saved_per_hour = founder_drops_per_hour * time_saved_per_drop
        
        # Effektive Freebie-Stunde: 60 - 2.5 = 57.5 Minuten
        # Das bedeutet mehr Freebies pro Stunde
        effective_minutes_per_hour = 60.0 - time_saved_per_hour
        
        # Zusätzliche Freebies durch Zeitersparnis
        normal_freebies_per_hour = self.calculate_freebies_per_hour()
        effective_freebies_per_hour = 60.0 / (
            self.params.freebie_timer_minutes * (effective_minutes_per_hour / 60.0)
        )
        
        additional_freebies = effective_freebies_per_hour - normal_freebies_per_hour
        
        # Gem-Äquivalent aus zusätzlichen Freebies
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        speed_boost_gems = (
            additional_freebies *
            refresh_mult *
            expected_rolls *
            self.params.freebie_gems_base
        )
        
        return speed_boost_gems
    
    def calculate_founder_gems_per_hour(self) -> float:
        """
        Berechnet Founder Gems pro Stunde.
        
        Founder Drop gibt:
        - Immer: founder_gems_base (10 Gems)
        - 1/100 Chance: 50 + 10 * Obelisk Level Gems
        
        Returns:
            Founder Gems pro Stunde
        """
        founder_drops_per_hour = 60.0 / self.params.founder_drop_interval_minutes
        
        # Feste Gems pro Drop
        base_gems = founder_drops_per_hour * self.params.founder_gems_base
        
        # Zusätzliche Gems durch 1/100 Chance
        bonus_gems_per_drop = 50.0 + 10.0 * self.params.obelisk_level
        bonus_gems = founder_drops_per_hour * self.params.founder_gems_chance * bonus_gems_per_drop
        
        return base_gems + bonus_gems
    
    def calculate_founder_bomb_boost_per_hour(self) -> float:
        """
        Berechnet den Founder Bomb Speed Boost pro Stunde (in Gem-Äquivalent).
        
        Founder Bomb Mechanik:
        - 1 Bomb-Drop alle 87 Sekunden
        - Pro Drop: 2 Charges (100%)
        - Pro Charge: 16% Chance auf "free bomb" (keine Charge verbraucht)
        - Pro Bomb: 10% Chance auf 2× Speed für 10 Sekunden
        
        Der Speed-Effekt spart Zeit, was effektiv mehr Freebies pro Stunde bedeutet.
        
        Returns:
            Founder Bomb Speed Boost (Gems) pro Stunde
        """
        # Founder Bomb Drops pro Stunde
        seconds_per_hour = 3600.0
        founder_bomb_drops_per_hour = seconds_per_hour / self.params.founder_bomb_interval_seconds
        
        # Effektive Bombs pro Charge (durch free bomb chance)
        # 16% Chance, dass Charge nicht verbraucht wird = 1 / (1 - 0.16) = 1.1905 Bombs pro Charge
        effective_bombs_per_charge = 1.0 / (1.0 - self.params.founder_bomb_free_chance)
        
        # Effektive Bombs pro Drop (2 Charges × effektive Bombs pro Charge)
        effective_bombs_per_drop = self.params.founder_bomb_charges_per_drop * effective_bombs_per_charge
        
        # Erwartete Speed-Aktivierungen pro Stunde
        # = Drops pro Stunde × effektive Bombs pro Drop × Speed-Chance
        expected_speed_activations = (
            founder_bomb_drops_per_hour *
            effective_bombs_per_drop *
            self.params.founder_bomb_speed_chance
        )
        
        # Zeitersparnis pro Aktivierung: 10 Sekunden mit 2× Speed = 5 Sekunden Zeitersparnis
        time_saved_per_activation = (
            self.params.founder_bomb_speed_duration_seconds /
            self.params.founder_bomb_speed_multiplier
        )
        
        # Gesamte Zeitersparnis pro Stunde (in Sekunden)
        total_time_saved_seconds = expected_speed_activations * time_saved_per_activation
        
        # Zeitersparnis in Minuten
        total_time_saved_minutes = total_time_saved_seconds / 60.0
        
        # Effektive Freebie-Stunde
        effective_minutes_per_hour = 60.0 - total_time_saved_minutes
        
        # Zusätzliche Freebies durch Zeitersparnis
        normal_freebies_per_hour = self.calculate_freebies_per_hour()
        effective_freebies_per_hour = 60.0 / (
            self.params.freebie_timer_minutes * (effective_minutes_per_hour / 60.0)
        )
        
        additional_freebies = effective_freebies_per_hour - normal_freebies_per_hour
        
        # Gem-Äquivalent aus zusätzlichen Freebies
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        bomb_boost_gems = (
            additional_freebies *
            refresh_mult *
            expected_rolls *
            self.params.freebie_gems_base
        )
        
        return bomb_boost_gems
    
    def calculate_ev_breakdown(self) -> Dict[str, Dict[str, float]]:
        """
        Berechnet die Aufschlüsselung jedes EV-Postens nach Basis, Jackpot und Refresh.
        
        Returns:
            Dictionary mit Aufschlüsselung für jeden Posten
        """
        freebies_per_hour = self.calculate_freebies_per_hour()
        base_rolls = 1.0
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        # Jackpot-Multiplikator (nur für Rolls)
        jackpot_mult = expected_rolls / base_rolls  # z.B. 1.2 / 1.0 = 1.2
        
        breakdown = {}
        
        # Gems Base
        # Basis: ohne Refresh, ohne Jackpot
        base_gems = freebies_per_hour * base_rolls * self.params.freebie_gems_base
        # Jackpot: zusätzliche Rolls ohne Refresh
        jackpot_gems = freebies_per_hour * (expected_rolls - base_rolls) * self.params.freebie_gems_base
        # Refresh auf Basis
        refresh_gems_base = base_gems * (refresh_mult - 1.0)
        # Refresh auf Jackpot
        refresh_gems_jackpot = jackpot_gems * (refresh_mult - 1.0)
        
        breakdown['gems_base'] = {
            'base': base_gems,
            'jackpot': jackpot_gems,
            'refresh_base': refresh_gems_base,
            'refresh_jackpot': refresh_gems_jackpot
        }
        
        # Stonks (nur auf erster Roll, kein Jackpot-Bonus)
        base_stonks = freebies_per_hour * self.params.stonks_chance * self.params.stonks_bonus_gems
        refresh_stonks = base_stonks * (refresh_mult - 1.0)
        
        breakdown['stonks_ev'] = {
            'base': base_stonks,
            'jackpot': 0.0,
            'refresh_base': refresh_stonks,
            'refresh_jackpot': 0.0
        }
        
        # Skill Shards (alle Rolls, inkl. Jackpot)
        base_shards = freebies_per_hour * base_rolls * self.params.skill_shard_chance * self.params.skill_shard_value_gems
        jackpot_shards = freebies_per_hour * (expected_rolls - base_rolls) * self.params.skill_shard_chance * self.params.skill_shard_value_gems
        refresh_shards_base = base_shards * (refresh_mult - 1.0)
        refresh_shards_jackpot = jackpot_shards * (refresh_mult - 1.0)
        
        breakdown['skill_shards_ev'] = {
            'base': base_shards,
            'jackpot': jackpot_shards,
            'refresh_base': refresh_shards_base,
            'refresh_jackpot': refresh_shards_jackpot
        }
        
        # Founder Speed Boost (nur Refresh, kein Jackpot)
        # Vereinfachte Berechnung - Refresh wirkt auf die zusätzlichen Freebies
        founder_speed_base = self.calculate_founder_speed_boost_per_hour() / refresh_mult
        founder_speed_refresh = self.calculate_founder_speed_boost_per_hour() - founder_speed_base
        
        breakdown['founder_speed_boost'] = {
            'base': founder_speed_base,
            'jackpot': 0.0,
            'refresh_base': founder_speed_refresh,
            'refresh_jackpot': 0.0
        }
        
        # Founder Gems (keine Multiplikatoren)
        founder_gems = self.calculate_founder_gems_per_hour()
        breakdown['founder_gems'] = {
            'base': founder_gems,
            'jackpot': 0.0,
            'refresh_base': 0.0,
            'refresh_jackpot': 0.0
        }
        
        # Founder Bomb Boost (nur Refresh, kein Jackpot)
        founder_bomb_base = self.calculate_founder_bomb_boost_per_hour() / refresh_mult
        founder_bomb_refresh = self.calculate_founder_bomb_boost_per_hour() - founder_bomb_base
        
        breakdown['founder_bomb_boost'] = {
            'base': founder_bomb_base,
            'jackpot': 0.0,
            'refresh_base': founder_bomb_refresh,
            'refresh_jackpot': 0.0
        }
        
        return breakdown
    
    def calculate_total_ev_per_hour(self) -> Dict[str, float]:
        """
        Berechnet den Gesamt-EV pro Stunde.
        
        Returns:
            Dictionary mit allen EV-Posten und Gesamtsumme
        """
        gems_base = self.calculate_gems_base_per_hour()
        stonks_ev = self.calculate_stonks_ev_per_hour()
        skill_shards_ev = self.calculate_skill_shards_ev_per_hour()
        founder_speed_boost = self.calculate_founder_speed_boost_per_hour()
        founder_gems = self.calculate_founder_gems_per_hour()
        founder_bomb_boost = self.calculate_founder_bomb_boost_per_hour()
        
        total = (
            gems_base +
            stonks_ev +
            skill_shards_ev +
            founder_speed_boost +
            founder_gems +
            founder_bomb_boost
        )
        
        return {
            'gems_base': gems_base,
            'stonks_ev': stonks_ev,
            'skill_shards_ev': skill_shards_ev,
            'founder_speed_boost': founder_speed_boost,
            'founder_gems': founder_gems,
            'founder_bomb_boost': founder_bomb_boost,
            'total': total
        }
    
    def print_detailed_report(self):
        """
        Gibt einen detaillierten Report aus.
        """
        ev = self.calculate_total_ev_per_hour()
        
        print("=" * 70)
        print("OBELISKGEMEV - DETAILLIERTER REPORT")
        print("=" * 70)
        print()
        
        print("Spielparameter:")
        print(f"  Freebie Gems (Basis): {self.params.freebie_gems_base}")
        print(f"  Freebie Timer: {self.params.freebie_timer_minutes} Minuten")
        print(f"  Skill Shard Chance: {self.params.skill_shard_chance * 100:.1f}%")
        print(f"  Skill Shard Wert: {self.params.skill_shard_value_gems} Gems")
        print(f"  Stonks Chance: {self.params.stonks_chance * 100:.1f}%")
        print(f"  Stonks Bonus: {self.params.stonks_bonus_gems} Gems")
        print(f"  Jackpot Chance: {self.params.jackpot_chance * 100:.1f}%")
        print(f"  Jackpot Rolls: {self.params.jackpot_rolls}")
        print(f"  Instant Refresh Chance: {self.params.instant_refresh_chance * 100:.1f}%")
        print(f"  Founder Drop Intervall: {self.params.founder_drop_interval_minutes} Minuten")
        print(f"  Founder Gems Base: {self.params.founder_gems_base}")
        print(f"  Founder Gems Chance: {self.params.founder_gems_chance * 100:.1f}%")
        print(f"  Obelisk Level: {self.params.obelisk_level}")
        print(f"  Founder Speed: {self.params.founder_speed_multiplier}× für {self.params.founder_speed_duration_minutes} Minuten")
        print(f"  Founder Bomb Intervall: {self.params.founder_bomb_interval_seconds} Sekunden")
        print(f"  Founder Bomb Charges pro Drop: {self.params.founder_bomb_charges_per_drop}")
        print(f"  Founder Bomb Free Chance: {self.params.founder_bomb_free_chance * 100:.1f}%")
        print(f"  Founder Bomb Speed Chance: {self.params.founder_bomb_speed_chance * 100:.1f}%")
        print(f"  Founder Bomb Speed: {self.params.founder_bomb_speed_multiplier}× für {self.params.founder_bomb_speed_duration_seconds} Sekunden")
        print()
        
        print("Multiplikatoren:")
        print(f"  Erwartete Rolls pro Claim: {self.calculate_expected_rolls_per_claim():.4f}")
        print(f"  Refresh-Multiplikator: {self.calculate_refresh_multiplier():.4f}")
        print(f"  Gesamt-Multiplikator: {self.calculate_total_multiplier():.4f}")
        print()
        
        print("EV pro Stunde (Gem-Äquivalent):")
        print(f"  Gems (Basis aus Rolls): {ev['gems_base']:.1f}")
        print(f"  Gems (Stonks EV): {ev['stonks_ev']:.1f}")
        print(f"  Skill Shards (Gem-Äq): {ev['skill_shards_ev']:.1f}")
        print(f"  Founder Speed Boost: {ev['founder_speed_boost']:.1f}")
        print(f"  Founder Gems: {ev['founder_gems']:.1f}")
        print(f"  Founder Bomb Boost: {ev['founder_bomb_boost']:.1f}")
        print(f"  {'─' * 50}")
        print(f"  TOTAL: {ev['total']:.1f} Gems-Äquivalent/h")
        print()
        print("=" * 70)
