# Archaeology Simulator - Feature Documentation

This document describes the Archaeology Simulator feature and its planned implementation.

## Overview

The Archaeology Simulator is a tool to simulate archaeology dig results and calculate expected values for the Obelisk game.

## Current Status

**Status**: Skeleton/Placeholder implemented

The basic window structure is in place. The actual simulation logic needs to be implemented based on the game mechanics described below.

## Planned Features

### Input Parameters

- [ ] Number of dig attempts
- [ ] Current archaeology level
- [ ] Available resources/currency
- [ ] Unlock status of various artifacts

### Simulation Options

- [ ] Single dig simulation
- [ ] Bulk simulation (1000+ digs)
- [ ] Expected value calculation
- [ ] Probability distribution display

### Results Display

- [ ] Average gems per dig
- [ ] Rare item drop rates
- [ ] Statistical breakdown with charts
- [ ] Confidence intervals

### Strategy Recommendations

- [ ] Optimal dig timing
- [ ] Resource allocation suggestions
- [ ] Break-even analysis

## Game Mechanics to Implement

*Please provide the following information to complete the implementation:*

### Basic Dig Mechanics

1. **Cost per dig**: What resources are required?
2. **Base rewards**: What are the possible outcomes?
3. **Probability distribution**: What are the chances for each outcome?

### Modifiers

1. **Level bonuses**: How does archaeology level affect rewards?
2. **Multipliers**: Are there any active multipliers?
3. **Special events**: Any timed bonuses?

### Rare Drops

1. **Artifact types**: What rare items can be found?
2. **Drop rates**: What are the probabilities?
3. **Value conversion**: How to convert to gem-equivalent?

## Technical Notes

### Window Class

`ArchaeologySimulatorWindow` in `gui.py`

- Follows the same pattern as `OptionAnalyzerWindow`
- Uses modern tooltip styling from DESIGN_GUIDELINES.md
- Resizable window with minimum size 650x500

### Integration

- Button in main window header (next to Lootbug button)
- Uses gem.png as temporary icon (can be replaced)
- Receives calculator instance from main GUI

## How to Use (Future)

1. Click the Archaeology button in the main window
2. Configure simulation parameters
3. Run simulation
4. View results and recommendations

## Contributing

To implement the full feature:

1. Document the exact game mechanics (see sections above)
2. Implement the probability calculations in `freebie_ev_calculator.py`
3. Build the GUI components in `ArchaeologySimulatorWindow`
4. Add unit tests for the calculations

## Version History

- **v0.1** (2026-01-20): Initial skeleton implementation


Infos von ChatGPT dazu:
README — Obelisk Idle Miner
Archaeology: Progression, Damage & Upgrade-Entscheidungen (Early Game)

Diese Datei fasst alle aktuell bekannten Regeln, Annahmen und Entscheidungsheuristiken zur Archaeology-Mechanik zusammen.
Ziel ist es, für jeden Zeitpunkt entscheiden zu können, welcher +1 Punkt (Skill oder Upgrade) den größten prozentualen Progress bringt.

1. Grunddefinition: Was ist „Progress“?

Im aktuellen Early Game ist Progress primär:

Blöcke / Floors pro Run

Tiefe (Unlock neuer Floors → neue Block-Tiers)

Sekundär (aber wichtig):

XP pro Zeit (Archaeology Level)

Fragments / Loot (später relevant)

Wichtig:
XP, Loot oder Mods bringen keinen Fortschritt, wenn du Floors nicht erreichst, die neue Tiers freischalten.

2. Harte Spielregeln (fix)
Combat & Ressourcen

1 Schlag = 1 Stamina

1 Schlag = 1 Sekunde

Aktuell: 1 Schlag / Sekunde

Aktueller Stamina-Pool: 100

Run endet sofort, wenn Stamina = 0

➡️ Ein Run besteht effektiv aus 100 Schlägen.

Damage & Defense (sehr wichtig)

Schaden ist integer

Es gibt keine Dezimalwerte

Effektiver Schaden wird abgerundet

Formel:

effective_damage = max(1, floor(damage − armor + armor_pen))


➡️ Das erzeugt Breakpoints
(+1 Schaden kann +20 % realen DPS bedeuten)

3. Enrage (Rage)

Triggert alle 60 Sekunden

Betrifft die nächsten 5 Schläge

Effekte:

+20 % Damage

+100 % Crit Damage

Wichtige Konsequenz

Enrage wirkt nur auf 5 von 60 Schlägen → 8.33 % Uptime

Ohne Crit Chance ist der Crit-Teil wertlos

Ohne Crit:

Enrage ≈ +1.67 % DPS

➡️ Enrage ist EARLY kein Build-Definer
Es skaliert erst, wenn Crit Chance steigt.

4. Aktueller Block-Pool (Status quo)

Du bist aktuell effektiv bei Floor 1 und schaffst noch nicht alle Blöcke.

Annahme (realistisch):

50 % Tier 1 Dirt

50 % Tier 1 Common

Blockwerte

Tier 1 Dirt

HP: 100

Armor: 0

Tier 1 Common

HP: 250

Armor: 5

5. Spawn-Logik (warum Tiefe so wichtig ist)

Neue Blocktypen erscheinen erst ab bestimmten Floors:

Tier 1 Rare: ab Floor 3

