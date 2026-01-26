# Archaeology Skill Point Optimizer

A simulation and optimization tool for the Archaeology minigame in Obelisk Idle Miner.

## Overview

The Archaeology Simulator helps you make optimal skill point and upgrade decisions by calculating the **expected floors per run** for any given build. It accounts for all combat mechanics including damage, armor penetration, critical hits, one-hit kills, and the Enrage ability.

## Features

- **Real-time efficiency calculation**: See exactly how much each skill point or upgrade improves your floors/run
- **Best next point recommendation**: Automatically suggests the optimal next investment
- **Stage-aware calculations**: Block stats and spawn rates adjust based on selected stage
- **Enrage toggle**: Enable/disable Enrage ability in calculations
- **Auto-save**: Your configuration persists between sessions

## Core Mechanics

### Combat System

| Mechanic | Value | Notes |
|----------|-------|-------|
| Base Damage | 10 | Starting damage at level 1 |
| Base Stamina | 100 | Maximum hits per run |
| Base Crit Damage | 1.5x | Multiplier on critical hits |
| Attack Speed | 1/sec | Fixed, 1 stamina per hit |

**Damage Formula:**
```
effective_damage = max(1, floor(total_damage - (block_armor - armor_pen)))
```

**Important**: Damage is always an integer (floored), creating breakpoints where +1 damage can significantly increase DPS.

### Abilities

Three abilities are available in Archaeology:

#### Enrage Ability

Enrage provides a buff every 60 seconds that affects the next 5 hits:
- **+20% Damage** (multiplicative with base)
- **+100% Crit Damage** (multiplicative on current crit: crit × (1 + 100%) = 2×, so 1.5× → 3×)

**Effective uptime**: 5/60 = 8.33% of all hits

Note: The Crit Damage bonus only matters if you have Crit Chance. At 0% crit, Enrage is only +1.67% average DPS.

#### Flurry Ability

Flurry provides a buff every 120 seconds:
- **+100% Attack Speed** (QoL only - stamina drains faster too, no floors/run advantage)
- **+5 Stamina** (one-time bonus on activation)

**Cooldown**: 120 seconds (reducible with fragment upgrades and misc card)

#### Quake Ability

