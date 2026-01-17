# Gift-EV Struktur - Berechenbare Komponenten

## 1. Basis-Roll (gleichverteilte Chance, 1/12 pro Item)

### Direkt Gem-wertige:
- **20-40 Gems** → Durchschnitt: 30 Gems
- **30-65 Gems** → Durchschnitt: 47.5 Gems

### Time-Boost (umrechenbar zu Gem-Äquivalent):
- **2-4 Blue Cow** → Jede Blue Cow = 16 min 2× Game Speed
  - Durchschnitt: 3 Blue Cows = 48 min 2× Speed
  - **Berechnung**: Ähnlich Founder Speed Boost → Zeitersparnis → mehr Freebies → Gem-Äquivalent
- **20-45 min 2× Game Speed** → Durchschnitt: 32.5 min 2× Speed
  - **Berechnung**: Direkt als Zeitersparnis umrechenbar

### Skill Shards:
- **2-5 Skill Shards** → Durchschnitt: 3.5 Skill Shards
  - **Berechnung**: 3.5 × 12.5 Gems = 43.75 Gems

### Obelisk Multiplier wirkt auf:
- **3-5 Relic Chests** → Durchschnitt: 4 Relic Chests (⚠️ Wert unbekannt)
- **10-15 Relic Chests** → Durchschnitt: 12.5 Relic Chests (⚠️ Wert unbekannt)
- **Gems** (werden multipliziert)
- **Skill Shards** (werden multipliziert)

### Andere (noch nicht berechenbar):
- 6-12 Primal Meat / 4-6 Sushi (nach Fishing)
- 10-15 Chaos Totem / 10-15 min 5× Fragment Gain (nach Archaeology)
- 60-120 min 2× Ore Income
- 25-40 Item Chests / 60-85 min 3× Golden Ore Multiplier
- 12-20 Charge Magnets / 10-15 min 5× Fishing Tick Chance +25%

## 2. Rare Rolls (sequenziell, spätere ersetzen frühere)

Diese Rollen werden **nacheinander** geprüft. Wenn eine triggert, ersetzt sie die Basis-Belohnung:

1. **1/20**: 60-90 min 2× Star Spawn Rate (Obelisk 23+) ⚠️ Wert unbekannt
2. **1/40**: 3 Gifts ✅ **Rekursiv** (3 × Gift-EV)
3. **1/45**: 80-130 Gems ✅ Durchschnitt: 105 Gems
4. **1/100**: 1 Mythic Chest ⚠️ Wert unbekannt
5. **1/37**: 4-8 Tier 2 Items (Obelisk 37+) ⚠️ Wert unbekannt
6. **1/30**: Drone Fuel (Obelisk Level × 1.5 bis Obelisk Level × 1.5 + 20) ⚠️ Wert unbekannt
7. **1/33**: 1-2 Idol Tokens (Obelisk 30+) ⚠️ Wert unbekannt
8. **1/45**: 15-24 Sushi (Obelisk 37+) ⚠️ Wert unbekannt
9. **1/175**: 50-60 Sushi (Obelisk 37+) ⚠️ Wert unbekannt
10. **1/200**: 1 Skin → **80-130 Gems** (wenn alle Skins vorhanden) ✅ Durchschnitt: 105 Gems
11. **1/2000**: 1 Gilded Skin → **25 Gifts** (wenn alle Gilded Skins vorhanden) ✅ **Rekursiv** (25 × Gift-EV)
12. **1/2500**: 1 Divine Chest ⚠️ Wert unbekannt

**Berechnung**: 
- Für jedes Rare Roll: Chance × Wert × (1 - Summe aller vorherigen Chancen, die getriggert haben könnten)
- Spätere Rolls haben niedrigere effektive Chance, weil frühere sie möglicherweise bereits ersetzt haben
- **Nach Rare Roll**: Obelisk Multiplier → Lucky Multiplier wird angewendet

## 3. Lucky Multiplier Rolls (separat, wirken auf alles außer Skins)

Diese sind **separate Rolls** (zwei unabhängige Würfel) und multiplizieren die **Mengen/Dauern** (nach Obelisk Multiplier):

- **1/20**: 3× Loot
- **1/2500**: 50× Loot

**Erwarteter Multiplikator** (für beide Rolls kombiniert):
Da es zwei separate Rolls sind:
- Beide Rolls treffen nicht: (19/20) × (2499/2500) = 0.9494 → 1×
- Nur 1. Roll (3×): (1/20) × (2499/2500) = 0.04994 → 3×
- Nur 2. Roll (50×): (19/20) × (1/2500) = 0.00038 → 50×
- Beide Rolls (150×): (1/20) × (1/2500) = 0.00002 → 150×

Erwarteter Multiplikator = 0.9494 × 1 + 0.04994 × 3 + 0.00038 × 50 + 0.00002 × 150
= 0.9494 + 0.14982 + 0.019 + 0.003
= **1.12122×**

**Wichtig**: 
- Wirkt auf **alle Mengen/Dauern** nach dem Obelisk Multiplier
- Reihenfolge: **Basis-Wert → × Obelisk Multiplier → × Lucky Multiplier → Verwendung**

## 4. Obelisk Level Multiplier

**Multiplier**: `1 + Obelisk Level × 0.08`

**Beispiel bei Obelisk Level 26**:
- Multiplier = 1 + 26 × 0.08 = **3.08×**