Tier 1 Epic: ab Floor 6

Tier 1 Legendary: ab Floor 12

Tier 1 Mythic: ab Floor 20

➡️ Solange du Floor 1–2 nicht zuverlässig schaffst, existieren viele Systeme praktisch nicht.

6. Aktueller Spielerstatus (zusammengeführt)

Base Damage: 10

Bonus Base Damage: +1

Armor Penetration: +2

Crit Chance: ~0 %

Stamina: 100

Effektive Armor

Dirt: 0

Common: 5 − 2 = 3

7. Skillpunkte (Archaeology Level)
Strength

+1 Flat Damage

+1 % Damage

+3 % Crit Damage (nur relevant mit Crit Chance)

Agility

+5 Max Stamina

+1 % Crit Chance

+0.20 % Speed Mod Chance

Intellect

+5 % Archaeology XP

+0.30 % Exp Mod Chance

Perception

+4 % Fragment Gain

+0.30 % Loot Mod Chance

+2 Armor Penetration

Luck

+2 % Crit Chance

+0.20 % All Mod Chances

+0.04 % One-Hit Chance

8. Upgrade-Routen (früh verfügbar)

Aktuell realistisch verfügbar:

Flat Damage +1

Armor Penetration +1

Viele andere Upgrades sind an Stage/Floor gebunden
(„Stage“ entspricht hier faktisch Floor-Progress).

9. Warum Strength im Early Game dominiert
Zentrale Einsicht

Stamina ist ein harter Cap →
Progress = Blöcke pro 100 Schläge

Strength:

reduziert Hits pro Block

reduziert Zeit pro Block

reduziert Stamina pro Block

Beispiel (Common Block)

Effektiver Schaden: 5

+1 Damage → 6
➡️ +20 % DPS gegen Common

➡️ Dieser Effekt wirkt gleichzeitig auf:

Tiefe

XP pro Run

Mods pro Zeit

Enrage-Nutzen (indirekt)

10. Flat Damage vs Armor Penetration
Flat Damage

Wirkt auf alle Blocks

Extrem stark bei:

niedrigem Damage

integer Breakpoints

Dirt + Common Dominanz

Armor Penetration

Wirkt nur, wenn Armor > 0

Kein Effekt auf Dirt

Wird stark, wenn:

Rare / Epic Blocks erscheinen

Armor ≥ 12

Damage bereits hoch ist

Faustregel:

Early: Flat Damage > Armor Pen

Mid: Mix

Later: Armor Pen skaliert besser

11. Agility & Enrage – richtige Einordnung

Agility ist der erste Enrage-Enabler, weil es Crit Chance gibt

Aber:

Enrage betrifft nur 5 Schläge

1 % Crit = sehr kleiner Effekt

+5 Stamina ≈ +5 % Tiefe

➡️ Agility ist gut, aber kein Early-Carry

12. Intellect – wann sinnvoll?

Intellect erhöht nur XP

Keine Auswirkung auf:

Hits pro Block

Tiefe

Unlocks

➡️ Sinnvoll erst, wenn:

Floor-Progress nicht mehr bottlenecked

du stabil tief bist

13. Allgemeines Entscheidungsprinzip (immer gültig)

Für jeden +1 Punkt gilt:

Rechne effektiven Schaden neu

Rechne Hits pro Block neu

Rechne Blöcke pro Run neu

Vergleiche %-Änderung

Primärer KPI:

% mehr Blöcke pro Run

Sekundär:

XP-Multiplikatoren

14. Aktuelle Empfehlung (Status jetzt)

Du bist Level 3, hast:

+1 Base Damage

+2 Armor Pen

➡️ 3× Strength ist aktuell optimal

Warum:

Du willst Floor 1 zuverlässig clearen

Du willst schnell zu Floor 3 → Rare freischalten

Strength nutzt:

integer damage

armor pen

stamina cap

Nächster Umschaltpunkt:

sobald Rare-Blocks dominieren

oder du Floor 1 problemlos schaffst

Dann:

Agility oder Perception neu bewerten

15. Mentales Kurzmodell

Early Game = Damage reduziert Stamina-Kosten
Mid Game = Mods + Speed verlängern Runs
Late Game = Crit, Enrage, Scaling


Archaeology – Charakterwerte auf Level 1
Grundstatus

Archaeology Level: 1

Highest Stage: 1

Max Stamina: 100

Current Stamina: 30 (situativ, nicht relevant für Baseline)

Kampfwerte

Damage: 10

Armor Penetration: 0

Attack Speed: 1 / sec

Crit Chance: 0%

Crit Damage: 1.50×

One-Hit-KO Chance: 0%

Ability Instacharge: 0%

XP / Loot / Mods

Experience Gain: 1×

Fragment Gain: 1×

Experience Mods

Exp Mod Chance: 0%

Exp Mod Gain: 3×

Loot Mods

Loot Mod Chance: 0%

Loot Mod Gain: 2×

Speed Mods

Speed Mod Chance: 0%

Speed Mod Gain: +10

Speed Mod Attack Rate: 2×

Stamina Mods

Stamina Mod Chance: 0%

Stamina Mod Gain: +3


Enrage auf Level 1

Mit diesen Stats bedeutet Enrage:

+20% Damage für 5 Hits

+100% Crit Damage → irrelevant, da Crit Chance = 0%