Quake provides AOE damage every 180 seconds:
- **5 Charges** every 180 seconds
- **20% Damage** to all other blocks on the floor (not the block you're currently attacking)
- Each hit on your target block triggers Quake splash damage to all other blocks

**Critical Rules for Quake:**

1. **Base Damage Only**: Quake uses ONLY base damage (`stats['total_damage']`), **NOT** affected by:
   - ❌ Enrage damage bonus (+20%)
   - ✅ But CAN crit (see below)

2. **Splash Can Crit**: Quake splash damage **CAN crit**, but:
   - Each block rolls **separately** for crits
   - Some blocks may crit while others don't on the same attack
   - Each hit rolls independently (if you hit 3 times, each block rolls 3 times)

3. **Splash Target**: Splash damage only hits **other blocks**, not the block you're currently attacking

4. **Armor Ignore**: Quake damage ignores armor (applied directly to HP)

**Example:**
- You have 58 base damage
- You attack Block 1 with 3 hits while Quake is active
- Block 2: Hit 1 crits (12 × 1.5 = 18), Hit 2 normal (12), Hit 3 crits (18) → Total: 48 damage
- Block 3: Hit 1 normal (12), Hit 2 normal (12), Hit 3 normal (12) → Total: 36 damage
- Block 1 (target): No Quake splash (you're attacking it directly)

**Edge Case**: If only 1 block remains on the floor and Quake activates, the charge is consumed but no splash damage occurs (no other blocks to hit).

**Cooldown**: 180 seconds (reducible with fragment upgrades and misc card)

### Skills

Each Archaeology level grants 1 skill point to allocate:

| Skill | Bonuses per Point |
|-------|-------------------|
| **Strength** | +1 Flat Damage, +1% Damage, +3% Crit Damage |
| **Agility** | +5 Max Stamina, +1% Crit Chance, +0.20% Speed Mod Chance |
| **Intellect** | +5% XP Bonus, +0.30% Exp Mod Chance, +3% Armor Pen Multiplier |
| **Perception** | +4% Fragment Gain, +0.30% Loot Mod Chance, +2 Armor Penetration |
| **Luck** | +2% Crit Chance, +0.20% All Mod Chances, +0.04% One-Hit Chance |

### Multiplikator-Regeln (Wichtig!)

**MULTIPLIKATIV (Multiplikator auf Basis):**
- **INT Armor Pen**: Basis wird zuerst gerundet, dann mit `(1 + INT * 0.03)` multipliziert
- **Crit Damage**: Basis 1.5× `* (1 + STR×0.03 + Fragment %)` — STR und Fragment **additiv** im gleichen Mult
- **INT XP Gain**: `(Base + Gem + Fragment Upgrades) * (1 + INT * 0.05)`
- **Fragment XP Multiplier**: Wenn vorhanden, multipliziert XP Base

**ADDITIV (Werte werden addiert):**
- Flat Damage: Base + STR * 1 + Upgrades
- Percent Damage: STR * 0.01 + Upgrades (dann multipliziert mit Flat)
- Armor Pen Base: Base + PER * 2 + Upgrades (vor INT Multiplikator)
- Max Stamina: Base + AGI * 5 + Upgrades
- Crit Chance: Base + AGI * 0.01 + LUC * 0.02 + Upgrades
- Fragment Gain: Base + PER * 0.04 + Gem + Upgrades
- Mod Chances: Alle additiv

**WICHTIG:**
- Armor Pen wird **ZUERST gerundet**, **DANN** mit INT multipliziert
- Crit Damage: STR-% und Fragment-% **addieren** im gleichen Mult (nicht nacheinander multiplizieren)
- INT XP Gain multipliziert die gesamte XP Base (inkl. Upgrades)

### Upgrades

Two main upgrades are available early:
- **Flat Damage**: +1 damage per upgrade
- **Armor Penetration**: +1 armor pen per upgrade

### Gem Upgrades

Premium upgrades purchasable with Gems. These provide both stat bonuses and mod chance increases:

| Upgrade | Effect per Level | Max Level | Starting Cost |
|---------|-----------------|-----------|---------------|
| **Stamina** | +2 Max Stamina, +0.05% Stamina Mod Chance | 50 | 300 Gems |
| **XP Boost** | +5% Arch XP, +0.05% Exp Mod Chance | 25 | 400 Gems |
| **Fragment** | +2% Fragment Gain, +0.05% Loot Mod Chance | 25 | 500 Gems |

**Cost Scaling**: Costs increase by ~5% per level up to level 25, then cap at 1000 Gems per level.

<details>
<summary>Full Gem Cost Tables</summary>

**Stamina Upgrade (Max 50)**
| Lvl | Cost | Lvl | Cost | Lvl | Cost | Lvl | Cost | Lvl | Cost |
|-----|------|-----|------|-----|------|-----|------|-----|------|
| 1 | 300 | 11 | 488 | 21 | 795 | 31 | 1000 | 41 | 1000 |
| 2 | 315 | 12 | 513 | 22 | 835 | 32 | 1000 | 42 | 1000 |
| 3 | 330 | 13 | 538 | 23 | 877 | 33 | 1000 | 43 | 1000 |
| 4 | 347 | 14 | 565 | 24 | 921 | 34 | 1000 | 44 | 1000 |
| 5 | 364 | 15 | 593 | 25 | 967 | 35 | 1000 | 45 | 1000 |
| 6 | 382 | 16 | 623 | 26 | 1000 | 36 | 1000 | 46 | 1000 |
| 7 | 402 | 17 | 654 | 27 | 1000 | 37 | 1000 | 47 | 1000 |
| 8 | 422 | 18 | 687 | 28 | 1000 | 38 | 1000 | 48 | 1000 |
| 9 | 443 | 19 | 721 | 29 | 1000 | 39 | 1000 | 49 | 1000 |
| 10 | 465 | 20 | 758 | 30 | 1000 | 40 | 1000 | 50 | 1000 |

**XP Boost Upgrade (Max 25)**
| Lvl | Cost | Lvl | Cost | Lvl | Cost |
|-----|------|-----|------|-----|------|
| 1 | 400 | 10 | 620 | 19 | 962 |
| 2 | 420 | 11 | 651 | 20 | 1000 |
| 3 | 441 | 12 | 684 | 21 | 1000 |
| 4 | 463 | 13 | 718 | 22 | 1000 |
| 5 | 486 | 14 | 754 | 23 | 1000 |
| 6 | 510 | 15 | 791 | 24 | 1000 |
| 7 | 536 | 16 | 831 | 25 | 1000 |
| 8 | 562 | 17 | 873 | | |
| 9 | 590 | 18 | 916 | | |

**Fragment Upgrade (Max 25)**
| Lvl | Cost | Lvl | Cost | Lvl | Cost |
|-----|------|-----|------|-----|------|
| 1 | 500 | 10 | 775 | 19 | 1000 |
| 2 | 525 | 11 | 814 | 20 | 1000 |
| 3 | 551 | 12 | 855 | 21 | 1000 |
| 4 | 578 | 13 | 897 | 22 | 1000 |
| 5 | 607 | 14 | 942 | 23 | 1000 |
| 6 | 638 | 15 | 989 | 24 | 1000 |
| 7 | 670 | 16 | 1000 | 25 | 1000 |
| 8 | 703 | 17 | 1000 | | |
| 9 | 738 | 18 | 1000 | | |

</details>

### Mods (Triggered Effects)

Mods can trigger per block destroyed:

| Mod | Effect | Source Skills |
|-----|--------|---------------|
| **Exp Mod** | 3x-5x XP (avg 4x) | Intellect, Luck |
| **Loot Mod** | 2x-5x Fragments (avg 3.5x) | Perception, Luck |
| **Speed Mod** | 2x attack speed for 10-110 attacks | Agility, Luck |
| **Stamina Mod** | +3 to +10 Stamina (avg 6.5) | Luck only |

**Speed Mod Note**: This is purely QoL (faster run completion). Stamina drains faster too, so there's no floors/run advantage.

**Stamina Mod**: The only mod that affects floors/run by effectively giving you more stamina.

## Block System

### Block Types

Six block types exist, unlocking at different stages:

| Type | Unlock Stage | Characteristics |
|------|--------------|-----------------|
| Dirt | 1 | No armor, low HP |
| Common | 1 | Low armor |
| Rare | 3 | Medium armor |
| Epic | 6 | High armor |
| Legendary | 12 | Very high armor |
| Mythic | 20 | Extreme armor |

### Block Tiers

Each block type has 3 tiers that become available at higher floors:

**Tier 1 (Early Game)**
| Type | HP | Armor | XP | Floors |
|------|---:|------:|---:|--------|
| Dirt | 100 | 0 | 0.05 | 1-11 |
| Common | 250 | 5 | 0.15 | 1-17 |
| Rare | 550 | 12 | 0.35 | 3-25 |
| Epic | 1,150 | 25 | 1.00 | 6-29 |
| Legendary | 1,950 | 50 | 3.50 | 12-31 |
| Mythic | 3,500 | 150 | 7.50 | 20-34 |

**Tier 2 (Mid Game)**
| Type | HP | Armor | XP | Floors |
|------|---:|------:|---:|--------|
| Dirt | 300 | 0 | 0.15 | 12-23 |
| Common | 600 | 9 | 0.45 | 18-28 |
| Rare | 1,650 | 21 | 1.05 | 26-35 |
| Epic | 3,450 | 44 | 3.00 | 30-41 |
| Legendary | 5,850 | 88 | 10.50 | 32-44 |
| Mythic | 10,500 | 262 | 22.50 | 36-49 |

**Tier 3 (Late Game)**
| Type | HP | Armor | XP | Floors |
|------|---:|------:|---:|--------|
| Dirt | 900 | 0 | 0.45 | 24+ |
| Common | 2,250 | 15 | 1.35 | 30+ |
| Rare | 4,950 | 37 | 3.15 | 36+ |
| Epic | 10,350 | 77 | 9.00 | 42+ |
| Legendary | 17,500 | 153 | 31.50 | 45+ |
| Mythic | 31,500 | 459 | 67.50 | 50+ |

### Spawn Rates by Stage

Block spawn rates change as you progress:

| Stage | Dirt | Common | Rare | Epic | Legendary | Mythic |
|-------|-----:|-------:|-----:|-----:|----------:|-------:|
| 1-2 | 66.7% | 33.3% | - | - | - | - |
| 3-4 | 51.6% | 25.8% | 22.6% | - | - | - |
| 6-9 | 42.5% | 18.2% | 20.8% | 18.5% | - | - |
| 12-14 | 38.5% | 14.4% | 16.2% | 18.3% | 12.6% | - |
| 20-24 | 32.0% | 12.0% | 13.5% | 20.2% | 14.2% | 8.2% |
| 50-75 | 25.5% | 12.7% | 14.9% | 20.8% | 17.9% | 8.4% |
| 75+ | 25.4% | 15.2% | 15.2% | 17.8% | 17.8% | 8.9% |

*Note: Percentages are normalized spawn probabilities.*

## Optimization Strategy

### Early Game Priority

**Primary Goal**: Maximize blocks/floors per run

1. **Strength** dominates early because:
   - Reduces hits per block (stamina efficiency)
   - Benefits from integer damage breakpoints
   - Works on ALL blocks (including Dirt)

2. **Flat Damage upgrades** are extremely valuable when:
   - Your damage is low
   - You're near a breakpoint (e.g., 5 → 6 damage = 20% DPS increase)

3. **Armor Penetration** becomes valuable when:
   - Rare+ blocks start spawning (Stage 3+)
   - Block armor exceeds your current pen
   - You can't one-shot Dirt anymore

### General Decision Framework

For each potential +1 point:
1. Calculate new effective damage
2. Calculate new hits per block (weighted by spawn rates)
3. Calculate new floors per run
4. Choose the option with highest % improvement

The simulator does this automatically and shows the efficiency of each option.

### When to Invest in Each Skill

| Skill | Best When |
|-------|-----------|
| Strength | Always good early; damage breakpoints matter |
| Agility | Need more stamina OR building crit |
| Intellect | Floor progress is stable, want faster leveling |
| Perception | Need armor pen OR want fragments |
| Luck | Building crit OR want one-hit chance |

## File Structure

```
archaeology/
├── __init__.py           # Package exports
├── README.md             # This documentation
├── MC_GUIDELINES.md      # Monte Carlo simulation rules and principles
├── simulator.py          # Main GUI and calculations
├── monte_carlo_crit.py   # Monte Carlo simulation engine
├── block_stats.py        # Block HP/Armor/XP data by tier
└── block_spawn_rates.py  # Spawn rates by stage
```

### Monte Carlo Simulations

For guidelines on implementing and using Monte Carlo simulations, see **[MC_GUIDELINES.md](MC_GUIDELINES.md)**.

This document covers:
- When to use MC vs. deterministic calculations
- Rules for MC Stage Pusher (dual simulations, starting floor, etc.)
- Statistical testing principles
- Code organization and best practices
- Common mistakes to avoid

## Usage

1. Launch from the main ObeliskFarm Calculator (Archaeology button)
2. Select your current stage from the dropdown
3. Add skill points and upgrades to match your character
4. The "Best Next Point" recommendation shows optimal investment
5. Use efficiency percentages to compare options
6. Toggle Enrage on/off to see its impact

Your configuration is automatically saved when closing the window.

## Technical Notes

### Calculation Details

**Floors per Run** is calculated by:
1. Getting weighted average hits/block for current stage
2. Accounting for Stamina Mod (adds expected stamina per block)
3. Simulating floor-by-floor stamina consumption
4. Block stats update as tiers change at higher floors

**Expected Hits** accounts for:
- Base damage with armor penetration
- Critical hit chance and damage
- One-hit kill chance
- Enrage uptime (if enabled)

### Assumptions

- 15 blocks per floor (configurable in code)
- Optimal play (no wasted hits)
- Average mod rolls (not min/max)
- No boss floors (standard spawn rates)

## Version History

- **v1.0** (2026-01-20): Full implementation with skill optimization, block data, spawn rates, and save/load functionality
