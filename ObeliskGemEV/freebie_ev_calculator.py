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
    freebie_claim_percentage: float = 100.0  # % der Freebies die pro Tag geclaimt werden
    
    # Skill Shards
    skill_shard_chance: float = 0.12  # 12%
    skill_shard_value_gems: float = 12.5
    
    # Stonks
    stonks_chance: float = 0.01  # 1%
    stonks_bonus_gems: float = 200.0
    
    # Jackpot
    jackpot_chance: float = 0.08  # 5% + 3%
    jackpot_rolls: int = 5
    
    # Refresh
    instant_refresh_chance: float = 0.05  # 5%
    
    # Founder
    vip_lounge_level: int = 3  # VIP Lounge Level (1-7)
    founder_gems_base: float = 10.0  # Feste Gems pro Drop
    founder_gems_chance: float = 0.01  # 1/100 Chance auf zusätzliche Gems
    obelisk_level: int = 29  # Obelisk Level für Founder Gem-Berechnung
    founder_speed_multiplier: float = 2.0
    founder_speed_duration_minutes: float = 5.0
    
    # VIP Lounge berechnet automatisch:
    # - founder_drop_interval_minutes = 60 - 2*(vip_lounge_level-1) Minuten
    # - double_drop_chance = 0.12 + 0.06*(vip_lounge_level-2) (ab Tier 2)
    # - triple_drop_chance = 0.16 wenn vip_lounge_level >= 7

    # Bombs - General
    free_bomb_chance: float = 0.16  # 16% Chance dass bomb click 0 charges verbraucht
    total_bomb_types: int = 12  # Gesamtanzahl Bomb-Typen (für Battery/D20 Berechnung)
    
    # Bomb recharge cards (0 = none, 1 = card, 2 = gilded, 3 = polychrome)
    # These affect ONLY charges gained from periodic recharges, not refills.
    gem_bomb_recharge_card_level: int = 0
    cherry_bomb_recharge_card_level: int = 0
    battery_bomb_recharge_card_level: int = 0
    d20_bomb_recharge_card_level: int = 0
    founder_bomb_recharge_card_level: int = 0
    
    # Gem Bomb
    gem_bomb_recharge_seconds: float = 46.0  # Recharge Zeit
    gem_bomb_gem_chance: float = 0.03  # 3% Chance per charge auf 1 Gem
    
    # Cherry Bomb
    cherry_bomb_recharge_seconds: float = 48.0  # Recharge Zeit
    # Workshop upgrade: chance that a Cherry Bomb click yields 3 free bomb clicks instead of 1.
    # (i.e., 1 Cherry click can "count as 3" for the free-click effect)
    cherry_bomb_triple_charge_chance: float = 0.0
    
    # Battery Bomb
    battery_bomb_recharge_seconds: float = 31.0  # Recharge Zeit
    battery_bomb_charges_per_charge: float = 2.0  # +2 charges to random bomb
    battery_bomb_cap_increase_chance: float = 0.001  # 0.1% chance to increase bomb cap by 1
    
    # D20 Bomb
    d20_bomb_recharge_seconds: float = 36.0  # Recharge Zeit
    d20_bomb_refill_chance: float = 0.05  # 5% chance to refill
    d20_bomb_charges_distributed: int = 42  # Anzahl Charges die verteilt werden
    
    # Founder Bomb
    founder_bomb_interval_seconds: float = 87.0  # recharge zeit
    founder_bomb_charges_per_drop: float = 2.0  # 100% Chance auf 2 Charges
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
    
    @staticmethod
    def _get_recharge_charge_multiplier(card_level: int) -> float:
        """Return expected charge multiplier for a bomb recharge card level.
        
        Levels:
          0 = none      -> 1.0x
          1 = card      -> 50% chance for 2x charges (EV = 1.5x)
          2 = gilded    -> 100% chance for 2x charges (EV = 2.0x)
          3 = polychrome-> 100% chance for 3x charges (EV = 3.0x)
        """
        return {
            0: 1.0,
            1: 1.5,  # 0.5*1 + 0.5*2
            2: 2.0,
            3: 3.0,
        }.get(int(card_level or 0), 1.0)
    
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
        Berücksichtigt den Claim-Prozentsatz (wie viel % der Freebies pro Tag geclaimt werden).
        
        Returns:
            Freebies pro Stunde (mit Claim-Prozentsatz multipliziert)
        """
        minutes_per_hour = 60.0
        base_freebies_per_hour = minutes_per_hour / self.params.freebie_timer_minutes
        # Multipliziere mit Claim-Prozentsatz (z.B. 100.0 = 100%, 50.0 = 50%)
        return base_freebies_per_hour * (self.params.freebie_claim_percentage / 100.0)
    
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
        # Berechne effektive Freebies pro Stunde (ohne Claim-Prozentsatz)
        base_effective_freebies_per_hour = 60.0 / (
            self.params.freebie_timer_minutes * (effective_minutes_per_hour / 60.0)
        )
        # Wende Claim-Prozentsatz auch auf effektive Freebies an
        effective_freebies_per_hour = base_effective_freebies_per_hour * (self.params.freebie_claim_percentage / 100.0)
        
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
    
    def calculate_gem_bomb_gems_per_hour(self) -> float:
        """
        Berechnet Gem Bomb Gems pro Stunde.
        
        Strategie: Gem zum Platzschaffen -> [Cherry -> Battery -> D20 -> Gem] repeat
        
        Mechanik:
        - Gem Bomb rechargt kontinuierlich (jeder Recharge = 1 Charge)
        - Cherry Bomb: Next bomb click consumes 0 charges (triggers free Gem Bomb)
        - Battery Bomb: Charges 2 random bombs (except itself)
        - D20 Bomb: 5% chance to distribute 42 charges to other bombs (except itself)
        - Free Bomb Chance: 16% dass ein Click keine Charges verbraucht (affects ALL bombs)
        - 2× Game Speed: Halbiert alle Bomb Recharge-Zeiten
        
        Returns:
            Gem Bomb Gems pro Stunde
        """
        seconds_per_hour = 3600.0
        
        # Berücksichtige 2× Game Speed von Founder Speed Boost
        founder_drop_interval = self.get_founder_drop_interval_minutes()
        founder_drops_per_hour = 60.0 / founder_drop_interval
        
        double_chance = self.get_double_drop_chance()
        triple_chance = self.get_triple_drop_chance()
        single_chance = 1.0 - double_chance - triple_chance
        
        expected_drops_per_event = (
            1.0 * single_chance +
            2.0 * double_chance +
            3.0 * triple_chance
        )
        
        # Minuten mit 2× Speed pro Stunde
        speed_minutes_per_hour = (
            founder_drops_per_hour *
            expected_drops_per_event *
            self.params.founder_speed_duration_minutes
        )
        
        # Prozent der Zeit mit 2× Speed
        speed_percentage = speed_minutes_per_hour / 60.0
        
        # Effektive Recharge-Zeiten (gewichtet mit Speed)
        effective_gem_bomb_recharge = (
            self.params.gem_bomb_recharge_seconds * (1.0 - speed_percentage) +
            (self.params.gem_bomb_recharge_seconds / 2.0) * speed_percentage
        )
        
        effective_cherry_bomb_recharge = (
            self.params.cherry_bomb_recharge_seconds * (1.0 - speed_percentage) +
            (self.params.cherry_bomb_recharge_seconds / 2.0) * speed_percentage
        )
        
        effective_battery_bomb_recharge = (
            self.params.battery_bomb_recharge_seconds * (1.0 - speed_percentage) +
            (self.params.battery_bomb_recharge_seconds / 2.0) * speed_percentage
        )
        
        effective_d20_bomb_recharge = (
            self.params.d20_bomb_recharge_seconds * (1.0 - speed_percentage) +
            (self.params.d20_bomb_recharge_seconds / 2.0) * speed_percentage
        )
        
        # Free Bomb Chance: Multipliziert die effektiven Clicks
        # 16% Chance dass Click free ist → 1 / (1 - 0.16) = 1.1905 effektive Clicks
        free_bomb_multiplier = 1.0 / (1.0 - self.params.free_bomb_chance)
        
        # Basis clicks per hour from periodic recharges ONLY (no refills yet).
        # Recharge cards affect ONLY these base values, not Battery/D20 refills.
        gem_mult = self._get_recharge_charge_multiplier(self.params.gem_bomb_recharge_card_level)
        cherry_mult = self._get_recharge_charge_multiplier(self.params.cherry_bomb_recharge_card_level)
        battery_mult = self._get_recharge_charge_multiplier(self.params.battery_bomb_recharge_card_level)
        d20_mult = self._get_recharge_charge_multiplier(self.params.d20_bomb_recharge_card_level)
        
        gem_bomb_clicks_base = (seconds_per_hour / effective_gem_bomb_recharge) * gem_mult
        # Cherry recharge cards affect Cherry's own periodic charges (i.e., how often you can click Cherry),
        # but the workshop upgrade affects the *effect* of a Cherry click (how many free clicks it grants),
        # not how many Cherry charges you receive from recharges/refills.
        cherry_bomb_clicks_base = (seconds_per_hour / effective_cherry_bomb_recharge) * cherry_mult
        battery_bomb_clicks_base = (seconds_per_hour / effective_battery_bomb_recharge) * battery_mult
        d20_bomb_clicks_base = (seconds_per_hour / effective_d20_bomb_recharge) * d20_mult
        
        # Effektive Clicks pro Stunde (mit Free Bomb Chance)
        gem_bomb_clicks = gem_bomb_clicks_base * free_bomb_multiplier
        cherry_bomb_clicks = cherry_bomb_clicks_base * free_bomb_multiplier
        battery_bomb_clicks = battery_bomb_clicks_base * free_bomb_multiplier
        d20_bomb_clicks = d20_bomb_clicks_base * free_bomb_multiplier
        
        # Strategie: Gem zum Platzschaffen -> [Cherry -> Battery -> D20 -> Gem] repeat
        # 
        # REKURSIVES SYSTEM: Battery und D20 refillen sich gegenseitig und Cherry,
        # was zu mehr Clicks führt, was wiederum zu mehr Refills führt.
        #
        # Wir lösen das iterativ:
        # 1. Start mit Basis-Clicks (durch Recharge)
        # 2. Berechne Refills basierend auf aktuellen Clicks
        # 3. Addiere Refills zu Clicks
        # 4. Wiederhole bis Konvergenz
        
        # Basis-Clicks (durch Recharge, ohne Refills)
        gem_bomb_base_clicks = gem_bomb_clicks
        cherry_bomb_base_clicks = cherry_bomb_clicks
        battery_bomb_base_clicks = battery_bomb_clicks
        d20_bomb_base_clicks = d20_bomb_clicks
        
        # Refill-Raten (pro Click der Quelle)
        # Battery gibt +2 charges zu einer zufälligen Bombe (außer sich selbst)
        battery_refill_per_click = self.params.battery_bomb_charges_per_charge / (self.params.total_bomb_types - 1)
        
        # D20 gibt 42 charges zu anderen Bomben (bei 5% Chance, außer sich selbst)
        d20_refill_per_click = (
            self.params.d20_bomb_refill_chance *
            self.params.d20_bomb_charges_distributed /
            (self.params.total_bomb_types - 1)
        )
        
        # Iterative Lösung (konvergiert, da Refills < 1 pro Click)
        # 
        # Konvergenz-Garantie:
        # - Battery gibt 2 charges zu einer zufälligen Bombe → erwarteter Wert pro Bombe = 2/(total-1) < 1
        # - D20 gibt 42 charges (5% Chance) → erwarteter Wert pro Bombe = 0.05*42/(total-1) < 1
        # - Da beide < 1 sind, konvergiert die Reihe (geometrische Reihe)
        #
        # Wir iterieren bis die Änderung < 0.01 Clicks pro Stunde ist
        gem_bomb_total = gem_bomb_base_clicks
        cherry_bomb_total = cherry_bomb_base_clicks
        battery_bomb_total = battery_bomb_base_clicks
        d20_bomb_total = d20_bomb_base_clicks
        
        max_iterations = 100
        convergence_threshold = 0.01
        
        for iteration in range(max_iterations):
            # Berechne Refills basierend auf aktuellen Clicks
            # Battery refills alle anderen Bomben
            battery_refills_to_gem = battery_bomb_total * battery_refill_per_click
            battery_refills_to_cherry = battery_bomb_total * battery_refill_per_click
            battery_refills_to_battery = battery_bomb_total * battery_refill_per_click  # Selbst-refill
            battery_refills_to_d20 = battery_bomb_total * battery_refill_per_click
            
            # D20 refills alle anderen Bomben
            d20_refills_to_gem = d20_bomb_total * d20_refill_per_click
            d20_refills_to_cherry = d20_bomb_total * d20_refill_per_click
            d20_refills_to_battery = d20_bomb_total * d20_refill_per_click
            d20_refills_to_d20 = d20_bomb_total * d20_refill_per_click  # Selbst-refill
            
            # Neue Totals = Basis + Refills
            gem_bomb_new = gem_bomb_base_clicks + battery_refills_to_gem + d20_refills_to_gem
            cherry_bomb_new = cherry_bomb_base_clicks + battery_refills_to_cherry + d20_refills_to_cherry
            battery_bomb_new = battery_bomb_base_clicks + battery_refills_to_battery + d20_refills_to_battery
            d20_bomb_new = d20_bomb_base_clicks + battery_refills_to_d20 + d20_refills_to_d20
            
            # Prüfe Konvergenz
            change = abs(gem_bomb_new - gem_bomb_total) + abs(cherry_bomb_new - cherry_bomb_total) + \
                     abs(battery_bomb_new - battery_bomb_total) + abs(d20_bomb_new - d20_bomb_total)
            
            if change < convergence_threshold:
                break
            
            # Update für nächste Iteration
            gem_bomb_total = gem_bomb_new
            cherry_bomb_total = cherry_bomb_new
            battery_bomb_total = battery_bomb_new
            d20_bomb_total = d20_bomb_new
        
        # Cherry Bomb: each Cherry click grants free Gem Bomb clicks.
        # Workshop upgrade: p chance for a Cherry click to grant 3 free clicks instead of 1.
        # Expected multiplier = (1-p)*1 + p*3 = 1 + 2p
        cherry_effect_mult = 1.0 + 2.0 * self.params.cherry_bomb_triple_charge_chance
        cherry_free_gem_bomb_clicks = cherry_bomb_total * cherry_effect_mult
        
        # Gesamte Gem Bomb Clicks pro Stunde:
        # 1. Normale Gem Bomb Clicks (zum Platzschaffen)
        # 2. Free Gem Bomb Clicks durch Cherry (inkl. refilled Cherry Clicks)
        # 3. Zusätzliche Charges durch Battery (als zusätzliche Clicks, inkl. rekursiver Refills)
        # 4. Zusätzliche Charges durch D20 (als zusätzliche Clicks, inkl. rekursiver Refills)
        total_gem_bomb_clicks = gem_bomb_total + cherry_free_gem_bomb_clicks
        
        # Gems: Jeder Click = 1 Charge mit 3% Chance auf 1 Gem
        gems_per_hour = total_gem_bomb_clicks * self.params.gem_bomb_gem_chance
        
        return gems_per_hour
    
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
        effective_bombs_per_charge = 1.0 / (1.0 - self.params.free_bomb_chance)
        
        # Founder Bomb charges per drop come from periodic drops -> treated like a "recharge".
        founder_mult = self._get_recharge_charge_multiplier(self.params.founder_bomb_recharge_card_level)
        charges_per_drop = self.params.founder_bomb_charges_per_drop * founder_mult
        
        # Effektive Bombs pro Drop (charges × effektive Bombs pro charge)
        effective_bombs_per_drop = charges_per_drop * effective_bombs_per_charge
        
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
        # Berechne effektive Freebies pro Stunde (ohne Claim-Prozentsatz)
        base_effective_freebies_per_hour = 60.0 / (
            self.params.freebie_timer_minutes * (effective_minutes_per_hour / 60.0)
        )
        # Wende Claim-Prozentsatz auch auf effektive Freebies an
        effective_freebies_per_hour = base_effective_freebies_per_hour * (self.params.freebie_claim_percentage / 100.0)
        
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
        
        # Gem Bomb Gems (keine Multiplikatoren - unabhängig von Freebie-System)
        gem_bomb_gems = self.calculate_gem_bomb_gems_per_hour()
        breakdown['gem_bomb_gems'] = {
            'base': gem_bomb_gems,
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
        gem_bomb_gems = self.calculate_gem_bomb_gems_per_hour()
        founder_bomb_boost = self.calculate_founder_bomb_boost_per_hour()
        
        total = (
            gems_base +
            stonks_ev +
            skill_shards_ev +
            founder_speed_boost +
            founder_gems +
            gem_bomb_gems +
            founder_bomb_boost
        )
        
        return {
            'gems_base': gems_base,
            'stonks_ev': stonks_ev,
            'skill_shards_ev': skill_shards_ev,
            'founder_speed_boost': founder_speed_boost,
            'founder_gems': founder_gems,
            'gem_bomb_gems': gem_bomb_gems,
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
        print(f"  Founder Bomb Speed Chance: {self.params.founder_bomb_speed_chance * 100:.1f}%")
        print(f"  Free Bomb Chance: {self.params.free_bomb_chance * 100:.1f}%")
        print(f"  Total Bomb Types: {self.params.total_bomb_types}")
        print(f"  Battery Bomb Recharge: {self.params.battery_bomb_recharge_seconds} Sekunden")
        print(f"  D20 Bomb Recharge: {self.params.d20_bomb_recharge_seconds} Sekunden")
        print(f"  D20 Bomb Refill Chance: {self.params.d20_bomb_refill_chance * 100:.1f}%")
        print(f"  D20 Bomb Charges Distributed: {self.params.d20_bomb_charges_distributed}")
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
        print(f"  Gem Bomb Gems: {ev['gem_bomb_gems']:.1f}")
        print(f"  Founder Bomb Boost: {ev['founder_bomb_boost']:.1f}")
        print(f"  {'─' * 50}")
        print(f"  TOTAL: {ev['total']:.1f} Gems-Äquivalent/h")
        print()
        print("=" * 70)
