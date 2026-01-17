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
    vip_lounge_level: int = 2  # VIP Lounge Level (1-7)
    founder_gems_base: float = 10.0  # Feste Gems pro Drop
    founder_gems_chance: float = 0.01  # 1/100 Chance auf zusätzliche Gems
    obelisk_level: int = 26  # Obelisk Level für Founder Gem-Berechnung
    founder_speed_multiplier: float = 2.0
    founder_speed_duration_minutes: float = 5.0
    
    # VIP Lounge berechnet automatisch:
    # - founder_drop_interval_minutes = 60 - 2*(vip_lounge_level-1) Minuten
    # - double_drop_chance = 0.12 + 0.06*(vip_lounge_level-2) (ab Tier 2)
    # - triple_drop_chance = 0.16 wenn vip_lounge_level >= 7

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
    
    def get_founder_drop_interval_minutes(self) -> float:
        """
        Berechnet das Founder Drop Intervall basierend auf VIP Lounge Level.
        
        Returns:
            Intervall in Minuten: 60 - 2*(tier-1)
        """
        return 60.0 - 2.0 * (self.params.vip_lounge_level - 1)
    
    def get_double_drop_chance(self) -> float:
        """
        Berechnet die Double Supply Drop Chance basierend auf VIP Lounge Level.
        
        Returns:
            Double Drop Chance: 12% bei Tier 2, +6% pro Tier
        """
        if self.params.vip_lounge_level < 2:
            return 0.0
        return 0.12 + 0.06 * (self.params.vip_lounge_level - 2)
    
    def get_triple_drop_chance(self) -> float:
        """
        Berechnet die Triple Supply Drop Chance basierend auf VIP Lounge Level.
        
        Returns:
            Triple Drop Chance: 16% bei Tier 7, sonst 0%
        """
        if self.params.vip_lounge_level >= 7:
            return 0.16
        return 0.0
    
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
        
        WICHTIG: Game Speed ist immer 2× (fix).
        Bei Double/Triple Drops verlängert sich nur die Dauer des Speed Boosts:
        - Single Drop: 2× Speed für 5 Minuten
        - Double Drop: 2× Speed für 10 Minuten (2 × 5 Minuten)
        - Triple Drop: 2× Speed für 15 Minuten (3 × 5 Minuten)
        
        Die Zeitersparnis berechnet sich als: (Dauer mit Speed) / Speed_Multiplier
        Bei 2× Speed: Zeitersparnis = Dauer / 2
        
        Returns:
            Founder Speed Boost (Gems) pro Stunde
        """
        # Founder Drops pro Stunde
        founder_drop_interval = self.get_founder_drop_interval_minutes()
        founder_drops_per_hour = 60.0 / founder_drop_interval
        
        # Durchschnittliche Anzahl Drops pro Drop-Event (mit Double/Triple Chance)
        double_chance = self.get_double_drop_chance()
        triple_chance = self.get_triple_drop_chance()
        single_chance = 1.0 - double_chance - triple_chance
        
        # Erwartete Drops pro Event: 1*single + 2*double + 3*triple
        expected_drops_per_event = (
            1.0 * single_chance +
            2.0 * double_chance +
            3.0 * triple_chance
        )
        
        # Erwartete Dauer des Speed Boosts pro Event (in Minuten)
        # Jeder Drop gibt 5 Minuten 2× Speed
        expected_duration_minutes = expected_drops_per_event * self.params.founder_speed_duration_minutes
        
        # Zeitersparnis pro Event: Bei 2× Speed = Dauer / 2
        # (NICHT: Speed wird höher, sondern Dauer verlängert sich)
        time_saved_per_event = expected_duration_minutes / self.params.founder_speed_multiplier
        
        # Zeitersparnis pro Stunde (in Minuten)
        time_saved_per_hour = founder_drops_per_hour * time_saved_per_event
        
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
        - Immer: founder_gems_base (10 Gems) pro Drop
        - 1/100 Chance: 50 + 10 * Obelisk Level Gems pro Drop
        - Berücksichtigt Double/Triple Drops durch VIP Lounge Level
        - 1/1234 Chance: 10 Gifts pro Supply Drop (mit eigenem GemEV)
        
        Returns:
            Founder Gems pro Stunde (inkl. Gift-EV)
        """
        founder_drop_interval = self.get_founder_drop_interval_minutes()
        founder_drops_per_hour = 60.0 / founder_drop_interval
        
        # Durchschnittliche Anzahl Drops pro Drop-Event (mit Double/Triple Chance)
        double_chance = self.get_double_drop_chance()
        triple_chance = self.get_triple_drop_chance()
        single_chance = 1.0 - double_chance - triple_chance
        
        # Erwartete Drops pro Event: 1*single + 2*double + 3*triple
        expected_drops_per_event = (
            1.0 * single_chance +
            2.0 * double_chance +
            3.0 * triple_chance
        )
        
        # Feste Gems pro Drop (pro Drop-Event mit erwarteten Drops)
        base_gems = founder_drops_per_hour * expected_drops_per_event * self.params.founder_gems_base
        
        # Zusätzliche Gems durch 1/100 Chance (pro Drop)
        bonus_gems_per_drop = 50.0 + 10.0 * self.params.obelisk_level
        bonus_gems = founder_drops_per_hour * expected_drops_per_event * self.params.founder_gems_chance * bonus_gems_per_drop
        
        # Gifts: 1/1234 Chance pro Supply Drop (pro Drop-Event)
        gift_chance = 1.0 / 1234.0
        gifts_per_drop = 10.0
        gift_ev_per_gift = self.calculate_gift_ev_per_gift()
        gift_gems = founder_drops_per_hour * gift_chance * gifts_per_drop * gift_ev_per_gift
        
        return base_gems + bonus_gems + gift_gems
    
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
    
    def calculate_obelisk_multiplier(self) -> float:
        """
        Berechnet den Obelisk Multiplier.
        
        Returns:
            Obelisk Multiplier = 1 + Obelisk Level × 0.08
        """
        return 1.0 + self.params.obelisk_level * 0.08
    
    def calculate_lucky_multiplier(self) -> float:
        """
        Berechnet den erwarteten Lucky Multiplier.
        
        Zwei separate Rolls:
        - 1/20: 3× Loot
        - 1/2500: 50× Loot
        
        Returns:
            Erwarteter Lucky Multiplier
        """
        # Beide Rolls treffen nicht
        neither = (19/20) * (2499/2500)
        # Nur 3× Roll
        three_x = (1/20) * (2499/2500)
        # Nur 50× Roll
        fifty_x = (19/20) * (1/2500)
        # Beide Rolls (150×)
        both = (1/20) * (1/2500)
        
        expected_mult = (
            neither * 1.0 +
            three_x * 3.0 +
            fifty_x * 50.0 +
            both * 150.0
        )
        return expected_mult
    
    def convert_time_boost_to_gem_equivalent(self, minutes_2x_speed: float) -> float:
        """
        Konvertiert Zeitersparnis durch 2× Game Speed zu Gem-Äquivalent.
        
        Ähnlich wie Founder Speed Boost: Zeitersparnis → mehr Freebies → Gem-Äquivalent
        
        Args:
            minutes_2x_speed: Minuten mit 2× Game Speed
            
        Returns:
            Gem-Äquivalent
        """
        # Zeitersparnis: minutes_2x_speed mit 2× Speed = minutes_2x_speed Minuten Zeitersparnis
        # (weil in dieser Zeit doppelt so viel Fortschritt gemacht wird)
        time_saved_minutes = minutes_2x_speed
        
        # Wie viele zusätzliche Freebies durch diese Zeitersparnis?
        # Normale Freebie-Rate: 1 alle 7 Minuten (oder params.freebie_timer_minutes)
        # Zeitersparnis in Stunden
        time_saved_hours = time_saved_minutes / 60.0
        
        # Zusätzliche Freebies durch Zeitersparnis
        # (Wenn ich time_saved_hours spare, kann ich in dieser Zeit mehr Freebies sammeln)
        additional_freebies = time_saved_hours * (60.0 / self.params.freebie_timer_minutes)
        
        # Gem-Äquivalent aus zusätzlichen Freebies
        expected_rolls = self.calculate_expected_rolls_per_claim()
        refresh_mult = self.calculate_refresh_multiplier()
        
        gem_equivalent = (
            additional_freebies *
            refresh_mult *
            expected_rolls *
            self.params.freebie_gems_base
        )
        
        # Auch Skill Shards und Stonks sollten berücksichtigt werden, aber vereinfacht
        # nur mit Basis-Gems für jetzt
        
        return gem_equivalent
    
    def calculate_gift_ev_per_gift(self) -> float:
        """
        Berechnet den Gem-EV pro 1 geöffneten Gift.
        
        Berücksichtigt:
        - Basis-Roll (Gems, Skill Shards, Blue Cow, 2× Speed)
        - Rare Rolls (3 Gifts rekursiv, 80-130 Gems, etc.)
        - Obelisk Multiplier (auf alle Mengen/Dauern)
        - Lucky Multiplier (auf alle Mengen/Dauern nach Obelisk)
        
        Returns:
            Gem-EV pro 1 Gift
        """
        obelisk_mult = self.calculate_obelisk_multiplier()
        lucky_mult = self.calculate_lucky_multiplier()
        skill_shard_value = self.params.skill_shard_value_gems
        
        # ============================================
        # 1. BASIS-ROLL EV (vor Multiplikatoren)
        # ============================================
        # Basis-Roll hat 12 Items, gleichverteilt
        # Nur relevante Items:
        
        # Gems (20-40): Durchschnitt = 30
        gems_20_40 = 30.0
        # Gems (30-65): Durchschnitt = 47.5
        gems_30_65 = 47.5
        # Skill Shards (2-5): Durchschnitt = 3.5
        skill_shards_base = 3.5
        # Blue Cow (2-4): Durchschnitt = 3 (jede = 16 min 2× Speed)
        blue_cows_base = 3.0
        minutes_per_blue_cow = 16.0
        # 2× Game Speed (20-45 min): Durchschnitt = 32.5
        speed_minutes_base = 32.5
        
        # Anzahl relevanter Items in Basis-Roll (wenn wir alle ignorieren, die nicht gem-wertig sind)
        # Wir nehmen an: 5 relevante Items (Gems x2, Skill Shards, Blue Cow, 2× Speed)
        num_relevant_items = 5
        chance_per_item = 1.0 / 12.0  # Gleichverteilt über 12 Items
        
        # Basis-Roll EV (ohne Multiplikatoren):
        base_roll_gems = chance_per_item * (gems_20_40 + gems_30_65)
        base_roll_shards = chance_per_item * skill_shards_base * skill_shard_value
        base_roll_blue_cow_minutes = chance_per_item * blue_cows_base * minutes_per_blue_cow
        base_roll_speed_minutes = chance_per_item * speed_minutes_base
        
        # Time Boost zu Gem-Äquivalent (vor Multiplikatoren)
        base_roll_time_boost_gems = (
            self.convert_time_boost_to_gem_equivalent(base_roll_blue_cow_minutes) +
            self.convert_time_boost_to_gem_equivalent(base_roll_speed_minutes)
        )
        
        base_roll_ev = base_roll_gems + base_roll_shards + base_roll_time_boost_gems
        
        # ============================================
        # 2. RARE ROLL EV (konditional, können Basis ersetzen)
        # ============================================
        # Rare Rolls werden sequenziell geprüft
        # Effektive Chancen (spätere haben niedrigere effektive Chance):
        
        # 1/40: 3 Gifts (rekursiv!)
        rare_gifts_3_chance = 1/40
        # 1/45: 80-130 Gems (Durchschnitt = 105)
        rare_gems_chance = (39/40) * (1/45)  # Nur wenn 3 Gifts nicht getriggert
        rare_gems_avg = 105.0
        # 1/200: 80-130 Gems (wenn alle Skins) - ignorieren wir erstmal oder als 0 annehmen
        # 1/2000: 25 Gifts (wenn alle Gilded Skins) - sehr selten, erstmal ignorieren
        
        # Rare Roll EV (ohne rekursive Gifts):
        rare_roll_gems_ev = rare_gems_chance * rare_gems_avg
        
        # ============================================
        # 3. MULTIPLIKATOREN ANWENDEN
        # ============================================
        # Reihenfolge: Basis → × Obelisk → × Lucky
        
        # Basis-Roll nach Multiplikatoren:
        # Gems und Skill Shards werden multipliziert
        base_gems_with_mult = base_roll_gems * obelisk_mult * lucky_mult
        base_shards_with_mult = base_roll_shards * obelisk_mult * lucky_mult
        
        # Time Boosts: Minuten werden multipliziert, dann zu Gems konvertiert
        base_blue_cow_minutes_mult = base_roll_blue_cow_minutes * obelisk_mult * lucky_mult
        base_speed_minutes_mult = base_roll_speed_minutes * obelisk_mult * lucky_mult
        base_time_boost_gems_mult = (
            self.convert_time_boost_to_gem_equivalent(base_blue_cow_minutes_mult) +
            self.convert_time_boost_to_gem_equivalent(base_speed_minutes_mult)
        )
        
        # Rare Roll nach Multiplikatoren:
        rare_gems_with_mult = rare_roll_gems_ev * obelisk_mult * lucky_mult
        
        # ============================================
        # 4. REKURSIVE GIFTS LÖSEN
        # ============================================
        # Gift-EV = A + B × Gift-EV
        # wobei A = Basis + Rare (ohne rekursive Gifts)
        # und B = rekursive Gifts EV-Koeffizient
        
        # A = Basis + Rare (ohne rekursive Gifts)
        A = (
            base_gems_with_mult +
            base_shards_with_mult +
            base_time_boost_gems_mult +
            rare_gems_with_mult
        )
        
        # B = Koeffizient für rekursive Gifts
        # 1/40: 3 Gifts → 3 × obelisk_mult × lucky_mult × Gift-EV
        recursive_gifts_coefficient = rare_gifts_3_chance * 3.0 * obelisk_mult * lucky_mult
        
        # Aufgelöst: Gift-EV = A / (1 - B)
        if recursive_gifts_coefficient >= 1.0:
            # Mathematisch problematisch (konvergiert nicht)
            # Fallback: iterativ lösen oder als sehr groß behandeln
            gift_ev = A * 10.0  # Vereinfachung
        else:
            gift_ev = A / (1.0 - recursive_gifts_coefficient)
        
        return gift_ev
    
    def calculate_gift_ev_breakdown(self) -> Dict[str, float]:
        """
        Berechnet die Contributions der einzelnen Basis-Belohnungen für Gift-EV.
        
        Returns:
            Dictionary mit Contributions pro Belohnungstyp (nach Multiplikatoren)
        """
        obelisk_mult = self.calculate_obelisk_multiplier()
        lucky_mult = self.calculate_lucky_multiplier()
        skill_shard_value = self.params.skill_shard_value_gems
        chance_per_item = 1.0 / 12.0  # Gleichverteilt über 12 Items
        
        # Basis-Werte (Durchschnitte)
        gems_20_40 = 30.0
        gems_30_65 = 47.5
        skill_shards_base = 3.5
        blue_cows_base = 3.0
        minutes_per_blue_cow = 16.0
        speed_minutes_base = 32.5
        
        # Basis-Roll EV pro Item (vor Multiplikatoren)
        gems_20_40_base = chance_per_item * gems_20_40
        gems_30_65_base = chance_per_item * gems_30_65
        skill_shards_base_ev = chance_per_item * skill_shards_base * skill_shard_value
        blue_cow_minutes_base = chance_per_item * blue_cows_base * minutes_per_blue_cow
        speed_minutes_base_ev = chance_per_item * speed_minutes_base
        
        # Nach Multiplikatoren (Obelisk × Lucky)
        gems_20_40_final = gems_20_40_base * obelisk_mult * lucky_mult
        gems_30_65_final = gems_30_65_base * obelisk_mult * lucky_mult
        skill_shards_final = skill_shards_base_ev * obelisk_mult * lucky_mult
        
        # Time Boosts: Minuten multiplizieren, dann zu Gems konvertieren
        blue_cow_minutes_final = blue_cow_minutes_base * obelisk_mult * lucky_mult
        speed_minutes_final = speed_minutes_base_ev * obelisk_mult * lucky_mult
        blue_cow_gems_final = self.convert_time_boost_to_gem_equivalent(blue_cow_minutes_final)
        speed_gems_final = self.convert_time_boost_to_gem_equivalent(speed_minutes_final)
        
        # Rare Roll Gems (1/45, aber nur wenn 3 Gifts nicht getriggert)
        rare_gems_chance = (39/40) * (1/45)
        rare_gems_avg = 105.0
        rare_gems_final = rare_gems_chance * rare_gems_avg * obelisk_mult * lucky_mult
        
        # Rekursive Gifts (müssen wir skalieren, damit die Summe dem totalen Gift-EV entspricht)
        # Wir berechnen den Beitrag der rekursiven Gifts separat
        gift_ev_total = self.calculate_gift_ev_per_gift()
        
        # A = Basis + Rare (ohne rekursive Gifts)
        A = (
            gems_20_40_final +
            gems_30_65_final +
            skill_shards_final +
            blue_cow_gems_final +
            speed_gems_final +
            rare_gems_final
        )
        
        # Der Beitrag der rekursiven Gifts ist: Gift-EV - A
        recursive_gifts_contribution = gift_ev_total - A
        
        return {
            'gems_20_40': gems_20_40_final,
            'gems_30_65': gems_30_65_final,
            'skill_shards': skill_shards_final,
            'blue_cow': blue_cow_gems_final,
            'speed_boost': speed_gems_final,
            'rare_gems': rare_gems_final,
            'recursive_gifts': recursive_gifts_contribution,
            'total': gift_ev_total
        }
    
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
        print(f"  VIP Lounge Level: {self.params.vip_lounge_level}")
        print(f"  Founder Drop Intervall: {self.get_founder_drop_interval_minutes():.1f} Minuten")
        print(f"  Double Drop Chance: {self.get_double_drop_chance()*100:.1f}%")
        print(f"  Triple Drop Chance: {self.get_triple_drop_chance()*100:.1f}%")
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
