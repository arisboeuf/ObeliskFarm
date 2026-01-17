# Gift-EV Analyse - Welche Komponenten sind für Gem EV relevant?

## 1. Direkt Gem-wertige Belohnungen

### Basis-Roll (gleichverteilt, 1/12 Chance pro Item):
- **20-40 Gems** ✅ Direkter Wert
- **30-65 Gems** ✅ Direkter Wert
- **2-5 Skill Shards** ✅ Konvertierbar (1 Skill Shard = 12.5 Gems laut Freebie-EV)
- **3-5 Relic Chests** ⚠️ Potenziell wertvoll, aber kein direkter Gem-Wert
- **10-15 Relic Chests** ⚠️ Potenziell wertvoll, aber kein direkter Gem-Wert

### Zusätzliche Rolls:
- **80-130 Gems** (1/45 Chance) ✅ Direkter Wert
- **80-130 Gems** (1/200 Chance, wenn alle Skins vorhanden) ✅ Direkter Wert
- **25 Gifts** (1/2000 Chance, wenn alle Gilded Skins vorhanden) ✅ Rekursiver Wert (muss berechnet werden)

## 2. Indirekt Gem-wertige Belohnungen (müssen geschätzt werden)

### Item-basierte Belohnungen:
- **25-40 Item Chests** ⚠️ Wert unbekannt (kein direkter Gem-Wert bekannt)
- **3-5 Tier 2 Items** (nach Fishing-Unlock, 1/37 bei Obelisk 37+) ⚠️ Wert unbekannt
- **4-8 Tier 2 Items** (1/37 bei Obelisk 37+) ⚠️ Wert unbekannt

### Chest-basierte Belohnungen:
- **1 Mythic Chest** (1/100 Chance) ⚠️ Wert unbekannt (höchstwahrscheinlich sehr wertvoll)
- **1 Divine Chest** (1/2500 Chance) ⚠️ Wert unbekannt (extrem wertvoll, sehr selten)

### Resource-basierte Belohnungen:
- **2-4 Blue Cow** → **3-5 Tier 2 Items** (nach Fishing-Unlock) ⚠️ Wert unbekannt
- **6-12 Primal Meat** → **4-6 Sushi** (nach Fishing-Unlock) ⚠️ Wert unbekannt
- **15-24 Sushi** (1/45 bei Obelisk 37+) ⚠️ Wert unbekannt
- **50-60 Sushi** (1/175 bei Obelisk 37+) ⚠️ Wert unbekannt

### Time-Boost Belohnungen:
- **60-120 min 2x Ore Income** ⚠️ Muss in Gem-Äquivalent umgerechnet werden (wie viel wert ist 2× Ore Income?)
- **20-45 min 2x Game Speed** ⚠️ Muss in Gem-Äquivalent umgerechnet werden (ähnlich wie Founder Speed Boost)
  → **1500-2750 Cherry Charges × (Obelisk Level - 36) / 6** (bei World 3 Monument) ⚠️ Wert unbekannt
- **60-90 min 2x Star Spawn Rate** (1/20, Obelisk 23+) ⚠️ Wert unbekannt
- **10-15 min 5x Fragment Gain** (nach Archaeology-Unlock) ⚠️ Wert unbekannt
- **60-85 min 3x Golden Ore Multiplier** (nach 5% Golden Ore Chance) ⚠️ Wert unbekannt
- **10-15 min 5x Fishing Tick Chance +25%** (nach Fishing-Unlock) ⚠️ Wert unbekannt

### Andere Belohnungen:
- **10-15 Chaos Totem** → **10-15 min 5x Fragment Gain** (nach Archaeology-Unlock) ⚠️ Wert unbekannt
- **12-20 Charge Magnets** → **10-15 min 5x Fishing Tick Chance +25%** (nach Fishing-Unlock) ⚠️ Wert unbekannt
- **Drone Fuel: Obelisk Level × 1.5 bis Obelisk Level × 1.5 + 20** (1/30, Obelisk 18+) ⚠️ Wert unbekannt
- **1-2 Idol Tokens** (1/33, Obelisk 30+) ⚠️ Wert unbekannt
- **1 Skin** (1/200, kann nicht dupliziert werden) ❌ Kein direkter Gem-Wert (kosmetisch)
- **1 Gilded Skin** (1/2000, kann nicht dupliziert werden) ❌ Kein direkter Gem-Wert (kosmetisch)