**Wirkt auf ALLE Mengen/Dauern** ✅:
- **Gems**: Anzahl × Multiplier (z.B. 20-40 Gems → 61.6-123.2 Gems)
- **Skill Shards**: Anzahl × Multiplier (z.B. 2-5 → 6.16-15.4)
- **Blue Cows**: Anzahl × Multiplier (z.B. 2-4 → 6.16-12.32)
- **2× Game Speed**: Dauer × Multiplier (z.B. 20-45 min → 61.6-138.6 min)
- **Relic Chests**: Anzahl × Multiplier
- **Gifts** (Rare Roll): Anzahl × Multiplier (z.B. 3 Gifts → 9.24 Gifts)
- **Alles andere**: Auch betroffen

**Wichtig**: Der Multiplier wird **direkt auf die Belohnungen angewendet**, bevor sie weiterverarbeitet werden!

## 5. Berechenbare Komponenten (Phase 1)

### Direkt berechenbar:
1. **Basis-Gems** (20-40, 30-65) → **ZUERST** × Obelisk Multiplier → dann Gem-Wert
2. **Rare-Roll Gems** (80-130) → **ZUERST** × Obelisk Multiplier → dann Gem-Wert
3. **Skill Shards** (2-5) → **ZUERST** × Obelisk Multiplier → dann zu Gems konvertiert
4. **Blue Cow** (2-4) → **ZUERST** × Obelisk Multiplier → dann (Anzahl × 16 min 2× Speed) → Zeitersparnis → Gem-Äquivalent
5. **2× Game Speed** (20-45 min) → **ZUERST** × Obelisk Multiplier → dann Zeitersparnis → Gem-Äquivalent
6. **Rekursive Gifts** (3 Gifts bei 1/40, 25 Gifts bei 1/2000) → **ZUERST** × Obelisk Multiplier → dann hängt von Gift-EV ab

### Berechnungsschritte:

**Berechnungsschritte** (Reihenfolge wichtig!):

**1. Basis-Roll EV** (vor Multiplikatoren):
- Gems (20-40): 1/12 × 30 Gems = 2.5 Gems
- Gems (30-65): 1/12 × 47.5 Gems = 3.96 Gems
- Skill Shards (2-5): 1/12 × 3.5 × 12.5 = 3.65 Gems
- Blue Cow (2-4): 1/12 × 3 × (16 min 2× Speed → Gem-Äquivalent)
- 2× Game Speed (20-45 min): 1/12 × 32.5 min → Gem-Äquivalent

**2. Rare Roll EV** (konditional, kann Basis-Roll ersetzen):
- 1/40 × (3 × Gift-EV) → aber Gift-EV hängt von sich selbst ab!
- 1/45 × 105 Gems = 2.33 Gems
- 1/200 × 105 Gems (wenn alle Skins) = 0.525 Gems
- 1/2000 × (25 × Gift-EV) → rekursiv

**3. Multiplikatoren anwenden** (Reihenfolge: Basis → Obelisk × → Lucky × → Verwendung):
- **Obelisk Multiplier**: Wirkt auf **alle** Mengen/Dauern (Gems, Skill Shards, Blue Cows, Time Boosts, Gifts, etc.)
- **Lucky Multiplier**: 1.121× (wirkt auf **alle** Mengen/Dauern nach Obelisk Multiplier)

**Wichtig**: 
- Beide Multiplikatoren werden **sequenziell** angewendet: Basis → × Obelisk → × Lucky
- Beispiel: 30 Gems → × 3.08 (Obelisk) → × 1.121 (Lucky) = 103.6 Gems

## 6. Besondere Herausforderungen

### Rekursive Gifts:
- 1/40: 3 Gifts
- 1/2000: 25 Gifts

**Lösung**: 
- Gift-EV = Basis-EV + Rare-EV (inkl. rekursiver Gifts)
- Mathematisch: `Gift-EV = A + B × Gift-EV` (wobei B der EV aus rekursiven Gifts ist)
- Aufgelöst: `Gift-EV = A / (1 - B)`

### Rare Roll Reihenfolge:
Da spätere Rolls frühere ersetzen, muss man die Wahrscheinlichkeiten korrekt berechnen:
- Roll 1 (1/20): Chance = 1/20
- Roll 2 (1/40): Effektive Chance = (19/20) × (1/40) = 19/800 = 0.02375
- Roll 3 (1/45): Effektive Chance = (19/20) × (39/40) × (1/45) = 741/36000 = 0.02058
- etc.

**Vereinfachung**: Wenn wir nur die wichtigsten Rare Rolls berücksichtigen (Gems, rekursive Gifts), können wir die anderen ignorieren oder als sehr kleine Beiträge behandeln.

## 7. Empfehlung für Berechnung

### Minimal (nur sicher berechenbar):
1. Basis-Gems (20-40, 30-65)
2. Skill Shards (2-5)
3. Rare-Roll Gems (80-130)
4. Blue Cow (2-4 × 16 min 2× Speed)
5. 2× Game Speed (20-45 min)
6. Obelisk Multiplier auf Gems/Skill Shards
7. Lucky Multiplier (1.1196×)
8. Rekursive Gifts (vereinfacht: als konstanter Multiplikator behandeln oder iterativ lösen)

### Ignorieren (erstmal):
- Relic Chests (Wert unbekannt)
- Item Chests, Tier 2 Items, Sushi, etc. (Wert unbekannt)
- Seltene Rare Rolls ohne Gems (Mythic Chest, Divine Chest, etc.)
- Time Boosts ohne bekannten Mechanismus (2× Star Spawn Rate, Fragment Gain, etc.)