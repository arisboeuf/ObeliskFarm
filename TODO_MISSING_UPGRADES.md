# To-Do: Fehlende Fragment Upgrade Effekte

Diese Liste enthält alle Fragment Upgrade Effekte, die noch **nicht vollständig in der Simulation implementiert** sind.

## ✅ Bereits implementiert

- ✅ Alle Cooldown-Reduktionen (`enrage_cooldown`, `flurry_cooldown`, `quake_cooldown`, `ability_cooldown`)
- ✅ Alle Damage/Stats Boni (flat_damage, percent_damage, armor_pen, etc.)
- ✅ Alle Mod Chances (exp_mod_chance, loot_mod_chance, etc.)
- ✅ Alle Mod Gain Boni (exp_mod_gain, loot_mod_multiplier, stamina_mod_gain)
- ✅ Skill Buffs (xp_bonus_skill, mod_chance_skill, armor_pen_skill, max_stamina_skill)
- ✅ Prozentuale Boni (armor_pen_percent, max_stamina_percent)
- ✅ Fragment Gain Multiplier (`fragment_gain_mult`)
- ✅ XP Bonus Multiplier (`xp_bonus_mult`)
- ✅ All Mod Chance (`all_mod_chance`)

---

## ❌ Noch NICHT implementiert

### 1. **`quake_attacks`** (Quake Buff Upgrade)
- **Effekt**: +1 zusätzliche Quake Attack pro Level (max 10)
- **Aktuell**: Quake hat immer 5 Charges (`QUAKE_CHARGES = 5`)
- **Benötigt**: 
  - `QUAKE_CHARGES` sollte `5 + frag_bonuses.get('quake_attacks', 0)` sein
  - In `simulator.py` und `monte_carlo_crit.py` anpassen
  - In `get_total_stats()` als `'quake_charges'` übergeben

### 2. **`ability_instacharge`** (Ability Stamina M1 Upgrade)
- **Effekt**: +0.30% Chance pro Level, dass eine Ability sofort verfügbar wird (wenn auf Cooldown)
- **Aktuell**: Wird nicht in der Simulation verwendet
- **Benötigt**:
  - In `monte_carlo_crit.py` bei jedem Ability Cooldown Check prüfen
  - Wenn `random() < ability_instacharge`, Cooldown auf 0 setzen
  - Gilt für Enrage, Flurry und Quake
  - In `get_total_stats()` als `'ability_instacharge'` übergeben

### 3. **`all_stat_cap`** (Exp Stat Cap M1 Upgrade)
- **Effekt**: +5 zu allen Stat Point Caps
- **Aktuell**: Stat Caps werden nicht simuliert (nur für Skill Point Limits relevant)
- **Status**: ⚠️ **Optional** - Nur relevant wenn Skill Point Caps implementiert werden sollen
- **Benötigt** (falls implementiert):
  - Skill Point Cap System
  - Max Skill Points pro Stat = Base Cap + `all_stat_cap`

---

## Implementierungs-Priorität

### 🔴 Hoch (wichtig für Simulation)
1. **`quake_attacks`** - Direkter Einfluss auf Quake DPS
2. **`ability_instacharge`** - Kann Ability Uptime signifikant erhöhen

### 🟡 Mittel (optional)
3. **`all_stat_cap`** - Nur relevant wenn Skill Point Caps simuliert werden

---

## Implementierungs-Details

### `quake_attacks` Implementation:
```python
# In simulator.py und monte_carlo_crit.py
frag_bonuses = self._get_fragment_upgrade_bonuses()
quake_charges = self.QUAKE_CHARGES + frag_bonuses.get('quake_attacks', 0)
```

### `ability_instacharge` Implementation:
```python
# In monte_carlo_crit.py simulate_block_kill()
ability_instacharge = stats.get('ability_instacharge', 0)

# Bei Enrage Cooldown Check:
if enrage_state['cooldown'] > 0 and random.random() < ability_instacharge:
    enrage_state['cooldown'] = 0
    enrage_state['charges_remaining'] = self.ENRAGE_CHARGES

# Ähnlich für Flurry und Quake
```

---

## Notizen

- `all_stat_cap` ist wahrscheinlich nicht kritisch, da Skill Point Caps normalerweise nicht in Damage/Performance Simulationen relevant sind
- `ability_instacharge` könnte einen signifikanten Einfluss haben bei hohen Levels (max 20 * 0.30% = 6% Chance)
- `quake_attacks` erhöht Quake DPS linear (5 → 15 Charges bei max Level)