## 3. Obelisk Level Multiplier

**Multiplier**: `1 + Obelisk Level × 0.08`

Betrifft:
- **Relic Chests** (wird mit Multiplier multipliziert)
- **Gems** (wird mit Multiplier multipliziert)
- **Skill Shards** (wird mit Multiplier multipliziert)

**Beispiel bei Obelisk Level 26**:
- Multiplier = 1 + 26 × 0.08 = 1 + 2.08 = **3.08×**

## 4. Multiplikator-Rolls (wirken auf alle obigen Belohnungen außer Skins)

- **1/20 Chance**: 3× Loot
- **1/2500 Chance**: 50× Loot

**Erwarteter Multiplikator**:
= (19/20 × 1) + (1/20 × 3) + (1/2500 × 50)
= 0.95 + 0.15 + 0.02
= **1.17×** (vereinfacht, da die 50× selten ist)

**Präziser**:
- Kein Multiplikator: 1 - 1/20 - 1/2500 = 0.9496 (94.96%)
- 3× Multiplikator: 1/20 = 0.05 (5%)
- 50× Multiplikator: 1/2500 = 0.0004 (0.04%)

Erwarteter Multiplikator = 0.9496 × 1 + 0.05 × 3 + 0.0004 × 50 = 0.9496 + 0.15 + 0.02 = **1.1196×**

## 5. Zusammenfassung: Gem EV relevante Komponenten

### ✅ Direkt berechenbar:
1. **Gems** (20-40, 30-65, 80-130) - mit Obelisk Multiplier
2. **Skill Shards** (2-5) - mit Obelisk Multiplier, konvertierbar zu Gems

### ⚠️ Braucht Annahmen/Schätzungen:
3. **Relic Chests** (3-5, 10-15) - mit Obelisk Multiplier, aber kein bekannter Gem-Wert
4. **Time Boosts** (2× Speed, 2× Ore Income, etc.) - ähnlich wie Founder Speed Boost berechenbar
5. **Rekursive Gifts** (25 Gifts bei 1/2000) - hängt vom Gift-EV ab

### ❌ Nicht direkt Gem-wertig:
6. **Skins** - kosmetisch, kein direkter Spielwert
7. **Items/Chests ohne bekannten Wert** - müsste man schätzen oder ignorieren

### 🔄 Mechanik-Komplexität:
- **Basis-Roll**: Gleichverteilte Chance (1/12 pro Item, aber Liste hat mehr Items - genau zählen!)
- **Zusätzliche Rolls**: Sequentielle Prüfungen, spätere ersetzen frühere (konditionale Wahrscheinlichkeiten)
- **Obelisk Multiplier**: Nur für Relic Chests, Gems, Skill Shards
- **Loot Multiplier**: 3× oder 50× (wirkt auf alle außer Skins)

## 6. Empfehlung für Implementierung

### Phase 1: Minimale Implementierung (nur direkt berechenbar)
- Gems (alle Varianten)
- Skill Shards
- Obelisk Multiplier
- Loot Multiplier (3×, 50×)

### Phase 2: Erweiterte Implementierung (mit Schätzungen)
- Relic Chests (z.B. 1 Relic Chest = X Gems schätzen)
- Time Boosts (2× Speed = ähnlich Founder Speed Boost berechnen)
- Rekursive Gifts (25 Gifts = 25 × Gift-EV)

### Phase 3: Volle Implementierung (wenn Werte bekannt)
- Alle Item/Chest-Typen
- Alle Time-Boosts mit genauen Werten
- Alle Resource-basierten Belohnungen